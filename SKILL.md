---
name: research-paper-hub
description: Route and coordinate paper-research workflows across CCFA-Skills and nature-skills. Use for 论文检索/精读/范文提取、research gap/idea、实验设计、论文撰写/改稿/审稿/rebuttal、引用与证据核验、科研图/PPT，或继续/归档一个长期 paper 项目。 This is the single front door for multi-skill research work; do not use for unrelated coding, generic prose, or simple factual questions that do not need a research workflow.
license: MIT
compatibility: Python 3.11+ recommended; git is required only for upstream skill synchronization.
---

# Research Paper Hub

Treat this skill as the **single front door** for paper-oriented research work. The user's explicit instructions always take precedence.

## Core rule

For every research request, create a workflow with **one primary owner per step**. Never let two writers, reviewers, searchers, or figure skills compete for the same artifact.

Router and orchestrator logic are internal modules, not separate discoverable skills:

- Read `references/ROUTER.md` when deciding owners, decomposing a composite request, or resolving overlap.
- Read `references/ORCHESTRATOR.md` when the task changes a persistent project, spans multiple steps, creates manuscript/review artifacts, or should be archived.
- Read only the specific additional reference needed for the current step. Do not load all references at once.

## Workflow

1. **Respect explicit selection.** If the user explicitly names an upstream skill, use that skill as the owner unless doing so is impossible or unsafe. Record the choice when a project is active.
2. **Detect project context.** If `<project>/.research/state.json` exists, reuse it. For a new long-running paper project, initialize `.research/` with `scripts/hub.py init <project>` when shell execution is available.
3. **Classify the request.** Separate single-step tasks from composite tasks. A turn such as “找一篇最近的 paper，精读后做组会汇报” is a sequence, not one ambiguous intent.
4. **Route each step.** Apply `references/ROUTER.md`. A step has exactly one owner. Supporting capabilities may supply prerequisite artifacts or audits but must not produce the same primary artifact.
5. **Reuse before recompute.** Prefer existing Reader/source-map, Paper Card, Exemplar, experiment, figure, and manuscript artifacts when their inputs and capability versions still match.
6. **Load the owner playbook progressively.** If synchronized upstream playbooks exist under `.research/vendor/<source>/<skill>/SKILL.md`, read the selected owner playbook and only the prerequisite/audit playbooks required for that step. Do not load every installed playbook.
7. **Execute and persist.** For persistent work, create/update a run record, artifact records, claim-evidence links, manuscript revision history, reviewer concern ledger, and snapshots according to `references/ORCHESTRATOR.md`.
8. **Audit at boundaries.** Before a formal manuscript milestone, separate bibliographic verification from scientific claim/evidence/numeric integrity. Do not conflate the two.
9. **Do not silently update upstream behavior.** It is fine to check for upstream changes; applying an upstream skill update requires an explicit user request. Record the exact commit/tree hash used by each run.

## Writing rules

When the user supplies or names a strong reference paper as a writing model, treat `ccf-paper-to-exemplar` as the bridge between reading and drafting. Extract reusable story structure, paragraph roles, rhetorical moves, and claim-evidence choreography; never copy source sentences or paper-specific claims.

Use exactly one primary writer for a manuscript pass:

- CS / CCF / AAAI / CVPR / NeurIPS / ACM / IEEE / TGRS-style targets → `ccf-paper-writer`.
- Nature / Nature-family targets → `nature-writing`.
- Unknown target → use the project's configured writing family; if absent, use the research domain and intended venue to make a best-effort choice and record it.

A polishing or humanization capability may run only after the primary drafting pass.

## Upstream synchronization

Use `scripts/hub.py sync` when shell execution is available. The synchronized upstream copies are **playbooks inside the project**, not top-level discoverable skills. This is deliberate: it prevents host-level implicit-trigger collisions.

Common commands:

```bash
python scripts/hub.py init /path/to/project --profile examples/remote-sensing-profile.yaml
python scripts/hub.py route --project /path/to/project --task "找最近论文并精读后做组会汇报"
python scripts/hub.py sync --project /path/to/project --check
python scripts/hub.py sync --project /path/to/project --apply --recommended
python scripts/hub.py sync --project /path/to/project --apply --skill ccf-paper-to-exemplar
python scripts/hub.py sync --project /path/to/project --rollback --skill ccf-paper-to-exemplar
python scripts/hub.py snapshot --project /path/to/project --note "before major rewrite"
python scripts/hub.py validate --project /path/to/project
```

If shell execution or network access is unavailable, use `config/capabilities.yaml` and `config/routing.yaml` as the fallback routing contract and continue with the best available workflow instead of blocking the user.

## Completion check

Before finishing a research turn, verify:

- each step had one owner;
- no blocked competitor produced the same artifact;
- reusable artifacts were not unnecessarily regenerated;
- claims and numbers are not stronger than the available evidence;
- any persistent output was archived or clearly marked as transient;
- the run records which upstream capability versions were used when version data is available.
