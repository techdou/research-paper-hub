from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib import (
    CONFIG_DIR,
    artifact_types,
    capability_version,
    dedupe_keep_order,
    detect_venue_family,
    load_json,
    load_yaml,
    project_paths,
    source_for_skill,
)


@dataclass
class Match:
    intent: str
    score: int
    signals: list[str]


def _match_intents(task: str, routing: dict[str, Any]) -> list[Match]:
    lower = task.lower()
    matches: list[Match] = []
    for intent, spec in routing.get("intents", {}).items():
        signals = [p for p in spec.get("triggers", []) if str(p).lower() in lower]
        if not signals:
            continue
        priority = int(spec.get("priority", 0))
        specificity = sum(len(str(s)) for s in signals)
        matches.append(Match(intent, priority * 1000 + specificity, signals))
    matches.sort(key=lambda x: x.score, reverse=True)
    return matches


def _default_intent(task: str) -> str:
    lower = task.lower()
    if any(k in lower for k in ["论文", "paper", "稿件", "manuscript"]):
        return "manuscript_write"
    return "literature_discovery"


def _owner(intent: str, spec: dict[str, Any], family: str, routing: dict[str, Any]) -> str | None:
    dyn = spec.get("dynamic_owner")
    if dyn:
        return routing.get("families", {}).get(family, {}).get(dyn)
    return spec.get("owner")


def _blocked(owner: str | None, spec: dict[str, Any], routing: dict[str, Any]) -> list[str]:
    blocked = list(spec.get("blocked", []))
    fam = spec.get("blocked_family")
    if fam:
        blocked.extend(x for x in routing.get("collision_families", {}).get(fam, []) if x != owner)
    return sorted(set(blocked))


def _needs_exemplar_before_write(task: str, matches: list[Match]) -> bool:
    intents = {m.intent for m in matches}
    return "paper_exemplar" in intents and "manuscript_write" in intents


def _order_intents(intents: list[str]) -> list[str]:
    preferred = [
        "skill_sync",
        "literature_discovery", "paper_download", "paper_read", "paper_card", "paper_exemplar",
        "opportunity_gap", "idea_review", "idea_optimize", "experiment_design", "experiment_log",
        "method_figure", "results_figure", "manuscript_write", "manuscript_review",
        "integrity_audit", "reference_verify", "language_polish", "submission_check",
        "response_rebuttal", "group_meeting_ppt", "project_archive", "literature_monitor",
    ]
    rank = {name: i for i, name in enumerate(preferred)}
    return sorted(dedupe_keep_order(intents), key=lambda x: rank.get(x, 999))


def _dependency_bundle(skill: str | None, caps: dict[str, Any], research: Path) -> list[dict[str, Any]]:
    if not skill or skill == "research-paper-hub":
        return []
    source = source_for_skill(skill, caps)
    if not source:
        return []
    spec = caps.get("sources", {}).get(source, {})
    cmap = spec.get("capabilities", {})
    queue = list(spec.get("support_dependencies", [])) + [skill]
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    while queue:
        item = queue.pop(0)
        if item in seen:
            continue
        seen.add(item)
        out.append({
            "source": source,
            "skill": item,
            "capability_version": capability_version(research, item),
        })
        queue.extend(cmap.get(item, {}).get("dependencies", []))
    return out


def route_task(task: str, research: Path) -> dict[str, Any]:
    routing = load_yaml(CONFIG_DIR / "routing.yaml")
    caps = load_yaml(CONFIG_DIR / "capabilities.yaml")
    paths = project_paths(research)
    state = load_json(paths["state"], {})
    profile = load_yaml(paths["profile"])
    family = detect_venue_family(state.get("target_venue"), profile, routing)
    existing = artifact_types(research)
    matches = _match_intents(task, routing)
    if not matches:
        matches = [Match(_default_intent(task), 0, [])]

    selected = [m.intent for m in matches]

    # Avoid interpreting generic PPT/presentation signals as a research-PPT intent unless the task is paper/research scoped.
    if "group_meeting_ppt" in selected and not any(k in task.lower() for k in ["paper", "论文", "组会", "讨论班", "research"]):
        selected.remove("group_meeting_ppt")

    # Explicit exemplar + writing is a two-step bridge; preserve both.
    if _needs_exemplar_before_write(task, matches):
        selected = [x for x in selected if x in {"paper_exemplar", "manuscript_write", "paper_read"}]

    # For a PPT request, reading/card are prerequisites and should not be duplicated merely because words like paper appear.
    if "group_meeting_ppt" in selected:
        selected = [x for x in selected if x not in {"manuscript_write"}]

    ordered = _order_intents(selected)
    steps: list[dict[str, Any]] = []
    inserted: set[str] = set()

    def add_step(intent: str, reason: str | None = None) -> None:
        if intent in inserted:
            return
        spec = routing.get("intents", {}).get(intent, {})
        prerequisite = spec.get("prerequisite_intent")
        required = set(spec.get("requires_any", []))
        if prerequisite and required and not (required & existing):
            add_step(prerequisite, f"Prerequisite for {intent}")
            # Account for artifact produced by inserted prerequisite within this plan.
            existing.update(routing.get("intents", {}).get(prerequisite, {}).get("outputs", []))

        owner = _owner(intent, spec, family, routing)
        source = "internal" if owner == "research-paper-hub" else (source_for_skill(owner, caps) if owner else None)
        audit_skills = list(spec.get("audit", []))
        preflight_skills: list[str] = []
        if intent == "manuscript_write":
            pf = routing.get("families", {}).get(family, {}).get("writer_preflight")
            if pf:
                preflight_skills.append(pf)
        bundle: list[dict[str, Any]] = []
        seen_bundle: set[tuple[str | None, str]] = set()
        for selected_skill in [owner] + preflight_skills + audit_skills:
            for item in _dependency_bundle(selected_skill, caps, research):
                key = (item.get("source"), item["skill"])
                if key not in seen_bundle:
                    seen_bundle.add(key)
                    bundle.append(item)
        step = {
            "step": len(steps) + 1,
            "intent": intent,
            "primary": {"source": source, "skill": owner},
            "preflight": [
                {"source": source_for_skill(s, caps), "skill": s, "capability_version": capability_version(research, s)}
                for s in preflight_skills
            ],
            "audit": [
                {"source": source_for_skill(s, caps), "skill": s, "capability_version": capability_version(research, s)}
                for s in audit_skills
            ],
            "playbook_bundle": bundle,
            "blocked_competitors": _blocked(owner, spec, routing),
            "expected_artifacts": spec.get("outputs", []),
            "reason": reason or "Matched the requested artifact/operation and applied one-owner routing.",
            "capability_version": capability_version(research, owner) if owner and owner != "research-paper-hub" else None,
        }
        steps.append(step)
        inserted.add(intent)
        existing.update(spec.get("outputs", []))

    for intent in ordered:
        add_step(intent)

    return {
        "task": task,
        "stage": state.get("stage", "seed"),
        "venue_family": family,
        "target_venue": state.get("target_venue"),
        "matched": [{"intent": m.intent, "signals": m.signals, "score": m.score} for m in matches],
        "steps": steps,
        "archive_after": any(s["intent"] in {
            "paper_exemplar", "experiment_design", "manuscript_write", "manuscript_review",
            "response_rebuttal", "submission_check"
        } for s in steps),
        "assumptions": [],
    }
