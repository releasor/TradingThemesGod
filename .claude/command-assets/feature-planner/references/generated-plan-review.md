# Generated Plan Review — Feature Planner

Use this local review loop after `.prizmkit/plans/feature-list.json` has been generated and validated. This is a planner-output review, not an implementation/code-diff review.

## Trigger

Run only when the current `feature-planner` session generated, appended, or rewrote final feature planning content. For validate-only, summary-only, or draft-save flows with no new final planning content, report: `Local generated-plan review: not applicable — no new final planning content written.`

## Direct Artifact Reads

Planning artifacts may be gitignored, untracked, or absent from staged and unstaged diffs. Read the actual files directly:

- Final list: `.prizmkit/plans/feature-list.json`
- Draft/source list when present: `.prizmkit/plans/feature-list.draft.json`
- Pre-session final list snapshot if captured in memory before edits
- In-memory draft object if the session has not written a draft file yet

Do not rely on `git status`, `git diff`, or `git diff --cached` to decide whether planner output exists or changed. Do not invoke `/prizmkit-code-review` for this planner-output gate; `/prizmkit-code-review` remains the implementation/code-diff review gate after `/prizmkit-implement`.

## Review Scope

1. If a pre-session final list exists, compare by stable feature IDs (`F-*`).
2. Treat features as changed only when item fields changed. Ignore root generator metadata and formatting-only differences such as `$schema`, `created_at`, and `created_by`.
3. Review newly added feature IDs and changed feature IDs.
4. Preserve unchanged historical features. Read unchanged entries only when needed to verify dependency references from reviewed features.
5. If no snapshot exists, review all feature entries produced by the current generation flow.

## Review Checklist

For every reviewed feature entry, check:

- Schema compatibility with `dev-pipeline-feature-list-v1` and `.prizmkit/dev-pipeline/templates/feature-list-schema.json`
- Dependency/DAG soundness: dependencies exist, no cycles, no poorly ordered prerequisite chains
- Description completeness and headless execution readiness
- Acceptance criteria specificity, measurability, and coverage of the described behavior
- User-provided wording preservation in `description`, `acceptance_criteria`, and `user_context`
- Task-scoped `user_context` isolation: no unrelated sibling feature descriptions, file references, or supplementary materials; shared context appears on multiple items only when explicitly global
- Priority/complexity calibration: every reviewed feature has short priority and complexity rationales, medium/low assignments are allowed when criteria fit, and high/high is not used merely because work is framework-related, multi-file, or user-requested
- Browser interaction fields for qualifying frontend/fullstack features when applicable

## Fix Loop

1. Present findings with IDs, severity, evidence, and suggested draft/source changes.
2. Accept only findings that improve planner correctness, completeness, or downstream execution readiness.
3. Apply accepted fixes to `.prizmkit/plans/feature-list.draft.json` or the in-memory draft object first.
4. Regenerate the final list through the existing generator:

```bash
python3 ${SKILL_DIR}/scripts/validate-and-generate.py generate --input .prizmkit/plans/feature-list.draft.json --output .prizmkit/plans/feature-list.json
```

5. Re-run validation/generation until valid. Do not hand-patch `.prizmkit/plans/feature-list.json` as the source of truth.
6. Repeat the local review only for entries changed by accepted fixes.

## Report Format

Report in the final handoff summary:

- `Local generated-plan review: PASS` or `NEEDS_FIXES`
- Reviewed feature IDs
- Accepted fixes, or `none`
- Final validation result
- Note when review was not applicable because no new final planning content was written
