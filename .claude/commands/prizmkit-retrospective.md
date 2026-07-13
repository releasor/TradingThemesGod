---
description: "Incremental .prizmkit/prizm-docs/ maintainer and normal development docs writer. Performs structural sync for changed modules and injects durable TRAPS/RULES/DECISIONS when feature, bugfix, refactor, or test work creates lasting project knowledge. Run after code review or implementation when the chosen lifecycle path changed structure, interfaces, dependencies, behavior, or durable knowledge, and before committing those changes. Trigger on: 'retrospective', 'retro', 'update docs', 'sync docs', 'wrap up', 'done with feature', 'feature complete'. (project)"
---

# PrizmKit Retrospective

`/prizmkit-retrospective` is the normal development writer for `.prizmkit/prizm-docs/`.

It performs two jobs:

1. **Structural Sync** — reflect changed code structure, interfaces, dependencies, and file mappings in `.prizmkit/prizm-docs/`.
2. **Knowledge Injection** — add durable TRAPS, RULES, and DECISIONS discovered during the task.

For first-time documentation setup, validation, rebuild, migration, or out-of-band repair after docs drift, use `/prizmkit-prizm-docs` instead.

## When to Use

- Full path: after code review passes and before commit when code/docs knowledge changed.
- Fast path: before commit only when structure, interfaces, dependencies, behavior, or durable project knowledge changed.
- Bug fixes: run structural sync when the fix changes interfaces/dependencies/observable behavior; run knowledge injection only when the fix reveals durable TRAPS/RULES/DECISIONS.
- Test-only changes: run only when tests reveal durable boundaries, traps, interface constraints, behavior rules, or regression knowledge worth preserving.
- User says "retrospective", "retro", "update docs", "sync docs", or "wrap up" during normal development.

## When NOT to Use

- Direct edit with no structural, behavioral, dependency, interface, or durable-knowledge change.
- Only comments, whitespace, or formatting changed.
- Only `.prizm` files changed — avoid circular updates.
- Test-only changes that merely add coverage for already documented behavior and reveal no new durable knowledge.
- Out-of-band doc repair/resync after merges or branch switches — use `/prizmkit-prizm-docs` Update/Rebuild/Validate.

## Input

| Parameter | Required | Description |
|-----------|----------|-------------|
| `artifact_dir` | No | Directory containing `spec.md`, `plan.md`, and optionally `review-report.md`. If omitted, scan `.prizmkit/` subdirectories for the most recently modified directory with a `plan.md`. When invoked as a handoff step, reuse the caller's `artifact_dir` rather than re-detecting. If no artifact directory is found, run standalone structural sync from `git diff`. |

## Job 1: Structural Sync

Synchronize `.prizmkit/prizm-docs/` structure with actual codebase changes from this session.

Read `.claude/command-assets/prizmkit-retrospective/references/structural-sync-steps.md` for the detailed procedure.

Key outputs:
- L1 file counts and module mappings
- L2 KEY_FILES / INTERFACES / DATA_FLOW / DEPENDENCIES for affected diff files
- New L1/L2 docs when newly changed source directories require them
- Stale TRAPS cleanup when needed

Memory hygiene: `.prizmkit/prizm-docs/` must not contain CHANGELOG sections/files, UPDATED/date metadata, feature/bug/refactor/task/session/run/pipeline/workflow IDs, branch names, absolute worktree paths, or `.prizmkit/specs` / `.prizmkit/dev-pipeline` artifact paths. Convert artifact-scoped wording into durable product/domain language before writing.

## Job 2: Knowledge Injection

Inject newly discovered durable project knowledge into architecture docs.

Read `.claude/command-assets/prizmkit-retrospective/references/knowledge-injection-steps.md` for the detailed procedure.

### Review Gate

Before Job 2, check `review-report.md` in the artifact directory when present:

- Verdict `PASS` → proceed.
- Verdict `NEEDS_FIXES` → skip Job 2 and warn: "Review report has unresolved findings. Skipping knowledge injection."
- No `review-report.md` → proceed with warning for Fast path or standalone mode.
- No artifact directory → skip Job 2 unless the user explicitly provides durable knowledge to record.

### Knowledge Injection Triggers

Run Job 2 when the task produced durable knowledge such as:

- New TRAPS, gotchas, race conditions, or surprising coupling
- New architectural rules or decisions
- Interface signature or contract changes
- Dependency additions/removals that affect module behavior
- Observable behavior changes to existing features
- Test-only discoveries that document new boundary conditions, regression rules, or interface constraints

Skip Job 2 for pure refactors with no durable design or behavior knowledge.

## Final: Stage Docs

Stage doc changes only after verifying they are intended:

```bash
git add .prizmkit/prizm-docs/
```

Do not stage unrelated files.

## Output

- Updated `.prizmkit/prizm-docs/*.prizm` files when sync or knowledge injection applies
- Summary of updated, created, and skipped docs with reasons
- Handoff: `/prizmkit-committer`
