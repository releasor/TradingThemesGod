---
description: Plan, validate, and manage features for an existing project — add or append features, reprioritize, split, summarize, and generate validated .prizmkit/plans/feature-list.json for dev-pipeline execution. Use this skill for feature scoping, incremental planning, continuing a feature plan, checking feature-list.json, or preparing pipeline input. For planning a new app from scratch, use app-planner instead.
---

# feature planner

Plan deliverable features for dev-pipeline on existing projects:
- **New Feature Set**: create an initial .prizmkit/plans/feature-list.json for a project that has code but no plan yet
- **Incremental Feature Planning**: append, adjust, or reprioritize features in an existing plan

Always produce a validated `.prizmkit/plans/feature-list.json` that conforms to `dev-pipeline-feature-list`.

For planning a **new application from scratch** (vision, tech stack, decomposition), use `app-planner` instead.

## Invocation Commitment (Hard Rule)

**When the user invokes `/feature-planner`, you MUST execute the feature-planner workflow.** You must NEVER:
- Decide on the user's behalf that the task "doesn't need feature-planner"
- Skip feature-planner to jump directly to spec/plan/implement or any other skill
- Bypass the interactive phases because you judge the task to be "simple" or "obvious"

If the user's request is about planning a new app from scratch (vision, tech stack selection, app architecture), recommend `app-planner` instead and ask the user to confirm before switching.

If you believe the task is better suited for a different workflow, you MUST:
1. **Explain why** you think a different path is more appropriate
2. **Ask the user explicitly** whether they want to switch or continue with feature-planner
3. **Only switch if the user confirms** — otherwise proceed with feature-planner as invoked

The user chose this skill intentionally. Respect that choice.

## Scope Boundary (Hard Rule)

**This skill is PLANNING ONLY.** You must NEVER:
- Create, modify, or delete source code files (*.js, *.ts, *.py, *.go, *.html, *.css, etc.)
- Create project scaffolding, directories, or boilerplate
- Run build/install/test commands (npm init, pip install, etc.)
- Execute any implementation action beyond writing `.prizmkit/plans/feature-list.json`

**Your ONLY writable outputs are:**
1. `.prizmkit/plans/feature-list.json` (`.prizmkit/plans/`)
2. Draft backups in `.prizmkit/plans/` (e.g., `feature-list.draft.json`)

**After planning is complete**, you MUST:
1. Present the summary and recommended next step (invoking `feature-pipeline-launcher` )
2. **Ask the user explicitly** whether they want to proceed to execution
3. If the user wants to adjust → continue refining `.prizmkit/plans/feature-list.json`
4. **NEVER auto-execute** the pipeline, launcher, or any implementation step

## User-Provided Content Priority (Hard Rule)

When the user provides detailed specifications, rules, or implementation requirements:

1. **Verbatim preservation**: The user's exact wording MUST be preserved in `description` and `acceptance_criteria` fields. Do NOT paraphrase, summarize, abstract, or simplify.
2. **No autonomous simplification**: A 200-word user specification must NOT become a 30-word description. Match the detail level of the user's input.
3. **Clarify, don't assume**: If any user-provided rule is ambiguous or potentially conflicts with another, ASK the user to clarify. No limit on clarification rounds. Do NOT proceed with unresolved ambiguities.
4. **Task-scoped `user_context`**: In single-feature planning, write the relevant user-provided materials into that feature's `user_context`. In multi-feature planning, multi-feature `user_context` must contain only the user text, file references, and supplementary materials relevant to that specific feature.
   - Preserve the matching user wording verbatim, but scope it to the item it belongs to.
   - Do NOT copy the full multi-feature request into every feature.
   - Ensure there are no unrelated sibling feature descriptions, file references, screenshots, or supplementary materials in a feature's `user_context`.
   - Shared global context may be copied to every item only when it is explicitly applicable to all generated items.
   - If a material applies to only one feature, attach it only to that matching feature.
   - If applicability is unclear, ask the user to map the material to the correct feature before generating the final list.
5. **`user_context` format**:
   - Feature-specific supplementary content or rules → store as-is (verbatim text) on the matching feature only
   - Feature-specific file references → store as path string, e.g. `src/auth/login.ts:42-78` or `src/utils/validate.ts — focus on validateEmail function`
   - Truly shared global constraints → repeat only when they apply to every generated feature

