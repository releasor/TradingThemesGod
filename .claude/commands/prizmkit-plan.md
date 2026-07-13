---
description: "Specify and plan development tasks: natural language → change artifact with spec.md and plan.md. Works for features, bug fixes, refactors, migrations, and other non-trivial changes. Use before /prizmkit-implement when the task needs written scope, design, or executable tasks; use simplified planning for Fast path changes and full planning for high-risk or multi-module work. Trigger on: 'specify', 'plan', 'new task', 'I want to add/build...', 'architect', 'design', 'break it down', 'create tasks'. (project)"
---

# PrizmKit Plan

A universal spec + plan generator. It turns a natural-language development task into a **change artifact**: `spec.md` (WHAT/WHY) and `plan.md` (HOW + Tasks).

A change artifact is not feature-only. It can describe a feature, bug fix, refactor, migration, test improvement, or other scoped change.

### When to Use
- Any non-trivial development task that benefits from written scope and task breakdown
- Before `/prizmkit-implement` when no suitable `plan.md` exists
- Fast path changes that still need a simplified plan and resumable Tasks section
- Full path changes involving multiple files/modules, public interfaces, data models, architecture, security, or unclear requirements
- User says "specify", "plan", "new task", "I want to add...", "architect", "design", or "break it down"

### When NOT to Use
- Direct edit: typo, pure formatting, small docs edit, or tiny config tweak with no behavior impact
- User explicitly asks for a one-off direct edit and the risk is low
- A current artifact directory already has an adequate `spec.md` + `plan.md` for the requested work

## Path Selection

Choose the lightest planning depth that protects correctness:

| Path | Planning behavior |
|---|---|
| Direct edit | Skip `/prizmkit-plan`; edit directly and verify the specific change. |
| Fast path | Create a concise `spec.md` and simplified `plan.md` with a Tasks section. |
| Full path | Create full `spec.md` and `plan.md` with architecture, risks, tests, and executable tasks. |

Use Full path for high-risk, multi-module, public API, data model, security, permission, payment, deployment-impacting, or ambiguous work. Use Fast path for small scoped behavior changes. Explain the chosen path briefly.

## Input

| Parameter | Required | Description |
|-----------|----------|-------------|
| `description` | Yes | Natural-language description of the task |
| `artifact_dir` | No | Directory to write the change artifact into. If omitted, auto-generates under `.prizmkit/specs/` using a numbered slug. |

## Execution

### Phase 0: Specify (`spec.md`)

Skip this phase if `spec.md` already exists in the artifact directory and still matches the requested change.

Steps:

1. Gather the task description. If missing and interactive, ask the user; otherwise abort with a clear error.
2. Determine artifact directory:
   - If `artifact_dir` is provided, use it directly.
   - If omitted, scan `.prizmkit/specs/` for existing numbered directories and create `.prizmkit/specs/###-task-slug/`.
   - The `.prizmkit/specs/` path is a generic change-artifact location; it is not limited to features.
3. Load project context: read `.prizmkit/prizm-docs/root.prizm` and relevant L1/L2 docs. If L2 is missing for an affected module, use relevant source files as fallback context.
4. Generate `spec.md` from `.claude/command-assets/prizmkit-plan/assets/spec-template.md`:
   - Focus on WHAT and WHY, not HOW.
   - Include only relevant sections.
   - Every goal needs acceptance criteria.
   - Mark genuine ambiguity with `[NEEDS CLARIFICATION]`.
5. If changes involve persistence, add a Data Model section. Read existing schema files to learn naming conventions, ID strategy, constraints, and migration patterns.
6. Resolve `[NEEDS CLARIFICATION]` markers:
   - Interactive: ask targeted questions using `.claude/command-assets/prizmkit-plan/references/clarify-guide.md`.
   - Non-interactive: choose conservative defaults and annotate the decision.

Internal ID hygiene: PrizmKit IDs, task IDs, session/run IDs, branch names, absolute worktree paths, and `.prizmkit/specs` / `.prizmkit/dev-pipeline` artifact paths are internal metadata. They may appear in change artifacts, but do not write them into `.prizmkit/prizm-docs/`, product UI copy, API responses, emails, notifications, or expected user-visible test strings.

### Phase 1: Design (`plan.md`)

Precondition: `spec.md` exists.

Steps:

1. Read `spec.md`.
2. Load project context if not already loaded: root Prizm doc, relevant L1/L2 docs, and source fallback for missing L2 docs.
3. Resolve any remaining clarification markers.
4. Generate `plan.md` from `.claude/command-assets/prizmkit-plan/assets/plan-template.md`:
   - Change approach
   - Component/file changes
   - Data model changes and migration approach when relevant
   - Interface/API contract design when relevant
   - Testing strategy, using risk-triggered `/prizmkit-test` criteria
   - Risk assessment
   - Behavior preservation strategy for refactors or behavior-adjacent changes
5. Cross-check every spec goal maps to a plan component.
6. Check alignment with `.prizmkit/prizm-docs/root.prizm` RULES.

### Phase 2: Task Generation

1. Choose task strategy: MVP-first, incremental, or parallel. Ask in interactive mode when the choice affects execution; otherwise infer from risk and dependencies.
2. Append `## Tasks` to `plan.md` using `.claude/command-assets/prizmkit-plan/assets/plan-template.md`:
   - Setup tasks
   - Foundation tasks
   - Core tasks mapped to goals or logical units
   - Polish tasks when needed
   - Checkpoint tasks between phases when integration risk exists
3. Mark parallel tasks with `[P]` only when they can safely run independently.
4. Run the verification checklist from `.claude/command-assets/prizmkit-plan/references/verification-checklist.md` and fix issues before the planning quality gate.

### Phase 3: Plan/Spec Review Loop

Run this phase every time `spec.md` and `plan.md` are created or updated, before reporting the plan or handing off to implementation.

1. Explicitly read `.claude/command-assets/prizmkit-plan/references/review-plan-spec-loop.md`.
2. Execute that guide against the current `spec.md` and `plan.md`.
3. Apply all resolvable `BLOCKER` fixes and accepted `SHOULD_FIX` fixes directly to `spec.md` and/or `plan.md`.
4. Treat `OPTIONAL` findings as non-blocking.
5. Rerun the review once when fixes were applied, respecting the guide's maximum of 2 total rounds.
6. If unresolved `BLOCKER` findings remain, stop and ask targeted clarification questions in interactive mode; in non-interactive mode, record the blocker and stop. Do not escalate to a Critic agent.
7. Only proceed to `/prizmkit-implement` handoff after the loop has no unresolved blockers.

The review loop is planning-only. It must not start implementation, run tests/builds, launch a pipeline, create a separate skill, or require a Critic agent.

## Output

| Directory | Files |
|---|---|
| `artifact_dir` or auto-generated `.prizmkit/specs/###-slug/` | `spec.md` + `plan.md` |

Report:
- artifact directory
- chosen path: Fast path or Full path
- key decisions
- task count and checkpoint summary

**HANDOFF:** `/prizmkit-implement`

## Examples

Read `.claude/command-assets/prizmkit-plan/references/examples.md` for worked examples of feature, refactoring, and bug fix planning.
