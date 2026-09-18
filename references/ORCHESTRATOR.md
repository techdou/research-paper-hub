# Orchestrator policy

Use this module for persistent or multi-step research work.

## Persistent state

Store project state under `<project>/.research/`. Do not write user research artifacts into the installed skill folder.

Recommended structure:

```text
.research/
  state.json
  profile.yaml
  artifacts/index.jsonl
  papers/index.jsonl
  claims/claim_evidence.jsonl
  exemplars/index.jsonl
  runs/
  manuscript/current/
  manuscript/history/
  reviews/concerns.jsonl
  snapshots/
  upstream/lock.json
  vendor/<source>/<skill>/
  vendor-history/<source>/<skill>/
  overrides/
```

## Stage model

`seed → discovery → reading → framing → experiment_design → experimentation → evidence_ready → drafting → internal_review → revision → submission_ready → submitted → rebuttal → accepted/archive`

Backward transitions are allowed when new evidence invalidates a claim or experiment.

Read `config/stages.yaml` before advancing a stage. Never advance only because a command ran; advance when the exit evidence exists.

## Run lifecycle

Create a run record for any meaningful persistent operation. A run records the planned step owners and the exact upstream capability versions used.

Minimum fields:

```yaml
run_id: ...
task: ...
status: planned|running|completed|partial|failed
steps:
  - intent: paper_exemplar
    owner: ccf-paper-to-exemplar
    capability_version:
      source: ccfa
      commit: ...
      tree_sha: ...
inputs: []
outputs: []
assumptions: []
started_at: ...
finished_at: ...
```

If a task partially fails, preserve valid outputs and mark recovery notes. Do not discard a usable Reader artifact just because a later PPT step failed.

## Artifact model

Every durable artifact should have:

- stable `artifact_id`
- type
- path
- input artifact IDs or input hashes
- producing skill
- upstream commit/tree hash when known
- creation time
- content SHA-256 when local
- scope/tags

This enables reuse and invalidation.

## Claim-evidence chain

Maintain scientific claims separately from prose:

`Claim → Prior Art → Experiment → Result → Figure/Table → Manuscript Section`

Statuses: `proposed`, `supported`, `partially_supported`, `unsupported`, `retired`.

When a result changes, locate affected claims and manuscript sections before polishing wording. Never preserve stronger prose than the evidence supports.

## Manuscript refinement loop

```text
Draft N
  → one primary reviewer
  → stable concern ledger
  → evidence / prose / figure fixes
  → integrity audit + reference verification
  → Draft N+1
  → snapshot + delta note
```

Reviewer concern IDs are stable across revisions. Valid statuses:

- `open`
- `addressed`
- `partially_addressed`
- `rejected_with_reason`
- `superseded`

## Exemplar library

Register strong reference-paper exemplars in `.research/exemplars/index.jsonl`.

Store:

- paper identity
- venue/year/domain
- source artifact IDs
- strongest reusable sections
- story-pattern tags
- method/evidence-pattern tags
- suitable target sections
- do-not-copy boundary
- producing `ccf-paper-to-exemplar` version

Writers should retrieve 1–3 matching exemplars. Exemplar use transfers structure and rhetorical function, not wording.

## Snapshot policy

Create snapshots at least:

- before major manuscript restructuring;
- after experiment-plan freeze;
- after a major result refresh;
- after each formal review/revision cycle;
- before submission or rebuttal.

Snapshots should contain state, locks, claim ledger, exemplar index, current manuscript metadata, review ledger, and hashes of copied files.

## Upstream update safety

Checking for updates may happen opportunistically. Applying updates must be explicit.

Never apply upstream updates in the middle of an active manuscript transformation without first creating a snapshot. Each run must remain reproducible from its recorded skill tree hashes.
