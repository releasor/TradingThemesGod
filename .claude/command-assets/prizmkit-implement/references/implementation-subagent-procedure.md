# Implementation Subagent Procedure

Use this reference only when `/prizmkit-implement` deliberately delegates implementation work to an inline implementation subagent. The default path remains direct Main Agent implementation. Delegation is allowed only when the active-checkout/no-worktree contract below can be satisfied.

## Launch Contract

The Main Agent must provide:
- Artifact directory containing `spec.md`, `plan.md`, and `context-snapshot.md` when available.
- Expected active checkout git top-level from the Main Agent's workspace.
- The exact plan tasks or files delegated.
- Any loaded Prizm docs traps/rules relevant to the delegated files.

The implementation subagent must run in the same active checkout as the Main Agent.

## Active Checkout Guard

Before reading or editing files, verify your current git top-level matches the expected active checkout git top-level provided by the Main Agent.

Stop immediately and report `WRONG_CHECKOUT` if any of these are true:
- You are running from a git worktree, tool-created worktree, `.claude/worktrees/`, `.prizmkit/state/worktrees/`, copied repository checkout, remote isolated checkout, or temporary clone.
- Your current git top-level differs from the expected active checkout git top-level.
- You are on a different branch because the launch path switched branches.
- You would need to create or enter another checkout to complete the work.

Do not create worktrees, copied repositories, remote checkouts, or branch switches. Do not continue from the wrong checkout even if files appear identical.

## Context Loading

1. Read `context-snapshot.md` first when it exists.
2. Use Section 3 for relevant Prizm rules/traps and Section 4 File Manifest for file summaries.
3. Do not re-read files already summarized in the File Manifest unless a specific implementation detail is missing.
4. If no context snapshot exists, read `.prizmkit/prizm-docs/root.prizm`, relevant L1/L2 docs, then targeted source files.
5. If a relevant L2 doc is missing, use source fallback and note that retrospective may create or update docs later.

## Implementation Rules

- Implement only the tasks delegated by the Main Agent and follow `plan.md` task order.
- Use TDD where meaningful: update/write the smallest relevant test first for behavior changes, then implement, then run the smallest useful check.
- For docs/config/mechanical refactors where test-first is not meaningful, use the smallest verification that proves the change.
- Mark delegated `plan.md` tasks `[x]` immediately after completion when the Main Agent explicitly authorizes task marking; otherwise report completed task IDs to the Main Agent for marking.
- Do not execute git `add`, `commit`, `reset`, `push`, branch checkout, rebase, merge, or stash operations.
- Do not spawn further agents.
- Do not perform broad repository rediscovery. Read only delegated files and targeted dependencies needed for correctness.
- Do not write PrizmKit feature/bug/refactor/task/session/run IDs, pipeline IDs, workflow IDs, branch names, absolute worktree paths, or `.prizmkit/specs` / `.prizmkit/dev-pipeline` artifact paths into `.prizmkit/prizm-docs/`, user-visible UI text, API responses, emails, notifications, or expected product-copy tests.
- If creating a new sub-module, note the durable facts needed for retrospective; do not overwrite existing `.prizmkit/prizm-docs/` files in full.

## Output Format

Report exactly:

```text
### Result: COMPLETED | BLOCKED | WRONG_CHECKOUT

### Completed Tasks
- [task id or description]

### Files Changed
- path: summary

### Verification
- command/check: result

### Notes for Main Agent
- durable decisions, missing L2 docs, or blockers
```

For `WRONG_CHECKOUT`, include only the checkout mismatch evidence and do not include normal implementation findings.
