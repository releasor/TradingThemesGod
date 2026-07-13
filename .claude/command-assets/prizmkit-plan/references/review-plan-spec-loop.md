# Review Plan/Spec Loop

## Purpose

Run this local planning-quality gate after `spec.md` and `plan.md` are drafted or updated, before handing off to `/prizmkit-implement`.

This is not a separate skill and it does not use a Critic agent. It is a bounded review loop executed inside `prizmkit-plan` to improve the planning artifacts only.

## Non-Goals

Do not do any of the following from this guide:

- Start implementation or edit product/source code.
- Run tests, builds, lint, or package commands.
- Launch a feature, bugfix, or refactor pipeline.
- Spawn or require a Critic agent.
- Create a separate review-loop skill.
- Expand scope beyond improving `spec.md` and `plan.md`.

## Required Inputs

- `spec.md` in the selected artifact directory.
- `plan.md` in the selected artifact directory.
- Relevant Prizm docs and source summaries already loaded by `prizmkit-plan`.

Use source reads sparingly. Prefer the context already loaded for planning. Read additional source only when a finding cannot be classified without confirming an existing interface, naming pattern, dependency, or constraint.

## Review Dimensions

Review both artifacts against these dimensions:

| Dimension | Check |
|---|---|
| Ambiguity | Requirements, scope, terms, or expected behavior are unclear or internally inconsistent. |
| Acceptance criteria completeness | Each goal has verifiable acceptance criteria; edge/error cases are included when meaningful. |
| Missing constraints | Security, data, compatibility, performance, platform, deployment, migration, or non-goal constraints are absent where relevant. |
| Task ordering errors | Tasks are sequenced before their prerequisites, checkpoints are misplaced, or dependency order is unsafe. |
| Dependency assumptions | The plan assumes missing APIs, schemas, files, services, packages, auth, environment variables, or generated artifacts without evidence. |
| Scope drift | The plan adds unrelated work, backlog items, nice-to-haves, or implementation beyond the spec. |
| Overengineering | The plan introduces abstractions, services, agents, workflows, data stores, or cross-module rewrites that the spec does not justify. |
| Implementation readiness | Tasks are actionable, file-scoped when possible, testable, and resumable; blockers are explicit. |
| Source-reading overhead | The implementation plan avoids broad rereads and identifies the minimum context/files needed for execution. |

## Finding Classification

Use exactly these classifications:

### BLOCKER

A finding is `BLOCKER` when implementation would likely fail, produce the wrong behavior, or require user clarification before a safe plan exists.

Examples:
- Acceptance criteria contradict each other.
- A required interface/data model decision is unresolved.
- The task order starts implementation before required schema/context decisions.
- The plan includes scope that conflicts with explicit non-goals.

### SHOULD_FIX

A finding is `SHOULD_FIX` when the artifact can be improved directly without changing user intent or requiring clarification.

Examples:
- Add missing acceptance criteria derived from the stated goal.
- Clarify a constraint already implied by the task context.
- Reorder dependent tasks.
- Remove an unjustified overengineered step.
- Add a minimal file/context note to reduce source-reading overhead.

### OPTIONAL

A finding is `OPTIONAL` when it is a nice-to-have improvement that does not block implementation readiness.

Examples:
- Extra detail that could help but is not necessary.
- Alternative task grouping with no correctness impact.
- A lower-risk cleanup suggestion outside current scope.

Optional findings do not block handoff.

## Loop Algorithm

1. Read this guide, then review the current `spec.md` and `plan.md` together.
2. Produce a concise internal finding list grouped by `BLOCKER`, `SHOULD_FIX`, and `OPTIONAL`.
3. Apply fixes directly to `spec.md` and/or `plan.md` for:
   - every `BLOCKER` that can be resolved from existing task context;
   - every `SHOULD_FIX` that is accepted as aligned with the user's intent.
4. Do not apply `OPTIONAL` findings unless they clearly improve readiness without expanding scope.
5. If any fixes were applied, rerun this review once.
6. Stop after at most 2 total review rounds.
7. If unresolved `BLOCKER` findings remain after the final round, stop planning and ask targeted clarification questions. Do not escalate to a Critic agent.
8. If no unresolved blockers remain, report that the planning quality gate passed and hand off to `/prizmkit-implement`.

## Output Summary

At handoff, include a short summary:

- Review rounds run: `1` or `2`.
- Fixes applied to `spec.md`: short list or `none`.
- Fixes applied to `plan.md`: short list or `none`.
- Optional findings deferred: short list or `none`.
- Unresolved blockers: `none` before handoff.
