# Planning Phases — Refactor Planner

Detailed procedures for Phases 4-6 of the refactor-planner interactive workflow, plus refactoring-specific assessment rules and browser verification guidance.

---

## Phase 4: Item Decomposition Procedure

Read `${SKILL_DIR}/assets/planning-guide.md` for decomposition patterns and dependency ordering rules.

For each refactoring goal:
1. Identify atomic refactoring operations
2. Determine inter-item dependencies (safe renames first, structural changes later)
3. Assess complexity per item from concrete indicators (file count, cross-module scope, public API/import-path impact, dependency depth, test coverage, behavior-preservation risk, migration impact)
4. Assign priority from concrete impact (blocked delivery, correctness/security/data risk, maintainability value, or local cleanup), not from size or user urgency alone
5. Assign behavior preservation strategy per item (read `${SKILL_DIR}/references/behavior-preservation.md`)

---

## Phase 5: Per-Item Confirmation Loop

For each item, display:

```
Refactor Item R-001:
  Title: [title]
  Type: [extract/rename/restructure/simplify/decouple/migrate]
  Scope: [files list]
  Priority: [critical/high/medium/low]
  Priority Rationale: [short concrete impact reason]
  Complexity: [low/medium/high]
  Complexity Rationale: [short scope/risk reason]
  Behavior Preservation: [test-gate/snapshot/manual]
  Acceptance Criteria:
    - [criterion 1]
    - [criterion 2]
  Dependencies: [none / R-002, R-003]
  
  Confirm? (Y/modify/skip)
```

- **Y**: Accept item as-is
- **modify**: User provides changes, update item, re-display for confirmation
- **skip**: Remove item from the list

Continue until all items are confirmed or skipped.

---

## Phase 6: Completeness Review Checklist

1. **Dependency ordering check**: Verify items form a valid DAG (no cycles). Items should be ordered: safe renames -> extract/inline -> structural changes -> migrations
2. **Behavior preservation check**: Every item must have a declared preservation strategy. Flag any item with `manual` strategy and no test coverage.
3. **Gap detection**: Are there intermediate steps needed between items? Does item A's output match item B's input assumption?
4. **Cross-module impact**: Do any items affect modules outside the declared scope?
5. **Headless Execution Readiness**: The refactor pipeline runs each item through an autonomous AI session with NO human interaction. For each item, verify:
   - **Scope clarity**: Are all affected files explicitly listed? The AI must know exactly where to look.
   - **Refactoring instructions**: Is the description specific enough to execute without ambiguity?
     - ❌ "Clean up the utils module" — what exactly should change?
     - ✅ "Extract validation functions (validateEmail, validatePhone, validateUrl) from src/utils/helpers.ts into src/utils/validation.ts. Update all 12 import sites. Preserve existing function signatures."
   - **Behavior preservation**: Is it clear what tests to run and what behavior must be preserved?
   - **Dependency context**: If item depends on earlier refactors, does the description reference what changed?

### Review Summary Table Format

Present review summary:

```
Item       | Priority | Priority Rationale       | Complexity | Complexity Rationale        | Deps Valid | Preservation | Gaps           | Status
R-001      | high     | Blocks core feature work  | high       | 3 modules + public imports  | OK         | test-gate    | -              | Ready
R-002      | medium   | Planned maintainability   | medium     | 5 files + tests exist       | OK         | test-gate    | -              | Ready
R-003      | low      | Local readability only    | low        | One file, no API change     | OK         | manual       | No test coverage| Needs attention
R-004      | medium   | Reduces bounded coupling  | medium     | 2 modules + snapshot check  | OK         | snapshot     | -              | Ready
```

If issues found, discuss with user and resolve before proceeding.

---

## Behavior Preservation Check

Every item MUST declare a behavior preservation strategy. Read `${SKILL_DIR}/references/behavior-preservation.md` for strategy details.

| Strategy | When to Use |
|----------|-------------|
| `test-gate` | Target area has good test coverage. Run full test suite after each change. |
| `snapshot` | Compare output/state before and after. Used when tests are insufficient but behavior is observable. |
| `manual` | Human verification required. Last resort when neither tests nor snapshots are feasible. |

Flag items using `manual` strategy prominently — they carry the highest risk of behavior regression.

---

## Dependency Ordering

Auto-detect inter-item dependencies and enforce safe ordering:
1. **Safe renames** first (lowest risk, no structural change)
2. **Extract/inline** operations (moderate risk, changes module boundaries)
3. **Structural changes** (higher risk, reorganizes architecture)
4. **Migrations** last (highest risk, changes patterns/paradigms)

---

## Complexity Assessment

Complexity is a behavior-preserving execution risk estimate, not a measure of how much the user wants the refactor. Do not default to high because a refactor spans multiple files, targets framework code, or improves maintainability.

Assess each item's complexity based on:
- **File count**: 1-3 files = low, 4-8 files = medium, 9+ files = high
- **Cross-module scope**: same module = low, 2 modules = medium, 3+ modules = high
- **Public API/import-path impact**: no public change = low, bounded internal interface = medium, public API/import migration = high
- **Dependency depth**: 0-2 import/update sites = low, 3-5 = medium, 6+ = high
- **Test coverage**: strong existing tests can keep complexity lower; weak/missing tests increase complexity
- **Behavior-preservation risk**: test-gate with clear assertions = lower, snapshot/manual verification = higher
- **Migration impact**: no rollout = low, compatibility shim = medium, cross-module migration or phased rollout = high

Take the highest well-supported individual assessment as the item's complexity, then record the rationale in the confirmation table.

### Mixed Calibration Examples

| Refactor | Priority | Complexity | Rationale |
|----------|----------|------------|-----------|
| Break circular dependency blocking auth feature work | high | high | Blocks core delivery; 3 modules, public imports, and weak tests. |
| Extract chart formatting helpers from dashboard files | medium | medium | Improves planned maintainability; 5 files with bounded helper API and existing tests. |
| Rename local variable in parser for readability | low | low | Local cleanup only; one file, no interface or behavior change. |

Anti-pattern: do not generate an all-high refactor list unless every item independently satisfies documented high-priority and high-complexity criteria.

---

## Browser Verification

Browser verification is supported for UI-affecting refactors, but it is supplemental. Every refactor still uses `behavior_preservation.strategy` as the primary behavior-preservation contract:

- `strategy: test-gate` — Rely on existing test suite. Pipeline runs tests before and after refactoring.
- `strategy: snapshot` — Compare behavior before/after refactoring using executable snapshots (outputs, API responses, side effects)
- `strategy: manual` — Require human verification that behavior is preserved

For refactors that modify UI code, add `browser_interaction.verify_steps` when visual or browser-flow verification is useful. Also keep behavior-preservation acceptance criteria explicit:

Example:
```
Refactor Title: Extract UserProfile component from AccountSettings
Type: extract
Strategy: snapshot
Acceptance Criteria:
  1. UserProfile component renders identically to inline version (compare snapshots)
  2. All props are correctly forwarded (unit tests pass)
  3. No visual regression (screenshot comparison)
  4. Component is reusable in other views
```

The refactor pipeline AI will use the snapshot strategy to verify external behavior is preserved during refactoring.