**Multi-feature isolation example:**
- User request includes: `Feature A: add saved filters to the dashboard`, `Feature B: export filtered results as CSV`, and `Shared: preserve existing auth permissions`.
- The saved-filters feature `user_context` includes `Feature A: add saved filters to the dashboard` and the shared auth constraint; it MUST NOT include `Feature B: export filtered results as CSV`.
- The CSV export feature `user_context` includes `Feature B: export filtered results as CSV` and the shared auth constraint; it MUST NOT include `Feature A: add saved filters to the dashboard`.

## When to Use

Trigger conditions are covered by the frontmatter `description`. Do NOT use this skill when:
- The user wants to plan a new app from scratch → use `app-planner`
- The user only wants to run the pipeline → use `feature-pipeline-launcher`
- The user is debugging/refactoring or wants to write source code directly

## Resource Loading Rules (Mandatory)

1. **Planning reference** — load before writing feature descriptions:
   - Read `.claude/command-assets/feature-planner/assets/planning-guide.md` for description writing standards, acceptance criteria patterns, complexity estimation, dependency rules, and session granularity

2. **Incremental planning reference** — load for incremental mode:
   - Read `.claude/command-assets/feature-planner/references/incremental-feature-planning.md`

3. **Load on-demand references when triggered**:
   - Validation errors or interrupted session → read `.claude/command-assets/feature-planner/references/error-recovery.md`
   - Browser interaction fields needed → read `.claude/command-assets/feature-planner/references/browser-interaction.md`
   - New feature set for a project (Route A) → read `.claude/command-assets/feature-planner/references/new-project-planning.md` for phase guide, quality rules, and delivery checklist
   - Feature decomposition from scratch → read `.claude/command-assets/feature-planner/references/decomposition-patterns.md` for common app patterns (CRUD, SaaS, Social, E-commerce)
   - Phase 6 completeness review → read `.claude/command-assets/feature-planner/references/completeness-review.md`

4. **Always validate output via script** — see §Output Rules for the validation command.
   
   If the script is not available, perform these manual validation checks:
   1. **ID sequence**: All feature IDs are sequential (F-001, F-002, F-003, ...)
   2. **No circular dependencies**: No feature depends (directly or transitively) on itself
   3. **Description length**: Minimum 15 words per description (error); see §Output Rules for the recommended-length warning thresholds
   4. **Dependency references**: All referenced features in dependencies exist in features array
   5. **Priority enums**: All priority values are exactly "critical", "high", "medium", or "low" (case-sensitive)
   6. **Status enum**: All status values are one of: pending, in_progress, completed, failed, skipped, split, auto_skipped
   7. **Acceptance criteria**: At least 1 criterion per feature, each is a concrete, measurable statement
   8. **Browser interaction**: If present, may include `tool` and `verify_steps`; planner should add concrete `verify_steps` when known, but the schema permits an empty object for AI runtime exploration.
   9. **Complexity enum**: If present, is one of: low, medium, high, critical
   10. **Model field**: If present, is a non-empty string
   11. **Retired fields**: `critic` and `critic_count` must not appear; validation fails if either field is present
   12. **Root schema**: Has $schema='dev-pipeline-feature-list-v1', project_name, and non-empty features array

5. **Use script output as source of truth** — if validation fails, fix and re-run until pass

## Prerequisites

Before questions, check optional context files (never block if absent):
- `.prizmkit/prizm-docs/root.prizm` (architecture/project context — typically created by app-planner with captured decisions)
- `.prizmkit/config.json` (existing stack preferences and detected tech stack)
- `.prizmkit/plans/project-brief.md` (project context from app-planner, if available)
- existing `.prizmkit/plans/feature-list.json` (required for incremental mode)
- Platform instruction file: use the `platform` field in `.prizmkit/manifest.json` as source of truth when present (`codex` → `AGENTS.md`, `claude` → `CLAUDE.md`, `codebuddy` → `CODEBUDDY.md`, `all` → read every matching file). Legacy manifests may contain `both`; treat it as read-only compatibility and read `CLAUDE.md` plus `CODEBUDDY.md` only when encountered.
- If `.prizmkit/prizm-docs/root.prizm` is absent and the project has existing source code, scan the directory structure to understand the codebase layout:
  ```bash
  find . -maxdepth 2 -type d \
    -not -path '*/node_modules/*' -not -path '*/.git/*' \
    -not -path '*/dist/*' -not -path '*/build/*' \
    -not -path '*/__pycache__/*' -not -path '*/vendor/*' \
    -not -path '*/.agents/*' -not -path '*/.codex/*' \
    -not -path '*/.claude/*' -not -path '*/.codebuddy/*' \
    -not -path '*/.prizmkit/*' \
    | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
  ```

