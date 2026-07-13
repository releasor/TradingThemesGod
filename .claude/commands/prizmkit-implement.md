---
description: "Execute plan.md tasks with a TDD-oriented approach. Respects task ordering, checkpoints, and dependencies for Fast path or Full path change artifacts. Reads Prizm docs before editing; optional inline implementation subagent delegation uses this skill's references and active-checkout/no-worktree constraints. Use after /prizmkit-plan. Trigger on: 'implement', 'build', 'code it', 'start coding', 'execute', 'write the code'. (project)"
---

# PrizmKit Implement

### When to Use
- After `/prizmkit-plan` when ready to write code
- Fast path or Full path has a `plan.md` with unchecked tasks
- User says "implement", "build", "code it", "start coding", "develop", or "execute"

### When NOT to Use
- No `plan.md` exists and the task is not a Direct edit — run `/prizmkit-plan` first
- All tasks in `plan.md` are checked off
- Direct edit: typo, pure formatting, small docs edit, or tiny config tweak with no behavior impact
- User is still asking for design/planning rather than implementation

## Preconditions

| Required Artifact | Check | If Missing |
|---|---|---|
| `plan.md` with Tasks section | File exists and has unchecked tasks | Run `/prizmkit-plan` |
| `spec.md` | File exists in same artifact directory | Run `/prizmkit-plan` |

Artifact directory: accept `artifact_dir` from caller. If not provided, scan `.prizmkit/` subdirectories for the most recently modified `plan.md` with unchecked tasks. When invoked as a handoff step, reuse the previous skill's `artifact_dir`; re-detection can select the wrong change artifact in a multi-task workspace.

## Context Loading

Before implementation, load context once:

1. **Task context**: read `plan.md` and `spec.md`. If companion documents exist in the artifact directory, read only those relevant to the change.
2. **Architecture context**:
   - Read `.prizmkit/prizm-docs/root.prizm`.
   - Read relevant L1 docs for affected modules.
   - Read relevant L2 docs when they exist, especially INTERFACES, TRAPS, and DECISIONS.
   - If a relevant L2 doc does not exist, read the target source files as fallback and note that no L2 was available. Do not stop implementation only because L2 is missing; `/prizmkit-retrospective` can create L2 after the change if durable detail exists.
3. **Dev rules**: if root Prizm docs reference `.prizmkit/rules/<layer>-rules.md`, read the relevant rule files. If a referenced rule file is missing, skip it and continue.

If a dev rule conflicts with `plan.md`, call out the conflict and ask the user unless the plan clearly supersedes the rule.

## Optional Inline Implementation Subagent Delegation

The default execution mode is direct Main Agent implementation. If delegation is useful for a narrow implementation slice, use only this skill's local reference:

```yaml
prompt_reference: .claude/command-assets/prizmkit-implement/references/implementation-subagent-procedure.md
isolation: current-workspace / active-checkout / no-worktree
subagent_kind: inline implementation prompt, not a platform-installed named agent
```

Delegation rules:
- Read `.claude/command-assets/prizmkit-implement/references/implementation-subagent-procedure.md` before preparing the subagent prompt.
- Pass the expected active checkout git top-level and the exact delegated task/file scope.
- Do not use worktree isolation, copied checkouts, remote isolated checkouts, branch switching, or a platform-installed named implementation agent.
- If active-checkout/no-worktree launch cannot be satisfied, stop with:

```text
Cannot delegate /prizmkit-implement because this platform cannot start an inline implementation subagent in the active checkout without worktree, copy, remote, or branch isolation.
```

## Execution

For each unchecked task in `plan.md`, in order:

1. Confirm relevant context for the target files is loaded: L1, L2 when present, or source fallback when L2 is absent.
2. Apply TDD where applicable:
   - Write or update a failing test first for behavior changes.
   - For UI-only, docs, configuration, or mechanical refactors where test-first does not apply, use the smallest meaningful verification instead.
3. Follow internal ID hygiene: do not place PrizmKit feature/bug/refactor IDs, task IDs, session/run IDs, branch names, absolute worktree paths, or `.prizmkit/specs` / `.prizmkit/dev-pipeline` artifact paths in `.prizmkit/prizm-docs/`, user-visible UI text, API responses, emails, notifications, or tests that assert visible product copy.
4. Cover relevant paths for changed logic:
   - happy path
   - domain-specific edge cases
   - error conditions
   Do not force meaningless edge/error tests when the function has none.
5. Avoid redundant tests. Check existing coverage before adding a new test; each new test should exercise a distinct behavior or boundary.
6. Test your own code and integration points, not framework internals, third-party library internals, or language built-ins.
7. Mark the task as `[x]` immediately after completion. Immediate marking makes interrupted sessions resumable.
8. Respect task semantics:
   - Sequential tasks stop on failure when later tasks depend on them.
   - `[P]` tasks may run in parallel within the same safe group.
   - `CP:` checkpoint tasks require build/tests/verification specified by the plan before continuing.
9. After all tasks complete, run the verification appropriate to the chosen path and risk. Full test orchestration via `/prizmkit-test` is risk-triggered, not mandatory for every change.

## Recovery

If a session is interrupted:

- Completed tasks should already be marked `[x]`.
- Re-run `/prizmkit-implement`; it resumes from the first unchecked task.
- If partially edited files exist without a completed task marker, inspect the diff and either finish the task or revert incomplete work before continuing.

## Output

- Code files created/modified as specified in `plan.md`
- `plan.md` Tasks section updated with `[x]` markers
- Implementation summary
- Suggested next step:
  - Full path or review-triggered risk: `/prizmkit-code-review`
  - Risk-triggered testing: `/prizmkit-test`
  - Docs/durable knowledge changed: `/prizmkit-retrospective`
  - Otherwise: `/prizmkit-committer`
