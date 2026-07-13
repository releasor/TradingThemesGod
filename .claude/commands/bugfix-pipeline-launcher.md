---
description: "Launch and manage the bugfix pipeline from within an AI CLI session. Start pipeline in background, monitor logs, check status, stop pipeline. Use this skill whenever the user wants to start fixing bugs, run the bugfix pipeline, check bugfix progress, or stop the bugfix pipeline. Trigger on: 'start fixing bugs', 'run bugfix pipeline', 'bugfix status', 'stop bug fix', 'launch bug fix', 'fix progress', 'stop fixing'. (project)"
---

# Bugfix-Pipeline Launcher

Launch the autonomous bug fix pipeline from within an AI CLI conversation. Only Background daemon mode is fully detached and survives AI CLI session closure; Foreground runs in the current session, and Manual prints commands without launching.

### Execution Mode

Three execution modes are available. The user chooses one before configuring other options:

1. **Foreground** (recommended) — `python3 ./.prizmkit/dev-pipeline/cli.py bugfix run`. Visible output, direct error feedback, no orphaned processes.
2. **Background daemon** — `python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix start .prizmkit/plans/bug-fix-list.json`. Runs fully detached, survives AI CLI session closure.
3. **Manual** — Display the assembled command(s) only. Do not execute anything. User runs them on their own.

**Background mode traceability**: Daemon mode metadata and logs are written by the Python runtime (`daemon bugfix start/status/logs`). Do not create any extra launcher-managed audit file.

### When to Use

**Start bugfix pipeline** -- User says:
- "start fixing bugs", "run bugfix pipeline", "launch bug fixes", "fix all bugs"
- "start bug fix", "execute bug list", "begin fixing", "batch fix"
- After bug-planner completes: "fix them", "start fixing"

**Check status** -- User says:
- "bugfix status", "check bug fixes", "how's the fixing going", "bug fix progress"
- "fix progress", "bug fix status", "check fix progress", "how far along are the fixes"

**Stop bugfix pipeline** -- User says:
- "stop bug fix", "stop fixing", "halt bugfix", "pause bug fix", "stop fix pipeline"

**Show logs** -- User says:
- "bugfix logs", "show fix logs", "what's being fixed"
- "view fix logs", "fix logs"

**Do NOT use this skill when:**
- User wants to plan/collect bugs (use `bug-planner` instead)
- User wants to fix a single bug interactively in current session (use `bug-fix-workflow`)
- User wants to launch the feature pipeline (use `feature-pipeline-launcher`)

### Prerequisites

Before any action, validate:

1. **bugfix pipeline exists**: Confirm `.prizmkit/dev-pipeline/cli.py` is present
2. **For start**: `.prizmkit/plans/bug-fix-list.json` must exist in `.prizmkit/plans/` (or user-specified path)
3. **Dependencies**: `python3`, `git`, and the configured AI CLI must be in PATH. Resolve and report the AI CLI from `AI_CLI` env, then `.prizmkit/config.json` `ai_cli`, then fallback to `claude` only when neither is configured. Read `.claude/command-assets/bugfix-pipeline-launcher/references/configuration.md` §Configured AI CLI Prerequisite Check before running the AI CLI check.
4. **Python version**: Requires Python 3.10+ for the unified dev-pipeline runtime
5. **Browser tools** (optional): If any bug has `browser_interaction` field, check the corresponding tool is available. Bugs may specify `tool: "playwright-cli"`, `tool: "opencli"`, or `tool: "auto"` (AI chooses at runtime).

Quick check:
```bash
command -v python3 >/dev/null && command -v git >/dev/null && echo "Core dependencies OK"
# AI CLI check: read `.claude/command-assets/bugfix-pipeline-launcher/references/configuration.md` §Configured AI CLI Prerequisite Check.
# It must print `Configured AI CLI: <name>` and verify that exact executable.
# Optional: browser interaction support (check both tools — bugs may use either)
command -v playwright-cli && echo "playwright-cli OK" || echo "playwright-cli not found (playwright browser verification will be skipped)"
command -v opencli && echo "opencli OK" || echo "opencli not found (opencli browser verification will be skipped)"
```

If `.prizmkit/plans/bug-fix-list.json` is missing, inform user:
> "No .prizmkit/plans/bug-fix-list.json found. Run the `bug-planner` skill first to generate one, or provide a path to your bug fix list."

### Workflow

Detect user intent from their message, then follow the corresponding workflow:

---

#### Intent A: Start Bugfix Pipeline

