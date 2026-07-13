---
description: Interactive refactoring planner. Understands refactoring intent through dialogue, analyzes current code structure, identifies refactoring targets, decomposes large refactors or code migrations, and produces validated .prizmkit/plans/refactor-list.json for dev-pipeline execution. Use whenever users discuss refactoring planning, code restructuring scope, code migration planning, or preparing .prizmkit/plans/refactor-list.json.
---

# refactor planner

Plan executable refactoring items for dev-pipeline:
- **Scope Assessment**: analyze current code structure and identify refactoring targets
- **Item Decomposition**: break refactoring goals into well-ordered, behavior-preserving items

Always produce a validated `.prizmkit/plans/refactor-list.json` that conforms to `dev-pipeline-refactor-list-v1`.

## Invocation Commitment (Hard Rule)

**When the user invokes `/refactor-planner`, you MUST execute the refactor-planner workflow.** You must NEVER:
- Decide on the user's behalf that the task "doesn't need refactor-planner"
- Skip refactor-planner to jump directly to refactor-workflow or any other skill
- Bypass the interactive phases because you judge the task to be "simple" or "obvious"

If you believe the task is better suited for a different workflow (e.g., single-file refactor via `/refactor-workflow`), you MUST:
1. **Explain why** you think a different path is more appropriate
2. **Ask the user explicitly** whether they want to switch or continue with refactor-planner
3. **Only switch if the user confirms** — otherwise proceed with refactor-planner as invoked

The user chose this skill intentionally. Respect that choice.

## Scope Boundary (Hard Rule)

**This skill is PLANNING ONLY.** You must NEVER:
- Create, modify, or delete source code files (*.js, *.ts, *.py, *.go, *.html, *.css, etc.)
- Execute refactoring operations (rename, move, extract, etc.)
- Run build/install/test commands
- Execute any implementation action beyond writing `.prizmkit/plans/refactor-list.json`

**Your ONLY writable outputs are:**
1. `.prizmkit/plans/refactor-list.json` (`.prizmkit/plans/`)
2. Draft backups in `.prizmkit/plans/` (e.g., `refactor-list.draft.json`)

**After planning is complete**, you MUST:
1. Present the summary and recommended next step
2. **Ask the user explicitly** whether they want to proceed to execution
3. If the user agrees → recommend invoking `refactor-pipeline-launcher` (do NOT execute it yourself)
4. If the user wants to adjust → continue refining `.prizmkit/plans/refactor-list.json`
5. **NEVER auto-execute** the pipeline, launcher, or any implementation step

## User-Provided Content Priority (Hard Rule)

When the user provides detailed specifications, rules, or implementation requirements:

1. **Verbatim preservation**: The user's exact wording MUST be preserved in `description` and `acceptance_criteria` fields. Do NOT paraphrase, summarize, abstract, or simplify.
2. **No autonomous simplification**: A 200-word user specification must NOT become a 30-word description. Match the detail level of the user's input.
3. **Clarify, don't assume**: If any user-provided rule is ambiguous or potentially conflicts with another, ASK the user to clarify. No limit on clarification rounds. Do NOT proceed with unresolved ambiguities.
4. **Task-scoped `user_context`**: In single-refactor planning, write the relevant user-provided materials into that refactor item's `user_context`. In multi-refactor planning, multi-refactor `user_context` must contain only the user text, file references, goals, and constraints relevant to that specific refactor item.
   - Preserve the matching user wording verbatim, but scope it to the item it belongs to.
   - Do NOT copy the full multi-refactor request into every item.
   - Ensure there are no unrelated sibling refactor goals, target files, constraints, desired end states, or supplementary materials in a refactor item's `user_context`.
   - Shared global context may be copied to every item only when it is explicitly applicable to all generated items.
   - If a goal, constraint, target file, or architecture note applies to only one refactor item, attach it only to that matching item.
   - If applicability is unclear, ask the user to map the material to the correct refactor item before generating the final list.
5. **`user_context` format**:
   - Refactor-specific supplementary content, goals, or constraints → store as-is (verbatim text) on the matching refactor item only
   - Refactor-specific file references → store as path string, e.g. `src/auth/login.ts:42-78` or `src/utils/validate.ts — focus on validateEmail function`
   - Truly shared global constraints → repeat only when they apply to every generated refactor item

