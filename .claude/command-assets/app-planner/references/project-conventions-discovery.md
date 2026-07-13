# Project Conventions Discovery

AI-driven procedure for discovering and capturing project-level conventions. SKILL.md retains the trigger condition and entry point; this file contains the full Analyze → Reason → Present workflow.

## Principle

**Do NOT follow any fixed checklist.** Every project is different. You must analyze the project first, then reason about what system-level conventions this specific project needs.

## Step 1: Analyze the project

- Read tech stack, dependencies, existing code, config files, README, any existing style guides or linter configs
- For brownfield: also read actual source code patterns (naming, file structure, error handling, etc.)
- For greenfield: use the user's stated goals and intended tech stack

## Step 2: Reason about what conventions matter for THIS project

Think about what decisions, if left unstandardized, would cause inconsistency as the project grows. Consider all dimensions relevant to the project — these might include (but are NOT limited to):

- Language and localization choices
- Code style and naming patterns
- Architecture and communication patterns
- Data format and storage decisions
- Security and auth approaches
- UI/UX patterns
- Testing strategies
- Deployment and environment patterns
- ...anything else you observe that needs a project-level decision

The point is: YOU decide what's relevant based on what you see. A Next.js SaaS app needs completely different conventions than a Python data pipeline or a Go microservice.

## Step 3: Present findings via `AskUserQuestion`

First, show "Already decided" conventions as text:
> **Already decided** (detected from your codebase):
> - [convention]: [value] (source: [where you found it])
> - [convention]: [value] (source: [where you found it])

Then use `AskUserQuestion` for conventions that need user input (up to 4 questions per call, use multiple calls as needed — no limit on total rounds). Each question:
- Question text includes the convention name AND why it matters for this project
- Options are the reasonable choices (2-4 per question)
- Mark the recommended option first with "(Recommended)" in its label
- Use `description` field to explain trade-offs

After each batch of `AskUserQuestion` calls, reassess: are there more project-level conventions to cover? If yes, continue with more `AskUserQuestion` calls. Keep going until ALL project-level conventions are fully addressed.

Then ask in text: "Anything I missed that you'd like to standardize?" — if the user adds more, continue the discovery loop.

## Rules

- **No interaction limit** — keep asking until every project-level convention is covered. Do NOT stop early or batch-skip to save rounds.
- Every proposed convention must be justified by something you observed in the project — explain WHY it matters
- Auto-confirm anything already evident from the codebase (show as "detected", let user override)
- Propose as many conventions as the project genuinely needs, but don't pad with irrelevant ones
- The "Anything I missed?" question is NOT the end — if the user adds items, ask follow-up `AskUserQuestion` calls to clarify those too

## After Discovery

→ Save answers to `AGENTS.md` / `CLAUDE.md` / `CODEBUDDY.md` under `### Project Conventions` section (format: one bullet per convention)
→ Output format will naturally vary per project — that is the intended behavior
