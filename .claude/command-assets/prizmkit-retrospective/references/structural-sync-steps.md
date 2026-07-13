# Structural Sync — Detailed Steps

## 1. Get changed files

Get changed files from staged and unstaged changes relative to HEAD:

```bash
git diff HEAD --name-status
```

If the caller supplied an explicit file list, use that list instead and note the source in the report.

## 2. Map files to modules

Read `.prizmkit/prizm-docs/root.prizm` and map each changed file to MODULE_INDEX or MODULE_GROUPS entries.

If a changed source file maps to no module, evaluate whether its directory qualifies as a new module:

- Contains source files forming a logical unit
- Contains entry/config/interface files
- Contains qualifying submodules
- Is referenced by multiple modules as a dependency

## 3. Classify changes

- `A` added → add to KEY_FILES and check for new public interfaces
- `D` deleted → remove from KEY_FILES and update file counts
- `M` modified → check public interfaces, dependencies, data flow, and durable traps/decisions
- `R` renamed → update path references

## 4. Decide whether sync is needed

Skip structural sync when changes are limited to:

- comments, whitespace, or formatting
- `.prizm` files only
- internal implementation details with no interface, dependency, data-flow, or module mapping impact
- test-only changes that reveal no durable boundaries, traps, interface constraints, behavior rules, or regression knowledge

Do not skip automatically just because the task is a bug fix or test change. Run the relevant part of retrospective when the change affects structure, interfaces, dependencies, observable behavior, or durable knowledge.

## 5. Update affected docs bottom-up

### L2

If L2 exists, update only sections affected by changed files in that module.

If L2 does not exist and the current diff includes Added or Modified source files with meaningful logic, create L2 with:

```text
MODULE
FILES
RESPONSIBILITY
KEY_FILES
DEPENDENCIES
INTERFACES
TRAPS
```

Add DATA_FLOW, RULES, or DECISIONS only when the changed files provide durable information for those sections. Populate from the diff files and targeted source reads, not from an unbounded full-module rescan.

### L1

Update FILES count, KEY_FILES, SUBDIRS, and DEPENDENCIES when module-level structure changes.

L1 does not contain INTERFACES, DATA_FLOW, TRAPS, or DECISIONS; those belong in L2.

### L0

Update MODULE_INDEX or MODULE_GROUPS only when module structure changed. Preserve any `PROJECT_BRIEF:` line because it is managed by `/prizmkit-init`.

## 6. New module handling

If a new directory qualifies as a module and matches no existing module:

1. Create L1 immediately.
2. Add it to MODULE_INDEX or MODULE_GROUPS.
3. Create L2 only when the current diff includes meaningful Added or Modified source files for the module.

## 7. Size limits

- L0 > 4KB → consolidate MODULE_INDEX or convert to MODULE_GROUPS when module count is high
- L1 > 4KB → trim KEY_FILES descriptions and keep RULES concise
- L2 > 5KB → remove derived detail or stale entries; keep durable knowledge only

## 8. TRAPS staleness check

Run only when an L2 doc's TRAPS section has more than 10 entries.

Process at most 5 oldest TRAPS per L2 doc:

1. If a TRAP has `STALE_IF:` and matched files no longer exist, delete the TRAP.
2. If a TRAP has `REF:` and the referenced file is gone or the commit is older than the review horizon, mark it `[REVIEW]` for the next knowledge pass.

This bounds context cost and prevents unbounded trap accumulation.
