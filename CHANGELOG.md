# Changelog

## 2.0.0 — 2026-09-11

- Breaking: collapsed `research-router`, `research-orchestrator`, and `research-shared` into one official-format `research-paper-hub` skill.
- Added `agents/openai.yaml` invocation metadata and implicit-invocation policy.
- Reworked routing from single-intent substring winner to multi-step, one-owner-per-step planning.
- Added artifact-aware prerequisite insertion and PDF/Reader reuse policy.
- Elevated `ccf-paper-to-exemplar` to a first-class writing bridge.
- Changed upstream skills from top-level deployed skills to project-local vendored playbooks, reducing implicit trigger collisions.
- Added per-skill commit/tree/content hashes, update checks, explicit apply, history, and rollback.
- Added support-dependency sync for `ccf-common` and `nature-shared`.
- Added official Agent Skills metadata validation and routing regression evals.
