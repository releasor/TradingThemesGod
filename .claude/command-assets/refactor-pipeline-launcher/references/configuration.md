# Configuration Reference — Refactor Pipeline Launcher

Environment variable mappings for the refactor launcher.

## Configured AI CLI Prerequisite Check

Read this section during launcher prerequisite validation before reporting AI CLI availability.

Runtime AI CLI selection is config-driven. Resolve the executable name in this order:
1. `AI_CLI` environment variable when set.
2. `.prizmkit/config.json` `ai_cli` when present.
3. `claude` fallback only when neither is configured.

Run this quick check from the project root:
```bash
command -v python3 >/dev/null && command -v git >/dev/null || { echo "python3 or git missing"; exit 1; }
AI_CLI="$(
  python3 - <<'PY'
import json, os, shlex
from pathlib import Path
cli = os.environ.get("AI_CLI", "").strip()
if not cli:
    config_path = Path(".prizmkit/config.json")
    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            cli = str(data.get("ai_cli") or "").strip()
        except (OSError, json.JSONDecodeError):
            cli = ""
cli = cli or "claude"
try:
    print(shlex.split(cli)[0])
except ValueError:
    print(cli.split()[0] if cli.split() else "claude")
PY
)"
printf 'Configured AI CLI: %s\n' "$AI_CLI"
command -v "$AI_CLI" >/dev/null && printf 'AI CLI OK: %s\n' "$(command -v "$AI_CLI")" || { printf 'AI CLI not found: %s\n' "$AI_CLI"; exit 1; }
echo "All dependencies OK"
```

Report the configured executable, for example `Configured AI CLI: claude`. Do not report the first arbitrary PATH match such as `cbc` when project config selects a different AI CLI.

## Environment Variable Mapping

Translating user responses to env vars:

| Config choice | Environment variable |
|-----------|---------------------|
| Verbose: On | `VERBOSE=1` |
| Verbose: Off | `VERBOSE=0` |
| Max retries: N | `MAX_RETRIES=N` |
| Strict behavior: On | `STRICT_BEHAVIOR_CHECK=1` |
| Strict behavior: Off | `STRICT_BEHAVIOR_CHECK=0` |
| Stop on failure: On | `STOP_ON_FAILURE=1` |
| Deploy: Yes | `ENABLE_DEPLOY=1` |
| Effort: value | `PRIZMKIT_EFFORT=<value>` |

## Advanced Environment Variables

Not exposed in interactive menu, pass via `--env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MODEL` | (none) | AI model override (e.g. `claude-opus-4.6`) |
| `AUTO_PUSH` | `0` | Auto-push to remote after successful refactor (`1` to enable) |
| `DEV_BRANCH` | auto-generated | Custom dev branch name (default: `refactor/pipeline-{run_id}`) |
| `HEARTBEAT_INTERVAL` | `30` | Heartbeat log interval in seconds |
| `HEARTBEAT_STALE_THRESHOLD` | `600` | Max seconds without heartbeat before marking stale |

## Error Handling

| Error | Action |
|-------|--------|
| `.prizmkit/plans/refactor-list.json` not found | Tell user to run `refactor-planner` skill first |
| Circular dependencies in refactor list | Fix dependency graph in `.prizmkit/plans/refactor-list.json` before launching |
| Test baseline failing | Fix failing tests before starting refactoring — behavior preservation requires a green baseline |
| `python3` not installed | Install Python 3.10+ and rerun the Python runtime command |
| `git` not installed | Install git; the Python runtime uses git for branch/worktree/status operations |
| Configured AI CLI not in PATH | Install the executable selected by `AI_CLI` or `.prizmkit/config.json` `ai_cli`, or update the config to a CLI available in PATH. |
| Refactor pipeline already running | Show status, ask if user wants to stop and restart |
| PID file stale (process dead) | `python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor start .prizmkit/plans/refactor-list.json` auto-cleans, retry start |
| Launch failed (process died immediately) | Show last 20 lines of log: `python3 ./.prizmkit/dev-pipeline/cli.py daemon refactor logs --lines 20` |
| Refactor stuck/blocked | Use `python3 ./.prizmkit/dev-pipeline/cli.py reset refactor <R-XXX> --clean --run` for a fresh retry |
| All refactors blocked/failed | Show status, suggest recovery: `python3 ./.prizmkit/dev-pipeline/cli.py reset refactor <R-XXX> --clean --run .prizmkit/plans/refactor-list.json` |
| `playwright-cli` not installed | Browser verification skipped for playwright refactors (non-blocking). Suggest: `npm install -g @playwright/cli@latest && playwright-cli install --skills` |
| `opencli` not installed | Browser verification skipped for opencli refactors (non-blocking). Install opencli for Chrome session-based browser verification |
| Deploy session failed | Pipeline completed but deploy session exited non-zero. Check `.prizmkit/state/refactor/deploy/<session_id>/logs/session.log`. Retry manually: `/prizmkit-deploy`. |
| Permission denied running Python CLI | Ensure Python is installed and the command uses `python3 ./.prizmkit/dev-pipeline/cli.py ...` |

## Advanced Configuration Round

Only run this when the user answered "Yes" to the **Advanced config?** question in step 6. It applies to a minority of sessions.

Ask a second round of `AskUserQuestion` with these 2 questions:

**Question 1 — Stop on failure** (multiSelect: false):
- Off (default) — Pipeline continues to next task after failure
- On — Pipeline halts immediately when a task exhausts all retries (`STOP_ON_FAILURE=1`)

**Question 2 — Deploy after completion?** (multiSelect: false):
- No (default) — Skip deployment after pipeline completes
- Yes — Run /prizmkit-deploy automatically after all refactors complete successfully (`ENABLE_DEPLOY=1`). Deployment is blocked if any refactor did not complete successfully (status not 'completed' or manually 'skipped').

Then ask about reasoning effort in a follow-up `AskUserQuestion` call:

**Question — Reasoning effort** (multiSelect: false):
- Default (none) — Use CLI default
- low — Minimize reasoning, fastest output (`PRIZMKIT_EFFORT=low`)
- medium — Moderate reasoning (`PRIZMKIT_EFFORT=medium`)
- high — Thorough reasoning for complex tasks (`PRIZMKIT_EFFORT=high`)
- xhigh — Extensive reasoning (`PRIZMKIT_EFFORT=xhigh`)
- max — Maximum reasoning, Claude Code only (`PRIZMKIT_EFFORT=max`)
