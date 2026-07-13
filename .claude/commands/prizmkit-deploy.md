---
description: "Universal deployment gateway for PrizmKit projects. Discovers project type and deployment target, then routes to SSH Linux automation, cloud platform guidance, Docker guidance, or documented fallback. Also operates existing deployments: status, logs, restart, rollback, health, history, and validate. Use whenever the user asks to deploy, host, go live, release, take live, check deployment status, view logs, restart, rollback, or troubleshoot server operations. If the user says only 'ship it', clarify whether they mean commit or deploy before invoking. (project)"
---

# PrizmKit Deploy — Universal Deployment Gateway

`/prizmkit-deploy` is the deployment and operations entry point. It discovers what is being deployed, where it should run, and which adapter or fallback applies.

Possible outcomes:

1. **Full automation** — SSH Linux server for supported Node.js apps using PM2 + Nginx blue/green.
2. **Guided setup** — cloud platforms or Docker where user CLI/account steps are required.
3. **Documented fallback** — unsupported project/target combinations get deploy documentation and an adapter-gap record.

### When to Use
- User says "deploy", "go live", "take this live", "release", "deploy to Vercel", "deploy to my server"
- User wants deploy status, logs, restart, rollback, health checks, history, or validation
- First-time deployment configuration or existing deployment repair/takeover
- Any deployment, hosting, or server operation question

### When NOT to Use
- User says only "ship it" — clarify commit vs deploy first
- Local development startup — use project dev scripts or `/run`
- Pure CI test failure unrelated to deployment
- User wants application code changes — use `/prizmkit-plan` and `/prizmkit-implement`

## Data Safety Gate

Before executing any command that could irreversibly destroy, overwrite, or modify data, pause and get explicit user confirmation.

Danger signals:

| Category | Examples | Action |
|---|---|---|
| Database reset/loss | `prisma migrate reset`, `DROP TABLE`, `TRUNCATE`, broad `DELETE`/`UPDATE` | Explain data loss and require clear yes/no confirmation |
| File/system overwrite | `rm -rf`, writes under `/etc/`, overwriting existing config without backup | Confirm and back up when applicable |
| Cloud/resource deletion | `terraform destroy`, `kubectl delete`, bucket/resource deletion | Confirm exact resources and impact |
| Production traffic switch | first production deploy, rollback, Nginx upstream change | Confirm target environment and rollback plan |

If a destructive data operation is detected in headless mode, refuse with `DATA_SAFETY_DENIED`; unattended pipelines must not destroy data.

Read `.claude/command-assets/prizmkit-deploy/references/data-safety-examples.md` when concrete examples are needed.

## Discovery

Before deploying, discover project and target.

### Project Detection

Scan build/package files and classify:

| Signal | Classification |
|---|---|
| `package.json` with `next` | Next.js |
| `package.json` with `vite` | Vite frontend |
| generic `package.json` | Node.js |
| `requirements.txt` / `pyproject.toml` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `Dockerfile` | Docker image |
| `docker-compose.yml` | Docker Compose |

Also detect:
- environment variables referenced in source
- ports/listen calls
- database dependencies
- existing deployment config at `.prizmkit/deploy/deploy.config.json`

### Target Detection

Priority:

1. User-specified target: Vercel, own server, Docker, etc.
2. Existing config: `.prizmkit/deploy/deploy.config.json`
3. Project files: `vercel.json`, `netlify.toml`, `fly.toml`, `Dockerfile`, `docker-compose.yml`, GitHub deploy workflow, `app.yaml`, `serverless.yml`
4. Interactive question: ask where the project should be deployed
5. Headless with missing target: exit `NEEDS_INPUT` and write pending questions to `.prizmkit/deploy/pending-input.json`

## Adapter Routing

| Target | Route | Reference |
|---|---|---|
| SSH Linux server + Node.js project | Full automation | `references/ssh-adapter-flow.md` |
| Vercel / Netlify / Fly.io | Guided CLI setup | `references/cloud-platform-deploy.md` |
| Docker / Docker Compose | Guided build/run | `references/docker-deploy.md` |
| Unsupported target or project type | Documented fallback | §Unsupported Fallback |

Compatibility check before SSH: the full SSH adapter currently requires a Node.js project with `package.json`. Non-Node Linux server targets route to Unsupported Fallback with an adapter-gap note.

## Mode Detection

Interactive mode:
- May ask questions and request approvals.
- May deploy to dev, test, or production.
- Production requires explicit confirmation before execution.

