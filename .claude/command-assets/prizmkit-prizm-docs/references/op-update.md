# Operation: Update — Out-of-Band Repair/Resync

Repair `.prizmkit/prizm-docs/` after docs drifted outside the normal development loop.

PRECONDITION: `.prizmkit/prizm-docs/` exists with `root.prizm`.

Use this operation for manual edits, merges, rebases, branch switches, generated code movement, or other changes that did not pass through `/prizmkit-retrospective`. During ordinary feature/bugfix/refactor work, use `/prizmkit-retrospective` instead.

STEPS:
1. Identify drift source. Prefer explicit user context; otherwise inspect git changes with `git diff --cached --name-status`, then `git diff --name-status`. If no git changes exist, run a bounded rescan comparing code structure against existing docs.
2. Map changed files to modules by matching MODULE_INDEX or MODULE_GROUPS in `root.prizm`.
3. Classify each change: A (added) -> new KEY_FILES entries; D (deleted) -> remove entries and update counts; M (modified) -> check dependency/interface/data-flow impact; R (renamed) -> update path references.
4. Update affected docs bottom-up: L2 first for INTERFACES/DATA_FLOW/DEPENDENCIES/TRAPS/DECISIONS, then L1 for FILES/KEY_FILES/SUBDIRS/DEPENDENCIES, then L0 only for structural module changes. L1 does not contain INTERFACES, DATA_FLOW, TRAPS, or DECISIONS.
5. Preserve `PROJECT_BRIEF:` in `root.prizm`; it is managed by `/prizmkit-init`.
6. Do not write CHANGELOG sections/files, UPDATED/date metadata, feature/bug/refactor/task/session/run/pipeline/workflow IDs, branch names, absolute worktree paths, or `.prizmkit/specs` / `.prizmkit/dev-pipeline` artifact paths.
7. Skip updates for comments/whitespace/formatting-only changes, `.prizm`-only changes, and test-only changes that reveal no durable boundaries, traps, interface constraints, behavior rules, or regression knowledge.
8. If a new directory qualifies as a module and matches no existing module, create L1 immediately and add it to MODULE_INDEX or MODULE_GROUPS. Create L2 only when source files contain meaningful behavior worth documenting.
9. During full rescan mode, check for missing L2 docs only for modules with meaningful source behavior. Create L2 docs when the missing detail would help future AI work; do not create empty placeholder L2 files.
10. Enforce size limits: L0 <= 4KB, L1 <= 4KB, L2 <= 5KB.
11. Validate memory hygiene and format compliance.
12. Stage updated `.prizm` files with `git add .prizmkit/prizm-docs/` only after reviewing the repair summary.

OUTPUT: List updated, created, removed, and skipped docs with reasons. Explicitly state that this was an out-of-band repair/resync, not a normal development retrospective.
