# Generated Plan Review — Refactor Planner

Use this local review loop after `.prizmkit/plans/refactor-list.json` has been generated and validated. This is a planner-output review, not an implementation/code-diff review.

## Trigger

Run only when the current `refactor-planner` session generated, appended, or rewrote final refactor planning content. For validate-only, summary-only, or draft-save flows with no new final planning content, report: `Local generated-plan review: not applicable — no new final planning content written.`

## Direct Artifact Reads

Planning artifacts may be gitignored, untracked, or absent from staged and unstaged diffs. Read the actual files directly:

- Final list: `.prizmkit/plans/refactor-list.json`
- Draft/source list when present: `.prizmkit/plans/refactor-list.draft.json`
- Pre-session final list snapshot if captured in memory before edits
- In-memory draft object if the session has not written a draft file yet

Do not rely on `git status`, `git diff`, or `git diff --cached` to decide whether planner output exists or changed. Do not invoke `/prizmkit-code-review` for this planner-output gate; `/prizmkit-code-review` remains the implementation/code-diff review gate after `/prizmkit-implement`.

## Review Scope

1. If a pre-session final list exists, compare by stable refactor IDs (`R-*`).
2. Treat refactors as changed only when item fields changed. Ignore root generator metadata and formatting-only differences such as `$schema`, `created_at`, and `created_by`.
3. Review newly added refactor IDs and changed refactor IDs.
4. Preserve unchanged historical refactors. Read unchanged entries only when needed to verify dependency references or behavior-preservation interactions with reviewed refactors.
5. If no snapshot exists, review all refactor entries produced by the current generation flow.

## Review Checklist

For every reviewed refactor entry, check:

- Schema compatibility with `dev-pipeline-refactor-list-v1` and `.prizmkit/dev-pipeline/templates/refactor-list-schema.json`
- Dependency/DAG soundness, including safe behavior-preserving order
- Description completeness, target scope clarity, and headless execution readiness
- Acceptance criteria specificity and measurable behavior-preservation verification
- `behavior_preservation` strategy quality and consistency with target scope and existing tests
- User-provided wording preservation in `description`, `acceptance_criteria`, and `user_context`
- Task-scoped `user_context` isolation: no unrelated sibling refactor goals, target files, constraints, desired end states, or supplementary materials; shared context appears on multiple items only when explicitly global
- Priority/complexity calibration: every reviewed refactor has short priority and complexity rationales, medium/low assignments are allowed when criteria fit, and high/high is not used merely because the work is cleanup, framework-related, multi-file, or user-requested

## Fix Loop

1. Present findings with IDs, severity, evidence, and suggested draft/source changes.
2. Accept only findings that improve planner correctness, completeness, or downstream behavior-preserving execution readiness.
3. Apply accepted fixes to `.prizmkit/plans/refactor-list.draft.json` or the in-memory draft object first.
4. Regenerate the final list through the existing generator:

```bash
python3 ${SKILL_DIR}/scripts/validate-and-generate-refactor.py generate --input .prizmkit/plans/refactor-list.draft.json --output .prizmkit/plans/refactor-list.json
```

5. Re-run validation/generation until valid. Do not hand-patch `.prizmkit/plans/refactor-list.json` as the source of truth.
6. Repeat the local review only for entries changed by accepted fixes.

## Report Format

Report in the final handoff summary:

- `Local generated-plan review: PASS` or `NEEDS_FIXES`
- Reviewed refactor IDs
- Accepted fixes, or `none`
- Final validation result
- Note when review was not applicable because no new final planning content was written
