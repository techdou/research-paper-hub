#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from archive import create_snapshot
from lib import load_json, research_root
from project import create_run, init_project, register_artifact, register_claim, register_revision, set_state
from router import route_task
from sync import apply_updates, check_updates, rollback_skill
from validate import validate_project, validate_skill_format


def emit(obj, fmt: str = "yaml") -> None:
    if fmt == "json":
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        return
    import yaml
    print(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True).rstrip())


def main() -> int:
    p = argparse.ArgumentParser(prog="research-paper-hub", description="Single-front-door router/orchestrator for paper research workflows")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="initialize persistent .research state")
    s.add_argument("project", type=Path)
    s.add_argument("--profile", type=Path)
    s.add_argument("--title")

    s = sub.add_parser("route", help="build a conflict-free multi-step execution plan")
    s.add_argument("--project", type=Path, required=True)
    s.add_argument("--task", required=True)
    s.add_argument("--plan-run", action="store_true")
    s.add_argument("--format", choices=["yaml", "json"], default="yaml")

    s = sub.add_parser("status")
    s.add_argument("--project", type=Path, required=True)

    s = sub.add_parser("sync", help="check/apply/rollback upstream skill playbooks")
    s.add_argument("--project", type=Path, required=True)
    mode = s.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    s.add_argument("--skill", action="append", default=[])
    s.add_argument("--recommended", action="store_true")
    s.add_argument("--format", choices=["yaml", "json"], default="yaml")

    s = sub.add_parser("snapshot")
    s.add_argument("--project", type=Path, required=True)
    s.add_argument("--note", default="")

    s = sub.add_parser("revision")
    s.add_argument("--project", type=Path, required=True)
    s.add_argument("--file", type=Path, required=True)
    s.add_argument("--note", default="")

    s = sub.add_parser("artifact")
    s.add_argument("--project", type=Path, required=True)
    s.add_argument("--file", type=Path, required=True)
    s.add_argument("--type", required=True)
    s.add_argument("--producer")
    s.add_argument("--run-id")

    s = sub.add_parser("claim")
    s.add_argument("--project", type=Path, required=True)
    s.add_argument("--text", required=True)
    s.add_argument("--id")
    s.add_argument("--status", default="proposed", choices=["proposed", "supported", "partially_supported", "unsupported", "retired"])

    s = sub.add_parser("set")
    s.add_argument("--project", type=Path, required=True)
    s.add_argument("--venue")
    s.add_argument("--stage")
    s.add_argument("--writing-family", choices=["cs", "nature"])

    s = sub.add_parser("validate")
    s.add_argument("--project", type=Path, required=True)

    sub.add_parser("validate-skill", help="validate Agent Skills metadata/layout constraints")

    a = p.parse_args()

    if a.cmd == "init":
        r = init_project(a.project, a.profile, a.title)
        print(f"Initialized: {r}")
        return 0
    if a.cmd == "validate-skill":
        result = validate_skill_format()
        emit(result)
        return 0 if result["ok"] else 2

    research = research_root(a.project)

    if a.cmd == "route":
        plan = route_task(a.task, research)
        if a.plan_run:
            plan["planned_run"] = create_run(research, a.task, plan)["run_id"]
        emit(plan, a.format)
        return 0
    if a.cmd == "status":
        emit(load_json(research / "state.json", {}))
        return 0
    if a.cmd == "sync":
        if a.rollback:
            if len(a.skill) != 1:
                raise SystemExit("--rollback requires exactly one --skill")
            result = rollback_skill(research, a.skill[0])
        elif a.apply:
            result = apply_updates(research, skills=a.skill or None, recommended=a.recommended)
        else:
            result = check_updates(research, skills=a.skill or None, recommended=a.recommended)
        emit(result, a.format)
        return 0
    if a.cmd == "snapshot":
        emit(create_snapshot(research, a.note))
        return 0
    if a.cmd == "revision":
        emit(register_revision(research, a.file, a.note))
        return 0
    if a.cmd == "artifact":
        emit(register_artifact(research, a.file, a.type, a.producer, a.run_id))
        return 0
    if a.cmd == "claim":
        emit(register_claim(research, a.text, a.status, a.id))
        return 0
    if a.cmd == "set":
        emit(set_state(research, venue=a.venue, stage=a.stage, writing_family=a.writing_family))
        return 0
    if a.cmd == "validate":
        result = validate_project(research)
        emit(result)
        return 0 if result["ok"] else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