**Multi-refactor isolation example:**
- User request includes: `Refactor A: extract auth validation into middleware`, `Refactor B: split dashboard chart utilities`, and `Shared: preserve all public APIs`.
- The auth middleware refactor `user_context` includes `Refactor A: extract auth validation into middleware` and the shared API constraint; it MUST NOT include `Refactor B: split dashboard chart utilities`.
- The chart utilities refactor `user_context` includes `Refactor B: split dashboard chart utilities` and the shared API constraint; it MUST NOT include `Refactor A: extract auth validation into middleware`.

## When to Use
- "Plan refactoring", "Scope a restructuring"
- "Prepare .prizmkit/plans/refactor-list.json", "Prepare dev-pipeline input for refactoring"
- "Assess code for refactoring", "Identify refactoring targets"
- "Plan a code migration", "Decompose a large refactor"

Do NOT use this skill when the user wants to:
- Execute a single refactor directly (use `refactor-workflow`)
- Plan new features (use `feature-planner`)
- Fix bugs (use `bug-planner`)

## Resource Loading Rules (Mandatory)

1. **Read decomposition guide**:
   - Read `.claude/command-assets/refactor-planner/assets/planning-guide.md` for decomposition patterns and description guidelines

2. **Read scope assessment reference**:
   - Read `.claude/command-assets/refactor-planner/references/refactor-scoping-guide.md` for scope classification and risk assessment

3. **Read behavior preservation reference**:
   - Read `.claude/command-assets/refactor-planner/references/behavior-preservation.md` for preservation strategy selection

4. **Load on-demand references when triggered**:
   - Validation errors or interrupted session -> see the "Error Recovery & Resume" section below

5. **Always validate output via script**:
   - Run:
     ```bash
     python3 .claude/command-assets/refactor-planner/scripts/validate-and-generate-refactor.py validate --input <output-path>
     ```

6. **Use script output as source of truth**:
   - If validation fails, **MUST** fix and re-run until pass

## Prerequisites

Before questions, check optional context files (never block if absent):
- `.prizmkit/prizm-docs/root.prizm` (architecture/project context)
- `.prizmkit/config.json` (existing stack preferences and detected tech stack)
- Existing test suite (critical for behavior preservation assessment)
- Existing `.prizmkit/plans/refactor-list.json` (if appending additional items)
- If `.prizmkit/prizm-docs/root.prizm` is absent and the project has existing source code, scan the directory structure:
  ```bash
  find . -maxdepth 2 -type d -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/__pycache__/*' -not -path '*/vendor/*' | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
  ```

**Test suite detection:**
- Scan for test runner config files (`jest.config.*`, `vitest.config.*`, `pytest.ini`, `.mocharc.*`, `karma.conf.*`)
- If no test suite detected, WARN: "No test suite found. Behavior preservation will rely on manual verification. Consider writing tests before refactoring."
- Record test suite status in planning context for downstream use

## Operation Modes

### Mode A: Interactive (default)
Full Q&A -> code analysis -> item generation. Used when starting from scratch or exploring refactoring scope.

### Mode B: From Analysis
When an existing analysis report (e.g., `refactor-analysis.md`) is available, skip the analysis phase and proceed directly to item decomposition.

### Mode C: Validate
Validate an existing `.prizmkit/plans/refactor-list.json` without regenerating it:
```bash
python3 .claude/command-assets/refactor-planner/scripts/validate-and-generate-refactor.py validate --input .prizmkit/plans/refactor-list.json
```

### Mode D: Summary
Display a human-readable summary of an existing `.prizmkit/plans/refactor-list.json`:
- Item count, dependency graph, complexity distribution, behavior preservation strategies

## Interactive Mode — Core Workflow

Execute the planning workflow in conversation mode with mandatory checkpoints:

### Phase 1: Project Context

**Goal**: Understand the current codebase structure and tech stack.

