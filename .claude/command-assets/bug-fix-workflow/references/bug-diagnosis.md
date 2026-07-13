# Bug Diagnosis — Question Framework

Procedural details for systematic bug clarification in bug-fix-workflow Phase 1.

## Step 1.2: Systematic Bug Clarification

Ask questions across these dimensions until every aspect is clear. **Adapt to what the user has already provided** — skip questions that are already answered.

### Reproduction Conditions
- What exact steps trigger the bug? (step-by-step)
- Which environment/browser/OS/version?
- Is it reproducible every time, or intermittent?
- When did it first appear? (after a specific change/deploy?)
- Does it happen for all users or only specific accounts/roles/data?

### Expected vs Actual Behavior
- What should happen? (the correct behavior)
- What actually happens? (the buggy behavior)
- Is there partial functionality (e.g., works for some inputs but not others)?

### Scope and Impact
- Which features/pages/modules are affected?
- Are there workarounds users are currently using?
- Is this blocking other work?
- Are there related symptoms elsewhere?

### Data and State
- What data/state triggers the issue? (specific input values, DB state, user session state)
- Does the bug involve data corruption or just incorrect display/behavior?
- If database-related: which tables/records are affected?

### Error Details (if not already provided)
- Full error message and stack trace?
- Browser console errors?
- Server-side logs?
- Network request/response details?

> Complexity assessment (simple vs complex routing) and the comparison with the
> background pipeline live in the skill body (§Step 1.4 and §Comparison with
> Pipeline Bug Fix) — they are flow-control decisions, kept here only by pointer
> to avoid drift.
