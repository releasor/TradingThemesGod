---
description: "Triage-based bug-fix workflow for interactive single-bug repair or pipeline handoff. Diagnoses enough to choose Fast Path, Pipeline Path, continue diagnosis, or existing-list launch; keeps a thicker Fast Path for one bug with reproduction, fix, review, user verification, commit, and merge choice. Use for 'fix this bug', 'debug this', stack traces, failed tests, bug IDs, manual bug fixes, or batch bugs that may need bug-planner -> bugfix-pipeline-launcher. Ordinary bug fixes skip retrospective unless structural docs or architecture change."
---

# Bug Fix Workflow

Triage-based entry point for bug fixing. Unlike feature/refactor workflows, this workflow intentionally keeps a thicker Fast Path because high-quality single-bug repair depends on interactive diagnosis, reproduction, verification, and commit decisions.

## Responsibility Boundary

This workflow owns:
- Single-bug interactive diagnosis and repair in the current workspace.
- Lightweight routing between Fast Path, Pipeline Path, existing-list launch, and continued diagnosis.
- User confirmation before workspace mutation.
- Reproduction evidence, root-cause fix, code review, user verification, commit, and merge decision for Fast Path.

This workflow does not own:
- Batch bug list generation, headless execution readiness, severity/priority calibration, schema validation, or plan review gates — those belong to `bug-planner`.
- Pipeline execution mode, runtime configuration, command assembly, status/log/stop/retry details — those belong to `bugfix-pipeline-launcher`.

Ordinary bug fixes do not run `/prizmkit-retrospective`. Run retrospective only when the fix intentionally changes durable architecture, module boundaries, public interfaces, or `.prizmkit/prizm-docs/` structure.

## When to Use

Use this workflow when:
- The user wants to fix one specific bug interactively.
- The user provides a stack trace, error message, failing test, or bug ID and wants diagnosis.
- The user wants to decide whether a bug is simple enough for current-session repair.
- The user provides multiple or complex bugs and wants routing to the bug-fix pipeline.

Do not use this workflow when:
- The user only wants to collect or plan bugs -> use `bug-planner`.
- The user only wants launch/status/logs/retry for an existing bug list -> use `bugfix-pipeline-launcher`.
- The user wants feature development -> use `feature-workflow`.
- The user wants behavior-preserving restructuring -> use `refactor-workflow`.

## Input Sources

Accept any of these sources:

| Source | Example | Route implication |
|---|---|---|
| Bug ID from `.prizmkit/plans/bug-fix-list.json` | `fix B-001` | Can use Fast Path for one bug or launcher for pipeline |
| Stack trace / error message | `TypeError: ...` | Diagnose before route selection |
| Natural-language report | `login crashes on submit` | Diagnose before route selection |
| Failed test | `src/auth/login.test.ts fails` | Use test as reproduction evidence |
| Multiple bugs/logs | `these 7 tests fail` | Usually Pipeline Path through `bug-planner` |

If no input source is clear, ask the user to describe the bug before proceeding.

## Route Selection

### Step 1: Diagnose enough to choose a path

Do not create a branch or modify files before path selection.

Gather enough information to decide whether this is:
- One bug suitable for interactive Fast Path.
- A complex single bug or batch bug set better suited for `bug-planner`.
- An existing bug list operation better suited for `bugfix-pipeline-launcher`.
- Still too unclear and needs continued diagnosis.

For systematic clarification, read `.claude/command-assets/bug-fix-workflow/references/bug-diagnosis.md` when the report lacks reproduction, expected vs actual behavior, affected scope, data/state trigger, or error details.

### Step 2: Confirm bug understanding

Before asking for an execution path, summarize:

```markdown
## Bug Understanding

- Symptom:
- Reproduction:
- Environment:
- Expected behavior:
- Actual behavior:
- Impact:
- Suspected affected area:
- Unknowns:
```

Ask whether the summary is accurate. If key fields are still unknown, include `Continue diagnosis` as an approach option.

### Step 3: Ask for approach selection

Use `AskUserQuestion`; do not render path options as plain text.