1. Read `.prizmkit/prizm-docs/root.prizm` and relevant L1 docs
2. Read `.prizmkit/config.json` for tech stack info
3. Identify existing test suite and coverage
4. Summarize project context to the user: "Here's what I found about your project..."
5. **Collect reference materials** — **Upfront Material Detection (Hard Rule)**: If the user has already provided materials (file paths, URLs, rules, specifications, code snippets) in the same message that invoked this skill: (a) Acknowledge what was received: "I received the following materials: [list]"; (b) Read/fetch all provided materials immediately; (c) You MUST still ask: "Are there any additional materials you'd like to provide?"; (d) NEVER skip this collection step just because the user already provided some materials.

   If the user has NOT provided any materials upfront, explicitly ask whether they have any supplementary materials for you to review before planning the refactoring:
   > "Do you have any reference materials I should review before planning the refactoring? This can include:
   > - **Code paths** — specific files or directories that are refactoring targets or dependencies
   > - **Documents** — design docs, architecture proposals, refactoring RFCs, or technical debt analyses
   > - **Knowledge docs** — `.prizmkit/prizm-docs/` files, README files, or internal wiki pages for the affected area
   > - **Images** — architecture diagrams, dependency graphs, or whiteboard photos
   > - **Web links** — reference implementations, design pattern articles, or migration guides
   >
   > If none, we'll proceed with what's available in the codebase."

   If the user provides materials, read/fetch them all before proceeding to Phase 2. For web links, use web fetch to retrieve and analyze the content. For images, read and analyze them visually. This context is critical for refactoring — understanding the target architecture and constraints prevents risky structural changes.

**CHECKPOINT CP-RP-0**: Project context loaded, tech stack and test suite status known.

### Phase 2: Refactor Goal Collection

**Goal**: Through interactive dialogue, understand what the user wants to refactor and why.

Support 4 input formats (users may mix formats):

**Format A — Natural language**:
> "This module is too large and hard to maintain"
> "The auth logic is scattered across too many files"

**Format B — Code smell pointer**:
> "src/api/handler.js is 800 lines"
> "There are 5 files that all implement similar validation logic"

**Format C — Architecture migration**:
> "Convert callbacks to async/await"
> "Migrate from class components to hooks"
> "Move from monolith to modular architecture"

**Format D — Dependency decoupling**:
> "There's a circular dependency between auth and user modules"
> "The database layer is tightly coupled to the HTTP layer"

For each input, ask clarifying questions:
- What is the specific target (files, modules, patterns)?
- What is the desired end state?
- Are there constraints (must preserve API, must not touch certain files)?
- What is the motivation (maintainability, performance, testability)?

Continue collecting goals until the user says they're done. There is no limit on rounds.

**CHECKPOINT CP-RP-1**: All refactoring goals collected and understood.

### Phase 3: Code Analysis

**Goal**: Analyze the target code to inform item decomposition.

Dispatch **parallel Agent reads** of target files:
- **Agent A (Structure)**: File inventory, dependency graph, module boundaries, public API surface
- **Agent B (Quality)**: Code smells, complexity hotspots, duplication, coupling metrics
- **Agent C (Tests)**: Test coverage of target areas, existing test patterns, behavior contracts

Present consolidated findings:
```
## Code Analysis Results

### Structure
- [file inventory, dependency graph]

### Quality Issues
- [code smells, complexity hotspots, duplication]

### Test Coverage
- [test status for target areas]
- [behavior contracts that must be preserved]

### Recommended Decomposition
- [suggested refactoring order based on findings]
```

Ask: "Based on this analysis, here's how I'd recommend decomposing the refactoring. Does this align with your expectations?"

**CHECKPOINT CP-RP-2**: Code analysis complete, user agrees with recommended approach.

### Phase 4: Item Decomposition

**Goal**: Split refactoring goals into executable, well-ordered items.

Read `.claude/command-assets/refactor-planner/references/planning-phases.md` for the full Phase 4-6 procedures — item decomposition patterns, per-item confirmation loop, and completeness review checklist.

**CHECKPOINT CP-RP-3**: All items decomposed with dependencies and preservation strategies.

### Phase 5: Per-Item Confirmation

**Goal**: Present each item to the user for confirmation, modification, or rejection.

See `.claude/command-assets/refactor-planner/references/planning-phases.md` for the display template and confirm/modify/skip loop procedure.

**CHECKPOINT CP-RP-4**: All items confirmed by user.

### Phase 6: Completeness Review

**Goal**: Check the full item set for consistency, gaps, and headless execution readiness.

See `.claude/command-assets/refactor-planner/references/planning-phases.md` for the full 5-step review checklist (DAG validation, preservation check, gap detection, cross-module impact, headless readiness criteria) and review summary table format.

**CHECKPOINT CP-RP-5**: Completeness review passed, all issues resolved.

### Phase 7: Generate & Validate

**Goal**: Produce `.prizmkit/plans/refactor-list.json` and validate it.

