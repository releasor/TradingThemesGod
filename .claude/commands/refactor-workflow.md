---
description: "Thin L3 refactor workflow router for behavior-preserving code restructuring. Clarifies enough to choose Fast Path, Pipeline Path, or existing-list launch; routes deep code analysis and item decomposition to refactor-planner and execution configuration to refactor-pipeline-launcher. Use when the user wants to refactor, clean up, restructure, decouple, simplify, migrate internal structure, extract modules, or run an existing refactor list without changing product behavior. Trigger on: 'refactor', 'clean up code', 'restructure', 'optimize code structure', 'extract module', 'decouple', 'code migration', 'batch refactor', 'run refactor list'."
---

# Refactor Workflow

Thin L3 entry point for behavior-preserving refactoring. This workflow routes the user to the right path, prepares a concise handoff brief, and avoids duplicating `refactor-planner` or `refactor-pipeline-launcher` internals.

## Responsibility Boundary

This workflow owns:
- Scenario recognition: Fast Path, Pipeline Path, existing-list launch, or behavior-change reroute.
- Lightweight behavior-risk triage.
- User path selection through `AskUserQuestion`.
- Prompt brief handoff to Fast Path L1 skills, `refactor-planner`, or `refactor-pipeline-launcher`.
- Continuation after `refactor-planner` when the user entered through this workflow.

This workflow does not own:
- Deep code analysis, item decomposition, dependency ordering, behavior-preservation strategy selection, schema validation, or plan review gates — those belong to `refactor-planner`.
- Execution mode, runtime configuration, preflight, command assembly, status/log/stop/retry details — those belong to `refactor-pipeline-launcher`.
- Product behavior changes — those should route to feature work unless explicitly framed as a behavior-preserving migration.

## Behavior-Preservation Boundary

Refactoring means external behavior remains unchanged:
- Public product behavior stays the same.
- User-visible outcomes stay the same.
- Public contracts stay stable unless the user explicitly confirms a compatibility-preserving migration.
- Tests and behavior checks are used to prove the change is structural.

If the request requires changed product behavior, new user-facing functionality, or a breaking public API change, route to `feature-workflow`. Internal API, import path, or module boundary changes can still be refactoring when external behavior remains unchanged and the planner can define a safe migration strategy.

## When to Use

Use this workflow when the user wants a guided refactoring entry point:
- Clean up or restructure existing code.
- Extract modules, helpers, middleware, or shared logic.
- Decouple modules or simplify structure.
- Plan or execute behavior-preserving migrations.
- Decide whether a refactor is small enough for current-session Fast Path or should use the refactor pipeline.
- Continue from an existing `.prizmkit/plans/refactor-list.json`.

Do not use this workflow when the user only wants:
- Refactor planning without execution intent -> use `refactor-planner`.
- Launch/status/logs/retry for an existing refactor list -> use `refactor-pipeline-launcher`.
- New functionality or changed product behavior -> use `feature-workflow`.
- Bug repair -> use `bug-fix-workflow` or the bug pipeline skills.

## Route Overview

| User situation | Route |
|---|---|
| Simple local behavior-preserving refactor | Fast Path in current workspace |
| Batch, cross-module, high-risk, weak-test, or multi-step refactor | `refactor-planner` -> return here -> `refactor-pipeline-launcher` |
| Product behavior change or breaking public API change | Route to `feature-workflow` |
| User explicitly says to run an existing refactor list | `refactor-pipeline-launcher` |
| Refactor list exists but the user did not explicitly ask to run it | Ask launch / inspect / update |

## Route Selection

### Step 1: Detect the entry mode

Classify the request before asking detailed refactoring questions:

- **Behavior-preserving refactor**: the user asks to clean up, restructure, simplify, extract, decouple, or migrate implementation structure.
- **Behavior change**: the user asks to change what the product does, add functionality, or break a public contract.
- **Existing list launch**: the user explicitly asks to run, start, resume, check, retry, or stop `.prizmkit/plans/refactor-list.json`.
- **Unclear**: the request mixes cleanup with behavior changes.

