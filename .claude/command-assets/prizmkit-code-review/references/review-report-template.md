# Review Report Lifecycle Template

`{artifact_dir}/review-report.md` is the only required persisted review artifact.

## Execution Start

Every `/prizmkit-code-review` execution replaces any prior report with:

```markdown
# Review Report

## Status: IN_PROGRESS
```

Within that execution, append sections only. Never edit or replace an earlier progress section.

## Progress Sections

### Main-Agent Review Round

```markdown
## Main Review Round <N>

- Status: COMPLETED
- Findings: <count>
- Accepted: <count>
- Rejected: <count>
- Unresolved: <count>
- Next: <next action>
```

### Repair Verification

```markdown
## Repair Verification

- Fixed Findings: <count>
- Verification: <evidence summary>
- Next: <next action>
```

### Final Verification

```markdown
## Final Verification

- Status: <COMPLETED|FAILED>
- Evidence: <evidence summary>
```

## Final Result

Exactly one Final Result terminates a completed execution:

```markdown
## Final Result

- Verdict: <PASS | NEEDS_FIXES>
- Main Review Rounds: <count>
- Accepted Findings: <count>
- Fixed Findings: <count>
- Rejected Findings: <count>
- Unresolved Findings: <count>
- Summary: <concise conclusion>
```

## Rules

- Start of a new execution removes stale progress and terminal results from prior executions.
- A phase appends its result before the next phase starts.
- Finding counts satisfy `accepted + rejected + unresolved = findings`.
- `PASS` requires every accepted finding fixed and zero unresolved findings.
- `NEEDS_FIXES` requires at least one unfixed accepted or unresolved finding.
- An IN_PROGRESS report without Final Result is incomplete.
- Generic or incidental verdict text outside the last Final Result does not prove completion.
- Do not append any section after Final Result.
- Do not persist a separate review-state JSON file.