**Tech stack from config.json:**
- If `.prizmkit/config.json` contains a `tech_stack` object, use it to pre-fill `global_context` fields in the generated `.prizmkit/plans/feature-list.json`.
- Map config fields to global_context: `language`, `runtime`, `frontend_framework`, `frontend_styling`, `backend_framework`, `database`, `orm`, `testing` → `testing_strategy`, `bundler`, `project_type`.
- Do NOT re-ask the user for tech stack info already present in config.json. Show detected stack and confirm.

## Global Context Population

The `global_context` object in `.prizmkit/plans/feature-list.json` provides technology stack information. Populate it from `.prizmkit/config.json` if available, or ask the user during Phase 1.

### Recommended Fields by Project Type

**Frontend-only projects:**
- `language` (required) — e.g., "TypeScript", "JavaScript"
- `frontend_framework` (required) — e.g., "React", "Vue", "Svelte"
- `frontend_styling` (recommended) — e.g., "Tailwind CSS", "styled-components"
- `testing_strategy` (recommended) — e.g., "Jest + React Testing Library"

**Backend-only projects:**
- `language` (required) — e.g., "TypeScript", "Python", "Go"
- `backend_framework` (required) — e.g., "Express", "Django", "FastAPI"
- `database` (required if applicable) — e.g., "PostgreSQL", "MongoDB"
- `testing_strategy` (recommended) — e.g., "Jest", "pytest"

**Full-stack projects (include both frontend AND backend fields):**
- `language`, `frontend_framework`, `backend_framework`, `database`, `testing_strategy` (all recommended)
- Additional: `frontend_styling`, `orm`, `bundler`, `runtime`

All `global_context` fields are optional — including recommended fields improves downstream code generation quality. See `.prizmkit/dev-pipeline/templates/feature-list-schema.json` for the full schema definition.

## Priority and Complexity Calibration (Mandatory)

Do not let planner output collapse into uniform `Priority: high` and `estimated_complexity: high`. Medium and low assignments are normal when the documented indicators fit. New framework work or multi-file work is not automatically `high` priority; the feature must satisfy the documented priority criteria independently.

### Priority Rubric

| Priority | Use When | Do NOT Use Merely Because |
|----------|----------|---------------------------|
| `critical` | A production-blocking capability, security/compliance requirement, data-loss prevention, or release blocker with no acceptable workaround. | The item is important, large, or requested by a stakeholder. |
| `high` | Core user workflow or platform capability is blocked, revenue/security/auth/data integrity is at risk, a hard deadline depends on it, or many downstream items cannot proceed without it. | The item is multi-file, framework-related, or described with urgent language but no concrete blocker. |
| `medium` | Valuable planned feature, quality improvement, integration, or automation that should be scheduled soon but has a workaround or does not block core operation. | It is less exciting than another item; medium is the default for normal planned work. |
| `low` | Nice-to-have, polish, documentation, cleanup, optional convenience, or isolated improvement with little user/runtime impact. | The item is small; small work can still be high only when it blocks critical outcomes. |

### Complexity Rationale Rules

Assign `estimated_complexity` from concrete scope indicators, not from perceived importance. For each feature, write a short rationale using at least two relevant indicators:
- affected module count and layer count
- file count or expected implementation surface
- API/interface or schema changes
- architectural impact or new infrastructure
- dependency depth and cross-feature coupling
- acceptance-criteria count and edge-case breadth
- test coverage and verification difficulty

Use `low` for focused changes in 1 module with <=5 acceptance criteria and no public API/schema changes. Use `medium` for normal multi-file or 2-3 module work with bounded interfaces. Use `high` only when multiple concrete high indicators are present, such as 3+ modules plus public API changes, deep dependencies, weak tests, or substantial architectural risk. Use `critical` only for system-wide architectural/infrastructure changes or safety-critical work requiring the strongest orchestrator/reviewer/test guardrails.

### Required Planning Review Summary

Before writing `.prizmkit/plans/feature-list.json`, show a calibration table with rationale columns:

