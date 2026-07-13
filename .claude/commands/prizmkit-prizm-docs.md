---
description: "Project documentation specification and management for AI-optimized progressive context loading. Defines the .prizmkit/prizm-docs/ L0/L1/L2 hierarchy, format rules, size limits, and loading protocol. Use this skill to bootstrap docs for new projects (init), check freshness (status), rebuild modules, validate format, migrate existing docs, or repair/resync docs after out-of-band drift such as manual edits, merges, or branch switches. For normal development updates after code changes, use /prizmkit-retrospective instead. Trigger on: 'initialize docs', 'check doc status', 'rebuild docs', 'validate docs', 'migrate docs', 'docs drifted', 'repair prizm docs'. (project)"
---

# Prizm Docs - AI Documentation Framework

Full specification: `.claude/command-assets/prizmkit-prizm-docs/assets/prizm-docs-format.md`

## Intent Routing

This skill handles documentation system operations. Determine the user's intent and execute the matching operation:

| User Intent | Operation | Trigger Phrases |
|---|---|---|
| Bootstrap new project docs | Init | "initialize docs", "set up prizm docs", "bootstrap documentation" |
| Repair docs after out-of-band drift | Update | "docs drifted", "repair prizm docs", "resync after merge", "docs stale after branch switch" |
| Check doc freshness | Status | "check docs", "are docs up to date", "doc status" |
| Regenerate module docs | Rebuild | "rebuild docs for X", "regenerate module docs" |
| Check format compliance | Validate | "validate docs", "check doc format", "docs valid?" |
| Convert existing docs | Migrate | "migrate docs", "convert docs to prizm format" |

Do not route ordinary development-loop "update docs" or "sync docs" here. In normal feature/bugfix/refactor work, use `/prizmkit-retrospective`; it is the development docs writer.

## Role Clarification

| Aspect | `/prizmkit-prizm-docs` | `/prizmkit-retrospective` |
|--------|------------------------|---------------------------|
| Role | Documentation specification, bootstrap, health checks, migration, out-of-band repair | Normal development writer |
| When | Project setup, validation, rebuild, migration, docs drift after merges/manual edits | After implementation/review when code changes affect docs or durable knowledge |
| Writes | Initial structure, rebuilds, migrations, repair/resync operations | Incremental task-scoped updates during development |
| Reads | Source code structure and existing docs | Git diff, task artifacts, review/test results, changed source |
| Knowledge | Defines format rules and loading protocol | Extracts durable TRAPS/RULES/DECISIONS |

Key principle: `/prizmkit-prizm-docs` defines and repairs the documentation system. `/prizmkit-retrospective` keeps docs in sync during ordinary development.

### When to Use
- First-time project documentation setup
- Checking whether docs are fresh or valid
- Rebuilding stale module docs after major structural changes
- Migrating existing docs to Prizm format
- Repairing docs that drifted because of manual edits, merges, branch switches, or changes made outside the normal dev loop

### When NOT to Use
- Incremental doc updates after normal code changes → use `/prizmkit-retrospective`
- User wants to edit code → use `/prizmkit-plan` and `/prizmkit-implement`
- Project has no `.prizmkit/prizm-docs/` and the user does not want to initialize docs

## Operation: Init

Bootstrap `.prizmkit/prizm-docs/` for the current project.

Precondition: no `.prizmkit/prizm-docs/` directory exists, or user confirms overwrite.

Read `.claude/command-assets/prizmkit-prizm-docs/references/op-init.md` for detailed steps.

## Operation: Update

Repair or resync `.prizmkit/prizm-docs/` after out-of-band drift.

Precondition: `.prizmkit/prizm-docs/` exists with `root.prizm`.

Use Update only when docs drifted outside the normal development loop, such as:

- manual code edits without retrospective
- merges or rebases
- branch switches
- generated code movement
- user explicitly asks to repair stale Prizm docs

During normal feature/bugfix/refactor work, do not use Update; use `/prizmkit-retrospective` to avoid duplicate writers and conflicting edits.

Read `.claude/command-assets/prizmkit-prizm-docs/references/op-update.md` for detailed steps.

## Operation: Status

Check freshness of all `.prizm` docs.

Precondition: `.prizmkit/prizm-docs/` exists with `root.prizm`.

Read `.claude/command-assets/prizmkit-prizm-docs/references/op-status.md` for detailed steps.

## Operation: Rebuild

Regenerate docs for a specific module from scratch.

Precondition: `.prizmkit/prizm-docs/` exists and module path is valid.

Read `.claude/command-assets/prizmkit-prizm-docs/references/op-rebuild.md` for detailed steps.

## Operation: Validate

Check format compliance and consistency of all `.prizm` docs.

Precondition: `.prizmkit/prizm-docs/` exists.

Read `.claude/command-assets/prizmkit-prizm-docs/references/op-validate.md` for detailed steps.

## Operation: Migrate

Convert existing documentation to `.prizmkit/prizm-docs/` format.

Precondition: existing `docs/`, `docs/AI_CONTEXT/`, README, or architecture docs; no `.prizmkit/prizm-docs/` unless user confirms overwrite.

Steps:
1. Discover existing docs: `docs/`, `docs/AI_CONTEXT/`, `README.md`, `ARCHITECTURE.md`, and structured documentation files.
2. Extract project metadata, module descriptions, architecture patterns, rules, decisions, and dependencies.
3. Map project-wide info to L0, module structure to L1, and behavioral details to L2.
4. Convert prose to KEY: value format and strip markdown tables, diagrams, and decorative formatting.
5. Generate `.prizmkit/prizm-docs/` using init structure seeded with extracted information.
6. Validate migrated docs against format rules and size limits.
7. Report files processed, generated `.prizm` files, and manual review items.

## Error Handling

- `root.prizm` corrupted or invalid: back it up, then rebuild affected docs from source.
- Broken pointers: create the missing `.prizm` file if the source module exists; remove the pointer if the source module was deleted.
- Size limit exceeded: consolidate L0, move L1 implementation detail to L2, trim L2 derived detail.
- No git history: fall back to filesystem timestamps for freshness checks and warn that accuracy is reduced.

## Key Protocols

For detailed protocol specifications, read `assets/prizm-docs-format.md`:

- Progressive Loading: Section 6.1
- Update/repair protocol: Section 7
- RULES hierarchy: Section 3.1

## Examples

**Init output:**

```text
Generated .prizmkit/prizm-docs/:
  root.prizm (L0) — 3 modules in MODULE_INDEX
  routes.prizm (L1) — module structure and dependencies
  models.prizm (L1) — module structure and dependencies
  services.prizm (L1) — module structure and dependencies
```

L1 docs are structural indexes. Interface signatures, data flow, TRAPS, and DECISIONS belong in L2 docs.

**Out-of-band repair after merge:**

```text
Changed outside normal dev loop: src/routes/avatar.ts (A), src/models/user.ts (M)
Updated: .prizmkit/prizm-docs/routes.prizm — added avatar route file mapping
Created: .prizmkit/prizm-docs/routes/avatar.prizm — recorded new route interfaces and traps
Updated: .prizmkit/prizm-docs/models.prizm — file count changed
```
