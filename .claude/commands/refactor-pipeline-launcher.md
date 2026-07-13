---
description: "Launch and manage the refactor pipeline from within an AI CLI session. Start pipeline in background, monitor logs, check status, stop pipeline. Use this skill whenever the user wants to start refactoring, run the refactor pipeline, check refactor progress, retry refactors, or stop the pipeline. Trigger on: 'run refactor pipeline', 'start refactoring', 'refactor pipeline status', 'stop refactor pipeline', 'retry refactor', 'launch refactor pipeline'. (project)"
---

# Refactor Pipeline Launcher

Launch the autonomous refactor pipeline from within an AI CLI conversation. Only Background daemon mode is fully detached and survives AI CLI session closure; Foreground runs in the current session, and Manual prints commands without launching.

### Execution Mode

Three execution modes are available. The user chooses one before configuring other options:

1. **Foreground** (recommended) — `python3 ./.prizmkit/dev-pipeline/cli.py refactor run`. Visible output, direct error feedback, no orphaned processes.
2. **Background daemon** — `python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor start .prizmkit/plans/refactor-list.json`. Runs fully detached, survives AI CLI session closure.
3. **Manual** — Display the assembled command(s) only. Do not execute anything. User runs them on their own.

### When to Use

**Start pipeline** -- User says:
- "run refactor pipeline", "start refactoring", "launch refactor pipeline"
- "execute refactor list", "refactor all", "start refactoring tasks"
- After refactor-planner completes: "refactor it", "start refactoring from the list"

**Check status** -- User says:
- "refactor pipeline status", "refactor progress", "check refactoring"
- "how's the refactoring going", "refactor status"

**Stop pipeline** -- User says:
- "stop refactor pipeline", "stop refactoring", "halt refactor", "pause refactoring"

**Show logs** -- User says:
- "refactor logs", "show refactor logs", "what's being refactored"
- "view refactor logs"

**Retry single refactor** -- User says:
- "retry R-001", "retry this refactor", "re-run R-001"

**Do NOT use this skill when:**
- User wants to plan refactoring (use `refactor-planner` instead)
- User wants a single interactive refactor in current session (use `refactor-workflow` — but note it will delegate back here for batch execution)
- User wants to implement features (use `feature-pipeline-launcher`)

### Prerequisites

Before any action, validate:

1. **refactor pipeline exists**: Confirm `.prizmkit/dev-pipeline/cli.py` is present
2. **For start**: `.prizmkit/plans/refactor-list.json` must exist in `.prizmkit/plans/` (or user-specified path)
3. **Dependencies**: `python3`, `git`, and the configured AI CLI must be in PATH. Resolve and report the AI CLI from `AI_CLI` env, then `.prizmkit/config.json` `ai_cli`, then fallback to `claude` only when neither is configured. Read `.claude/command-assets/refactor-pipeline-launcher/references/configuration.md` §Configured AI CLI Prerequisite Check before running the AI CLI check.
4. **Python version**: Requires Python 3.10+ for the unified dev-pipeline runtime
5. **Browser tools** (optional): If any refactor has `browser_interaction` field, check the corresponding tool is available. Refactors may specify `tool: "playwright-cli"`, `tool: "opencli"`, or `tool: "auto"` (AI chooses at runtime).

Quick check:
```bash
command -v python3 >/dev/null && command -v git >/dev/null && echo "Core dependencies OK"
# AI CLI check: read `.claude/command-assets/refactor-pipeline-launcher/references/configuration.md` §Configured AI CLI Prerequisite Check.
# It must print `Configured AI CLI: <name>` and verify that exact executable.
# Optional: browser interaction support (check both tools — refactors may use either)
command -v playwright-cli && echo "playwright-cli OK" || echo "playwright-cli not found (playwright browser verification will be skipped)"
command -v opencli && echo "opencli OK" || echo "opencli not found (opencli browser verification will be skipped)"
```