If behavior preservation is unclear, ask one concise clarification question before route selection.

### Step 2: Lightweight triage for behavior-preserving work

Use lightweight criteria only. Do not perform full code analysis or item decomposition here.

Fast Path candidate when all are true:
- One focused refactor or a small tightly related cleanup.
- Expected work is localized and follows existing patterns.
- Behavior-preservation checks are obvious or already available.
- No broad dependency ordering, public behavior change, or risky migration is needed.

Pipeline Path candidate when any are true:
- Multiple refactor items or batch refactoring request.
- Cross-module or multi-layer impact.
- Import-path, internal API, or module-boundary migration needs ordering.
- Weak test coverage creates behavior-preservation risk.
- The user wants autonomous/background execution.
- The request needs `refactor-planner` to analyze code, split items, validate ordering, and review entries.

### Step 3: Ask for path selection

Use `AskUserQuestion`; do not render path options as plain text.

```text
Question: How would you like to proceed?
Header: Approach
Options:
- Refactor now (Fast Path) — current session/current workspace via /prizmkit-plan -> /prizmkit-implement with behavior checks
- Use Pipeline Path — refactor-planner creates/reviews refactor-list.json, then refactor-pipeline-launcher configures execution
- Continue clarifying — ask a few more route-level questions before choosing
```

If the request appears to change product behavior:

```text
Question: This appears to change behavior rather than only restructure code. What should we do?
Header: Boundary
Options:
- Route to feature-workflow (Recommended) — treat behavior change as feature work
- Keep as refactor — only if behavior remains externally unchanged or this is a compatibility-preserving migration
- Continue clarifying — define which behavior must stay unchanged
```

For an auto-discovered existing refactor list:

```text
Question: Existing refactor-list.json found. What should we do with it?
Header: Refactor list
Options:
- Launch existing list — hand off to refactor-pipeline-launcher
- Inspect summary first — show refactor count/status, then ask again
- Update/re-plan — hand off to refactor-planner in incremental mode
- Ignore and start fresh — continue route selection from the new request
```

If the user explicitly asked to run an existing list, that explicit request counts as path selection; hand off directly to `refactor-pipeline-launcher`.

## Workflow Handoff Brief

When handing off, include this prompt brief in the next skill invocation. Do not write the brief to disk.

```markdown
## Workflow Handoff Brief

### Source
- workflow: refactor-workflow
- selected_path: fast_path | pipeline_path | existing_list_launch | behavior_change_reroute

### User Goal
- original_request: <preserve the user's wording>
- normalized_goal: <lightly normalized refactoring goal>

### Scope
- included: <explicitly in scope>
- excluded: <explicitly out of scope or unknown>

### Behavior Preservation
- must_remain_unchanged: <public behavior, user-visible outcomes, APIs, workflows, tests>
- suspected_behavior_changes: <items that may need feature-workflow>

### Materials
- provided_paths: <paths/directories supplied by the user>
- provided_docs_or_urls: <docs, links, screenshots, or specs supplied by the user>
- notes: <rules, constraints, or emphasis from the user>

### Decision
- route_reason: <why this path was selected>
- user_confirmed: yes

### Next Skill Instruction
- For planner: Use this brief as input; perform your own required code analysis, behavior-preservation planning, validation, generation, and review gate.
- For Fast Path: Use this brief to create spec.md/plan.md and implement only this behavior-preserving scope.
```

## Selected Path Execution

### Fast Path

Use Fast Path only after explicit user selection.

1. Invoke `/prizmkit-plan` with the handoff brief and behavior-preservation expectations.
2. Invoke `/prizmkit-implement` after the plan is ready.
3. Run behavior-preservation checks identified in the plan.
4. Run `/prizmkit-test` only when risk triggers match: public contracts, data models, migration behavior, weak behavior-preservation evidence, or explicit user verification request.
5. Run `/prizmkit-code-review` when the user requested review, behavior-preservation uncertainty is high, or Full-path-level risk appears during implementation.
6. Run `/prizmkit-retrospective` only when structure, interfaces, dependencies, behavior, or durable project knowledge changed.
7. Run `/prizmkit-committer` with a `refactor(<scope>):` message.
8. End the workflow after commit; do not call `refactor-planner`, `refactor-pipeline-launcher`, or monitoring.

