# Changelog

## 2.1.0 — 2026-11-26

- Aligned capabilities and routing with Nov 2026 upstream updates (`CCFA-Skills` v0.12.1 + 6 venue templates, `nature-skills` PR #283–#299).
- Added `ccf-research-engineer` to `ccfa.recommended` and wired `research_engineering` routing for codebase selection, baseline reproduction, model implementation, and training diagnosis.
- Registered `nature-data` (`data_availability`) and `nature-citation` (`cns_citation`) as optional non-recommended Nature capabilities.
- Expanded `families.cs.venues` in `config/routing.yaml` to cover ACL, EMNLP, NAACL, IJCAI, KDD, SIGKDD, SIGIR, WWW, ACM-MM, CHI, and MICCAI.
- Documented explicit upstream exclusion boundaries (`ccf-pipeline-orchestrator`, `ccf-project-scaffolder`, `ccf-skill-forger`, and `nature-paper2word`/`nature-image2ppt`/`nature-proposal-writer`/`nature-paper-xray`) to preserve local skill ownership (`dou-tone`, `paper-reading`, `nenu-computer-tech-proposal`, `ppt-studio`, `chinese-professional-docx`).
- Added regression coverage for `research_engineering`, optional `nature-data`/`nature-citation`, and ACL venue routing.

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
