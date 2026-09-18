from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from lib import CONFIG_DIR, compact_timestamp, copytree_replace, dump_json, git, load_json, load_yaml, project_paths, run_cmd, sha256_tree, utcnow


def _capabilities(path: Path | None = None) -> dict[str, Any]:
    return load_yaml(path or (CONFIG_DIR / "capabilities.yaml"))


def cache_root() -> Path:
    cfg = load_yaml(CONFIG_DIR / "sync.yaml")
    env_name = cfg.get("cache_env", "RESEARCH_PAPER_HUB_CACHE")
    raw = os.environ.get(env_name)
    default = Path(str(cfg.get("cache_default", "~/.cache/research-paper-hub"))).expanduser()
    return Path(raw).expanduser().resolve() if raw else default.resolve()


def _ensure_cache(source: str, spec: dict[str, Any]) -> Path:
    root = cache_root()
    repo = root / source
    branch = spec.get("branch", "main")
    root.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        run_cmd(["git", "clone", "--branch", branch, "--single-branch", spec["repo"], str(repo)])
    else:
        git(repo, "fetch", "origin", branch)
    return repo


def _remote_commit(repo: Path, branch: str) -> str:
    return git(repo, "rev-parse", f"origin/{branch}")


def _repo_path(spec: dict[str, Any], skill: str) -> str:
    prefix = str(spec.get("path_prefix", "")).strip("/")
    return f"{prefix}/{skill}" if prefix else skill


def _tree_sha(repo: Path, commit: str, repo_path: str) -> str | None:
    p = run_cmd(["git", "rev-parse", f"{commit}:{repo_path}"], cwd=repo, check=False)
    return p.stdout.strip() if p.returncode == 0 else None


def _extract_dir(repo: Path, commit: str, path: str, dest: Path) -> None:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        archive = td_path / "tree.tar"
        with archive.open("wb") as f:
            proc = subprocess.run(["git", "archive", "--format=tar", commit, path], cwd=repo, stdout=f, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="replace").strip() or f"git archive failed for {path}")
        extract_root = (td_path / "extract").resolve()
        extract_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, "r") as tf:
            for member in tf.getmembers():
                target = (extract_root / member.name).resolve()
                if extract_root != target and extract_root not in target.parents:
                    raise RuntimeError(f"unsafe archive path: {member.name}")
                if member.issym() or member.islnk():
                    raise RuntimeError(f"symlink/hardlink not allowed in synced skill archive: {member.name}")
            tf.extractall(extract_root)
        src = td_path / "extract" / path
        if not src.exists():
            raise FileNotFoundError(path)
        copytree_replace(src, dest)


def _copy_license(repo: Path, commit: str, source_dir: Path) -> str | None:
    for name in ["LICENSE", "LICENSE.txt", "LICENSE.md"]:
        p = run_cmd(["git", "show", f"{commit}:{name}"], cwd=repo, check=False)
        if p.returncode == 0:
            source_dir.mkdir(parents=True, exist_ok=True)
            out = source_dir / f"{name}.upstream"
            out.write_text(p.stdout, encoding="utf-8")
            return str(out)
    return None


def _selected_for_source(spec: dict[str, Any], skills: list[str] | None, recommended: bool) -> list[str]:
    caps = spec.get("capabilities", {})
    initial = list(spec.get("recommended", [])) if recommended else [s for s in (skills or []) if s in caps]
    if not initial:
        return []
    queue = list(spec.get("support_dependencies", [])) + initial
    out: list[str] = []
    while queue:
        skill = queue.pop(0)
        if skill in out:
            continue
        out.append(skill)
        queue.extend(caps.get(skill, {}).get("dependencies", []))
    return out


def check_updates(research: Path, skills: list[str] | None = None, recommended: bool = False, capabilities_path: Path | None = None) -> dict[str, Any]:
    caps = _capabilities(capabilities_path)
    paths = project_paths(research)
    lock = load_json(paths["lock"], {"version": 2, "skills": {}, "sources": {}})
    report: dict[str, Any] = {"checked_at": utcnow(), "sources": {}, "skills": {}}

    requested = set(skills or [])
    for source, spec in caps.get("sources", {}).items():
        if skills and not any(s in spec.get("capabilities", {}) for s in requested):
            continue
        selected = _selected_for_source(spec, skills, recommended) if (skills or recommended) else _selected_for_source(spec, None, True)
        try:
            repo = _ensure_cache(source, spec)
            commit = _remote_commit(repo, spec.get("branch", "main"))
            report["sources"][source] = {"status": "ok", "commit": commit}
        except Exception as exc:
            report["sources"][source] = {"status": "error", "error": str(exc)}
            continue
        for skill in selected:
            tree = _tree_sha(repo, commit, _repo_path(spec, skill))
            prev = lock.get("skills", {}).get(skill, {})
            status = "missing_upstream" if tree is None else ("update_available" if prev.get("tree_sha") and prev.get("tree_sha") != tree else ("not_synced" if not prev.get("tree_sha") else "up_to_date"))
            report["skills"][skill] = {
                "source": source,
                "status": status,
                "remote_commit": commit,
                "remote_tree_sha": tree,
                "pinned_commit": prev.get("commit"),
                "pinned_tree_sha": prev.get("tree_sha"),
            }
    dump_json(report, paths["sync_status"])
    return report


