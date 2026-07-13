# Initial Feature Set Planning Reference

Use this reference when an existing or already app-planned project needs its first `.prizmkit/plans/feature-list.json`.

Do not use this reference to define app vision, tech stack, or architecture from scratch. That belongs to `app-planner`.

## Phase Guide

### Phase 1: Existing Context

Capture or infer:
- project brief and current product goals
- already implemented capabilities
- target users and primary workflows from existing docs or code
- explicit non-goals already documented for the project

### Phase 2: Existing Stack and Architecture

Read `.prizmkit/config.json`, `.prizmkit/plans/project-brief.md`, `.prizmkit/prizm-docs/root.prizm`, and platform instruction files when present. If app-level context is missing and the user is asking for product/stack decisions, recommend `app-planner`.

### Phase 3: MVP Features

Rules:
- Include foundational setup feature first only when the existing project still needs setup work.
- Aim 5-12 features for an initial executable plan unless the user explicitly scopes smaller.
- Keep each feature implementable in one pipeline unit unless clearly too large.

For each feature define:
- `id`
- `title`
- `description`
- `priority` — string: `"critical"`, `"high"`, `"medium"`, or `"low"` (never numeric)
- `estimated_complexity`
- `dependencies`
- `acceptance_criteria`
- `status: "pending"`
- `browser_interaction` when UI verification is useful (see §Browser Interaction Planning in SKILL.md)

### Phase 4: Dependency & Priority

Check:
- no cycles
- all dependency targets exist
- order is executable
- priorities align with delivery value and risk

### Phase 5: Granularity

Split into `sub_features` when:
- scope crosses too many modules
- acceptance criteria are excessive
- complexity is high and uncertainty is high

### Phase 6: Generate + Validate

1. Write `.prizmkit/plans/feature-list.draft.json`.
2. Generate the final file:
   ```bash
   python3 ${SKILL_DIR}/scripts/validate-and-generate.py generate --input .prizmkit/plans/feature-list.draft.json --output .prizmkit/plans/feature-list.json
   ```
3. Fix draft errors, then re-run generate.

## Quality Rules

- Keep titles concise and English.
- Make descriptions implementation-oriented: clear boundaries, interfaces, behavior.
- Description depth by complexity:
  - Low complexity: ≥30 words — what to build, key behavior, which files/modules are affected
  - Medium complexity: ≥50 words — add integration points, data model overview, error handling approach
  - High complexity: ≥80 words — add architecture decisions, performance considerations, security implications, migration strategy if applicable
- Description must cover what, integration points, key behaviors, data model when applicable, and error/edge cases.
- Write at least 1 testable acceptance criterion to satisfy schema validation. Fewer than 3 criteria is a planner quality warning; medium/high features should usually target 5+.
- Keep dependency graph simple and explicit.

## Final Delivery Checklist

- [ ] User confirmed initial feature scope
- [ ] IDs are sequential
- [ ] `status` initialized to `pending`
- [ ] Validation passes
- [ ] Next step recommendation: `feature-pipeline-launcher`
