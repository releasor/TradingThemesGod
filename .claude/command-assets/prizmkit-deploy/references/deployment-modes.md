# Deployment Mode Details

Read this file when the user needs a detailed comparison of deployment modes during mode selection. SKILL.md contains the routing logic; this file has the full descriptions.

## Mode A — Direct Upload

1. Local build on the user's machine.
2. SCP built output + `node_modules` + `.env.production` to server.
3. PM2 start → health check → Nginx switch.
4. After success: offer to upgrade to CI/CD.
5. Bypasses: deploy key, git clone on server, server-side build.

Best for: first-time deployment, getting something live fast, low-spec servers.

## Mode B1 — CI/CD Push

1. Generate `.github/workflows/deploy.yml`: checkout → install → build → SCP tarball → SSH restart.
2. Add GitHub Secrets: `SSH_HOST`, `SSH_USER`, `SSH_KEY`, `SSH_PORT`.
3. First deploy triggered by push to configured branch.
4. Server only needs Node.js runtime + PM2 — no git, no build tools needed.
5. GitHub Actions runner handles the heavy lifting.

Best for: low-spec servers, heavy build processes, projects with large dependencies.

## Mode B2 — CI/CD Pull

1. Configure deploy key on server → add to GitHub.
2. Generate `.github/workflows/deploy.yml`: triggers SSH command on server.
3. Server-side deploy script: `git pull` → install → build → PM2 restart → health check.
4. Server needs full build toolchain (Node.js, npm, git).
5. Simpler workflow file, heavier server load.

Best for: simple setup, servers with sufficient CPU/RAM, projects where build is fast.

## Comparison

| Aspect | Push mode | Pull mode |
|------|----------|----------|
| Build location | GitHub Actions runner | Server (local) |
| Server load | Low (runs app only) | High (build + run) |
| Config complexity | Medium (needs SCP transfer) | Low (SSH-triggered script only) |
| Best for | Low-spec servers, heavy builds | Simple setup, capable servers |
| Deploy Key required | No | Yes |
| Artifact transfer | SCP tarball | git pull (incremental) |

## Common ground between all modes

- Same PM2 + Nginx blue/green strategy.
- Same health check and traffic switch procedure.
- Same ops commands (status/logs/restart/rollback).
