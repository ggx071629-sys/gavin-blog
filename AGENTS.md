# Agent Map

This file is the only L0 document; it is always loaded and stays a map, never an encyclopedia.

## Start Here

1. Read `harness/INDEX.md` for task routing.
2. Load only the L1 documents selected by that index.
3. Query L2 documents only when an L1 route is insufficient.
4. Never preload or recursively read all of `harness/docs/`.

## Product Boundaries

- Product brief: `harness/docs/product/brief.md`.
- Architecture boundaries: `harness/docs/architecture/boundaries.md`.
- Web application boundary: `apps/web/README.md`.
- API application boundary: `apps/api/README.md`.
- Shared contracts boundary: `packages/contracts/README.md`.

## Task Routing

- Intake or ambiguity: `harness/workflows/intake.md`.
- Behavior, API, data, security, or cross-stack change: use SDD.
- SDD rules: `harness/specs/_sdd/README.md`.
- Active specs: `harness/specs/active/`.
- Implementation: `harness/workflows/implement.md`.
- Verification: `harness/workflows/verify.md`.
- Publishing: `harness/workflows/publish.md`.
- Retrospective: `harness/workflows/retrospect.md`.

## Loading Levels

- L0: this file only.
- L1: task-relevant policy, workflow, spec, or project baseline.
- L2: supporting detail queried only when needed.
- Use generated indexes instead of broad full-text loading.
- Respect each document's `load_when` metadata.

## Spec Rules

- Create a spec only when the SDD risk triggers require one.
- Use task IDs shaped as `YYYYMMDD-short-slug`.
- Keep active specs short-lived.
- Close specs only through the deterministic close command.
- A close must preserve the original spec in Git history.

## Verification Rules

- VDD includes TDD, contracts, integration, E2E, and quality gates.
- Prefer executable checks over narrative claims.
- Keep checks separate from evidence.
- Commit compact evidence manifests only.
- Never commit heavy logs, reports, screenshots, or raw artifacts.

## Telemetry and Evolution

- Telemetry observes; it never changes agent behavior.
- Raw telemetry remains local and uncommitted.
- Evolution accepts only events listed in `harness/config.toml`.
- Evolution proposals require human confirmation before application.
- Evolution must never modify this file automatically.

## Automation

- Run commands from the `harness/` directory.
- Generate indexes with `python -m tools.harness index`.
- Verify the harness with `python -m tools.harness verify [task_id]`.
- Freeze or resume a task with `python -m tools.harness <freeze|resume> <task_id> --reason "..."`.
- Close a task with `python -m tools.harness close <task_id>`.
- Emit an event with `python -m tools.harness emit-event ...`.
- Deterministic summaries are authoritative; optional LLM annotations must cite sources.

## Change Discipline

- Preserve unrelated user changes.
- Do not invent deployment, storage, or CI structure prematurely.
- Do not generate Nuxt or FastAPI business code during harness work.
- Update source metadata, then regenerate indexes.
- Keep `AGENTS.md` between 60 and 80 physical lines.
- Escalate durable decisions to `harness/docs/decisions/`.
