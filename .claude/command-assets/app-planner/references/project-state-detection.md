# Project State Detection — Brownfield Behavior

Detailed procedures for detecting and handling existing (brownfield) projects during app planning.

## Detection Signals

| Signal | Greenfield | Brownfield |
|--------|-----------|------------|
| `package.json` / `pyproject.toml` / `go.mod` / `Cargo.toml` / `pom.xml` | absent | present |
| `src/` or `app/` directory with source files | absent | present |
| `.git` with commit history | absent or initial commit only | present with history |
| Empty or near-empty directory | yes | no |

## Greenfield Behavior (default)

Proceed with the standard Core Workflow — ask all questions from scratch.

## Brownfield Behavior

When an existing project is detected:

### Step 1: Prerequisite Check (Mandatory)

Before ANY planning work, check if AI-essential project context files exist:

| File | Purpose | Status |
|------|---------|--------|
| `.prizmkit/prizm-docs/root.prizm` | Project architecture context for AI | exists / missing |
| `.prizmkit/config.json` | Tech stack + runtime config | exists / missing |
| `.prizmkit/plans/project-brief.md` | Product vision checklist | exists / missing |

**If ANY are missing**, show the status table, then use `AskUserQuestion`:

**Question**: "Some AI context files are missing. These help AI understand your project — making planning much more effective. How would you like to proceed?"
- **Run project init first** — invoke `prizmkit-init` to scan your codebase and generate these files, then return to planning
- **Continue without init** — I'll scan the project manually during this session (less thorough)
- **Skip, I'll set these up later** — proceed with planning using only what's available

- **Run project init first** -> Invoke `prizmkit-init`, then resume app-planner from where it left off
- **Continue without init** -> Continue with Step 2 below (manual scan)
- **Skip** -> Continue with Step 3, skip scanning

### Step 2: Proactive Project Scanning

Do NOT ask the user to describe their project — read it yourself first:

1. **Scan project structure** to understand the codebase layout:
   ```bash
   find . -maxdepth 2 -type d -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/__pycache__/*' -not -path '*/vendor/*' | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
   ```

2. **Read existing project metadata** to infer tech stack and purpose:
   - `package.json` -> name, description, dependencies, scripts
   - `pyproject.toml` / `requirements.txt` -> Python dependencies
   - `go.mod` -> Go module info
   - `README.md` -> project description and goals
   - `.prizmkit/config.json` -> previously detected tech stack
   - `.prizmkit/prizm-docs/root.prizm` -> existing architecture context

3. **Read key source files** (entry points, main routes, core models) to understand what the project actually does — don't rely solely on metadata.

### Step 3: Present Inferred Summary with Confirmation

Show the summary as text, then use `AskUserQuestion`:

> Based on my analysis of your codebase:
>
> **Project**: [name] — [inferred description]
> **Tech Stack**: [framework] + [language] + [key dependencies]
> **Key Features Found**: [list 3-5 detected capabilities]
> **Architecture**: [e.g., monolithic, microservices, serverless]

**Question**: "Does this look correct?"
- **Yes, looks correct** — proceed with planning
- **Mostly correct, with changes** — I'll note corrections
- **This is off** — let me describe the project

### Step 4: Pre-fill and Focus

- Phase 2 tech stack selection -> largely pre-filled from dependencies
- Vision/problem statement -> inferred from README or package description (user confirms)
- Existing features -> note them as `[x]` items in project brief

**Focus remaining questions** (as options where possible) on what CANNOT be inferred:
- Target users and core value proposition
- Future direction and planned capabilities
- Non-functional requirements (performance, scale, security)
- Design direction (for frontend projects)
