---
id: evolution-20260811-harness-close-signal-integrity-workflow-friction_confirmed
level: L1
summary: Review evolution event workflow.friction_confirmed for 20260811-harness-close-signal-integrity
load_when:
  - process-evolution
  - task:20260811-harness-close-signal-integrity
task_id: 20260811-harness-close-signal-integrity
status: applied
---

# Evolution proposal: workflow.friction_confirmed

Reason: Spec closure creates unactionable evolution proposals and loses Goal and Acceptance criteria when active specs use H1 section headings.

## Allowed outcome

After human confirmation, update only relevant L1/L2 sources, templates, workflows, indexes, or checks.

## Observed evidence

- All 43 lifecycle-generated `spec.completed` proposals were ultimately reviewed with no action. The only applied proposal was created from a concrete `workflow.friction_confirmed` event.
- Before the latest review, 25 pending proposals had identical 22-line boilerplate bodies with no observed evidence, proposed change, or human decision section.
- 23 of 43 compressed spec archives contain `Not recorded.` for both Goal and Acceptance criteria even though the original active specs contain those sections.
- `tools/summarizer.py` recognizes only exact H2 headings (`## Goal` and `## Acceptance criteria`), while the SDD template names the required sections without fixing a heading level and valid recent specs use H1 headings.

## Proposed change

- Preserve the `spec.completed` lifecycle event on deterministic close, but do not create a proposal from that generic event by default.
- Keep explicitly emitted, evidence-bearing events capable of generating a proposal for human review.
- Extract Goal and Acceptance criteria from exact H1 or H2 headings, preserving backward compatibility while avoiding matches on deeper nested headings.
- Refuse and roll back close when either required section is absent or empty instead of writing `Not recorded.` into a new archive.
- Make the canonical section structure explicit in the SDD template and lifecycle guidance.
- Add focused executable coverage for H1 and H2 extraction, missing-section rollback, close without an empty proposal, and explicit event proposal creation.
- Do not rewrite existing compressed archives automatically; their original active specs remain available in Git history.

## Acceptance criteria for application

- A normal `python -m tools.harness close <task_id>` creates the archive, evidence, indexes, and lifecycle event without adding an evolution proposal.
- `python -m tools.harness emit-event ...` continues to create a proposal containing the supplied concrete reason.
- H1 and H2 spec fixtures preserve non-empty Goal and Acceptance criteria in the compressed archive.
- Missing or empty required sections leave the active spec intact and create no archive, evidence, event, or proposal residue.
- Focused Harness tests and the full Harness verification suite pass after indexes are regenerated.

## Forbidden outcome

This proposal must not modify `AGENTS.md` automatically.

It must not change product behavior, rewrite historical archives, or resume the two frozen GitHub specs.

## Human decision

Accepted by Gavin on 2026-08-11. Implementation is limited to lifecycle event/proposal separation, lossless required-section compression, focused tests, and the related L1 guidance described above.

## Implementation result

- Deterministic close now records its `spec.completed` event with proposal creation disabled; explicitly emitted events retain proposal creation.
- Compression accepts exact H1 or H2 required sections, preserves deeper nested headings, and rejects missing or empty Goal/Acceptance criteria before deleting the active spec.
- The SDD template and lifecycle guidance now define the canonical H1 structure, backward-compatible H2 handling, and close failure semantics.
- Eight focused lifecycle tests cover section extraction, invalid structures, explicit proposal creation, and close event behavior; the full Harness suite passes 10 tests.
- Full `quality:release` passed: API 257, Harness 10, Web unit 104, production quality 10, failure states 5, core E2E 25, and Lighthouse 99/100/100/100.
- Closing `20260811-harness-close-signal-integrity` preserved its H1 Goal and Acceptance criteria, created the lifecycle event, and created no `spec.completed` proposal.

## Follow-up restoration decision

Confirmed by Gavin on 2026-08-11 after a read-only dry-run proved all 23 affected archives recoverable from committed active specs. This decision supersedes only the earlier historical-backfill non-goal: restore exact Goal and Acceptance criteria content, record the source commit and restoration date in each archive, and leave all other archived content unchanged.

## Follow-up restoration result

- All 23 affected archives now contain Goal and Acceptance criteria copied exactly from their recorded Git source objects; independent comparison reported 23 exact matches, zero mismatches, and zero remaining `Not recorded.` sections.
- Each restored archive records a full `restoration_source` commit/path and `restored_at: 2026-08-11`; Result, Evidence, and original close timestamps were left unchanged.
- The restoration was committed independently as `ef6a7ee`, after Harness tests passed 10/10 and Harness verification passed all checks.
- Post-restoration `quality:release` passed: API 257, Harness 10, Web unit 104, production quality 10, failure states 5, core E2E 25, and Lighthouse 99/100/100/100.