If `.prizmkit/plans/refactor-list.json` is missing, inform user:
> "No .prizmkit/plans/refactor-list.json found. Run the `refactor-planner` skill first to generate one, or provide a path to your refactor list."

### Workflow

Detect user intent from their message, then follow the corresponding workflow:

---

#### Intent A: Start Pipeline

> **Execution model**: The pipeline processes eligible refactor tasks one at a time. The `dependencies` field is active: dependencies must complete before dependents are selected. Among unrelated eligible refactors, stable list order determines selection.

1. **Check prerequisites**:
   ```bash
   ls .prizmkit/plans/refactor-list.json 2>/dev/null && echo "Found" || echo "Missing"
   ```

2. **Check not already running**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor status 2>/dev/null
   ```
   If running, inform user and ask: "Refactor pipeline is already running. Want to restart it, check status, or view logs?"

3. **Show refactor summary** (so user knows what will be refactored):
   ```bash
   python3 -c "
   import json
   with open('.prizmkit/plans/refactor-list.json') as f:
       data = json.load(f)
   refactors = data.get('refactors', [])
   print(f'Total refactor tasks: {len(refactors)}')
   type_counts = {}
   for r in refactors:
       t = r.get('type', 'unknown')
       type_counts[t] = type_counts.get(t, 0) + 1
   if type_counts:
       print(f'By type: {dict(sorted(type_counts.items()))}')
   print()
   priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
   refactors_sorted = sorted(refactors, key=lambda r: (priority_order.get(r.get('priority', 'medium'), 2), r.get('id', '')))
   for r in refactors_sorted:
       print(f\"  {r['id']}: [{r.get('priority','medium').upper()}] [{r.get('type','?')}] {r.get('title', 'untitled')}\")
   "
   ```
   If pipeline state already exists, use the status command instead:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py refactor status .prizmkit/plans/refactor-list.json
   ```

4. **Run preflight checks** (behavior-preservation baseline):

   Before refactoring, verify the codebase is in a clean, testable state:
   ```bash
   # Check git working tree is clean
   git status --porcelain | head -5

   # Detect the likely baseline test command
   python3 - <<'PY'
   from pathlib import Path
   if Path('package.json').exists():
       print('Detected package.json; use the project test script if configured')
   elif Path('pytest.ini').exists() or Path('pyproject.toml').exists():
       print('Detected Python project; use pytest if configured')
   elif Path('go.mod').exists():
       print('Detected Go project; use go test ./...')
   else:
       print('No obvious test command detected; ask the user for the baseline command')
   PY
   ```

   Use the detected command, an existing project convention, or a user-provided command to establish the baseline before launch.

   If git working tree is dirty, warn the user:
   > "Working tree has uncommitted changes. It's recommended to commit or stash changes before starting refactoring so each refactor task has a clean baseline. Continue anyway?"

   If no baseline command is detected, warn and ask the user for the correct command or explicit permission to continue without an automated baseline.

   If test baseline fails, warn the user:
   > "Test suite is not passing. Refactoring relies on tests to verify behavior preservation. Fix failing tests before starting the refactor pipeline, or continue at your own risk."

   Wait for user confirmation before proceeding.

5. **Ask execution mode** (first user decision):

   Present the three execution modes from the **Execution Mode** section above as a single standalone `AskUserQuestion` call (exactly 1 question, multiSelect: false). Wait for the user's response before continuing to step 6.

   Each `AskUserQuestion` round is a genuine gate: callers tend to merge interactive rounds and pre-fill answers, which skips real user decisions and produces wrong configs. Therefore: ask execution mode (step 5) and configuration (step 6) as SEPARATE `AskUserQuestion` calls, in order, and do not assemble or show the final command (step 7) until the user has answered both. If you find yourself writing the final command before the user has answered, STOP — you are violating this rule.

6. **Ask configuration options** — a SEPARATE `AskUserQuestion` call from step 5, applies to ALL execution modes (Foreground, Background, AND Manual).

   Use `AskUserQuestion` to present ALL 4 configuration choices (the full 4-question budget goes to config, NOT shared with execution mode):

   **Question 1 — Verbose logging** (multiSelect: false):
   - On (default) — Detailed AI session logs including tool calls and subagent activity
   - Off — Minimal logging

   **Question 2 — Max retries** (multiSelect: false):
   - 3 (default)
   - 1
   - 5

   **Question 3 — Strict behavior check** (multiSelect: false):
   - On (default) — Run full test suite after each refactor task to verify behavior preservation
   - Off — Skip post-task test verification (faster but riskier)

   **Question 4 — Advanced config?** (multiSelect: false):
   - No (default) — Use defaults for failure behavior
   - Yes — Configure stop-on-failure, deploy-after-completion, and reasoning effort options

   Note: Refactor filter defaults to all refactor items. Runtime selects eligible refactors in stable list order after dependencies are completed; planners should order unrelated refactors by user priority before launch. If the user selects "Other" on any option, handle their custom input.

   **If user chose "Yes" to Advanced config**, run the advanced configuration round (a second `AskUserQuestion` round, plus a reasoning-effort follow-up). It applies to a minority of sessions, so the full question set lives in `.claude/command-assets/refactor-pipeline-launcher/references/configuration.md` → **Advanced Configuration Round**.

   Read `.claude/command-assets/refactor-pipeline-launcher/references/configuration.md` for the current environment-variable mapping and advanced environment-variable tables.


7. **Show final command**: After user confirms configuration in step 6, assemble the complete command from execution mode + user-confirmed configuration, and present it to the user.

   **Foreground command:**
   ```bash
   VERBOSE=1 STRICT_BEHAVIOR_CHECK=1 python3 ./.prizmkit/dev-pipeline/cli.py refactor run .prizmkit/plans/refactor-list.json
   ```
   Selected-options example:
   ```bash
   VERBOSE=1 STRICT_BEHAVIOR_CHECK=1 MAX_RETRIES=5 STOP_ON_FAILURE=1 ENABLE_DEPLOY=1 PRIZMKIT_EFFORT=high \
     python3 ./.prizmkit/dev-pipeline/cli.py refactor run .prizmkit/plans/refactor-list.json
   ```

   **Background daemon command:**
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor start .prizmkit/plans/refactor-list.json --env "VERBOSE=1 STRICT_BEHAVIOR_CHECK=1"
   ```
   Selected-options example:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor start .prizmkit/plans/refactor-list.json \
     --env "VERBOSE=1 STRICT_BEHAVIOR_CHECK=1 MAX_RETRIES=5 STOP_ON_FAILURE=1 ENABLE_DEPLOY=1 PRIZMKIT_EFFORT=high"
   ```

   **Manual mode**: Print the assembled command(s) and **stop here**. Do not execute anything. Do not proceed to step 8.
   ```
   # To run in foreground:
   VERBOSE=1 STRICT_BEHAVIOR_CHECK=1 python3 ./.prizmkit/dev-pipeline/cli.py refactor run .prizmkit/plans/refactor-list.json

   # To run in background (detached):
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor start .prizmkit/plans/refactor-list.json --env "VERBOSE=1 STRICT_BEHAVIOR_CHECK=1"

   # To check status:
   python3 ./.prizmkit/dev-pipeline/cli.py refactor status .prizmkit/plans/refactor-list.json
   ```

8. **Confirm and launch** (Foreground and Background only — Manual mode ends at step 7):

   Use a separate `AskUserQuestion` call: "Ready to launch the refactor pipeline with the above command?"
   Options:
   - Launch now (Recommended)
   - Cancel

   After user confirms, execute the command from step 7.

9. **Post-launch** (depends on execution mode):

   **If foreground**: Pipeline runs to completion in the terminal. After it finishes:
   - Summarize results: total refactors, succeeded, failed, skipped
   - If all succeeded: each refactor session has already run `prizmkit-retrospective` internally. Ask user what's next.
   - If some failed: show failed refactor IDs and suggest `python3 ./.prizmkit/dev-pipeline/cli.py reset refactor <R-XXX> --clean --run` for a fresh retry
   - **Browser verification**: Refactor sessions with `browser_interaction` perform supplemental UI verification during execution. After completion, use `python3 ./.prizmkit/dev-pipeline/cli.py refactor status .prizmkit/plans/refactor-list.json` and per-refactor session logs as the source of truth before summarizing browser verification results.

   **If background daemon**:
   1. Verify launch:
      ```bash
      python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor status
      ```
   2. Start log monitoring — Use the Bash tool with `run_in_background: true`:
      ```bash
      python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor logs --follow
      ```
   3. Report to user:
      - Pipeline PID
      - Log file location
      - "You can ask me 'refactor status' or 'show refactor logs' at any time"
      - "Closing this session will NOT stop the pipeline"

---

#### Intent B: Check Status

1. **Check daemon status**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor status
   ```

2. **Show refactor-level progress**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py refactor status .prizmkit/plans/refactor-list.json
   ```

3. **Show recent log activity** (last 20 lines):
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor logs --lines 20
   ```

4. **Summarize** to user: total refactors, completed, in-progress, failed, pending.

---

#### Intent C: Stop Pipeline

1. **Stop the daemon**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor stop
   ```

2. **Verify stopped**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor status 2>/dev/null || true
   ```

3. **Inform user**: "Refactor pipeline stopped. State is preserved -- you can resume later with 'start refactoring' and it will pick up where it left off."

---

#### Intent D: Show Logs

1. **Check if running**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor status 2>/dev/null
   ```

2. **If running** -- Start live tail with Bash tool `run_in_background: true`:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor logs --follow
   ```

3. **If not running** -- Show last 50 lines:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor logs --lines 50
   ```

4. **For per-refactor session logs** (when user asks about a specific refactor):
   ```bash
   # Check refactor status for last session ID
   cat .prizmkit/state/refactor/<REFACTOR_ID>/status.json 2>/dev/null
   # Then tail that refactor's session log
   tail -100 .prizmkit/state/refactor/<REFACTOR_ID>/sessions/<SESSION_ID>/logs/session.log
   ```

---

#### Intent E: Retry Single Refactor

When user says "retry R-001" or "clean retry R-001":

```bash
python3 ./.prizmkit/dev-pipeline/cli.py reset refactor R-001 --clean --run .prizmkit/plans/refactor-list.json
```

Notes:
- `python3 ./.prizmkit/dev-pipeline/cli.py reset refactor <R-XXX> --clean --run .prizmkit/plans/refactor-list.json` performs a full clean (deletes session history and artifacts) before retrying the selected refactor — this gives a fresh start.
- Keep pipeline daemon mode for main run management (`python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor start`, `python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor status`, or `python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor stop`).

---

### Error Handling

Read the error-handling table in `.claude/command-assets/refactor-pipeline-launcher/references/configuration.md` for the full list of errors and recovery actions.

### Integration Notes

- **After refactor-planner**: This is the natural next step. When user finishes refactor planning and has `.prizmkit/plans/refactor-list.json`, suggest launching the refactor pipeline.
- **Session independence**: Only Background daemon mode runs detached. Foreground runs in the current AI CLI session, and Manual mode prints commands without launching.
- **Single instance per family**: Only one refactor pipeline can run at a time. Different pipeline families may coexist because they use separate daemon metadata and state directories.
- **Pipeline coexistence**: Refactor pipeline uses `.prizmkit/state/refactor/` separate from `.prizmkit/state/features/` (features) and `.prizmkit/state/bugfix/` (bugs), so all three pipelines can run simultaneously without conflict.
- **State preservation**: Stopping and restarting the pipeline resumes from where it left off -- completed refactors are not re-run.
- **HANDOFF**: After pipeline completes all refactors, each session has already run `prizmkit-retrospective` internally. Ask user what's next.
