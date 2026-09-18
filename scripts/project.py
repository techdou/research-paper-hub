from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from lib import (
    SKILL_ROOT,
    append_jsonl,
    compact_timestamp,
    dump_json,
    dump_yaml,
    load_json,
    load_yaml,
    project_paths,
    research_root,
    sha256_file,
    slugify,
    utcnow,
)

VALID_STAGES = [
    "seed", "discovery", "reading", "framing", "experiment_design", "experimentation",
    "evidence_ready", "drafting", "internal_review", "revision", "submission_ready",
    "submitted", "rebuttal", "accepted", "archive",
]


def init_project(project: Path, profile: Path | None = None, title: str | None = None) -> Path:
    project = project.expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    research = research_root(project, require=False)
    paths = project_paths(research)
    for p in [paths["runs"], paths["manuscript_current"], paths["manuscript_history"], paths["snapshots"], paths["vendor"], paths["vendor_history"], paths["overrides"]]:
        p.mkdir(parents=True, exist_ok=True)
    for p in [paths["artifacts"], paths["papers"], paths["claims"], paths["exemplars"], paths["reviews"]]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch(exist_ok=True)

    if not paths["profile"].exists():
        src = profile or (SKILL_ROOT / "assets" / "project-profile.template.yaml")
        data = load_yaml(src)
        if title:
            data.setdefault("project", {})["title"] = title
        dump_yaml(data, paths["profile"])

    if not paths["state"].exists():
        prof = load_yaml(paths["profile"])
        pconf = prof.get("project", {})
        now = utcnow()
        state = {
            "project_id": slugify(title or pconf.get("title") or project.name),
            "title": title or pconf.get("title") or project.name,
            "stage": "seed",
            "target_venue": pconf.get("target_venue") or None,
            "primary_writing_family": pconf.get("primary_writing_family") or "cs",
            "created_at": now,
            "updated_at": now,
            "active_manuscript_revision": None,
            "last_run_id": None,
        }
        dump_json(state, paths["state"])

    if not paths["lock"].exists():
        dump_json({"version": 2, "skills": {}, "sources": {}, "updated_at": None}, paths["lock"])
    return research


def create_run(research: Path, task: str, plan: dict[str, Any]) -> dict[str, Any]:
    run_id = f"{compact_timestamp()}-{plan['steps'][0]['intent'] if plan.get('steps') else 'task'}"
    run = {
        "run_id": run_id,
        "task": task,
        "status": "planned",
        "steps": plan.get("steps", []),
        "inputs": [],
        "outputs": [],
        "assumptions": plan.get("assumptions", []),
        "started_at": utcnow(),
        "finished_at": None,
        "notes": None,
    }
    dump_json(run, research / "runs" / f"{run_id}.json")
    state = load_json(project_paths(research)["state"], {})
    state["last_run_id"] = run_id
    state["updated_at"] = utcnow()
    dump_json(state, project_paths(research)["state"])
    return run


def register_artifact(research: Path, path: Path, artifact_type: str, producer: str | None = None, run_id: str | None = None, inputs: list[str] | None = None) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    record = {
        "artifact_id": f"{artifact_type}-{compact_timestamp()}-{uuid.uuid4().hex[:6]}",
        "type": artifact_type,
        "path": str(path),
        "producer": producer,
        "run_id": run_id,
        "inputs": inputs or [],
        "sha256": sha256_file(path) if path.is_file() else None,
        "created_at": utcnow(),
        "tags": [],
    }
    append_jsonl(record, project_paths(research)["artifacts"])
    return record


def register_claim(research: Path, text: str, status: str = "proposed", claim_id: str | None = None) -> dict[str, Any]:
    record = {
        "claim_id": claim_id or f"C-{compact_timestamp()}",
        "claim": text,
        "status": status,
        "prior_art": [],
        "experiments": [],
        "results": [],
        "figures_tables": [],
        "sections": [],
        "updated_at": utcnow(),
    }
    append_jsonl(record, project_paths(research)["claims"])
    return record


def register_revision(research: Path, source: Path, note: str = "") -> dict[str, Any]:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    paths = project_paths(research)
    rev_id = f"rev-{compact_timestamp()}"
    history = paths["manuscript_history"] / rev_id
    history.mkdir(parents=True, exist_ok=False)
    hist_file = history / source.name
    shutil.copy2(source, hist_file)
    current = paths["manuscript_current"]
    current.mkdir(parents=True, exist_ok=True)
    for p in current.iterdir():
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    cur_file = current / source.name
    shutil.copy2(source, cur_file)
    meta = {
        "revision_id": rev_id,
        "created_at": utcnow(),
        "file": str(cur_file),
        "history_file": str(hist_file),
        "sha256": sha256_file(hist_file),
        "note": note,
    }
    dump_json(meta, history / "revision.json")
    state = load_json(paths["state"], {})
    state["active_manuscript_revision"] = rev_id
    if state.get("stage") in VALID_STAGES[:7]:
        state["stage"] = "drafting"
    state["updated_at"] = utcnow()
    dump_json(state, paths["state"])
    return meta


def set_state(research: Path, *, venue: str | None = None, stage: str | None = None, writing_family: str | None = None) -> dict[str, Any]:
    state = load_json(project_paths(research)["state"], {})
    if venue is not None:
        state["target_venue"] = venue or None
    if stage is not None:
        if stage not in VALID_STAGES:
            raise ValueError(f"invalid stage: {stage}")
        state["stage"] = stage
    if writing_family is not None:
        if writing_family not in {"cs", "nature"}:
            raise ValueError("writing_family must be cs or nature")
        state["primary_writing_family"] = writing_family
    state["updated_at"] = utcnow()
    dump_json(state, project_paths(research)["state"])
    return state
