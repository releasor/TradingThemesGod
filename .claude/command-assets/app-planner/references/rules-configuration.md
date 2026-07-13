# Rules Configuration — Full Procedure

Procedure for configuring per-layer development rules during app planning.

## Step 1: Detect Layers

- Prefer `.prizmkit/config.json` `tech_stack` when present.
- Otherwise infer layers from project files:
  - frontend: `package.json` plus React/Vue/Svelte/Next/Vite indicators
  - backend: Express/FastAPI/Django/Go/Java service indicators
  - database: migrations, ORM config, schema files, or DB dependencies
  - mobile: Flutter/React Native/iOS/Android indicators
- Present detected layers with `AskUserQuestion`; include "Skip rules configuration" as a non-blocking option.

## Step 2: Choose Configuration Mode

- Quick mode asks only manifest groups marked `quick_mode: true`.
- Full mode asks every manifest group in order.
- Skip mode records no rules file for that layer and continues without reminders.

## Step 3: Ask Questions with AskUserQuestion

- Convert each question-bank option group into selectable `AskUserQuestion` options.
- Do not ask users to type letter shortcuts such as `A` or `1`; those shortcuts are legacy notation in question banks only.
- Every non-essential question includes a skip/defer option.

## Step 4: Configure Each Selected Layer — Full Q&A Workflow

For each selected layer, run the 4-phase rule generation pattern:

### Phase A — Load Layer Resources

- Read `${SKILL_DIR}/references/rules/<layer>/fixed-rules.md` — industry-consensus rules injected without asking
- Read `${SKILL_DIR}/references/rules/<layer>/question-bank.md` — interactive questions organized in groups (G1->G10): authoritative source for question text, options, "Recommended" markers, and Notes
- Read `${SKILL_DIR}/references/rules/<layer>/question-manifest.json` — machine-readable structure for this layer. This is the asking checklist. It lists, per question: `group`, `required`, `maps_to`, `required_if`, `auto_derived_when`, and `options_vary_by`. Its `groups[]` carries each group's `quick_mode` flag, and `template_placeholders` is the expected-set for the Phase D self-check. Use the manifest to track coverage; use question-bank.md for the actual wording you present to the user. If a question id in one file is absent from the other, trust question-bank.md for content and note the drift.

### Phase B — Interactive Q&A

- Ask questions one group at a time (max 3 questions per message), as defined in question-bank.md.
- Each question shows a "Recommended" option to reduce decision cost.
- Quick mode: ask only the groups whose `quick_mode` is `true` in `question-manifest.json`. All other groups adopt recommended defaults silently.
- Full mode: ask all groups in manifest order (`groups[]`).
- Conditional questions:
  - `required_if: "<expr>"` — ask this question only when the expression over prior answers holds. If false, the question is legitimately skipped.
  - `auto_derived_when: "<expr>"` — when true, fill the mapped placeholder(s) from the prior answer without asking. Count as satisfied, not skipped.
  - `options_vary_by: "<Qid>"` — the question is still asked; only its option list depends on that prior answer.
- Legacy shortcut labels in question banks such as `recommended`, `default`, or `skip` are converted into selectable options in `AskUserQuestion`.
- Do not ask the user to type these commands manually; selectable options prevent merged or missed decisions.
- Record answers in memory after each group. Track which manifest questions are answered, auto-derived, or conditionally skipped so Phase D can verify coverage.

### Phase C — Auto-derivation

- Read `${SKILL_DIR}/references/rules/<layer>/derivation-rules.md`.
- Match user answers against the trigger map using keyword matching.
- Derive platform-specific rules without asking the user.

### Phase D — Render and Write

- Read `${SKILL_DIR}/references/rules/<layer>/template.md`.
- Fill all template placeholders with accumulated content from Phases A+B+C.
- Post-render self-check driven by `question-manifest.json` -> `template_placeholders`:
  1. Coverage pass — for every placeholder in `from_questions`, confirm it traces to an answered question OR an `auto_derived_when` path OR a conditionally-skipped question (`required_if` false). If a `from_questions` placeholder has no source, go back and ask it before writing.
  2. Residual pass — scan the rendered document for any residual `{{ ` or ` }}`; count must be 0. Placeholders in `from_fixed_rules`, `auto_generated`, and `metadata` are filled from fixed rules, Phase D generation, and project metadata.
- Generate Appendix A (Deny List) and Appendix B (Recommended Tools) per template instructions.
- Create `.prizmkit/rules/` directory if it doesn't exist.
- Write `.prizmkit/rules/<layer>-rules.md`.

## Step 5: Update root.prizm RULES Pointer

- Ensure `.prizmkit/prizm-docs/root.prizm` has a concise `RULES:` pointer to configured rules.
- If root.prizm exists, update only the `RULES:` line.
- If root.prizm is absent, create a minimal valid root.prizm with required fields and a `RULES:` pointer.
- Do not write architecture decisions, project brief content, or changelog metadata into root.prizm.