def _backup_existing(paths: dict[str, Path], source: str, skill: str, lock_item: dict[str, Any]) -> Path | None:
    current = paths["vendor"] / source / skill
    if not current.exists():
        return None
    key = f"{compact_timestamp()}-{(lock_item.get('tree_sha') or sha256_tree(current))[:12]}"
    dst = paths["vendor_history"] / source / skill / key
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(current, dst)
    dump_json({"lock_item": lock_item, "backed_up_at": utcnow()}, dst / ".research-paper-hub-history.json")
    return dst


def apply_updates(research: Path, skills: list[str] | None = None, recommended: bool = False, capabilities_path: Path | None = None) -> dict[str, Any]:
    if not skills and not recommended:
        raise ValueError("Specify at least one --skill or use --recommended")
    caps = _capabilities(capabilities_path)
    paths = project_paths(research)
    lock = load_json(paths["lock"], {"version": 2, "skills": {}, "sources": {}})
    report: dict[str, Any] = {"applied_at": utcnow(), "skills": {}, "sources": {}}
    requested = set(skills or [])

    for source, spec in caps.get("sources", {}).items():
        if skills and not any(s in spec.get("capabilities", {}) for s in requested):
            continue
        selected = _selected_for_source(spec, skills, recommended)
        if not selected:
            continue
        repo = _ensure_cache(source, spec)
        branch = spec.get("branch", "main")
        commit = _remote_commit(repo, branch)
        report["sources"][source] = {"commit": commit, "license": _copy_license(repo, commit, paths["vendor"] / source)}
        lock.setdefault("sources", {})[source] = {"repo": spec["repo"], "branch": branch, "commit": commit, "checked_at": utcnow()}

        for skill in selected:
            repo_path = _repo_path(spec, skill)
            tree = _tree_sha(repo, commit, repo_path)
            if tree is None:
                report["skills"][skill] = {"source": source, "status": "missing_upstream"}
                continue
            previous = lock.get("skills", {}).get(skill, {})
            current = paths["vendor"] / source / skill
            if previous.get("tree_sha") == tree and current.exists():
                report["skills"][skill] = {"source": source, "status": "unchanged", "tree_sha": tree}
                continue
            backup = _backup_existing(paths, source, skill, previous)
            _extract_dir(repo, commit, repo_path, current)
            content_sha = sha256_tree(current)
            item = {
                "source": source,
                "repo": spec["repo"],
                "branch": branch,
                "commit": commit,
                "tree_sha": tree,
                "content_sha256": content_sha,
                "synced_at": utcnow(),
            }
            lock.setdefault("skills", {})[skill] = item
            report["skills"][skill] = {
                "source": source,
                "status": "synced",
                "tree_sha": tree,
                "content_sha256": content_sha,
                "backup": str(backup) if backup else None,
            }
    lock["updated_at"] = utcnow()
    dump_json(lock, paths["lock"])
    return report


def rollback_skill(research: Path, skill: str, capabilities_path: Path | None = None) -> dict[str, Any]:
    caps = _capabilities(capabilities_path)
    source = None
    for s, spec in caps.get("sources", {}).items():
        if skill in spec.get("capabilities", {}):
            source = s
            break
    if source is None:
        raise ValueError(f"Unknown skill: {skill}")
    paths = project_paths(research)
    hist_root = paths["vendor_history"] / source / skill
    candidates = sorted([p for p in hist_root.iterdir() if p.is_dir()], reverse=True) if hist_root.exists() else []
    if not candidates:
        raise RuntimeError(f"No rollback history for {skill}")
    chosen = candidates[0]
    meta_path = chosen / ".research-paper-hub-history.json"
    meta = load_json(meta_path, {})
    # Copy without our history metadata file.
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td) / skill
        shutil.copytree(chosen, temp)
        marker = temp / ".research-paper-hub-history.json"
        if marker.exists():
            marker.unlink()
        current = paths["vendor"] / source / skill
        old_lock = load_json(paths["lock"], {"version": 2, "skills": {}, "sources": {}}).get("skills", {}).get(skill, {})
        _backup_existing(paths, source, skill, old_lock)
        copytree_replace(temp, current)
    lock = load_json(paths["lock"], {"version": 2, "skills": {}, "sources": {}})
    restored = meta.get("lock_item") or {
        "source": source,
        "commit": None,
        "tree_sha": None,
        "content_sha256": sha256_tree(current),
        "synced_at": utcnow(),
    }
    restored["rolled_back_at"] = utcnow()
    restored["content_sha256"] = sha256_tree(current)
    lock.setdefault("skills", {})[skill] = restored
    lock["updated_at"] = utcnow()
    dump_json(lock, paths["lock"])
    return {"skill": skill, "source": source, "status": "rolled_back", "from": str(chosen), "restored": restored}