```text
Question: How would you like to proceed?
Header: Approach
Options:
- Fix now (Fast Path) — create/use a fix branch in this workspace, reproduce, fix, review, verify, commit, and choose merge behavior
- Use Pipeline Path — bug-planner creates/reviews bug-fix-list.json, then bugfix-pipeline-launcher configures execution
- Continue diagnosis — inspect or ask more before choosing a path
```

For an auto-discovered existing bug list:

```text
Question: Existing bug-fix-list.json found. What should we do with it?
Header: Bug list
Options:
- Launch existing list — hand off to bugfix-pipeline-launcher
- Inspect summary first — show bug count/status, then ask again
- Update/re-plan — hand off to bug-planner in append/update mode
- Fix one bug interactively — choose a single bug for Fast Path
```

If the user explicitly asked to run an existing list, that explicit request counts as path selection; hand off directly to `bugfix-pipeline-launcher`.

## Workflow Handoff Brief

When handing off to `bug-planner`, `bugfix-pipeline-launcher`, or Fast Path L1 skills, include this prompt brief. Do not write the brief to disk.

```markdown
## Workflow Handoff Brief

### Source
- workflow: bug-fix-workflow
- selected_path: fast_path | pipeline_path | existing_list_launch | continue_diagnosis

### Bug Goal
- original_request: <preserve the user's wording>
- normalized_bug_summary: <symptom, expected/actual, impact>

### Evidence
- reproduction: <known steps or failing test>
- error_output: <stack trace, logs, console output, or omitted>
- affected_paths: <files/modules/tests mentioned by user or discovered during diagnosis>
- environment: <runtime/browser/OS/data state if known>

### Scope
- included: <bug behavior to fix>
- excluded: <unrelated cleanup, refactor, feature work>

### Decision
- route_reason: <why this path was selected>
- user_confirmed: yes

### Next Skill Instruction
- For bug-planner: Use this brief as input; perform your own required clarification, validation, generation, and review gate.
- For Fast Path: Fix only the root cause for this bug and preserve unrelated behavior.
```

## Fast Path — Single Bug Interactive Repair

Fast Path starts only after the user selects `Fix now`.

### Phase 1: Branch setup

1. Check current branch.
2. If on `main` or a shared branch, create a dedicated `fix/<BUG_ID-or-short-desc>` branch.
3. If already on a fix branch, ask whether to continue on it or create a new one.
4. Record the original branch for the merge decision.

This phase occurs after path selection so Pipeline Path users do not receive unnecessary workspace mutations.

### Phase 2: Root-cause triage

1. Read `.prizmkit/prizm-docs/root.prizm` and relevant L1/L2 docs for affected modules.
2. Read files from the error, stack trace, failing test, or bug summary.
3. Check relevant TRAPS in `.prizmkit/prizm-docs/`.
4. Identify root cause, blast radius, and fix complexity.
5. Present diagnosis and ask whether to proceed.

### Phase 3: Reproduce

1. Write or identify a focused reproduction test/check when practical.
2. Confirm the reproduction fails before the fix when practical.
3. If automatic reproduction is impractical, record a manual checklist and explain the limitation.

### Phase 4: Fix

1. Make the smallest root-cause fix.
2. Avoid unrelated refactoring or feature work.
3. Run the reproduction test/check.
4. Run the relevant regression tests.
5. If regressions appear, revise up to three attempts, then ask whether to continue, switch to Pipeline Path, or stop.

If the fix requires a written implementation plan, invoke `/prizmkit-plan` with the handoff brief, then `/prizmkit-implement`. Do not switch to Pipeline Path solely because a current-session plan is useful.

### Phase 5: Review

Run `/prizmkit-code-review` against the bug context and current diff. The review should check root-cause coverage, reproduction strength, edge cases, regressions, and project conventions.

If review needs fixes, apply accepted fixes directly in the current workspace and rerun the review loop according to `/prizmkit-code-review` rules.

### Phase 6: User verification

Use `AskUserQuestion` for the verification decision:

```text
Question: Fix passes the available checks. Would you like to verify before committing?
Header: Verify
Options:
- Run the app — start the relevant dev command and manually check the scenario
- Run a command — user provides a test/check command
- Skip verification — automated checks are enough for now
```

