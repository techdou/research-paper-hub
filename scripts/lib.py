from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Run: pip install -r requirements.txt") from exc

SKILL_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = SKILL_ROOT / "config"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact_timestamp() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%S") + f"{now.microsecond // 1000:03d}Z"


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def append_jsonl(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(path: Path) -> str:
    h = hashlib.sha256()
    if not path.exists():
        return ""
    for p in sorted(x for x in path.rglob("*") if x.is_file()):
        rel = p.relative_to(path).as_posix().encode("utf-8")
        h.update(rel)
        h.update(b"\0")
        h.update(bytes.fromhex(sha256_file(p)))
    return h.hexdigest()


def slugify(text: str, default: str = "project") -> str:
    text = re.sub(r"[^\w\-]+", "-", text.strip(), flags=re.UNICODE).strip("-").lower()
    return text[:80] or default


def run_cmd(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if check and proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip() or f"command failed: {' '.join(args)}"
        raise RuntimeError(msg)
    return proc


def git(repo: Path, *args: str, check: bool = True) -> str:
    return run_cmd(["git", *args], cwd=repo, check=check).stdout.strip()


def copytree_replace(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


def project_root(project: Path) -> Path:
    return project.expanduser().resolve()


def research_root(project: Path, require: bool = True) -> Path:
    r = project_root(project) / ".research"
    if require and not (r / "state.json").exists():
        raise SystemExit(f"Not an initialized research-paper-hub project: {project}")
    return r


def project_paths(research: Path) -> dict[str, Path]:
    return {
        "state": research / "state.json",
        "profile": research / "profile.yaml",
        "artifacts": research / "artifacts" / "index.jsonl",
        "papers": research / "papers" / "index.jsonl",
        "claims": research / "claims" / "claim_evidence.jsonl",
        "exemplars": research / "exemplars" / "index.jsonl",
        "runs": research / "runs",
        "manuscript_current": research / "manuscript" / "current",
        "manuscript_history": research / "manuscript" / "history",
        "reviews": research / "reviews" / "concerns.jsonl",
        "snapshots": research / "snapshots",
        "vendor": research / "vendor",
        "vendor_history": research / "vendor-history",
        "overrides": research / "overrides",
        "lock": research / "upstream" / "lock.json",
        "sync_status": research / "upstream" / "last-check.json",
    }


def source_for_skill(skill: str, capabilities: dict[str, Any]) -> str | None:
    for source, spec in capabilities.get("sources", {}).items():
        if skill in spec.get("capabilities", {}):
            return source
    return None


def detect_venue_family(target: str | None, profile: dict[str, Any], routing: dict[str, Any]) -> str:
    if target:
        lower = target.lower()
        for family, spec in routing.get("families", {}).items():
            if any(str(v).lower() in lower for v in spec.get("venues", [])):
                return family
    project = profile.get("project", {})
    return project.get("primary_writing_family") or "cs"


def artifact_types(research: Path) -> set[str]:
    return {row.get("type") for row in read_jsonl(project_paths(research)["artifacts"]) if row.get("type")}


def capability_version(research: Path, skill: str) -> dict[str, Any] | None:
    lock = load_json(project_paths(research)["lock"], {"skills": {}})
    item = lock.get("skills", {}).get(skill)
    if not item:
        return None
    return {
        "source": item.get("source"),
        "commit": item.get("commit"),
        "tree_sha": item.get("tree_sha"),
        "content_sha256": item.get("content_sha256"),
    }


def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
