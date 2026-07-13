# Generated Plan Review — App Planner

Use this local review loop before app-planner presents the final completion summary for current-session final planning artifacts. This is a planner-output review, not an implementation/code-diff review.

## Trigger

Run only when the current `app-planner` session wrote or rewrote final app-level planning content. This includes project brief finalization, project conventions, infrastructure configuration, architecture decisions, rules files, or a `root.prizm` `RULES:` pointer update.

For explore-only sessions, draft-save exits, validate-only checks, or other flows with no new final planning content, report: `Local generated-plan review: not applicable — no new final planning content written.`

## Direct Artifact Reads

Planning artifacts may be gitignored, untracked, or absent from staged and unstaged diffs. Read the actual files and source sections directly when they were produced or changed in the current session:

- Project brief: `.prizmkit/plans/project-brief.md`
- Draft brief when present: `.prizmkit/plans/project-brief.draft.md`
- Project instruction files selected by `.prizmkit/manifest.json`: `AGENTS.md`, `CLAUDE.md`, `CODEBUDDY.md`
- Generated rule files: `.prizmkit/rules/<layer>-rules.md`
- Prizm docs root pointer: `.prizmkit/prizm-docs/root.prizm` `RULES:` line only
- In-memory answers, draft brief data, rules configuration answers, or section snapshots captured before writes

Do not rely on `git status`, `git diff`, or `git diff --cached` to decide whether app-planner output exists or changed. Do not invoke `/prizmkit-code-review` for this planner-output gate; `/prizmkit-code-review` remains the implementation/code-diff review gate after `/prizmkit-implement`.

## Review Scope

1. Compare current final artifacts with pre-session snapshots or in-memory drafts when available.
2. Review only newly added or changed app-planning sections from the current session.
3. Preserve unchanged historical project brief ideas, instruction-file sections, rules files, and Prizm doc content.
4. For `.prizmkit/prizm-docs/root.prizm`, review only the `RULES:` pointer line managed by rules configuration.
5. If no snapshot exists, review only the artifacts the current app-planner session reports as produced.

## Source-of-Truth Map

- `project-brief.md` fixes go through the draft/checklist project brief source representation described in `project-brief-guide.md`, then rewrite the final brief through the existing project brief writer path.
- Project conventions, infrastructure, and architecture decisions are source sections in `AGENTS.md`, `CLAUDE.md`, or `CODEBUDDY.md`. If a fix changes user-approved wording or meaning, ask for user confirmation before rewriting.
- `.prizmkit/rules/<layer>-rules.md` fixes should re-render from the rules configuration answers and template inputs when available. If no structured source remains, update the source rule section explicitly and report that source path.
- `root.prizm` fixes are limited to correcting or adding the `RULES:` pointer line; do not rewrite unrelated root content.

## Review Checklist

For every reviewed app-planning artifact or section, check:

- Project brief completeness: goal, users, differentiators, constraints, tech stack assumptions, and at least three actionable ideas when producing a final brief
- Consistency among conventions, infrastructure, architecture decisions, and project brief content
- Infrastructure completeness or explicit deferral for database, deployment, and cloud services topics when those flows ran
- Rules pointer consistency: generated `.prizmkit/rules/<layer>-rules.md` files are referenced by the `root.prizm` `RULES:` line when rules were configured
- User-provided wording preservation in project brief ideas, conventions, infrastructure notes, architecture decisions, and rules
- Downstream readiness: `feature-planner` has enough context to produce `.prizmkit/plans/feature-list.json` without guessing core app purpose, stack, constraints, or implementation conventions
- No implementation/scaffolding actions are introduced by the app plan; outputs stay within app-planner's writable boundary

## Fix Loop

1. Present findings with artifact path, section name, severity, evidence, and suggested source change.
2. Accept only findings that improve planner correctness, consistency, user wording preservation, or downstream feature-planner readiness.
3. Apply accepted fixes to the source representation first: brief draft/checklist, instruction-file section source, rules answer/template source, or `root.prizm` `RULES:` pointer source.
4. Regenerate or rewrite final artifacts through the same writer path used by app-planner. Do not hand-patch final artifacts as a shortcut when a draft/source representation exists.
5. Re-read the changed final artifacts directly and re-run the local review only for changed sections.

## Report Format

Report in the final completion summary:

- `Local generated-plan review: PASS` or `NEEDS_FIXES`
- Reviewed app-planning sections/artifacts
- Accepted fixes, or `none`
- Final writer/validation result for each changed artifact
- Note when review was not applicable because no new final planning content was written
