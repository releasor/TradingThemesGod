---
description: "Thin L3 feature workflow router. Clarifies enough to choose Fast Path, Pipeline Path, existing-list launch, or greenfield app planning; hands deep feature planning to feature-planner, app-level planning to app-planner, and execution configuration to feature-pipeline-launcher. Use when the user wants to develop features from idea to code, add features to an existing project, batch implement features, run an existing feature list, or build a new app that should first go through app-planner. Trigger on: 'develop features', 'implement features', 'add feature', 'batch implement', 'one-stop development', 'build an app', 'build a new application', 'create a project', 'run feature list'."
---

# Feature Workflow

Thin L3 entry point for feature development. This skill routes the user to the right execution path, prepares a concise handoff brief, and avoids duplicating planner or launcher internals.

## Responsibility Boundary

This workflow owns:
- Scenario recognition: Fast Path, Pipeline Path, greenfield app planning, or existing-list launch.
- Lightweight triage: enough context to recommend a path, not full feature planning.
- User path selection through `AskUserQuestion`.
- Prompt brief handoff to `app-planner`, `feature-planner`, `feature-pipeline-launcher`, or Fast Path L1 skills.
- Continuation after `feature-planner` when the user entered through this workflow.

This workflow does not own:
- Deep feature clarification, decomposition, dependency/DAG decisions, priority/complexity calibration, schema validation, or plan review gates — those belong to `feature-planner`.
- Execution mode, runtime configuration, preflight, command assembly, status/log/stop/retry details — those belong to `feature-pipeline-launcher`.
- App-level vision, tech stack, conventions, architecture decisions, or project brief — those belong to `app-planner`.

## When to Use

Use this workflow when the user wants a guided feature-development entry point:
- Build, add, or implement features.
- Decide whether a feature should be implemented now or planned for pipeline execution.
- Batch implement multiple feature requests.
- Continue from an existing `.prizmkit/plans/feature-list.json`.
- Start from a greenfield app idea, where this workflow will route to `app-planner` first.

Do not use this workflow when the user only wants:
- App-level planning without feature execution intent -> use `app-planner`.
- Feature list generation only -> use `feature-planner`.
- Launch/status/logs/retry for an existing feature list -> use `feature-pipeline-launcher`.
- Bug fixing -> use `bug-fix-workflow` or the bug pipeline skills.
- Behavior-preserving restructuring -> use `refactor-workflow`.

## Route Overview

| User situation | Route |
|---|---|
| Greenfield app, new application, create project | `app-planner` first; then optionally `feature-planner` |
| Existing project, simple scoped feature | Fast Path in current workspace |
| Existing project, complex or batch features | `feature-planner` -> return here -> `feature-pipeline-launcher` |
| User explicitly says to run an existing feature list | `feature-pipeline-launcher` |
| Feature list exists but the user did not explicitly ask to run it | Ask launch / inspect / update |

## Route Selection

### Step 1: Detect the entry mode

Classify the user's request before asking detailed feature questions:

- **Greenfield app**: the user says “build a new app”, “create a project”, “start from scratch”, or asks for app-level architecture/tech stack/conventions.
- **Existing list launch**: the user explicitly asks to run, start, resume, check, retry, or stop `.prizmkit/plans/feature-list.json`.
- **Existing project feature work**: the user asks to add or implement features in a project that already has source code or project context.
- **Unclear**: the user mixes app design, feature planning, and implementation intent.

If the request is unclear, ask one concise clarification question before route selection.

### Step 2: Lightweight triage for existing-project feature work

Use lightweight criteria only. Do not perform full feature decomposition here.

Fast Path candidate when all are true:
- One scoped feature or a very small set of tightly related changes.
- Expected work is localized and follows existing patterns.
- No app-level architecture, new infrastructure, or broad dependency ordering is needed.
- Acceptance intent is clear enough for `/prizmkit-plan` to create a spec and plan.

Pipeline Path candidate when any are true:
- Multiple independent features or a batch implementation request.
- Cross-module or multi-layer impact.
- New data model, API design, infrastructure, external service, or dependency ordering is likely.
- The user wants autonomous/background execution.
- The request needs `feature-planner` to clarify, split, validate, and review feature entries.

### Step 3: Ask for path selection

Use `AskUserQuestion`; do not render path options as plain text.

For existing-project feature work:

```text
Question: How would you like to proceed?
Header: Approach
Options:
- Implement now (Fast Path) — current session/current workspace via simplified /prizmkit-plan -> /prizmkit-implement -> conditional test/review/retro -> /prizmkit-committer
- Use Pipeline Path — feature-planner creates/reviews feature-list.json, then feature-pipeline-launcher configures execution
- Continue clarifying — ask a few more route-level questions before choosing
```

For greenfield app work:

```text
Question: This looks like app-level planning before feature decomposition. How would you like to proceed?
Header: App plan
Options:
- Start app-planner (Recommended) — capture vision, tech stack, conventions, architecture decisions, and project brief first
- Feature-plan anyway — continue only if the user confirms they already have app-level context
- Continue clarifying — resolve whether this is app planning or feature planning
```

For an auto-discovered existing feature list:

```text
Question: Existing feature-list.json found. What should we do with it?
Header: Feature list
Options:
- Launch existing list — hand off to feature-pipeline-launcher
- Inspect summary first — show feature count/status, then ask again
- Update/re-plan — hand off to feature-planner in incremental mode
- Ignore and start fresh — continue route selection from the new request
```

If the user explicitly asked to run an existing list, that explicit request counts as path selection; hand off directly to `feature-pipeline-launcher`.

## Workflow Handoff Brief

When handing off, include this prompt brief in the next skill invocation. Do not write the brief to disk.

