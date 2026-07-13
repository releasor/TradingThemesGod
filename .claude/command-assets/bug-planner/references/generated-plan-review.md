# Generated Plan Review — Bug Planner

Use this local review loop after `.prizmkit/plans/bug-fix-list.json` has been generated and validated. This is a planner-output review, not an implementation/code-diff review.

## Trigger

Run only when the current `bug-planner` session generated, appended, or rewrote final bug planning content. For validate-only, summary-only, or draft-save flows with no new final planning content, report: `Local generated-plan review: not applicable — no new final planning content written.`

## Direct Artifact Reads

Planning artifacts may be gitignored, untracked, or absent from staged and unstaged diffs. Read the actual files directly:

- Final list: `.prizmkit/plans/bug-fix-list.json`
- Draft/source list when present: `.prizmkit/plans/bug-fix-list.draft.json`
- Pre-session final list snapshot if captured in memory before edits
- In-memory draft object if the session has not written a draft file yet

Do not rely on `git status`, `git diff`, or `git diff --cached` to decide whether planner output exists or changed. Do not invoke `/prizmkit-code-review` for this planner-output gate; `/prizmkit-code-review` remains the implementation/code-diff review gate after `/prizmkit-implement`.

## Review Scope

1. If a pre-session final list exists, compare by stable bug IDs (`B-*`).
2. Treat bugs as changed only when item fields changed. Ignore root generator metadata and formatting-only differences such as `$schema`, `created_at`, and `created_by`.
3. Review newly added bug IDs and changed bug IDs.
4. Preserve unchanged historical bugs. Read unchanged entries only when needed to verify dependency references, duplicate handling, or root-cause overlap with reviewed bugs.
5. If no snapshot exists, review all bug entries produced by the current generation flow.

## Review Checklist

For every reviewed bug entry, check:

- Schema compatibility with `dev-pipeline-bug-fix-list-v1` and `.prizmkit/dev-pipeline/templates/bug-fix-list-schema.json`
- Dependency/DAG consistency, duplicate handling, and root-cause overlap
- Description completeness: expected vs actual behavior, reproduction path, code-location hints, affected environment, and headless execution readiness
- Acceptance criteria specificity and measurable verification method
- User-provided wording preservation in `description`, `acceptance_criteria`, and `user_context`
- Task-scoped `user_context` isolation: no unrelated sibling bug descriptions, logs, stack traces, reproduction steps, expected/actual behavior notes, or supplementary materials; shared context appears on multiple bugs only when explicitly global
- Severity/priority calibration: every reviewed bug has a short severity rationale and priority rationale, the preserved severity-to-priority mapping is followed, and high priority is not used without core outage, data loss/integrity, security/auth, timeout/crash, or no-workaround indicators
- Browser interaction and verification fields for UI-reproducible bugs when applicable

## Fix Loop

1. Present findings with IDs, severity, evidence, and suggested draft/source changes.
2. Accept only findings that improve planner correctness, completeness, or downstream bug-fix execution readiness.
3. Apply accepted fixes to `.prizmkit/plans/bug-fix-list.draft.json` or the in-memory draft object first.
4. Regenerate the final list through the existing generator:

```bash
python3 ${SKILL_DIR}/scripts/validate-bug-list.py generate --input .prizmkit/plans/bug-fix-list.draft.json --output .prizmkit/plans/bug-fix-list.json
```

5. Re-run validation/generation until valid. Do not hand-patch `.prizmkit/plans/bug-fix-list.json` as the source of truth.
6. Repeat the local review only for entries changed by accepted fixes.

## Report Format

Report in the final handoff summary:

- `Local generated-plan review: PASS` or `NEEDS_FIXES`
- Reviewed bug IDs
- Accepted fixes, or `none`
- Final validation result
- Note when review was not applicable because no new final planning content was written