**IMPORTANT: Do NOT hand-write the final JSON file.** Instead:
1. Write a draft JSON to `.prizmkit/plans/refactor-list.draft.json` with all collected refactor data.
2. Call the generate script to validate and produce the final file:
   ```bash
   python3 .claude/command-assets/refactor-planner/scripts/validate-and-generate-refactor.py generate --input .prizmkit/plans/refactor-list.draft.json --output .prizmkit/plans/refactor-list.json
   ```
   The script fills in defaults (`$schema`, `created_at`, `created_by`), validates all fields, and writes the final file only if validation passes.
3. If validation fails -> fix the draft and retry (max 3 attempts)
4. If validation passes -> run the mandatory Local Generated-Plan Review Gate (see §Local Generated-Plan Review Gate below); apply accepted fixes to the draft/source plan, regenerate, and revalidate until pass
5. If review and validation pass -> present final summary

**CHECKPOINT CP-RP-6**: `.prizmkit/plans/refactor-list.json` generated and validated.

**CHECKPOINT CP-RP-7**: Local generated-plan review loaded `.claude/command-assets/refactor-planner/references/generated-plan-review.md`, reviewed only newly added/changed refactor entries, applied accepted fixes through draft/source data, regenerated, and revalidated.

## Checkpoints (Mandatory Gates)

| Checkpoint | Artifact/State | Criteria | Phase |
|-----------|----------------|----------|-------|
| **CP-RP-0** | Project Context | Tech stack, test suite status, .prizmkit/prizm-docs loaded | 1 |
| **CP-RP-1** | Goals Collected | All refactoring goals understood, no open ambiguities | 2 |
| **CP-RP-2** | Code Analyzed | Analysis complete, user agrees with approach | 3 |
| **CP-RP-3** | Items Decomposed | All items have deps, complexity, preservation strategy | 4 |
| **CP-RP-4** | Items Confirmed | User confirmed/modified/skipped each item | 5 |
| **CP-RP-5** | Completeness OK | DAG valid, preservation strategies declared, no gaps | 6 |
| **CP-RP-6** | Output Valid | `.prizmkit/plans/refactor-list.json` passes validation script | 7 |
| **CP-RP-7** | Local Plan Review Passed | Local generated-plan review loaded `.claude/command-assets/refactor-planner/references/generated-plan-review.md`, reviewed only newly added/changed refactor entries, applied accepted fixes through draft/source data, regenerated, and revalidated | 7 |

## Local Generated-Plan Review Gate

User requirement preserved verbatim: `there is a litter bug for prizm-code-review will to check git diff in working space and staged space , however the .prizmkit will be gitignored in most situation.  so do you think the content should be change to inline a new reference file instead of use prizmkit-code-review`

Run this gate **after** `.prizmkit/plans/refactor-list.json` passes the validation/generate script and **before** the final handoff summary recommends `refactor-pipeline-launcher`. This gate applies to full workflow, Mode B from analysis, and fast-path refactor planning when the current session generated, appended, or rewrote final refactor planning content. For validate-only, summary-only, or draft-save flows with no new final planning content, report: `Local generated-plan review: not applicable — no new final planning content written.`

1. **Load the local reference**: read `.claude/command-assets/refactor-planner/references/generated-plan-review.md` and follow it as the source of truth for this planner-output review loop.
2. **Read actual planning artifacts directly**: inspect `.prizmkit/plans/refactor-list.json`, `.prizmkit/plans/refactor-list.draft.json` when present, and any pre-session or in-memory draft snapshot. Do not rely on `git status`, `git diff`, or `git diff --cached`, because `.prizmkit` planning artifacts are often gitignored or untracked.
3. **Identify review scope**: compare by stable refactor IDs and item fields against the pre-session list when one existed. Ignore root generator metadata such as `$schema`, `created_at`, and `created_by`. Review only newly added or changed refactor entries; preserve unchanged historical entries except when needed to verify dependency references or behavior-preservation interactions.
4. **Run the local checklist** from the reference: schema compatibility, dependency/DAG soundness, safe behavior-preserving order, description completeness, headless execution readiness, acceptance criteria measurability, `behavior_preservation` strategy quality, user-provided wording preservation, task-scoped `user_context` isolation, and priority/complexity calibration.
5. **Keep the review planning-only**: do NOT start `refactor-pipeline-launcher`, do NOT run the refactor pipeline, do NOT run tests/builds/installs, and do NOT implement source-code refactors.
6. **Apply accepted review fixes through the draft/source plan**: when a finding is accepted, update `.prizmkit/plans/refactor-list.draft.json` or the in-memory draft representation first, then regenerate the final file with:
   ```bash
   python3 .claude/command-assets/refactor-planner/scripts/validate-and-generate-refactor.py generate --input .prizmkit/plans/refactor-list.draft.json --output .prizmkit/plans/refactor-list.json
   ```
   Do not hand-patch the final JSON as the source of truth; map final-output findings back to draft entries before regeneration.