```
ID    | Title                 | Priority | Priority Rationale                 | Complexity | Complexity Rationale
F-001 | Auth outage recovery  | high     | Core login blocked; no workaround  | high       | Auth API + middleware + weak tests
F-002 | Export polish option  | medium   | Useful workflow; not blocking      | medium     | UI + API parameter; bounded tests
F-003 | Tooltip copy update   | low      | Cosmetic clarity only              | low        | One component; no interface change
```

Anti-pattern rule: do not assign every generated item `Priority: high` and `Complexity: high` unless each item independently satisfies the documented high criteria and its rationale names those criteria. In feature JSON this means `estimated_complexity: high`; in user-facing review summaries label the column `Complexity`.


---

## Scenario Routing

Classify user intent first:

### Route A: Initial Feature Set for Existing/App-Planned Project
Use when source code or app-level context already exists but no `.prizmkit/plans/feature-list.json` exists yet. If the user is still defining vision, stack, or product brief from scratch, switch to `app-planner` only after confirmation.

Actions:
1. Understand the existing codebase and what's already implemented
2. Run interactive planning phases to identify needed features
3. Generate initial `.prizmkit/plans/feature-list.json`

### Route B: Incremental Feature Planning
Use when user already has a `.prizmkit/plans/feature-list.json` and wants to add or adjust features.

Actions:
1. Load `.claude/command-assets/feature-planner/references/incremental-feature-planning.md`
2. Read existing `.prizmkit/plans/feature-list.json` first (if missing, ask whether to start new plan)
3. Append features with next sequential `F-NNN` IDs
4. Preserve style/language/detail consistency with existing plan

## Core Workflow

Execute the planning workflow in conversation mode with mandatory checkpoints:

### Interactive Phases
1. Clarify scope and goals
   1.1 **Requirement clarification** — for ANY unclear aspect of the user's goals or scope, ask questions one at a time (cite the unclear point, give a recommended answer with rationale) until you fully understand. No limit on rounds. Do not proceed to Phase 2 with unresolved ambiguities.
   1.2 **Collect reference materials** — **Upfront Material Detection (Hard Rule)**: If the user has already provided materials (file paths, URLs, rules, specifications, code snippets) in the same message that invoked this skill: (a) Acknowledge what was received: "I received the following materials: [list]"; (b) Read/fetch all provided materials immediately; (c) You MUST still ask: "Are there any additional materials you'd like to provide?"; (d) NEVER skip this collection step just because the user already provided some materials.

   If the user has NOT provided any materials upfront, explicitly ask whether they have any supplementary materials for you to review. Present this as a single prompt covering all material types:
   > "Do you have any reference materials I should review before planning? This can include:
   > - **Code paths** — files or directories I should read to understand existing implementation
   > - **Documents** — design docs, PRDs, API specs, architecture proposals, or internal wiki pages
   > - **Knowledge docs** — `.prizmkit/prizm-docs/` files, README files, or project-specific documentation
   > - **Images** — wireframes, mockups, architecture diagrams, or screenshots
   > - **Web links** — reference implementations, API documentation pages, or relevant articles
   >
   > If none, we'll proceed with what's available in the codebase."

   If the user provides materials, read/fetch them all before proceeding to Phase 2. For web links, use web fetch to retrieve and analyze the content. For images, read and analyze them visually. Record what was reviewed for traceability.
2. Confirm constraints and existing architecture
3. Propose feature set with dependencies
4. Refine descriptions and acceptance criteria
   4.1 **Per-feature clarification** — for each feature, if the description, acceptance criteria, or scope is vague or could be interpreted multiple ways, ask the user to clarify before finalizing.
   4.2 **Browser interaction** (mandatory for fullstack/frontend projects) — see §Browser Interaction Planning below. Qualifying features get `browser_interaction` by default. Only confirm with the user as a batch summary; do NOT ask per-feature.
5. Verify DAG/order/priorities and show the mandatory priority/complexity calibration table with short rationales for every item
6. Pre-generation completeness review (see §Pre-Generation Completeness Review below)
7. Build or append `.prizmkit/plans/feature-list.json`
8. Apply default testing strategy (see §Testing Defaults below)
9. Validate and fix until pass
10. Run the mandatory Local Generated-Plan Review Gate (see §Local Generated-Plan Review Gate below); apply accepted fixes to the draft/source plan, regenerate, and revalidate until pass
11. Summarize final feature table with local review result and validation outcome

### Checkpoints (Mandatory Gates)

Checkpoints catch cascading errors early — skipping one means the next phase builds on unvalidated assumptions, which compounds into much harder debugging later.

