---
description: "Launch and manage the dev-pipeline from within an AI CLI session. Start pipeline in background, monitor logs, check status, stop pipeline. Use this skill whenever the user wants to start building features, run the pipeline, check pipeline progress, retry features, or stop the pipeline. Trigger on: 'run pipeline', 'start pipeline', 'start building', 'pipeline status', 'stop pipeline', 'retry feature', 'launch pipeline', 'start implementing', 'check pipeline status', 'stop the pipeline'. (project)"
---

# Dev-Pipeline Launcher

Launch the autonomous development pipeline from within an AI CLI conversation. Only Background daemon mode is fully detached and survives AI CLI session closure; Foreground runs in the current session, and Manual prints commands without launching.

Three execution modes are available (Foreground / Background daemon / Manual); they are defined authoritatively in **Intent A, step 5** below.

### When to Use

**Start pipeline** -- User says:
- "run feature pipeline", "run pipeline", "start building features", "launch feature pipeline"
- "start implementing", "execute feature list", "build all features"
- After feature-planner completes: "build them", "start building from the list"
- Supports running a feature subset (e.g. "run only F-001 to F-005", "run features F-001,F-003").

**Check status** -- User says:
- "pipeline status", "feature progress", "check the pipeline", "how's the build going"

**Stop pipeline** -- User says:
- "stop pipeline", "stop the pipeline", "halt pipeline", "pause the build"

**Show logs** -- User says:
- "pipeline logs", "show pipeline logs", "what's building"

**Retry single feature** -- User says:
- "retry F-001", "re-run F-001", "retry this feature"

**Do NOT use this skill when:**
- User wants to plan features (use `feature-planner` instead)
- User wants to implement a single feature manually within current session (use `prizmkit-implement`)
- User wants to define specs/plan (use `prizmkit-plan`)

### Prerequisites

Before any action, validate:

1. **dev-pipeline exists**: Confirm `.prizmkit/dev-pipeline/cli.py` is present
2. **For start**: `.prizmkit/plans/feature-list.json` must exist in `.prizmkit/plans/` (or user-specified path)
3. **Dependencies**: `python3`, `git`, and the configured AI CLI must be in PATH. Resolve and report the AI CLI from `AI_CLI` env, then `.prizmkit/config.json` `ai_cli`, then fallback to `claude` only when neither is configured. Read `.claude/command-assets/feature-pipeline-launcher/references/configuration.md` §Configured AI CLI Prerequisite Check before running the AI CLI check.
4. **Python version**: Requires Python 3.10+ for the unified dev-pipeline runtime
5. **Browser tools** (optional): If any feature has `browser_interaction` field, check the corresponding tool is available. Features may specify `tool: "playwright-cli"`, `tool: "opencli"`, or `tool: "auto"` (AI chooses at runtime).

Quick check:
```bash
command -v python3 >/dev/null && command -v git >/dev/null && echo "Core dependencies OK"
# AI CLI check: read `.claude/command-assets/feature-pipeline-launcher/references/configuration.md` §Configured AI CLI Prerequisite Check.
# It must print `Configured AI CLI: <name>` and verify that exact executable.
# Optional: browser interaction support (check both tools — features may use either)
command -v playwright-cli && echo "playwright-cli OK" || echo "playwright-cli not found (playwright browser verification will be skipped)"
command -v opencli && echo "opencli OK" || echo "opencli not found (opencli browser verification will be skipped)"
```

If `.prizmkit/plans/feature-list.json` is missing, inform user:
> "No .prizmkit/plans/feature-list.json found. Run the `feature-planner` skill first to generate one, or provide a path to your feature list."

### Workflow

Detect user intent from their message, then follow the corresponding workflow:

---

#### Intent A: Start Pipeline

> **Execution model**: The pipeline processes eligible features one at a time. The `dependencies` field is active: dependencies must complete before dependents are selected, and unrelated eligible items preserve stable list order.

1. **Check prerequisites**:
   ```bash
   ls .prizmkit/plans/feature-list.json 2>/dev/null && echo "Found" || echo "Missing"
   ```