7. **Revalidate after every accepted fix batch**: the generate script must pass again before the planner can proceed. If validation fails, fix the draft and rerun until pass.
8. **Report the gate outcome** in the final summary: include local generated-plan review verdict, reviewed refactor IDs, accepted fixes (or "none"), and final validation result.

## Output Rules

`.prizmkit/plans/refactor-list.json` must satisfy:
- `$schema` = `dev-pipeline-refactor-list-v1`
- Non-empty `refactors` array
- Sequential IDs: `R-001`, `R-002`, ...
- Valid dependency DAG (no cycles)
- Each item has a declared `behavior_preservation` object with `strategy` field: `"test-gate"`, `"snapshot"`, or `"manual"`. Optional fields: `existing_tests` (boolean), `new_tests_needed` (string array). See `.prizmkit/dev-pipeline/templates/refactor-list-schema.json` for the full schema.
- `priority` must be a string: `"critical"`, `"high"`, `"medium"`, or `"low"`
- New items default `status: "pending"`
- English titles for stable slug generation
- `type` field must be one of: `extract`, `rename`, `restructure`, `simplify`, `decouple`, `migrate`
- Descriptions minimum 15 words (error). Recommended: 30/50/80 words for low/medium/high complexity (warning).
- `model` field is optional — omitting it means the pipeline uses $MODEL env or CLI default
- `scope` object with nested structure: `files` array (target file paths) and `modules` array (module names)

## Verification Defaults

Set behavior-preservation and testing expectations for each refactor item. Do not generate retired review-agent configuration fields.

| Priority | Complexity | Verification expectation |
|----------|-----------|--------------------------|
| critical | high | Strong behavior-preservation evidence plus scoped tests and review gate |
| critical | medium/low | Focused behavior-preservation evidence plus review gate |
| high | high | Scoped tests for changed boundaries plus review gate |
| other combinations | any | Smallest meaningful behavior-preservation check |

Never emit `critic` or `critic_count`; those fields are fully removed and validators reject them.

---

## Fast Path

For simple refactoring with minimal scope (1-2 items, low/medium complexity, no cross-module impact, existing test coverage). Read `.claude/command-assets/refactor-planner/references/fast-path.md` for eligibility criteria, full workflow (including AskUserQuestion format), conditions NOT to use, and an example session.

## Browser Verification

Browser verification is supported for UI-affecting refactors as a supplement to `behavior_preservation`. Refactors must still declare `behavior_preservation.strategy`; add `browser_interaction` only when UI behavior should be visually checked after refactoring. Read `.claude/command-assets/refactor-planner/references/planning-phases.md` for strategy details and UI refactoring examples.

---

## Priority and Complexity Calibration (Mandatory)

Refactor planning must not collapse into uniform `Priority: high` and `Complexity: high`. Refactoring work can be low or medium priority even when it touches several files. Do not use high/high merely because code needs cleanup, the user cares about maintainability, the target is framework code, or multiple files are involved.

### Priority Rubric

| Priority | Use When | Do NOT Use Merely Because |
|----------|----------|---------------------------|
| `critical` | Behavior-preserving restructure is required to unblock an imminent release, security/compliance fix, or safe migration with no acceptable workaround. | The refactor is large or architectural in wording. |
| `high` | Current structure blocks core feature delivery, creates ongoing correctness/security/data-risk, prevents supported runtime upgrades, or many downstream tasks cannot proceed. | The code is messy, multi-file, or important to the user. |
| `medium` | Refactor improves maintainability, testability, or dependency boundaries for planned work but does not block current operation. | Medium is the normal default for useful refactors. |
| `low` | Local cleanup, rename, simplification, documentation-oriented organization, or isolated code-health improvement with low behavior risk. | Small scope alone does not make it low if it blocks a high-impact outcome. |

### Complexity Rationale Rules

Assign complexity from concrete refactor scope indicators and include a short rationale:
- file count and expected import/update sites
- cross-module scope and dependency depth
- public API/interface or import-path change
- existing test coverage and behavior-preservation strategy
- behavior-preservation risk and snapshot/manual verification needs
- migration impact, rollout phases, or compatibility shims

