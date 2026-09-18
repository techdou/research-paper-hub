from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import load_json, load_yaml, project_paths
from project import init_project, register_artifact, set_state
from router import route_task
from sync import apply_updates, check_updates, rollback_skill
from validate import validate_project, validate_skill_format


def _intents(plan):
    return [s["intent"] for s in plan["steps"]]


def test_format():
    out = validate_skill_format(ROOT)
    assert out["ok"], out
    assert out["metadata"]["name"] == "research-paper-hub"


def test_router_and_reuse(tmp: Path):
    project = tmp / "paper"
    research = init_project(project, ROOT / "examples" / "remote-sensing-profile.yaml", "demo")

    plan = route_task("找一篇最近的多模态多标签遥感论文，精读后做组会汇报", research)
    assert _intents(plan) == ["literature_discovery", "paper_read", "paper_card", "group_meeting_ppt"], plan

    plan = route_task("拿这篇 TGRS 论文的写法当模板，重构我的 Introduction", research)
    assert _intents(plan) == ["paper_read", "paper_exemplar", "manuscript_write"], plan
    assert plan["steps"][-1]["primary"]["skill"] == "ccf-paper-writer"
    assert "nature-writing" in plan["steps"][-1]["blocked_competitors"]

    reader = tmp / "reader.md"
    reader.write_text("reader", encoding="utf-8")
    register_artifact(research, reader, "reader_artifact", "nature-reader")
    plan = route_task("把这篇论文做成写作范文", research)
    assert _intents(plan) == ["paper_exemplar"], plan

    set_state(research, venue="Nature Communications", writing_family="nature")
    plan = route_task("帮我写论文 Introduction", research)
    assert _intents(plan) == ["manuscript_write"]
    assert plan["steps"][0]["primary"]["skill"] == "nature-writing"

    plan = route_task("检查 CCFA 和 nature 的科研 skills 有没有更新，但先不要应用", research)
    assert _intents(plan) == ["skill_sync"], plan
    assert plan["steps"][0]["primary"]["source"] == "internal"

    plan = route_task("把当前论文项目做一个存档快照", research)
    assert _intents(plan) == ["project_archive"], plan

    valid = validate_project(research)
    assert valid["ok"], valid


def _git(cwd: Path, *args: str):
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)


def test_sync_and_rollback(tmp: Path):
    upstream = tmp / "upstream"
    upstream.mkdir()
    _git(upstream, "init")
    _git(upstream, "checkout", "-b", "main")
    _git(upstream, "config", "user.email", "test@example.com")
    _git(upstream, "config", "user.name", "Test")
    (upstream / "LICENSE").write_text("demo license\n", encoding="utf-8")
    (upstream / "common").mkdir()
    (upstream / "common" / "README.md").write_text("common v1\n", encoding="utf-8")
    (upstream / "demo-skill").mkdir()
    (upstream / "demo-skill" / "SKILL.md").write_text("---\nname: demo-skill\ndescription: demo\n---\nv1\n", encoding="utf-8")
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-m", "v1")

    registry = tmp / "caps.yaml"
    registry.write_text(
        "version: 1\nsources:\n"
        "  demo:\n"
        f"    repo: {upstream.as_posix()}\n"
        "    branch: main\n"
        "    support_dependencies: [common]\n"
        "    recommended: [demo-skill]\n"
        "    capabilities:\n"
        "      common: {role: support}\n"
        "      demo-skill: {role: demo}\n",
        encoding="utf-8",
    )

    project = tmp / "project"
    research = init_project(project, None, "sync")
    os.environ["RESEARCH_PAPER_HUB_CACHE"] = str(tmp / "cache")

    out = apply_updates(research, skills=["demo-skill"], capabilities_path=registry)
    assert out["skills"]["demo-skill"]["status"] == "synced", out
    assert (project / ".research" / "vendor" / "demo" / "common").exists()
    skill_file = project / ".research" / "vendor" / "demo" / "demo-skill" / "SKILL.md"
    assert skill_file.read_text(encoding="utf-8").endswith("v1\n")

    (upstream / "demo-skill" / "SKILL.md").write_text("---\nname: demo-skill\ndescription: demo\n---\nv2\n", encoding="utf-8")
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-m", "v2")

    check = check_updates(research, skills=["demo-skill"], capabilities_path=registry)
    assert check["skills"]["demo-skill"]["status"] == "update_available", check
    apply_updates(research, skills=["demo-skill"], capabilities_path=registry)
    assert skill_file.read_text(encoding="utf-8").endswith("v2\n")

    rb = rollback_skill(research, "demo-skill", capabilities_path=registry)
    assert rb["status"] == "rolled_back"
    assert skill_file.read_text(encoding="utf-8").endswith("v1\n")


def main():
    test_format()
    with tempfile.TemporaryDirectory() as td:
        test_router_and_reuse(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_sync_and_rollback(Path(td))
    print("all tests passed")


if __name__ == "__main__":
    main()