2. **Check not already running**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature status 2>/dev/null
   ```
   If running, inform user and ask: "Pipeline is already running. Want to restart it, check status, or view logs?"

3. **Show feature summary** (so user knows what will be built):
   ```bash
   python3 -c "
   import json
   with open('.prizmkit/plans/feature-list.json') as f:
       data = json.load(f)
   features = data.get('features', [])
   print(f'Total features: {len(features)}')
   for f in features:
       print(f\"  {f['id']}: {f.get('title', 'untitled')}\")
   "
   ```
   If pipeline state already exists, use the status command instead:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py feature status .prizmkit/plans/feature-list.json
   ```

4. **Run environment preflight checks** (database connectivity, migrations, dev server):

   Run the preflight script to auto-detect the database type, verify env vars, test connectivity, and check migration status:
   ```bash
   python3 <feature-pipeline-launcher-skill-dir>/scripts/preflight-check.py .prizmkit/plans/feature-list.json
   ```

   Replace `<feature-pipeline-launcher-skill-dir>` with the resolved skill directory path before running. Do not execute a literal unresolved `.claude/command-assets/feature-pipeline-launcher` shell variable.

   The script:
   - Reads `global_context.database` from `.prizmkit/plans/feature-list.json` and `.prizmkit/config.json`
   - Scans `.env.local` / `.env` for connection variables (supports Supabase, PostgreSQL, MySQL, MongoDB, Firebase, and generic `DATABASE_URL`)
   - Tests connectivity using the appropriate method per database type
   - Checks migration status (Prisma, Drizzle, Supabase raw SQL, or generic migration directories)
   - Checks if the dev server is running (from `browser_interaction` URLs)
   - Outputs `PREFLIGHT ✓` (pass), `PREFLIGHT ⚠` (warning), or `PREFLIGHT ℹ` (info) lines
   - Exits 0 (all clear), 1 (warnings found), or 2 (error — feature list not found)

   If the script reports `⚠` warnings, present them to the user and ask:
   > "Environment preflight found issues (listed above). The pipeline can still run, but database-related features may produce code that passes mock tests without real database verification. Continue anyway?"

   Wait for user confirmation. If they want to fix issues first, suggest remediation based on the warnings (apply migrations, configure env vars, check database service status).

   If `global_context.database` is absent and no features mention database keywords, the script skips DB checks automatically.

5. **Ask execution mode** (first user decision):

   **RULE: Ask step 5 and step 6 in separate `AskUserQuestion` calls.** Combining them makes the model merge the questions and skip the mode selection. Ask execution mode ALONE here, wait for the response, THEN proceed to step 6.

   Use `AskUserQuestion` with exactly 1 question:

   **Question 1 — Execution mode** (multiSelect: false):
   - Foreground (Recommended) — pipeline runs in the current session via `python3 ./.prizmkit/dev-pipeline/cli.py feature run`. Visible output and direct error feedback.
   - Background daemon — pipeline runs fully detached via `python3 ./.prizmkit/dev-pipeline/cli.py daemon feature start .prizmkit/plans/feature-list.json`. Survives AI CLI session closure.
   - Manual — display the final assembled commands only. Do not execute anything. User runs them on their own.

   STOP HERE and wait for user response before continuing to step 6.

6. **Ask configuration options** — MANDATORY INTERACTIVE STEP, applies to ALL execution modes (Foreground, Background, AND Manual). This is a SEPARATE `AskUserQuestion` call from step 5 (see the RULE above). You MUST call `AskUserQuestion` with the 4 questions below and WAIT for the user's response before proceeding to step 7. Do NOT assume defaults, do NOT show the command as text and ask "ready?", and do NOT merge step 6 and step 7. If you find yourself writing the final command before the user has answered these 4 questions, STOP — you are violating this rule.

   Use `AskUserQuestion` to present ALL 3 configuration choices:

   **Question 1 — Verbose logging** (multiSelect: false):
   - On (default) — Detailed AI session logs including tool calls and subagent activity
   - Off — Minimal logging

   **Question 2 — Max retries** (multiSelect: false):
   - 3 (default)
   - 1
   - 5

   **Question 3 — Advanced config?** (multiSelect: false):
   - No (default) — Use defaults for failure behavior
   - Yes — Configure stop-on-failure, deploy-after-completion, and reasoning effort options

   **If user chose "Yes" to Advanced config**, ask a second round of `AskUserQuestion` — see the advanced config questions (stop-on-failure, deploy-after-completion, reasoning effort) in `.claude/command-assets/feature-pipeline-launcher/references/configuration.md`.

   Read `.claude/command-assets/feature-pipeline-launcher/references/configuration.md` for the current environment-variable mapping and advanced environment-variable tables.


7. **Show final command**: After user confirms configuration in step 6, assemble the complete command from execution mode + user-confirmed configuration, and present it to the user.

   **Foreground command:**
   ```bash
   VERBOSE=1 python3 ./.prizmkit/dev-pipeline/cli.py feature run .prizmkit/plans/feature-list.json
   ```
   Selected-options example:
   ```bash
   VERBOSE=1 MAX_RETRIES=5 STOP_ON_FAILURE=1 ENABLE_DEPLOY=1 PRIZMKIT_EFFORT=high \
     python3 ./.prizmkit/dev-pipeline/cli.py feature run .prizmkit/plans/feature-list.json --features F-001:F-005
   ```

   **Background daemon command:**
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature start .prizmkit/plans/feature-list.json --env "VERBOSE=1"
   ```
   Selected-options example:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature start .prizmkit/plans/feature-list.json --features F-001:F-005 \
     --env "VERBOSE=1 MAX_RETRIES=5 STOP_ON_FAILURE=1 ENABLE_DEPLOY=1 PRIZMKIT_EFFORT=high"
   ```

   **Manual mode**: Print the assembled command(s) and **stop here**. Do not execute anything. Do not proceed to step 8.
   ```
   # To run in foreground:
   VERBOSE=1 python3 ./.prizmkit/dev-pipeline/cli.py feature run .prizmkit/plans/feature-list.json

   # To run in background (detached):
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature start .prizmkit/plans/feature-list.json --env "VERBOSE=1"

   # To check status:
   python3 ./.prizmkit/dev-pipeline/cli.py feature status .prizmkit/plans/feature-list.json
   ```

8. **Confirm and launch** (Foreground and Background only — Manual mode ends at step 7):

   Use a separate `AskUserQuestion` call: "Ready to launch the pipeline with the above command?"
   Options:
   - Launch now (Recommended)
   - Cancel

   After user confirms, execute the command from step 7.

9. **Post-launch** (depends on execution mode):

   **If foreground**: Pipeline runs to completion in the terminal. After it finishes:
   - Summarize results: total features, succeeded, failed, skipped
   - If all succeeded: each feature session has already run `prizmkit-retrospective` internally. Ask user what's next.
   - If some failed: show failed feature IDs and suggest `python3 ./.prizmkit/dev-pipeline/cli.py reset feature <F-XXX> --clean --run` for a fresh retry
   - **Browser verification**: If any completed features have `browser_interaction` and the corresponding browser tool (`playwright-cli` or `opencli`) is installed, offer to run browser verification (see Post-Pipeline Browser Verification)

   **If background daemon**:
   1. Verify launch:
      ```bash
      python3 ./.prizmkit/dev-pipeline/cli.py daemon feature status
      ```
   2. Start log monitoring — Use the Bash tool with `run_in_background: true`:
      ```bash
      python3 ./.prizmkit/dev-pipeline/cli.py daemon feature logs --follow
      ```
   3. Report to user:
      - Pipeline PID
      - Log file location
      - "You can ask me 'pipeline status' or 'show logs' at any time"
      - "Closing this session will NOT stop the pipeline"

---

#### Intent B: Check Status

1. **Check daemon status**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature status
   ```

2. **Show feature-level progress**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py feature status .prizmkit/plans/feature-list.json
   ```

3. **Show recent log activity** (last 20 lines):
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature logs --lines 20
   ```

4. **Summarize** to user: total features, completed, in-progress, failed, pending.

---

#### Intent C: Stop Pipeline

1. **Stop the daemon**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature stop
   ```

2. **Verify stopped**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature status 2>/dev/null || true
   ```

3. **Inform user**: "Pipeline stopped. State is preserved -- you can resume later with 'start pipeline' and it will pick up where it left off."

---

#### Intent D: Show Logs

1. **Check if running**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature status 2>/dev/null
   ```

2. **If running** -- Start live tail with Bash tool `run_in_background: true`:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature logs --follow
   ```

3. **If not running** -- Show last 50 lines:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon feature logs --lines 50
   ```

4. **For per-feature session logs** (when user asks about a specific feature):
   ```bash
   # Check feature status for last session ID
   cat .prizmkit/state/features/<FEATURE_ID>/status.json 2>/dev/null
   # Then tail that feature's session log
   tail -100 .prizmkit/state/features/<FEATURE_ID>/sessions/<SESSION_ID>/logs/session.log
   ```

---

#### Intent E: Retry Single Feature Node

When user says "retry F-003" or "clean retry F-003":

```bash
python3 ./.prizmkit/dev-pipeline/cli.py reset feature F-003 --clean --run .prizmkit/plans/feature-list.json
```

Notes:
- `python3 ./.prizmkit/dev-pipeline/cli.py reset feature <F-XXX> --clean --run .prizmkit/plans/feature-list.json` performs a full clean (deletes session history and artifacts) before retrying the selected feature — this gives a fresh start.
- Keep pipeline daemon mode for main run management (`python3 ./.prizmkit/dev-pipeline/cli.py daemon feature start`, `python3 ./.prizmkit/dev-pipeline/cli.py daemon feature status`, or `python3 ./.prizmkit/dev-pipeline/cli.py daemon feature stop`).

---

#### Post-Pipeline Browser Verification

After pipeline completion, if features have `browser_interaction` fields and the corresponding browser tool (`playwright-cli` or `opencli`) is installed:

If list status may be stale, use the runtime status command as the source of truth for completion state:
`python3 ./.prizmkit/dev-pipeline/cli.py feature status .prizmkit/plans/feature-list.json`.

1. **Check which completed features have browser verification configured**:
   - Read `browser_interaction` configuration from `.prizmkit/plans/feature-list.json`.
   - Use the runtime status command output to decide which configured features are actually completed.
   - Do not rely on list-file `status` alone when runtime state exists, because daemon/foreground bookkeeping may be newer than the plan file.

2. **Ask user**: "N features have browser verification configured. Run browser verification now? (Y/n)"

3. **If yes**, for each qualifying feature:
   - Start dev server if `setup_command` is specified
   - Select browser tool based on `browser_interaction.tool`:
     - `"playwright-cli"` → Use `playwright-cli snapshot` to discover element refs, then verify each goal in `verify_steps`
     - `"opencli"` → Use `opencli browser` to interact with Chrome's logged-in session (ideal for OAuth/third-party verification)
     - `"auto"` → AI chooses the appropriate tool based on context (default: `playwright-cli` for local dev, `opencli` for authenticated flows)
   - Take a screenshot after verification
   - Close browser and stop dev server

4. **Report results**:
   - For each feature: URL opened, tool used, steps executed, screenshot path
   - If any step fails: flag as verification failure

**Important**: Browser verification is best-effort — failures here do NOT change the feature's pipeline status. They serve as visual confirmation aids for the user.

---

### Error Handling

Read `.claude/command-assets/feature-pipeline-launcher/references/configuration.md` for the full error handling table covering feature-list, dependency checks, pipeline state, browser tooling, permission, and deploy failures.

### Integration Notes

- **After feature-planner**: This is the natural next step. When user finishes planning and has `.prizmkit/plans/feature-list.json`, suggest launching the pipeline.
- **Session independence**: Only Background daemon mode runs detached. Foreground runs in the current AI CLI session, and Manual mode prints commands without launching.
- **Single instance per family**: Only one feature pipeline can run at a time. Different pipeline families may coexist because they use separate daemon metadata and state directories.
- **Pipeline coexistence**: Feature, bugfix, and refactor pipelines use separate state directories (`.prizmkit/state/features/`, `.prizmkit/state/bugfix/`, `.prizmkit/state/refactor/`), so all three can run simultaneously without conflict.
- **State preservation**: Stopping and restarting the pipeline resumes from where it left off -- completed features are not re-run.
- **HANDOFF**: After pipeline completes all features, each session has already run `prizmkit-retrospective` internally. Ask user what's next.