| Checkpoint | Artifact/State | Criteria | Phase |
|-----------|----------------|----------|-------|
| **CP-FP-1** | Scope Confirmed | User confirmed what features to plan and context understood | 1 |
| **CP-FP-2** | Feature Proposals | Feature set with titles+deps identified (pre-validation) | 3-5 |
| **CP-FP-3** | DAG Validity | No cycles, dependencies resolved (validation dry-run) | 5 |
| **CP-FP-3.1** | Browser Interaction Applied | Qualifying features have `browser_interaction` field; user confirmed or opted out | 4 |
| **CP-FP-3.2** | Testing Defaults Applied | All features have appropriate testing expectations and no retired `critic`/`critic_count` fields | 7 |
| **CP-FP-3.3** | Completeness Review Passed | All features reviewed for description adequacy and cross-feature gaps | 6 |
| **CP-FP-4** | `.prizmkit/plans/feature-list.json` Generated | Schema validates, all required keys present | 7-8 |
| **CP-FP-5** | Final Validation Pass | Python script returns `"valid": true` with zero errors | 9 |
| **CP-FP-6** | Local Plan Review Passed | Local generated-plan review loaded `.claude/command-assets/feature-planner/references/generated-plan-review.md`, reviewed only newly added/changed feature entries, applied accepted fixes through draft/source data, regenerated, and revalidated | 10 |

**Resume Detection**: If existing artifacts are found, read `.claude/command-assets/feature-planner/references/error-recovery.md` §Resume Support for checkpoint-based resumption.

## Pre-Generation Completeness Review (Phase 6)

Before generating `.prizmkit/plans/feature-list.json`, review the full feature set holistically.

→ Read `.claude/command-assets/feature-planner/references/completeness-review.md` for the full review process (description adequacy scan, cross-feature completeness check, user presentation, and interactive supplementation).

This gate ensures all features are implementation-ready before output generation. Thin descriptions here cost minutes to fix; misimplemented features downstream cost hours.

## Fast Path (Simple Incremental)

For simple incremental planning, skip detailed Phase 2-3 analysis:

### Eligibility Criteria (ALL must apply)
- **Incremental mode only** — not new feature set
- **Adding 1-2 features max** to existing plan
- **Each feature**: ≤5 acceptance criteria, <100 words description
- **Dependencies**: depends on ≤2 existing features (no chains)
- **Complexity**: "low" or "medium" only
- **No architectural changes** to existing tech stack

### Fast Path Workflow
1. Read existing `.prizmkit/plans/feature-list.json` and confirm scope
2. **User confirmation (mandatory)** — Use `AskUserQuestion` to present interactive selectable options:

   ```
   AskUserQuestion:
     question: "This qualifies for fast-path (simple incremental addition). How would you like to proceed?"
     header: "Approach"
     options:
       - label: "Fast-path"
         description: "Skip detailed Phase 2-3 analysis, draft features directly and add to feature-list.json"
       - label: "Full workflow"
         description: "Use the complete planning workflow with detailed analysis"
   ```

   - **Fast-path** → Continue with fast-path workflow below
   - **Full workflow** → Exit fast path, use full workflow from Phase 2
   - If the user wants direct implementation instead of planning, exit the planner flow after explicit confirmation and recommend `/prizmkit-plan`; do not invoke implementation from inside `feature-planner`.
   
   **NEVER proceed without explicit user selection via `AskUserQuestion`. Do NOT render options as plain text — the user must be able to click/select.**
3. Generate next sequential feature IDs
4. Draft features (title + description + acceptance_criteria + dependencies)
5. Write draft to `.prizmkit/plans/feature-list.draft.json`, then call the generate script:
   ```bash
   python3 .claude/command-assets/feature-planner/scripts/validate-and-generate.py generate --input .prizmkit/plans/feature-list.draft.json --output .prizmkit/plans/feature-list.json
   ```
6. If valid → run the mandatory Local Generated-Plan Review Gate, then summarize and recommend next step
7. If invalid → apply fixes to the draft, re-run generate (max 2 attempts, then escalate to full workflow)

## Browser Interaction Planning

For fullstack/frontend projects, qualifying features get `browser_interaction` **by default**.

### Auto-Detection Rule

A feature **qualifies** when ALL true:
1. `global_context.frontend_framework` exists
2. The feature's `acceptance_criteria` contain UI-related keywords: click, button, modal, page, form, display, navigate, tab, input, opens, shows, renders, visible, redirect, download, upload, preview, select, toggle, dropdown, popup, toast, menu

