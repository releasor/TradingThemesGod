# Fast Path — Refactor Planner

For simple refactoring with minimal scope.

## Eligibility Criteria (ALL must apply)
- 1-2 refactor items only
- Complexity: `low` or `medium` for all items
- No cross-module impact (all items within same module)
- Well-known refactoring pattern (rename, extract method/class, inline)
- Existing test coverage for target area

## Fast Path Workflow
1. Confirm refactoring scope with user
2. **User confirmation (mandatory)** — Use `AskUserQuestion` to present interactive selectable options:

   ```
   AskUserQuestion:
     question: "This qualifies for fast-path (simple refactoring). How would you like to proceed?"
     header: "Approach"
     options:
       - label: "Fast-path"
         description: "Skip detailed analysis, draft refactor items directly and add to refactor-list.json"
       - label: "Full workflow"
         description: "Use the complete planning workflow with detailed code analysis"
   ```

   - **Fast-path** → Continue with fast-path workflow below
   - **Full workflow** → Exit fast path, use full workflow from Phase 2
   - If the user wants direct implementation instead of planning, exit the planner flow after explicit confirmation and recommend `/prizmkit-plan`; do not invoke implementation from inside `refactor-planner`.

   **NEVER proceed without explicit user selection via `AskUserQuestion`. Do NOT render options as plain text — the user must be able to click/select.**
3. Draft items (title + type + scope + description + acceptance_criteria + behavior_preservation + dependencies)
4. Write draft to `.prizmkit/plans/refactor-list.draft.json`, then call the generate script:
   ```bash
   python3 ${SKILL_DIR}/scripts/validate-and-generate-refactor.py generate --input .prizmkit/plans/refactor-list.draft.json --output .prizmkit/plans/refactor-list.json
   ```
5. If valid -> run the mandatory Local Generated-Plan Review Gate from the main `refactor-planner` skill before summarizing or recommending `refactor-pipeline-launcher`.
6. If invalid -> apply fixes to the draft, re-run generate (max 2 attempts, then escalate to full workflow)

## When NOT to Use Fast Path
- More than 2 refactor items
- Any item with `high` complexity
- Cross-module impact
- Architecture migration patterns (Format C goals)
- No existing test coverage for target area

## Example Fast Path Session
```
User: "Rename the auth middleware function from checkAuth to requireAuth everywhere."
AI: [Detects simple rename, single module]
AI: [Qualifies for fast path: 1 item, low complexity, no cross-module impact]
AI: [Uses AskUserQuestion with options: "Fast-path", "Full workflow"]
User: [Selects "Fast-path"]
AI: "Drafting R-001..."
AI: [Validates immediately]
AI: [Runs the Local Generated-Plan Review Gate on R-001 only]
AI: "Ready to proceed to dev-pipeline."
```
