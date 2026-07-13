---
description: "Full-lifecycle PrizmKit development toolkit index. Routes users to the right core skill for project init, planning, implementation, review, docs maintenance, testing, commit, and deploy. Use when the user asks 'which command?', 'help', 'how do I start a feature', 'get started', 'what tools', 'dev workflow', 'lifecycle', or '/prizmkit'. Clarifies Direct edit vs Fast path vs Full path and asks whether ambiguous 'ship it' means commit or deploy. (project)"
---

# PrizmKit — Full-Lifecycle Development Toolkit

### When to Use
- User asks "which command?", "help", "how do I start a feature", "get started", "what tools"
- User wants to understand the PrizmKit development lifecycle
- User invokes "/prizmkit" or asks about dev workflow
- User is new to the project and needs orientation
- User says an ambiguous phrase such as "ship it" and intent could mean commit or deploy

### When NOT to Use
- User already knows which specific skill to use — run the `/that` command directly
- Mid-implementation — use the specific skill needed (`/prizmkit-implement`, `/prizmkit-code-review`, etc.)
- User wants to execute immediately without orientation — route to the correct specific skill

## Task Execution Model

PrizmKit uses self-contained task sessions. Each task starts by reading project context and ends by preserving durable knowledge when the change warrants it.

Per-task context normally comes from:

**Application level**:
- `.prizmkit/prizm-docs/root.prizm` — L0 project architecture index
- `.prizmkit/plans/project-brief.md` — product vision generated during project initialization
- `.prizmkit/config.json` — tech stack and runtime config

**Task level**:
- `spec.md` / `plan.md` — change artifact for the current task
- Relevant `.prizmkit/prizm-docs/<module>.prizm` L1 docs
- Relevant L2 docs when they exist; if an L2 doc is missing, implementation reads the target source files as fallback and retrospective may create L2 afterward

## Lifecycle Paths

Choose the lightest path that still protects correctness. Explain the chosen path briefly before proceeding.

### Direct edit

Use for low-risk work with no meaningful behavior or interface impact.

Examples:
- Typo or wording fixes
- Pure formatting
- Small documentation edits
- Tiny config tweaks with no behavior change

Direct edit does not create `spec.md` or `plan.md`. Run only the verification that fits the edit.

### Fast path

Use for small, well-scoped behavior changes where a full lifecycle would add more process than value.

Default flow:

```text
simplified /prizmkit-plan -> /prizmkit-implement -> conditional test/retro -> /prizmkit-committer
```

Rules:
- Use a simplified `plan.md` with a Tasks section so implementation can resume safely.
- Full `/prizmkit-code-review` is optional unless risk or user request requires it.
- Run `/prizmkit-test` only when the change hits the risk-triggered testing criteria.
- Run `/prizmkit-retrospective` only when structure, interfaces, dependencies, behavior, or durable project knowledge changed.

### Full path

Use for high-risk work, multi-module changes, new capabilities, architecture changes, public API/interface changes, data model/schema changes, security/permission/payment logic, or unclear requirements.

Default flow:

```text
/prizmkit-plan -> /prizmkit-implement -> risk-triggered /prizmkit-test if needed -> /prizmkit-code-review -> /prizmkit-retrospective -> /prizmkit-committer
```

Rules:
- `/prizmkit-plan` produces a full `spec.md` and `plan.md`.
- `/prizmkit-code-review` is the default quality gate.
- `/prizmkit-retrospective` is the normal development writer for `.prizmkit/prizm-docs/`.
- `/prizmkit-test` is risk-triggered rather than always mandatory.

## Risk-Triggered Testing

Recommend or require `/prizmkit-test` when the change affects:
- Observable behavior
- Public interfaces or API contracts
- Data models, migrations, or schema
- Security, permissions, authentication, billing, payments, or entitlements
- Deployment readiness or user-requested quality verification

Skip `/prizmkit-test` for pure docs, formatting, internal renames with no behavior change, or tiny config tweaks unless the user asks for tests.

## Development Scenarios

PrizmKit supports any development scenario through the same skill chain. `/prizmkit-plan` produces a change artifact (`spec.md` + `plan.md`) regardless of whether the task is a feature, bug fix, refactor, or migration.

| Scenario | Artifacts | When to Use |
|----------|-----------|-------------|
| Feature | `spec.md` -> `plan.md` -> code | New functionality, UI, API, data model changes |
| Bug fix | `spec.md` -> `plan.md` -> code | Complex defects, regressions, crash fixes; simple bugs can use Direct edit or Fast path |
| Refactor | `spec.md` -> `plan.md` -> code | Restructure, extract, rename, performance work with behavior preservation |

## Core Skill Reference

| Skill | Purpose | Trigger Phrases |
|-------|---------|-----------------|
| `/prizmkit-init` | Project bootstrap entry point: use before planning in a newly installed/taken-over project; scans codebase, generates `.prizmkit/prizm-docs/`, config, and project brief. | "init", "initialize", "take over this project", "bootstrap" |
| `/prizmkit-plan` | First implementation planning step: run ahead of `/prizmkit-implement` to turn natural language into `spec.md` + `plan.md` with executable tasks. | "specify", "plan", "new task", "architect", "break it down" |
| `/prizmkit-implement` | Implementation step: use after `/prizmkit-plan` to execute `plan.md` tasks with TDD where applicable, task order, and checkpoints. | "implement", "build", "code it", "start coding" |
| `/prizmkit-test` | Risk-triggered quality gate: run after implementation when behavior, interfaces, data, security, or deploy risk requires tests and boundary coverage. | "test", "run tests", "verify", "quality check", "boundary tests" |
| `/prizmkit-code-review` | Full path quality gate: run after implementation; requires the dedicated reviewer agent in the active checkout and stops if that launch mode is unavailable. | "review", "check code", "code review", "is it ready to commit" |
| `/prizmkit-retrospective` | Docs maintenance step: run after review/implementation when structure, interfaces, dependencies, behavior, or durable knowledge changed. | "retrospective", "retro", "update docs", "sync docs", "wrap up" |
| `/prizmkit-committer` | Final lifecycle commit step: use after required gates are satisfied; safely stages and creates a Conventional Commit without changing changelog by default. | "commit", "submit", "finish", "done" |
| `/prizmkit-prizm-docs` | Documentation system entry point: use for init/status/rebuild/validate/migrate or out-of-band repair, not normal development sync. | "initialize docs", "check docs", "rebuild docs", "validate docs", "docs drifted" |
| `/prizmkit-deploy` | Deployment lifecycle entry point: use after code is ready to release or for existing deployment operations. | "deploy", "go live", "take live", "release", "rollback", "deploy status" |

## Ambiguous Ship Intent

If the user says only "ship it", ask whether they mean:

1. Commit the current changes with `/prizmkit-committer`.
2. Deploy or release the project with `/prizmkit-deploy`.

Do not route ambiguous "ship it" directly to commit or deploy without clarification.

## Quick Start

1. `npx prizmkit install .` — install skills, rules, hooks, and platform scaffolding
2. `/prizmkit-init` — scan project, generate docs/config/brief
3. `/prizmkit-plan` — create a change artifact for the first non-trivial task
4. `/prizmkit-implement` — implement plan tasks
5. Run `/prizmkit-test` if risk-triggered
6. Run `/prizmkit-code-review` for Full path or when requested/risk-triggered
7. Run `/prizmkit-retrospective` if docs or durable knowledge changed
8. `/prizmkit-committer` — safe Conventional Commit

> Rules and hooks are installed by `npx prizmkit install`, not by `/prizmkit-init`.
