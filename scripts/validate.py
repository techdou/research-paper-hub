from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lib import CONFIG_DIR, SKILL_ROOT, load_json, load_yaml, project_paths, read_jsonl, sha256_tree
from project import VALID_STAGES

VALID_CLAIM = {"proposed", "supported", "partially_supported", "unsupported", "retired"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_skill_format(root: Path = SKILL_ROOT) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        return {"ok": False, "errors": ["SKILL.md missing"], "warnings": []}
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append("SKILL.md must start with YAML frontmatter")
        meta = {}
    else:
        try:
            _, front, _ = text.split("---", 2)
            import yaml
            meta = yaml.safe_load(front) or {}
        except Exception as exc:
            errors.append(f"invalid frontmatter: {exc}")
            meta = {}
    name = meta.get("name")
    desc = meta.get("description")
    if not name:
        errors.append("frontmatter.name missing")
    elif not NAME_RE.fullmatch(str(name)):
        errors.append("name must be lowercase alphanumeric and hyphens only")
    elif len(str(name)) > 64:
        errors.append("name exceeds 64 characters")
    if name and root.name != name:
        errors.append(f"name '{name}' must match parent directory '{root.name}'")
    if not desc:
        errors.append("frontmatter.description missing")
    elif len(str(desc)) > 1024:
        errors.append("description exceeds 1024 characters")
    if not (root / "agents" / "openai.yaml").exists():
        warnings.append("agents/openai.yaml missing (optional but recommended for invocation policy/UI)")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "metadata": meta}


def validate_project(research: Path) -> dict[str, Any]:
    paths = project_paths(research)
    errors: list[str] = []
    warnings: list[str] = []
    state = load_json(paths["state"], {})
    for key in ["project_id", "stage", "created_at", "updated_at"]:
        if not state.get(key):
            errors.append(f"state.json missing required field: {key}")
    if state.get("stage") not in VALID_STAGES:
        errors.append(f"invalid stage: {state.get('stage')}")
    if state.get("primary_writing_family") not in {"cs", "nature"}:
        errors.append("primary_writing_family must be cs or nature")
    try:
        load_yaml(paths["profile"])
    except Exception as exc:
        errors.append(f"invalid profile.yaml: {exc}")
    seen: set[str] = set()
    for i, row in enumerate(read_jsonl(paths["claims"]), 1):
        cid = row.get("claim_id")
        if not cid:
            errors.append(f"claim line {i}: missing claim_id")
        elif cid in seen:
            warnings.append(f"duplicate claim_id: {cid}")
        seen.add(cid)
        if row.get("status") not in VALID_CLAIM:
            errors.append(f"claim {cid}: invalid status {row.get('status')}")
    lock = load_json(paths["lock"], {"skills": {}})
    for skill, item in lock.get("skills", {}).items():
        source = item.get("source")
        folder = paths["vendor"] / str(source) / skill
        if not folder.exists():
            warnings.append(f"locked capability missing locally: {skill}")
        elif item.get("content_sha256") and sha256_tree(folder) != item.get("content_sha256"):
            warnings.append(f"vendor capability modified after sync: {skill}; use overrides instead")
    return {"ok": not errors, "errors": errors, "warnings": warnings}
