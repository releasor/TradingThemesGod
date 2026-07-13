---
description: Recover and resume interrupted PrizmKit workflow or pipeline sessions. Auto-detects feature-workflow, bug-fix-workflow, refactor-workflow, plan lists, pipeline state, git branches, diffs, spec/plan artifacts, review artifacts, and session summaries; then offers recovery script, manual command, interactive resume, clean retry, or start-fresh options. Use when an AI CLI session timed out, crashed, hit token limits, left partial work, or the user says recover, resume, continue where I left off, pick up where it left off, or salvage partial work.
---

# Recovery Workflow

Recover interrupted workflow or pipeline work. This skill is intentionally different from the ordinary feature/bug/refactor workflows: the success criterion is high-quality continuation of interrupted work, not structural consistency with other workflows.

## When to Use

Use this skill when the user says:
- Recover, resume, continue where I left off, or pick up where it left off.
- Session interrupted, timed out, crashed, or hit token limits.
- A pipeline/AI session left partial work and the user wants to salvage or complete it.
- The user does not know whether the interrupted work was feature, bug fix, or refactor work.

Do not use this skill when:
- The user only wants normal pipeline status/logs/stop/retry for a healthy pipeline -> use the matching launcher.
- The user explicitly wants a clean retry of one pipeline item -> use the matching launcher reset guidance.
- The user wants to discard all interrupted work and start fresh -> route to the original workflow after confirmation.

## Recovery Approach Policy

Always present the user with recovery choices after detection. Do not silently choose between script recovery and interactive recovery.

Recommended default:
- Use `python3 ./.prizmkit/dev-pipeline/cli.py recovery run` when the interrupted work appears to be a pipeline or AI-session continuation problem and the user wants autonomous completion.

Interactive recovery remains valid when:
- The user wants control in the current conversation.
- The recovery script is unavailable or fails.
- The interrupted work is a small current-workspace Fast Path task.
- The user wants to inspect before launching another AI session.

Clean retry is different from recovery:
- Use clean retry when the user wants to discard the failed item attempt and rerun from scratch.
- Use recovery when partial work, context, or decisions should be preserved.

## Detection Signals

Inspect multiple signals. Do not depend on a single artifact.

| Signal | Meaning |
|---|---|
| Current branch | `fix/*`, `feat/*`, `refactor/*`, or task-specific branch names can indicate workflow family |
| Git diff / staged / untracked files | Shows partial implementation or planning work |
| `spec.md` / `plan.md` | Current-session Fast Path planning artifacts |
| `.prizmkit/plans/feature-list.json` | Feature pipeline planning artifact |
| `.prizmkit/plans/bug-fix-list.json` | Bugfix pipeline planning artifact |
| `.prizmkit/plans/refactor-list.json` | Refactor pipeline planning artifact |
| `.prizmkit/state/features/` | Feature pipeline state |
| `.prizmkit/state/bugfix/` | Bugfix pipeline state |
| `.prizmkit/state/refactor/` | Refactor pipeline state |
| `session-summary.md` / `context-snapshot.md` | Previous-session context handoff |
| Review artifacts | Evidence that implementation reached review |
| `.prizmkit/bugfix/<BUG_ID>/fix-plan.md` / `fix-report.md` | Optional bug recovery signals when present, not required contract |

Run the detection script for the first pass:

```bash
python3 .claude/command-assets/recovery-workflow/scripts/detect-recovery-state.py
```

For the signature matching and phase inference tables, read `.claude/command-assets/recovery-workflow/references/detection.md`.

## Recovery Flow

### Phase 0: Auto-detect

1. Run the detection script.
2. If the script fails, fall back to manual checks: branch, git status, list files, pipeline state directories, and obvious session artifacts.
3. Identify primary workflow family: bug-fix, feature, refactor, or unknown.
4. Identify whether the work is current-workspace Fast Path, planned pipeline work, active pipeline work, failed pipeline item, or ambiguous.

Checkpoint: recovery target and likely phase are known, or no workflow is detected.

### Phase 1: Diagnose workspace health

Before recommending recovery, inspect and summarize:

- Current branch.
- Whether the working tree has uncommitted changes.
- Whether code/test files changed.
- Which plan lists exist.
- Which pipeline state directories exist.
- Failed, in-progress, pending, and completed items when status commands are available.
- Residual task branches that may correspond to failed/interrupted work.
- Detected artifacts such as `spec.md`, `plan.md`, review reports, session summaries, or optional bugfix reports.

Use concise markdown, not box-drawing banners:

```markdown
## Workspace Diagnosis

- Branch: fix/B-001-login-crash
- Working tree: 3 uncommitted files
- Code changes: 2 source files, 1 test file
- Plan lists: bug-fix-list.json found
- Pipeline state: bugfix has 1 failed item
- Session artifacts: plan.md found, review report not found

## Detected Recovery Target

- Workflow: bug-fix-workflow
- Likely phase: Review
- Reason: fix branch + code changes + no review artifact
- Remaining work: review -> verification -> commit -> merge decision
```

If code changes exist, run or suggest the project test command when it is safe and reasonably detectable. Report failures without hiding them.

### Phase 2: Select recovery target

If multiple failed or interrupted targets exist, use `AskUserQuestion` to choose the first target.

For up to three targets, list each target explicitly plus an all-sequential option. If there are more than three targets, group choices to avoid an overloaded question:

```text
Question: Multiple interrupted targets found. Which should we recover first?
Header: Target
Options:
- Highest-priority failed item — recover the most urgent failed item first
- Choose from summary — show full target list before selecting
- Recover all sequentially — recover each failed/interrupted item in priority order
- Stop here — do not recover now
```

### Phase 3: Select recovery approach

Use `AskUserQuestion` for the approach. Do not proceed without an explicit selection.

```text
Question: Interrupted work was detected. How would you like to recover?
Header: Recovery
Options:
- Run recovery script (Recommended) — execute python3 ./.prizmkit/dev-pipeline/cli.py recovery run to generate a bootstrap prompt and complete remaining phases in a dedicated AI session
- Resume interactively — continue from the inferred phase in this conversation
- Clean retry — discard the failed item attempt and rerun it from scratch through the matching launcher reset flow
- Start fresh — abandon interrupted work and restart the original workflow
```

If the user wants to inspect first, offer:

```bash
python3 ./.prizmkit/dev-pipeline/cli.py recovery detect
python3 ./.prizmkit/dev-pipeline/cli.py recovery run --dry-run
```

### Phase 4: Execute the selected approach

**Run recovery script**:

```bash
python3 ./.prizmkit/dev-pipeline/cli.py recovery run
```

After launch, stop this skill and report how the user can monitor the recovery session.

**Resume interactively**:

1. Read the target workflow SKILL.md.
2. Read available context artifacts in this order:
   - `context-snapshot.md` when present.
   - `session-summary.md` when present.
   - `spec.md`, `plan.md`, review reports, relevant diffs, and list entries.
3. Read relevant `.prizmkit/prizm-docs/` according to the project progressive-loading protocol.
4. Continue from the inferred phase using the target workflow's rules.
5. Preserve existing work where safe; do not restart from scratch unless the user chooses that.

**Clean retry**:

Route to the matching launcher reset flow:

```bash
python3 ./.prizmkit/dev-pipeline/cli.py reset feature <FEATURE_ID> --clean --run .prizmkit/plans/feature-list.json
python3 ./.prizmkit/dev-pipeline/cli.py reset bugfix <BUG_ID> --clean --run .prizmkit/plans/bug-fix-list.json
python3 ./.prizmkit/dev-pipeline/cli.py reset refactor <REFACTOR_ID> --clean --run .prizmkit/plans/refactor-list.json
```

Ask before running a clean retry because it intentionally discards that item's prior session state.

**Start fresh**:

Suggest the original workflow:
- `feature-workflow`
- `bug-fix-workflow`
- `refactor-workflow`

Stop after the user confirms restart.

## Per-Workflow Recovery Notes

### Bug-fix recovery

Bug-fix recovery should not assume `fix-plan.md` or `fix-report.md` exists. Use them when present, but also infer from:

- `fix/*` branch.
- Code/test diff.
- `spec.md` / `plan.md`.
- Review artifacts.
- Commits ahead of the original branch.
- User-provided bug ID or matching bug-fix-list entry.