Headless mode:
- Never wait for user input.
- May target only dev or test environments.
- Reject production with `ENVIRONMENT_DENIED`.
- If required info is missing, exit `NEEDS_INPUT` and write `.prizmkit/deploy/pending-input.json`.
- Perform only actions already authorized by `deploy.config.json`.

## Command Routing

Determine intent from the first word after `/prizmkit-deploy`:

```text
/prizmkit-deploy                    -> deploy if config exists, otherwise configure
/prizmkit-deploy configure          -> first-run or repair configuration wizard
/prizmkit-deploy deploy             -> full deployment pipeline
/prizmkit-deploy status             -> show runtime and active release status
/prizmkit-deploy logs --app <id>    -> show recent logs
/prizmkit-deploy restart --app <id> -> restart active app process and health check
/prizmkit-deploy rollback --app <id> [--to <releaseId>] -> rollback
/prizmkit-deploy health --app <id>  -> run health checks
/prizmkit-deploy history            -> list deploy history
/prizmkit-deploy validate           -> validate config and target without deploying
```

No-arg behavior:
- If config is missing, start configuration.
- If config exists and validates, show deployment summary and ask for environment.
- If config exists but is incomplete or stale, enter repair flow.

## Artifact Structure

All deployment artifacts live under `.prizmkit/deploy/`:

```text
.prizmkit/deploy/
  deploy.md
  deploy.config.json
  pending-input.json
  deploy-history/
  deploy-scripts/
  secrets.enc.json
  secrets.local.json
```

Read `references/deploy-config-schema.md` when writing or validating config. Read `references/deploy-history-schema.md` when writing history records.

Reference index:
- `references/ssh-adapter-flow.md` — load when routing to SSH Linux full automation.
- `references/deployment-modes.md` — load when the user needs push/pull/direct-upload comparison.
- `references/ssh-bootstrap-flow.md`, `references/firewall-setup.md`, `references/database-setup.md` — load during SSH bootstrap branches.
- `references/direct-upload.md`, `references/ci-cd-workflows.md` — load for strategy-specific setup.
- `references/dns-setup.md`, `references/ssl-setup.md` — load for domain and HTTPS setup.
- `references/ssh-execution-flow.md`, `references/nginx-blue-green.md`, `references/ssh-takeover.md` — load for deploy execution, traffic switching, rollback, or takeover.
- `references/cloud-platform-deploy.md`, `references/docker-deploy.md` — load for non-SSH guided routes.
- `references/live-validation-notes.md` — load when troubleshooting bootstrap or deploy failures.

Never record raw secret values in config, docs, or history. Secret presence metadata is allowed; raw values and unsalted hashes are not.

## SSH Automation Route

When routing to SSH Linux full automation, read `.claude/command-assets/prizmkit-deploy/references/ssh-adapter-flow.md` first. That reference coordinates the detailed SSH sub-procedures:

- deployment mode selection and first-run wizard
- server model and directory layout
- bootstrap and privileged action safety
- direct upload vs CI/CD push vs CI/CD pull
- DNS and SSL guidance
- PM2 + Nginx blue/green execution
- rollback and operations commands
- secrets and multi-app coordination

Key invariants:
- Present privileged bootstrap plans before execution.
- Back up existing config before modification.
- Run `nginx -t` before reload.
- Do not switch traffic until staged health checks pass.
- If failure happens before traffic switch, leave the live version unchanged.
- Preserve failed releases/logs for debugging.

## Cloud and Docker Routes

Cloud platforms:
- Read `references/cloud-platform-deploy.md`.
- Detect required CLI/account steps.
- Generate or update deploy documentation and config.
- Guide the user through interactive login or dashboard steps when needed.

Docker:
- Read `references/docker-deploy.md`.
- Detect Dockerfile/Compose configuration.
- Build/run/validate with explicit environment and volume handling.
- For destructive volume or database operations, apply the Data Safety Gate.

## Unsupported Fallback

When no adapter covers the detected target/project type:

1. Detect what you can: language, framework, build/start commands, env vars, port usage, databases.
2. Generate `.prizmkit/deploy/deploy.md` with prerequisites, env vars, build/start instructions, health checks, and manual steps.
3. Record adapter gap in deploy history: missing adapter, detected project type, target, fallback output.
4. Offer to generate basic CI/CD config when applicable.

## Validation

Before production deploy, validate:

- target connectivity
- required tools
- repository or artifact availability
- port availability
- required environment variables
- process manager/runtime config
- Nginx syntax when applicable
- health check routes
- rollback readiness

Persist validation results in `deploy.config.json` under the relevant `validated` fields.

## Output

Report:
- detected project and target
- selected adapter or fallback
- environment and deploy strategy
- actions performed
- validation/health results
- deploy history record path
- next recommended action