A feature is **exempt** when ANY true:
- Backend-only (API endpoints, database migrations, no UI criteria)
- Config/setup/infrastructure
- `status: "completed"` (already implemented)

### Default Behavior (Phase 4.2)

1. **Ask user for browser tool preference (Mandatory)**: Before generating any `browser_interaction` fields, use `AskUserQuestion` to ask which browser verification tool to use as the project default. Read `.claude/command-assets/feature-planner/references/browser-interaction.md` §Browser Tool Selection for the exact question format and options (`auto`/`playwright-cli`/`opencli`). Do NOT skip this step or assume a default without asking.
2. **Auto-generate** `browser_interaction` for ALL qualifying features. Read `.claude/command-assets/feature-planner/references/browser-interaction.md` for the object format, field rules, and per-feature `tool` override logic.
3. **Tool assignment per feature**: Use the user's chosen default. Override to `"opencli"` when the feature involves OAuth/SSO callbacks, third-party dashboard verification, or requires real login state. Override to `"playwright-cli"` when the feature is purely local UI (forms, components, routing). If user chose `"auto"`, AI assigns per-feature based on these rules.
4. **Present a summary** to the user showing which features received `browser_interaction` (including the `tool` value for each).
5. **User can opt-OUT** specific features or override the `tool` choice.

## Output Rules

`.prizmkit/plans/feature-list.json` must conform to `.prizmkit/dev-pipeline/templates/feature-list-schema.json` (`$schema` = `dev-pipeline-feature-list-v1`).

Key requirements:
- non-empty `features` array
- sequential feature IDs (`F-001`, `F-002`, ...)
- valid dependency DAG (no cycles, all referenced IDs exist)
- `priority`: `"critical"`, `"high"`, `"medium"`, or `"low"` (string, NOT numeric)
- new items default `status: "pending"`
- English feature titles for stable slug generation
- `browser_interaction` auto-generated for qualifying frontend features (with `tool` selection: `auto`/`playwright-cli`/`opencli`)
- descriptions: minimum 15 words (error), recommended minimum 30/50/80/100+ for low/medium/high/critical (warning). No upper limit — more detail prevents AI guessing
- `estimated_complexity` determines pipeline execution tier:
  - `low` / `medium` → **lite** (single agent, no subagents)
  - `high` → **standard** (orchestrator + reviewer guardrails, 3-agent metadata)
  - `critical` → **full** (strongest orchestrator/reviewer guardrails). Use for: architectural changes touching 10+ files, cross-module refactoring with API surface changes, or safety/security/data-loss risk

**IMPORTANT: Do NOT hand-write the final JSON file.** Instead:
1. Write a draft JSON to a temporary path (e.g., `.prizmkit/plans/feature-list.draft.json`)
2. Call the generate script to validate and produce the final file:
```bash
python3 .claude/command-assets/feature-planner/scripts/validate-and-generate.py generate --input .prizmkit/plans/feature-list.draft.json --output .prizmkit/plans/feature-list.json
```
The script fills in defaults (`$schema`, `created_at`, `created_by`), validates all fields, and writes the final file only if validation passes. If validation fails, fix the draft and retry.

## Local Generated-Plan Review Gate

User requirement preserved verbatim: `there is a litter bug for prizm-code-review will to check git diff in working space and staged space , however the .prizmkit will be gitignored in most situation.  so do you think the content should be change to inline a new reference file instead of use prizmkit-code-review`

Run this gate **after** `.prizmkit/plans/feature-list.json` passes the validation/generate script and **before** the final handoff summary recommends `feature-pipeline-launcher`. This gate applies to full workflow and fast-path incremental planning when the current session generated, appended, or rewrote final feature planning content. For validate-only, summary-only, or draft-save flows with no new final planning content, report: `Local generated-plan review: not applicable — no new final planning content written.`

