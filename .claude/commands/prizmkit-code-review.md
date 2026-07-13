---
description: Review the complete current change in a bounded Main-Agent loop. Adjudicate findings with evidence, directly repair accepted findings, verify repairs, and append progress until the review converges to PASS or stops with unresolved findings as NEEDS_FIXES. (project)
---

# PrizmKit Code Review

Use one Main-Agent review loop. The Main Agent performs the complete review, filters candidate findings, repairs accepted findings, verifies the repairs, and decides the final result without delegating code review.

## When to Use

- After `/prizmkit-implement` as the Full path quality gate
- For Fast path when behavior, impact, or the user warrants review
- When the user asks to validate implementation, find defects, assess regressions, or decide commit readiness

## Input

| Parameter | Required | Description |
|---|---|---|
| `artifact_dir` | No | Directory containing `spec.md` and `plan.md`. Reuse a caller-provided directory; otherwise locate the current completed change artifact. |

## Required Asset

- `.claude/command-assets/prizmkit-code-review/references/review-report-template.md`: report lifecycle and append contract

## Phase 0: Initialize Report and Collect Context

1. Resolve `{artifact_dir}` and `{artifact_dir}/review-report.md`.
2. At the start of every execution, replace any prior report with a new execution header using the report template. The new report begins with `## Status: IN_PROGRESS` and contains no prior Final Result.
3. Read `spec.md`, `plan.md`, relevant `/prizmkit-test` evidence, `.prizmkit/prizm-docs/root.prizm`, applicable progressive docs, and project rules.
4. Inspect the complete current Git change:
   - staged and unstaged tracked changes;
   - untracked files;
   - deleted and renamed files;
   - relevant unchanged callers, dependents, contracts, and tests.
5. Review in the active workspace so dirty and untracked content is authoritative.
6. If no changes exist, append final verification and exactly one final result with `PASS`, then finish.

## Phase 1: Main-Agent Review Loop

The Main Agent reviews and repairs in the current context. The fixed limit is ten completed review rounds.

Track cumulative counts:

```yaml
main_review_rounds: 0
accepted_findings: 0
fixed_findings: 0
rejected_findings: 0
unresolved_findings: 0
```

### Review One Round

Each round examines the complete current change against goals, contracts, rules, callers, dependents, regression risks, and test evidence.

1. Identify concrete candidate findings. A finding must describe a reproducible failure scenario, affected behavior, and supporting evidence.
2. Classify each candidate as exactly one of:
   - `accepted`: concrete evidence supports the failure scenario and an in-scope repair is required;
   - `rejected`: code, tests, contracts, or governing evidence disproves the failure scenario;
   - `unresolved`: correctness cannot be established or repaired safely with the available evidence or environment.
3. Treat Missing tools, permissions, environment, or required evidence as an unresolved finding when they prevent required verification. Do not treat missing evidence as success.
4. Append `## Main Review Round N` with findings, accepted, rejected, unresolved, and the next action.
5. Apply these rules:

```text
accepted = 0 and unresolved = 0                     -> review converged
accepted > 0 and round < 10                         -> Main Agent directly repairs, verifies, and continues
accepted > 0 at ten completed review rounds         -> NEEDS_FIXES
unresolved > 0                                      -> NEEDS_FIXES
repair cannot be completed safely                   -> unresolved finding -> NEEDS_FIXES
required verification fails or cannot be performed -> unresolved finding -> NEEDS_FIXES
```

When all candidate findings are rejected, `accepted = 0` and `unresolved = 0`, so the review converges. Rejected findings do not cause another round.

## Phase 2: Repair and Verification

When a round has accepted findings and fewer than ten rounds have completed:

1. Main Agent directly repairs every accepted in-scope finding in the active workspace.
2. Run targeted tests, static checks, or other verification appropriate to each repaired behavior.
3. Inspect resulting changes and ensure the repair did not introduce a new regression.
4. Append `## Repair Verification` with fixed findings, verification evidence, and the next round.
5. Start the next complete review round.

If a repair is unsafe, incomplete, or cannot receive required verification, record the affected finding as unresolved and finish with `NEEDS_FIXES`.

## Phase 3: Append-Only Reporting

`{artifact_dir}/review-report.md` is the only required persisted review artifact.

Within one execution, append new sections only. Do not rewrite an earlier progress section. Append after:

- every Main-Agent review round;
- every repair and verification batch;
- final verification;
- the final result.

An interrupted execution remains `IN_PROGRESS` and shows its latest completed phase. It has no terminal verdict.

## Phase 4: Final Verification and Result

Before completing:

1. Confirm the final workspace still represents the complete reviewed change.
2. Confirm required tests and checks have credible evidence.
3. Confirm no accepted or unresolved finding remains for `PASS`.
4. Append `## Final Verification`.
5. Append exactly one final result:

```markdown
## Final Result

- Verdict: PASS | NEEDS_FIXES
- Main Review Rounds: <count>
- Accepted Findings: <count>
- Fixed Findings: <count>
- Rejected Findings: <count>
- Unresolved Findings: <count>
- Summary: <concise conclusion>
```

Final outcomes:

- `PASS`: review converged with `accepted = 0`, `unresolved = 0`, and required verification evidence is complete.
- `NEEDS_FIXES`: round ten still has accepted findings, any finding remains unresolved, a repair cannot be completed safely, or required verification is unavailable or failed.

Exactly one final result is allowed. Do not append progress after Final Result.

Completion handoff:

- `PASS`: run `/prizmkit-retrospective` when structural docs or durable knowledge changed; otherwise proceed to `/prizmkit-committer`.
- `NEEDS_FIXES`: report unresolved findings and stop.