Typical inference:

| Detected state | Resume from |
|---|---|
| Fix branch, no implementation artifacts | Diagnosis / triage |
| `spec.md` or `plan.md`, no code changes | Fix implementation |
| Code/test changes, no review artifact | Review |
| Review artifact or optional `fix-report.md` | User verification |
| Fix commit exists on branch | Merge decision |

### Feature recovery

Feature recovery is usually list/pipeline driven:

| Detected state | Resume from |
|---|---|
| No feature list and no Fast Path artifacts | Route selection or feature clarification |
| Valid feature list, no pipeline state | `feature-pipeline-launcher` launch |
| Feature list plus pipeline state | `feature-pipeline-launcher` status/retry or recovery script |
| Current-workspace Fast Path artifacts | Continue `/prizmkit-implement`, review, retrospective, or commit based on state |

### Refactor recovery

Refactor recovery mirrors feature recovery but must preserve behavior checks:

| Detected state | Resume from |
|---|---|
| No refactor list and no Fast Path artifacts | Route selection or refactor clarification |
| Valid refactor list, no pipeline state | `refactor-pipeline-launcher` launch |
| Refactor list plus pipeline state | `refactor-pipeline-launcher` status/retry or recovery script |
| Current-workspace Fast Path artifacts | Continue implementation, behavior checks, review, retrospective, or commit based on state |

## Runtime Status Reference

Recovery may inspect pipeline state before choosing recovery, interactive resume, or clean retry. Use the canonical Python runtime forms:

```bash
python3 ./.prizmkit/dev-pipeline/cli.py recovery run
python3 ./.prizmkit/dev-pipeline/cli.py recovery detect
python3 ./.prizmkit/dev-pipeline/cli.py feature status .prizmkit/plans/feature-list.json
python3 ./.prizmkit/dev-pipeline/cli.py bugfix status .prizmkit/plans/bug-fix-list.json
python3 ./.prizmkit/dev-pipeline/cli.py refactor status .prizmkit/plans/refactor-list.json
python3 ./.prizmkit/dev-pipeline/cli.py reset feature <F-XXX> --clean --run .prizmkit/plans/feature-list.json
python3 ./.prizmkit/dev-pipeline/cli.py reset bugfix <B-XXX> --clean --run .prizmkit/plans/bug-fix-list.json
```

Use the matching launcher for healthy status/logs/retry flows. Use clean retry only after explicit user confirmation because it discards the selected item session state.

## Error Handling

| Scenario | Action |
|---|---|
| No workflow signature matches | Report no interrupted workflow detected and suggest original workflow skills |
| Multiple workflows match | Present the evidence and ask which target to recover first |
| Branch and artifacts disagree | Trust git diff/status as ground truth, but report the discrepancy |
| Detection script fails | Fall back to manual detection checks |
| Tests fail during diagnosis | Report failures and ask whether to continue recovery, fix tests, or stop |
| Recovery script unavailable | Offer interactive recovery or clean retry |
| Clean retry requested with uncommitted changes | Warn that retry may discard item session state; ask for explicit confirmation |

## Relationship to Other Skills

| Skill or command | Relationship |
|---|---|
| `feature-workflow` | Recovery target for interrupted feature workflows |
| `bug-fix-workflow` | Recovery target for interrupted bug-fix workflows |
| `refactor-workflow` | Recovery target for interrupted refactor workflows |
| `feature-pipeline-launcher` | Status/logs/retry for healthy or resumable feature pipelines |
| `bugfix-pipeline-launcher` | Status/logs/retry for healthy or resumable bugfix pipelines |
| `refactor-pipeline-launcher` | Status/logs/retry for healthy or resumable refactor pipelines |
| `/prizmkit-code-review` | Used when interactive recovery resumes at review |
| `/prizmkit-committer` | Used when interactive recovery resumes at commit |
| `python3 ./.prizmkit/dev-pipeline/cli.py recovery run` | Dedicated script recovery counterpart |

## Output

- Recovery diagnosis summary.
- User-selected recovery target and approach.
- Either launched recovery script, interactive continuation, clean retry command, or start-fresh handoff.
- Final recovery summary when interactive recovery completes.