1. **Load the local reference**: read `.claude/command-assets/feature-planner/references/generated-plan-review.md` and follow it as the source of truth for this planner-output review loop.
2. **Read actual planning artifacts directly**: inspect `.prizmkit/plans/feature-list.json`, `.prizmkit/plans/feature-list.draft.json` when present, and any pre-session or in-memory draft snapshot. Do not rely on `git status`, `git diff`, or `git diff --cached`, because `.prizmkit` planning artifacts are often gitignored or untracked.
3. **Identify review scope**: compare by stable feature IDs and item fields against the pre-session list when one existed. Ignore root generator metadata such as `$schema`, `created_at`, and `created_by`. Review only newly added or changed feature entries; preserve unchanged historical entries except when needed to verify dependency references.
4. **Run the local checklist** from the reference: schema compatibility, dependency/DAG soundness, description completeness, headless execution readiness, acceptance criteria measurability, user-provided wording preservation, task-scoped `user_context` isolation, priority/complexity calibration, and browser interaction fields when applicable.
5. **Keep the review planning-only**: do NOT start `feature-pipeline-launcher`, do NOT run the dev-pipeline, do NOT run tests/builds/installs, and do NOT implement source-code changes.
6. **Apply accepted review fixes through the draft/source plan**: when a finding is accepted, update `.prizmkit/plans/feature-list.draft.json` or the in-memory draft representation first, then regenerate the final file with:
   ```bash
   python3 .claude/command-assets/feature-planner/scripts/validate-and-generate.py generate --input .prizmkit/plans/feature-list.draft.json --output .prizmkit/plans/feature-list.json
   ```
   Do not hand-patch the final JSON as the source of truth; map final-output findings back to draft entries before regeneration.
7. **Revalidate after every accepted fix batch**: the generate script must pass again before the planner can proceed. If validation fails, fix the draft and rerun until pass.
8. **Report the gate outcome** in the final summary: include local generated-plan review verdict, reviewed feature IDs, accepted fixes (or "none"), and final validation result.

## Testing Defaults (Phase 8)

Set default testing-related fields for each feature. The user can opt out of generated testing expectations, but do not generate retired review-agent configuration fields.

| Priority | Testing expectation | Rationale |
|----------|---------------------|-----------|
| high | Require scoped tests and review-gate evidence | Higher-risk feature behavior needs stronger verification. |
| medium | Require focused tests for changed public behavior | Normal changes need meaningful boundary coverage. |
| low | Require the smallest relevant verification | Low-risk changes should stay lightweight. |

Never emit `critic` or `critic_count`; those fields are fully removed and the validator rejects them.

For frontend features with `browser_interaction`, browser verification is enabled by default. The `tool` field uses the user's choice from the mandatory browser tool question in Phase 4.2 (see §Browser Interaction Planning → Default Behavior).

Present a consolidated testing summary table at Phase 8, then ask for confirmation.

## Next-Step Execution Policy (after planning)

Recommend invoking `feature-pipeline-launcher` to configure and launch the dev-pipeline. Do NOT recommend running shell scripts directly — that is the launcher's responsibility. Follow the post-planning handoff in §Scope Boundary (never auto-execute).

## Error Recovery & Resume

If validation fails or a session is interrupted → read `.claude/command-assets/feature-planner/references/error-recovery.md` for the full error type table, decision tree, retry logic, and checkpoint-based resume support.

Key behaviors:
- Warnings only → proceed with user approval
- Critical errors → group by type, auto-fix where possible, max 3 total attempts
- Interrupted session → detect checkpoint from existing artifacts, offer resume or restart
- `.prizmkit/plans/feature-list.json` MUST be written to `.prizmkit/plans/` (project root level: `./{root}/.prizmkit/plans/feature-list.json`)

## Session Exit Gate

Prevent accidental session exit without deliverable completion.

### Trigger Conditions
Activate when ALL true:
- User expressed intent to produce .prizmkit/plans/feature-list.json
- Current phase < Phase 7
- No valid `.prizmkit/plans/feature-list.json` written in this session

### Gate Behavior
When the session appears to be ending:
1. **Remind**: "You set out to produce `.prizmkit/plans/feature-list.json` but we haven't completed it yet."
2. Use `AskUserQuestion` with one question:
   - **Continue to completion (Recommended)** — resume from current phase
   - **Save draft & exit** — write current progress as `.prizmkit/plans/feature-list.draft.json`
   - **Abandon** — exit without saving

## Handoff Message Template

After successful validation and the Local Generated-Plan Review Gate, report:
1. Output file path
2. Total features + newly added features
3. Dependency and priority highlights
4. Local generated-plan review result: verdict, reviewed feature IDs, accepted fixes (or "none"), and final validation result
5. Recommended next action: `feature-pipeline-launcher`

Then apply the post-planning handoff in §Scope Boundary (ask before proceeding; never auto-execute).