> **Execution model**: The pipeline processes eligible bugs one at a time. The `dependencies` field is active: dependencies must complete before dependents are selected. Among unrelated eligible bugs, stable list order determines selection.

1. **Check prerequisites**:
   ```bash
   ls .prizmkit/plans/bug-fix-list.json 2>/dev/null && echo "Found" || echo "Missing"
   ```

2. **Check not already running**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix status 2>/dev/null
   ```
   If running, inform user and ask: "Bugfix pipeline is already running. Want to restart it, check status, or view logs?"

3. **Show bug summary** (so user knows what will be fixed):
   ```bash
   python3 -c "
   import json
   with open('.prizmkit/plans/bug-fix-list.json') as f:
       data = json.load(f)
   bugs = data.get('bugs', [])
   severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
   print(f'Total bugs: {len(bugs)}')
   sev_counts = {}
   for b in bugs:
       s = b.get('severity', 'medium')
       sev_counts[s] = sev_counts.get(s, 0) + 1
   print(f'By severity: {dict(sorted(sev_counts.items(), key=lambda x: severity_order.get(x[0], 2)))}')
   print()
   for b in bugs:
       print(f\"  {b['id']}: [{b.get('severity','?').upper()}] {b.get('title', 'untitled')}\")
   "
   ```
   If pipeline state already exists, use the status command instead:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py bugfix status .prizmkit/plans/bug-fix-list.json
   ```

4. **Ask execution mode** (first user decision — SEPARATE `AskUserQuestion` call with exactly 1 question):

   Present the three execution modes from the **Execution Mode** section above (Foreground / Background daemon / Manual), multiSelect: false. Then STOP and wait for the user's response before continuing to step 5.

5. **Ask configuration options** — applies to ALL execution modes (Foreground, Background, AND Manual). This is a SEPARATE `AskUserQuestion` call from step 4.

   RULE: Execution mode (step 4) and configuration (step 5) are two distinct `AskUserQuestion` calls, asked in order, each followed by waiting for the user's answer. Merging them, assuming defaults, or showing the final command before the user has answered both rounds produces a misconfigured pipeline that runs autonomously for a long time — so it MUST NOT happen. If you find yourself writing the final command before the user has answered, STOP.

   The step-5 questions (4 round-1 questions, plus a round 2 if the user picks "Yes" to Advanced config) and their env-var mappings are enumerated in `.claude/command-assets/bugfix-pipeline-launcher/references/configuration.md` under "Interactive Configuration Options". Present round 1 as one `AskUserQuestion` call; run round 2 only if Advanced config = Yes. Then STOP and wait for the user's response before continuing to step 6.
6. **Show final command**: Assemble the complete command from execution mode + confirmed configuration, and present it to the user.

   **Foreground command:**
   ```bash
   VERBOSE=1 python3 ./.prizmkit/dev-pipeline/cli.py bugfix run .prizmkit/plans/bug-fix-list.json
   ```
   Selected-options example:
   ```bash
   VERBOSE=1 MAX_RETRIES=5 STOP_ON_FAILURE=1 ENABLE_DEPLOY=1 PRIZMKIT_EFFORT=high \
     python3 ./.prizmkit/dev-pipeline/cli.py bugfix run .prizmkit/plans/bug-fix-list.json
   ```

   **Background daemon command:**
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix start .prizmkit/plans/bug-fix-list.json --env "VERBOSE=1"
   ```
   Selected-options example:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix start .prizmkit/plans/bug-fix-list.json \
     --env "VERBOSE=1 MAX_RETRIES=5 STOP_ON_FAILURE=1 ENABLE_DEPLOY=1 PRIZMKIT_EFFORT=high"
   ```

   **Manual mode**: Print the assembled command(s) and **stop here**. Do not execute anything. Do not proceed to step 7.
   ```
   # To run in foreground:
   VERBOSE=1 python3 ./.prizmkit/dev-pipeline/cli.py bugfix run .prizmkit/plans/bug-fix-list.json

   # To run in background (detached):
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix start .prizmkit/plans/bug-fix-list.json --env "VERBOSE=1"

   # To check status:
   python3 ./.prizmkit/dev-pipeline/cli.py bugfix status .prizmkit/plans/bug-fix-list.json
   ```

7. **Confirm and launch** (Foreground and Background only — Manual mode ends at step 6):

   Use a separate `AskUserQuestion` call: "Ready to launch the bugfix pipeline with the above command?"
   Options:
   - Launch now (Recommended)
   - Cancel

   After user confirms, execute the command from step 6.

8. **Post-launch** (depends on execution mode):

   **If foreground**: Pipeline runs to completion in the terminal. After it finishes:
   - Summarize results: total bugs, fixed, failed, skipped
   - If all fixed: each bug session has already run `prizmkit-retrospective` internally (structural sync by default; full retrospective when the fix changed interfaces, dependencies, or observable behavior). Ask user what's next.
   - If some failed: show failed bug IDs and suggest `python3 ./.prizmkit/dev-pipeline/cli.py reset bugfix <B-XXX> --clean --run` for a fresh retry
   - **Browser verification**: Bug sessions with `browser_interaction` perform their own verification attempts during execution. After completion, use `python3 ./.prizmkit/dev-pipeline/cli.py bugfix status .prizmkit/plans/bug-fix-list.json` and per-bug session logs as the source of truth before summarizing browser verification results.

   **If background daemon**:
   1. Verify launch:
      ```bash
      python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix status
      ```
   2. Start log monitoring — Use the Bash tool with `run_in_background: true`:
      ```bash
      python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix logs --follow
      ```
   3. Report to user:
      - Pipeline PID
      - Log file location
      - "You can ask me 'bugfix status' or 'show fix logs' at any time"
      - "Closing this session will NOT stop the pipeline"

---

#### Intent B: Check Status

1. **Check daemon status**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix status
   ```

2. **Show bug-level progress**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py bugfix status .prizmkit/plans/bug-fix-list.json
   ```

3. **Show recent log activity** (last 20 lines):
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix logs --lines 20
   ```

4. **Summarize** to user: total bugs, completed, in_progress, failed, pending, needs_info.

---

#### Intent C: Stop Bugfix Pipeline

1. **Stop the daemon**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix stop
   ```

2. **Verify stopped**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix status 2>/dev/null || true
   ```

3. **Inform user**: "Bugfix pipeline stopped. State is preserved -- you can resume later with 'start bug fix' and it will pick up where it left off."

---

#### Intent D: Show Logs

1. **Check if running**:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix status 2>/dev/null
   ```

2. **If running** -- Start live tail with Bash tool `run_in_background: true`:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix logs --follow
   ```

3. **If not running** -- Show last 50 lines:
   ```bash
   python3 ./.prizmkit/dev-pipeline/cli.py daemon bugfix logs --lines 50
   ```

4. **For per-bug session logs** (when user asks about a specific bug):
   ```bash
   # Check bug status for last session ID
   cat .prizmkit/state/bugfix/<BUG_ID>/status.json 2>/dev/null
   # Then tail that bug's session log
   tail -100 .prizmkit/state/bugfix/<BUG_ID>/sessions/<SESSION_ID>/logs/session.log
   ```

---

#### Intent E: Retry Single Bug

When user says "retry B-001":

```bash
python3 ./.prizmkit/dev-pipeline/cli.py reset bugfix B-001 --clean --run .prizmkit/plans/bug-fix-list.json
```

**Note:** `python3 ./.prizmkit/dev-pipeline/cli.py reset bugfix <B-XXX> --clean --run .prizmkit/plans/bug-fix-list.json` performs a full clean (deletes session history and artifacts) before retrying the selected bug — this gives a fresh start.

### Error Handling

Read `.claude/command-assets/bugfix-pipeline-launcher/references/configuration.md` for the full error handling table.

### Integration Notes

- **After bug-planner**: This is the natural next step. When user finishes bug planning and has `.prizmkit/plans/bug-fix-list.json`, suggest launching the bugfix pipeline.
- **Session independence**: Only Background daemon mode runs detached. Foreground runs in the current AI CLI session, and Manual mode prints commands without launching.
- **Single instance per family**: Only one bugfix pipeline can run at a time. Different pipeline families may coexist because they use separate daemon metadata and state directories.
- **Pipeline coexistence**: Bugfix, feature, and refactor pipelines use separate state directories (`.prizmkit/state/bugfix/`, `.prizmkit/state/features/`, `.prizmkit/state/refactor/`), so all three can run simultaneously without conflict.
- **State preservation**: Stopping and restarting the bugfix pipeline resumes from where it left off -- completed bugs are not re-fixed.
- **Bug ordering**: Dependencies are active. Runtime selects eligible bugs in stable list order after dependencies are completed; planners should order unrelated bugs by severity/priority before launch.
- **Background mode traceability**: Daemon mode metadata/logging is runtime-owned; use `daemon bugfix status` and `daemon bugfix logs`.
- **HANDOFF**: After pipeline completes all bugs, summarize results and ask what the user wants next. Individual sessions already run retrospective according to the bug-fix documentation policy.
