# Research Paper Hub

A single-front-door [Agent Skill](https://agentskills.io/specification) for persistent paper-research workflows. It routes requests across two upstream skill families — **CCFA-Skills** (CS/CCF venues) and **nature-skills** (Nature-family journals) — while guaranteeing that no two skills ever compete for the same artifact.

## Why a hub

Research requests are usually composite: *"find a recent paper, read it closely, then report at group meeting"* is a sequence of steps, not one intent. Running a standalone skill per step invites conflicts — two writers, two searchers, two figure skills all claiming the same output. This hub solves that with three rules:

1. **One owner per step.** Each step of a routed plan has exactly one responsible upstream skill. Supporting capabilities may supply audits or prerequisites, but never produce the same primary artifact.
2. **Progressive disclosure.** Only the owner playbook and its declared prerequisites are loaded for a given step. Routing and orchestration logic live as internal modules, not as competing top-level skills.
3. **Version-locked upstreams.** Upstream skills are synchronized into your paper project as project-local playbooks under `.research/vendor/`, each pinned with commit / git tree / content SHA-256 hashes. Updates are checked freely but applied only on explicit request.

## How it works

```text
User research task
    ↓
research-paper-hub        ← the only implicit entry point
    ↓
Internal Router           ← decompose task, assign one owner per step
    ↓
Internal Orchestrator     ← durable state, archives, evidence chains
    ↓
On-demand playbooks from .research/vendor/ (CCFA / Nature)
```

Durable research state (run records, artifacts, claim–evidence links, manuscript revision history, reviewer concern ledgers, snapshots) is stored under `<project>/.research/` and survives across sessions.

## Installation

Copy the whole folder into your Agent Skills user directory:

```text
$HOME/.agents/skills/research-paper-hub/
```

Or import it as a Skill ZIP into any product that supports the Agent Skills format.

Requirements:

- Python 3.11+ (recommended) with [PyYAML](requirements.txt):

```bash
pip install -r requirements.txt
```

- `git` is required only for upstream skill synchronization.

## Quick start

Initialize a long-running paper project:

```bash
python scripts/hub.py init /path/to/my-paper \
  --profile examples/remote-sensing-profile.yaml
```

Synchronize the recommended upstream playbooks:

```bash
python scripts/hub.py sync --project /path/to/my-paper --apply --recommended
```

This places the selected playbooks under `/path/to/my-paper/.research/vendor/` — they are **not** registered as competing top-level skills.

## CLI reference

```bash
# Route a composite task into a one-owner-per-step plan
python scripts/hub.py route --project /path/to/my-paper \
  --task "Find a recent paper on multimodal multilabel remote sensing, read it closely, then report at group meeting"

# Check upstream updates without applying them
python scripts/hub.py sync --project /path/to/my-paper --check

# Update a single skill (shared dependencies are pulled in automatically)
python scripts/hub.py sync --project /path/to/my-paper --apply --skill ccf-paper-to-exemplar

# Roll that skill back to the previous project-local version
python scripts/hub.py sync --project /path/to/my-paper --rollback --skill ccf-paper-to-exemplar

# Snapshot project state before a major rewrite
python scripts/hub.py snapshot --project /path/to/my-paper --note "before Introduction restructure"

# Validate project state integrity
python scripts/hub.py validate --project /path/to/my-paper
```

Update policy: updates are **checked** freely but never **applied** silently. Every run records the exact commit/tree hash it used, so a manuscript written last month stays reproducible.

## Writing policy

Exactly one primary writer runs per manuscript pass:

| Target venue | Primary writer | Polish pass |
|---|---|---|
| CCF / AAAI / CVPR / NeurIPS / ACM / IEEE / TGRS | `ccf-paper-writer` | `ccf-humanization` |
| Nature / Nature-family journals | `nature-writing` | `nature-polishing` |

When a reference paper is supplied as a writing model, `ccf-paper-to-exemplar` bridges reading and drafting: it extracts story structure, paragraph roles, and claim–evidence choreography — never source sentences.

## Directory layout

```text
research-paper-hub/
├── SKILL.md              # Front door: workflow rules and invocation contract
├── agents/openai.yaml    # Host invocation metadata
├── references/           # Router / orchestrator / artifact model / policies
├── config/               # Capabilities, routing, stages, sync contracts
├── scripts/              # hub.py CLI and supporting modules
├── evals/                # Trigger and routing regression cases
├── examples/             # Example project profile
├── assets/               # Project profile template
└── tests/                # Test suite
```

## Upstream playbooks

This skill routes to two upstream skill families, synchronized into user projects on demand:

| Family | Upstream | License | Coverage |
|---|---|---|---|
| CCFA-Skills | [mikubaka88/CCFA-Skills](https://github.com/mikubaka88/CCFA-Skills) | MIT | Literature search/monitor, idea review, experiment design, writing, review, humanization, rebuttal, integrity audit, figures, submission checks |
| nature-skills | [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | Apache-2.0 | Literature discovery, reading, paper cards, statistics, reference verification, figures, polishing, writing, review, response, group-meeting PPT |

This repository does **not** vendor upstream code. Upstream skills are fetched into your project at sync time and recorded with their licenses preserved.

## Testing

```bash
python tests/test_all.py
```

The suite covers routing regression (composite discovery/read/PPT, exemplar→writer, venue switching, artifact reuse, update routing, archive routing) and per-skill sync behavior against a fake-Git harness.

## License

[MIT](LICENSE.txt). Upstream playbooks remain under their own licenses (see table above) and are never redistributed from this repository.