If the refactor starts changing behavior or grows beyond Fast Path criteria, pause and ask whether to switch to `feature-workflow` or Pipeline Path.

### Pipeline Path

1. Invoke `refactor-planner` with the handoff brief.
2. `refactor-planner` performs code analysis, item decomposition, behavior-preservation planning, validation, and plan review.
3. After `refactor-planner` reports a validated `.prizmkit/plans/refactor-list.json`, show a concise summary: item count, ordering highlights, preservation strategy summary, and review/validation outcome.
4. Ask whether to proceed to launch.
5. If yes, invoke `refactor-pipeline-launcher`.

Do not duplicate launcher execution-mode, strict-behavior-check, or runtime configuration questions in this workflow; the launcher owns them.

### Existing list launch

If the user explicitly requested launch/status/logs/retry/stop for an existing refactor list, invoke `refactor-pipeline-launcher` with the user's intent and list path.

If this workflow discovered the list on its own, use the `Existing refactor-list.json found` question in §Route Selection before invoking the launcher.

## Resume Guidance

| State found | Action |
|---|---|
| Fast Path `spec.md` / `plan.md` exists | Ask whether to continue current-workspace refactor or re-plan |
| Valid `.prizmkit/plans/refactor-list.json` exists and user wants execution | Invoke `refactor-pipeline-launcher` |
| Valid refactor list exists but intent is unclear | Ask launch / inspect / update |
| No plan/list artifacts | Start route selection |

For interrupted autonomous pipeline sessions, prefer `refactor-pipeline-launcher` status/retry operations or `recovery-workflow` when the user explicitly asks to recover a broken AI session.

## Runtime Status Reference

This workflow does not assemble runtime commands, but it may show lightweight status before handoff or recovery. Use the canonical Python runtime forms:

```bash
python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor status
python3 ./.prizmkit/dev-pipeline/cli.py refactor status .prizmkit/plans/refactor-list.json
```

For start/stop/logs/retry execution, hand off to `refactor-pipeline-launcher`; do not duplicate launcher configuration here.

## Error Handling

| Situation | Action |
|---|---|
| Behavior change is required | Route to `feature-workflow` unless user confirms a behavior-preserving migration |
| User wants planning only | Route to `refactor-planner` and stop after planner summary |
| User wants execution only | Route to `refactor-pipeline-launcher` |
| No behavior checks exist | Warn user; recommend Pipeline Path unless scope is very small |
| Fast Path reveals broader risk | Pause and ask whether to switch to Pipeline Path |
| Planner needs more detail | Let `refactor-planner` ask its own clarification questions |
| Launcher finds baseline/config issues | Let `refactor-pipeline-launcher` handle confirmation and configuration |

## Handoff Map

| From | To | Condition |
|---|---|---|
| `refactor-workflow` | `feature-workflow` | Request requires product behavior change |
| `refactor-workflow` | `/prizmkit-plan` | User selects Fast Path |
| `refactor-workflow` | `refactor-planner` | User selects Pipeline Path |
| `refactor-planner` | `refactor-workflow` | Planner completed from workflow-origin Pipeline Path |
| `refactor-workflow` | `refactor-pipeline-launcher` | User confirms launch after planner completion or explicitly requests existing-list execution |

## Output

- Fast Path: `spec.md`, `plan.md`, behavior-preserving code changes, behavior-check evidence, conditional test/review evidence when triggered, Prizm docs sync only when durable knowledge changed, and one refactor commit.
- Pipeline Path: handoff brief, validated `.prizmkit/plans/refactor-list.json` from `refactor-planner`, and pipeline launch/status handled by `refactor-pipeline-launcher`.
