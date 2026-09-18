# Router policy

Use this module when a request could match more than one research capability or contains multiple deliverables.

## Routing objective

Optimize for: correct owner, minimal context, minimal duplicate work, reproducibility, and no same-artifact competition.

The unit of routing is a **step**, not an entire user turn. Composite requests become an ordered plan. Every step has:

- `intent`
- exactly one `primary_skill`
- zero or more prerequisite/audit skills
- expected input artifacts
- expected output artifacts
- blocked competitors
- archive policy

## Decision order

1. Explicit user-selected skill.
2. Requested artifact type and operation.
3. Existing project artifacts that can satisfy prerequisites.
4. Target venue/family.
5. Project stage.
6. Default owner in `config/routing.yaml`.

Do not route by generic words such as “paper” alone when a more specific requested artifact is present.

## Decomposition examples

“找一篇最近的 paper，精读后做组会汇报”:

1. `literature_discovery` → `nature-academic-search`
2. `paper_read` → `nature-reader`
3. `paper_card` → `nature-paper-card`
4. `group_meeting_ppt` → `nature-paper2ppt`

“拿这篇 TGRS 论文的写法当模板，重构我的 Introduction”:

1. reuse or create Reader artifact → `nature-reader`
2. `paper_exemplar` → `ccf-paper-to-exemplar`
3. `manuscript_write` → venue-aware writer (`ccf-paper-writer` for TGRS)
4. optional integrity boundary → `ccf-integrity-auditor`

“帮我找创新点并设计消融实验”:

1. `literature_discovery` only if retrieval is needed → `nature-academic-search`
2. `opportunity_gap` → `ccf-literature-searcher`
3. `idea_review` or `idea_optimize` when needed
4. `experiment_design` → `ccf-experiment-designer`
5. statistical-design support → `nature-statistics`

## Owner boundaries

### Literature

- discovery / multi-source retrieval / citation lookup: `nature-academic-search`
- recurring feed: `nature-literature-pipeline`
- closest-work map / gap / novelty / benchmark opportunity reasoning: `ccf-literature-searcher`
- lawful acquisition: `nature-downloader`
- source-grounded full reading: `nature-reader`
- deep-reading card: `nature-paper-card`
- reusable writing exemplar: `ccf-paper-to-exemplar`

### Ideas and experiments

- idea gate/reviewer: `ccf-idea-reviewer`
- idea refinement: `ccf-idea-optimizer`
- experiment package / baseline / ablation logic: `ccf-experiment-designer`
- statistical design/check: `nature-statistics`
- experiment logging: `nature-experiment-log`

### Writing

- CS/CCF/AAAI/CVPR/NeurIPS/ACM/IEEE/TGRS family: `ccf-paper-writer`
- Nature family: `nature-writing`
- exemplar/structure transfer: `ccf-paper-to-exemplar`
- language polish: `nature-polishing` by default; `ccf-humanization` only when specifically preferred/configured

Never run two primary writers on the same revision pass.

### Review and integrity

- venue-aware scientific manuscript review: `ccf-paper-reviewer` or `nature-reviewer`, one only
- bibliographic fields / DOI / reference-file integrity: `nature-ref-verifier`
- claim support / numeric consistency / citation-context / manuscript-result alignment: `ccf-integrity-auditor`

A formal review may be followed by both audits because they inspect different failure classes.

### Visuals and presentation

- method/story architecture figure: `ccf-visual-composer`
- results/statistical multi-panel figure: `nature-figure`
- group-meeting paper deck: `nature-paper2ppt`

## Artifact-aware prerequisite insertion

Before adding a prerequisite step, check the artifact registry. Reuse when:

- artifact exists;
- its source/input hash is unchanged;
- its producing capability version/tree hash has not been invalidated by a required update;
- the requested scope is compatible.

Important reuse rules:

- do not parse a PDF twice if a valid `reader_artifact` + `source_map` exists;
- both `nature-paper-card` and `ccf-paper-to-exemplar` should consume the same Reader/source-map when possible;
- a writer may retrieve 1–3 existing exemplars instead of regenerating them;
- do not regenerate figures if only prose changed and figure inputs are unchanged.

## Ambiguity policy

Do not ask a clarification question when a best-effort route is safe and reversible. Record assumptions in the route plan.

Ask only when the ambiguity would materially change an irreversible action, required external access, or the target artifact itself.

## Collision policy

Blocked competitors are scoped to one step/artifact. A blocked skill may be used later for a different artifact.

Examples:

- while `ccf-paper-to-exemplar` owns `exemplar_card`, both writers are blocked;
- while `ccf-paper-writer` owns a CS manuscript revision, `nature-writing` is blocked as primary but `nature-polishing` may run later;
- while `nature-ref-verifier` owns reference metadata audit, `ccf-integrity-auditor` is not a substitute, but may run as a separate claim-integrity step.
