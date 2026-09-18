from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from lib import compact_timestamp, dump_json, project_paths, sha256_file, utcnow


def create_snapshot(research: Path, note: str = "") -> dict[str, Any]:
    paths = project_paths(research)
    sid = f"snapshot-{compact_timestamp()}"
    dst = paths["snapshots"] / sid
    dst.mkdir(parents=True, exist_ok=False)
    copied: list[Path] = []
    for src in [paths["state"], paths["profile"], paths["artifacts"], paths["papers"], paths["claims"], paths["exemplars"], paths["reviews"], paths["lock"]]:
        if src.exists():
            target = dst / src.relative_to(research)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied.append(target)
    if paths["manuscript_current"].exists():
        target = dst / "manuscript" / "current"
        shutil.copytree(paths["manuscript_current"], target, dirs_exist_ok=True)
        copied.extend(p for p in target.rglob("*") if p.is_file())
    manifest = {
        "snapshot_id": sid,
        "created_at": utcnow(),
        "note": note,
        "files": [
            {"path": str(p.relative_to(dst)), "sha256": sha256_file(p)}
            for p in sorted(set(copied)) if p.is_file()
        ],
    }
    dump_json(manifest, dst / "manifest.json")
    return manifest