If the user reports the fix still fails, return to Phase 4. After two additional failed attempts, ask whether to continue or switch to Pipeline Path.

### Phase 7: Retrospective, commit, and merge decision

1. Run `/prizmkit-retrospective` only if the fix changed durable architecture/docs or structural interfaces.
2. Run `/prizmkit-committer` with a `fix(<scope>):` message.
3. Use `AskUserQuestion` for merge behavior:

```text
Question: Fix committed on the fix branch. What would you like to do next?
Header: Merge
Options:
- Merge back — merge to the original branch and delete the fix branch
- Keep branch — retain it for PR/review workflow
- Decide later — leave the branch as-is
```

Do not push unless the user explicitly asks.

## Pipeline Path

Use Pipeline Path for multiple bugs, uncertain/broad root cause, structural fix planning, or background autonomous execution.

1. Invoke `bug-planner` with the handoff brief.
2. `bug-planner` performs bug collection, severity/priority calibration, headless readiness checks, validation, and plan review.
3. After `bug-planner` reports a validated `.prizmkit/plans/bug-fix-list.json`, show a concise summary: bug count, severity distribution, and review/validation outcome.
4. Ask whether to proceed to launch.
5. If yes, invoke `bugfix-pipeline-launcher`.

Do not duplicate launcher execution-mode or configuration questions in this workflow; the launcher owns them.

## Existing List Operations

If the user explicitly requests launch/status/logs/retry/stop for an existing bug list, invoke `bugfix-pipeline-launcher` with the user's intent and list path.

If the user wants to add, edit, deduplicate, or validate bugs, invoke `bug-planner`.

## Resume Guidance

| State found | Action |
|---|---|
| On fix branch with uncommitted code changes | Resume Fast Path at review or verification depending on test/review status |
| Fast Path `spec.md` / `plan.md` exists | Ask whether to continue implementation, review, or re-plan |
| Fix committed on fix branch | Ask merge preference |
| Valid `.prizmkit/plans/bug-fix-list.json` exists and user wants execution | Invoke `bugfix-pipeline-launcher` |
| Bug list exists but intent is unclear | Ask launch / inspect / update / fix one bug interactively |
| Recovery is ambiguous after interruption | Use `recovery-workflow` |

## Error Handling

| Situation | Action |
|---|---|
| Bug report is too vague | Ask systematic clarification questions from `references/bug-diagnosis.md` |
| Bug ID missing from bug list | Ask user for details or route to `bug-planner` to update the list |
| Many bugs provided to Fast Path | Recommend Pipeline Path and ask via `AskUserQuestion` |
| Cannot reproduce automatically | Record manual reproduction and proceed only with user awareness |
| Fix causes regressions | Revise up to three attempts, then ask whether to continue or switch paths |
| Root cause remains unclear | Continue diagnosis or switch to Pipeline Path based on user choice |
| Merge conflict occurs | Stop and report the conflict; ask whether user wants manual resolution or to keep the branch |

## Handoff Map

| From | To | Condition |
|---|---|---|
| `bug-fix-workflow` | `/prizmkit-plan` / `/prizmkit-implement` | Fast Path needs a written current-session plan |
| `bug-fix-workflow` | `/prizmkit-code-review` | Fast Path fix is implemented |
| `bug-fix-workflow` | `/prizmkit-retrospective` | Structural docs/architecture changed |
| `bug-fix-workflow` | `/prizmkit-committer` | Fast Path fix is reviewed and ready |
| `bug-fix-workflow` | `bug-planner` | User selects Pipeline Path or wants bug-list planning |
| `bug-planner` | `bug-fix-workflow` | Planner completed from workflow-origin Pipeline Path |
| `bug-fix-workflow` | `bugfix-pipeline-launcher` | User confirms launch after planner completion or explicitly requests existing-list execution |

## Output

- Fast Path: root-cause fix, reproduction evidence, relevant tests/checks, review result, optional structural doc sync, one fix commit, and merge decision.
- Pipeline Path: handoff brief, validated `.prizmkit/plans/bug-fix-list.json` from `bug-planner`, and pipeline launch/status handled by `bugfix-pipeline-launcher`.