```markdown
## Workflow Handoff Brief

### Source
- workflow: feature-workflow
- selected_path: fast_path | pipeline_path | existing_list_launch | app_planning_first

### User Goal
- original_request: <preserve the user's wording>
- normalized_goal: <lightly normalized feature/app goal>

### Scope
- included: <explicitly in scope>
- excluded: <explicitly out of scope or unknown>

### Materials
- provided_paths: <paths/directories supplied by the user>
- provided_docs_or_urls: <docs, links, screenshots, or specs supplied by the user>
- notes: <rules, constraints, or emphasis from the user>

### Decision
- route_reason: <why this path was selected>
- user_confirmed: yes

### Next Skill Instruction
- For planner: Use this brief as input; perform your own required clarification, validation, generation, and review gate.
- For Fast Path: Use this brief to create spec.md/plan.md and implement only this scope.
```

## Selected Path Execution

### Greenfield app path

1. Invoke `app-planner` with the handoff brief.
2. Let `app-planner` capture app-level context and produce its planning artifacts.
3. After `app-planner` completes, ask whether the user wants to decompose the app into executable features.
4. If yes, invoke `feature-planner` with the app-planner output and the original brief.
5. When `feature-planner` finishes and the user entered through this workflow, continue to the Pipeline Launch handoff.

Do not generate `feature-list.json` inside this workflow; `feature-planner` owns that output.

### Fast Path

Use Fast Path only after explicit user selection.

1. Invoke `/prizmkit-plan` with the handoff brief; use simplified planning for this scoped feature.
2. Invoke `/prizmkit-implement` after the plan is ready.
3. Run `/prizmkit-test` only when risk triggers match: behavior, public interface, data model, security/permission/payment, deployment readiness, or explicit user verification request.
4. Run `/prizmkit-code-review` when the user requested review, implementation uncertainty is high, or Full-path-level risk appears during implementation.
5. Run `/prizmkit-retrospective` only when structure, interfaces, dependencies, behavior, or durable project knowledge changed.
6. Run `/prizmkit-committer` with a `feat(<scope>):` message.
7. End the workflow after commit; do not call `feature-planner`, `feature-pipeline-launcher`, or monitoring.

If implementation scope grows beyond the Fast Path criteria, pause and ask whether to switch to Pipeline Path.

### Planner handoff — Pipeline Path

1. Invoke `feature-planner` with the handoff brief.
2. `feature-planner` performs deep clarification, decomposition, validation, and plan review.
3. After `feature-planner` reports a validated `.prizmkit/plans/feature-list.json`, show a concise summary: item count, major dependencies, and review/validation outcome.
4. Ask whether to proceed to launch.
5. **Launcher handoff**: if yes, invoke `feature-pipeline-launcher`.

Do not duplicate launcher execution-mode or configuration questions in this workflow; the launcher owns them.

### Existing list launch

If the user explicitly requested launch/status/logs/retry/stop for an existing feature list, invoke `feature-pipeline-launcher` with the user's intent and list path.

If this workflow discovered the list on its own, use the `Existing feature-list.json found` question in §Route Selection before invoking the launcher.

## Resume Guidance

| State found | Action |
|---|---|
| Fast Path `spec.md` / `plan.md` exists | Ask whether to continue current-workspace implementation or re-plan |
| Valid `.prizmkit/plans/feature-list.json` exists and user wants execution | Invoke `feature-pipeline-launcher` |
| Valid feature list exists but intent is unclear | Ask launch / inspect / update |
| No plan/list artifacts | Start route selection |

For interrupted autonomous pipeline sessions, prefer `feature-pipeline-launcher` status/retry operations or `recovery-workflow` when the user explicitly asks to recover a broken AI session.

## Runtime Status Reference

This workflow does not assemble runtime commands, but it may show lightweight status before handoff or recovery. Use the canonical Python runtime forms:

```bash
python3 ./.prizmkit/dev-pipeline/cli.py daemon feature status
python3 ./.prizmkit/dev-pipeline/cli.py feature status .prizmkit/plans/feature-list.json
```

For start/stop/logs/retry execution, hand off to `feature-pipeline-launcher`; do not duplicate launcher configuration here.

## Error Handling

| Situation | Action |
|---|---|
| Request is app-level, not feature-level | Route to `app-planner` |
| User wants planning only | Route to `feature-planner` and stop after planner summary |
| User wants execution only | Route to `feature-pipeline-launcher` |
| Fast Path becomes complex | Pause and ask whether to switch to Pipeline Path |
| Planner cannot proceed without more detail | Let `feature-planner` ask its own clarification questions |
| Launcher finds preflight/config issues | Let `feature-pipeline-launcher` handle config and confirmation |

## Handoff Map

| From | To | Condition |
|---|---|---|
| `feature-workflow` | `app-planner` | Greenfield or app-level planning is required |
| `feature-workflow` | `/prizmkit-plan` | User selects Fast Path |
| `feature-workflow` | `feature-planner` | User selects Pipeline Path |
| `feature-planner` | `feature-workflow` | Planner completed from workflow-origin Pipeline Path |
| `feature-workflow` | `feature-pipeline-launcher` | User confirms launch after planner completion or explicitly requests existing-list execution |

## Output

- Fast Path: concise `spec.md`, simplified `plan.md`, code changes, conditional test/review evidence when triggered, Prizm docs sync only when durable knowledge changed, and one feature commit.
- Pipeline Path: handoff brief, validated `.prizmkit/plans/feature-list.json` from `feature-planner`, and pipeline launch/status handled by `feature-pipeline-launcher`.
- Greenfield path: app-level planning artifacts from `app-planner`, optionally followed by feature planning and launch.
