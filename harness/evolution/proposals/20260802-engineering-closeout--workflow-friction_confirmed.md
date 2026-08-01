---
id: evolution-20260802-engineering-closeout-workflow-friction_confirmed
level: L1
summary: Review evolution event workflow.friction_confirmed for 20260802-engineering-closeout
load_when:
  - process-evolution
  - task:20260802-engineering-closeout
task_id: 20260802-engineering-closeout
status: proposed
---

# Evolution proposal: workflow.friction_confirmed

Reason: Closing verified specs failed because durable README links targeted short-lived active spec files; lifecycle-safe references need an executable guard.

## Allowed outcome

After human confirmation, update only relevant L1/L2 sources, templates, workflows, indexes, or checks.

## Observed evidence

The deterministic close of `20260801-content-portability` passed its pre-close checks, then failed the post-close link check because the root `README.md` linked directly to its short-lived file under `harness/specs/active/`. The close command rolled back correctly. Replacing durable README links with the generated specification index removed the blocker.

## Proposed change

- Extend `harness/verification/checks/links.py` so Markdown outside `harness/specs/` cannot link directly into `harness/specs/active/`.
- Update the spec lifecycle guidance to direct durable documents to `harness/specs/INDEX.md` or a durable decision instead of an active spec path.
- Add focused executable coverage for both rejected active-spec links and allowed index/archive-safe links.

If confirmed, set this proposal to `accepted`, implement the guard without modifying `AGENTS.md`, regenerate indexes, and rerun the Harness and local release candidate gates.

## Forbidden outcome

This proposal must not modify `AGENTS.md` automatically.
