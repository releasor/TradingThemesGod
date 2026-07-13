---
description: "Pure git commit workflow with safety checks. Stages intended files safely, generates a Conventional Commit message, commits, and verifies the result. Does not modify CHANGELOG.md or .prizmkit/prizm-docs/ by default; run /prizmkit-retrospective first only when the chosen lifecycle path requires docs sync. Trigger on: 'commit', 'submit', 'finish', 'done'. If the user says only 'ship it', clarify whether they mean commit or deploy. (project)"
---

# PrizmKit Committer

### When to Use
- User says "commit", "submit", "finish", "done with this task"
- The current lifecycle path is ready to record changes in git
- Required gates for the chosen path have passed or been explicitly deemed not applicable

### When NOT to Use
- No uncommitted changes exist — nothing to commit
- User says only "ship it" — clarify commit vs deploy first
- Current path still has required unresolved gates, such as failed tests, unresolved review findings, or required retrospective work
- Mid-merge conflict resolution — handle conflicts manually before committing

## Gate Policy

`/prizmkit-committer` does not decide the entire lifecycle. It checks that the gates required by the chosen path are satisfied:

| Path | Commit gate expectation |
|---|---|
| Direct edit | Verify the specific edit as appropriate; no spec/review/retro artifact required. |
| Fast path | Simplified plan tasks complete; run tests or retrospective only if risk/knowledge triggers apply. |
| Full path | Implementation complete; review passed; retrospective completed when docs or durable knowledge changed; tests completed when risk-triggered. |

If a gate is missing but not applicable, state why before committing. If a gate is missing and applicable, stop and run or request the missing gate.

## Workflow

Follow these steps in order. The goal is to commit exactly the intended changes and avoid staging secrets or unrelated files.

### Step 1: Status Check

```bash
git status
```

- If the working tree is clean, inform the user and stop.
- If changes exist, inspect modified, deleted, and untracked files before staging.
- Warn about sensitive-looking files: `.env*`, `*credential*`, `*secret*`, `*.pem`, `*.key`.

### Step 2: Generate Commit Message

Analyze the staged/unstaged diff and task context to generate a concise Conventional Commit message:

```bash
<type>(<scope>): <description>
```

The message should capture what changed and why it matters.

### Step 3: Stage Safely

Never use `git add .` or `git add -A`; broad staging can accidentally include secrets or unrelated files.

1. Stage tracked modified/deleted files with `git add -u` when all tracked changes are intended.
2. Stage new files explicitly by path after confirming they belong in the commit.
3. Verify staged content:

```bash
git diff --cached --stat
```

If staged content differs from the intended change set, unstage and correct it before committing.

### Step 4: Commit

```bash
git commit -m "<type>(<scope>): <description>"
```

Do not update `CHANGELOG.md` by default. Changelog updates belong to release, publish, version-bump workflows, or explicit user requests.

### Step 5: Verification

```bash
git log -1 --stat
git status
```

Confirm the commit was recorded and report whether the working tree is clean or has remaining intentionally uncommitted changes.

### Step 6: Optional Push

Ask user: "Push to remote?"

- Yes: run `git push`
- No: stop after reporting the commit hash

**Headless mode**: If invoked with `--headless`, skip the push question, do not push, and stop after Step 5 verification.

## Examples

```bash
git commit -m "feat(avatar): add user avatar upload with S3 storage"
git commit -m "fix(auth): handle null token in refresh flow"
git commit -m "docs(prizm): clarify lifecycle gate policy"
```