Use `low` for 1-3 files in one module with good tests and no public API/import-path change. Use `medium` for 4-8 files or two modules with bounded public impact and clear behavior-preservation tests. Use `high` only for 9+ files, 3+ modules, public API/import-path migration, weak test coverage, manual preservation risk, or cross-module migration impact.

### Required Planning Review Summary

Before writing `.prizmkit/plans/refactor-list.json`, show a calibration table with rationale columns:

```
ID    | Title                       | Priority | Priority Rationale              | Complexity | Complexity Rationale
R-001 | Break auth/user cycle        | high     | Blocks feature work; core risk  | high       | 3 modules + public imports + weak tests
R-002 | Extract chart format helpers | medium   | Maintainability for planned UI  | medium     | 5 files; bounded helper API; tests exist
R-003 | Rename local temp variable   | low      | Local readability only          | low        | One file; no interface or behavior change
```

Anti-pattern rule: do not assign every generated item `Priority: high` and `Complexity: high` unless each item independently satisfies the documented high-priority and high-complexity criteria and the rationale names those criteria.

## Refactoring-Specific Features

### Behavior Preservation Check

Every item MUST declare a behavior preservation strategy. Read `.claude/command-assets/refactor-planner/references/behavior-preservation.md` for strategy details. See `.claude/command-assets/refactor-planner/references/planning-phases.md` for the strategy selection table and manual-strategy flagging rules.

### Dependency Ordering

Auto-detect inter-item dependencies and enforce safe ordering. Read `.claude/command-assets/refactor-planner/references/planning-phases.md` for the full dependency ordering rules (safe renames -> extract/inline -> structural -> migrations).

### Complexity Assessment

Assess each item's complexity from concrete indicators: file count, cross-module scope, public API/import-path changes, dependency depth, test coverage, behavior-preservation risk, and migration impact. Read `.claude/command-assets/refactor-planner/references/planning-phases.md` for the full complexity assessment criteria and scoring rules. Every confirmation/review summary must include a short complexity rationale.

## Next-Step Execution Policy (after planning)

Recommend invoking `refactor-pipeline-launcher` to configure and launch the dev-pipeline. Do NOT recommend running shell scripts directly — that is the launcher's responsibility.

## Error Recovery & Resume

Key behaviors:
- Warnings only -> proceed with user approval
- Critical errors -> group by type, auto-fix where possible, max 3 total attempts
- Interrupted session -> detect checkpoint from existing artifacts, offer resume or restart
- `.prizmkit/plans/refactor-list.json` MUST be written to `.prizmkit/plans/` (project root level: `./{root}/.prizmkit/plans/refactor-list.json`)

### Resume Detection

If existing artifacts are found, offer to resume from the appropriate checkpoint/phase:

| Artifact Found | Resume From |
|---------------|------------|
| Nothing | Phase 1: Project Context |
| Draft in `.prizmkit/plans/` | Phase matching draft state |
| Partial `.prizmkit/plans/refactor-list.json` | Phase 6: Completeness Review |
| Valid `.prizmkit/plans/refactor-list.json` | Mode D: Summary |

### Session Exit Gate

Prevent accidental session exit without deliverable completion.

**Trigger conditions** — activate the exit gate when ALL are true:
- User invoked `/refactor-planner` (not just mentioned refactoring)
- Current phase < Phase 7 (validation not yet passed)
- No valid `.prizmkit/plans/refactor-list.json` has been written in this session

**Gate behavior** — when the session appears to be ending:
1. **Remind**: "You set out to produce `.prizmkit/plans/refactor-list.json` but we haven't completed it yet."
2. **Offer 3 options**:
   - **(a) Continue to completion** — resume from current phase
   - **(b) Save draft & exit** — write current progress as draft, exit session
   - **(c) Abandon** — exit without saving
3. **If (b)**: Write draft and remind: "This is a draft, not validated. Run `/refactor-planner` again to resume."
4. **If (c)**: Accept without further prompting.

## Handoff Message Template

After successful validation and the Local Generated-Plan Review Gate, report:
1. Output file path
2. Total refactor items
3. Dependency ordering highlights (which items must run first)
4. Behavior preservation strategy distribution (N items with test-gate, M with snapshot, etc.)
5. Local generated-plan review result: verdict, reviewed refactor IDs, accepted fixes (or "none"), and final validation result
6. Recommended next action: `refactor-pipeline-launcher`
