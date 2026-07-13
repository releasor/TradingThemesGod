# Recovery Phase Detection

Detection uses priority-ordered signals, but no single signal is authoritative. Prefer a conservative recovery phase when signals disagree.

## Signature Priority

1. Current branch starts with `fix/` -> likely `bug-fix-workflow`.
2. `.prizmkit/state/bugfix/` or `.prizmkit/plans/bug-fix-list.json` has relevant failed/in-progress state -> likely bugfix pipeline.
3. `.prizmkit/bugfix/` has optional bugfix artifacts -> possible `bug-fix-workflow`.
4. Current branch starts with `refactor/` -> likely `refactor-workflow`.
5. `.prizmkit/plans/refactor-list.json` or `.prizmkit/state/refactor/` exists -> likely refactor pipeline.
6. Current branch starts with `feat/` -> likely `feature-workflow`.
7. `.prizmkit/plans/feature-list.json` or `.prizmkit/state/features/` exists -> likely feature pipeline.
8. `spec.md` or `plan.md` exists without family-specific signals -> current-workspace Fast Path; ask which workflow it belongs to.
9. None of the above -> no workflow detected.

Bug-fix signals are prioritized because interactive bug recovery benefits most from preserving local diagnosis and fix work.

## Optional vs Required Artifacts

`fix-plan.md` and `fix-report.md` are optional bug recovery signals. They are useful when present, but bug-fix recovery must also infer from branch, diff, `spec.md`, `plan.md`, review artifacts, commits, and bug-list entries.

## If No Workflow Is Detected

Show guidance and exit:

```markdown
No interrupted workflow was detected in this workspace.

Start a new workflow:
- /feature-workflow — build features from idea to code
- /bug-fix-workflow — fix a specific bug interactively
- /refactor-workflow — restructure code while preserving behavior
```

## Phase Inference Tables

### Bug-Fix Recovery

| Detected state | Resume from | Actions |
|---|---|---|
| `fix/*` branch, no implementation artifacts | Diagnosis / triage | Restore bug context, confirm understanding, choose next action |
| `spec.md` or `plan.md`, no code changes | Fix | Read plan and implement the root-cause fix |
| Optional `fix-plan.md`, no code changes | Fix | Read fix plan and implement the fix |
| Code/test changes, no review artifact | Review | Run tests if safe, then invoke `/prizmkit-code-review` |
| Review artifact or optional `fix-report.md` | User verification | Ask user whether to verify manually before commit |
| Commit ahead on fix branch | Merge decision | Ask merge / keep branch / decide later |

Bug-fix diagnosis, triage, and reproduction do not always create durable artifacts. If interrupted before code changes or a plan artifact, restart from diagnosis rather than guessing.

### Feature Recovery

| Detected state | Resume from | Actions |
|---|---|---|
| No feature list and no Fast Path artifacts | Route selection | Clarify whether to plan, implement Fast Path, or start app planning |
| `spec.md` or `plan.md` with feature context | Fast Path continuation | Continue implementation, review, retrospective, or commit based on diff |
| `.prizmkit/plans/feature-list.json`, no pipeline state | Launch | Invoke `feature-pipeline-launcher` |
| Feature list plus `.prizmkit/state/features/` | Monitor/recover | Check launcher status or run recovery script |

### Refactor Recovery

| Detected state | Resume from | Actions |
|---|---|---|
| No refactor list and no Fast Path artifacts | Route selection | Clarify behavior-preserving refactor goal |
| `spec.md` or `plan.md` with refactor context | Fast Path continuation | Continue implementation, behavior checks, review, retrospective, or commit |
| `.prizmkit/plans/refactor-list.json`, no pipeline state | Launch | Invoke `refactor-pipeline-launcher` |
| Refactor list plus `.prizmkit/state/refactor/` | Monitor/recover | Check launcher status or run recovery script |
