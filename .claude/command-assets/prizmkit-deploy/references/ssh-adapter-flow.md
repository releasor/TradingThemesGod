# SSH Adapter Flow

Read this file when Discovery routes `/prizmkit-deploy` to SSH Linux full automation.

The SSH adapter supports Node.js projects using PM2 + Nginx blue/green deployment.

## 1. Deployment Mode Selection

Before entering the configuration wizard, ask how the user wants to deploy:

1. **Direct Upload** — build locally, transfer artifacts to the server, start with PM2. Best for first deployment and low-spec servers.
2. **CI/CD Auto-Deploy** — configure GitHub Actions so pushes deploy automatically.

If the user chooses CI/CD, ask which mode:

- **Push mode** — GitHub Actions builds and SCPs artifacts to server. Low server load.
- **Pull mode** — server pulls code and builds itself. Simpler workflow but requires a deploy key and build tools on the server.

Read `references/deployment-modes.md` when the user needs the full comparison.

Config field: `deployStrategy` in `deploy.config.json` is `direct-upload`, `ci-cd-push`, or `ci-cd-pull`. Existing configs without this field default to `ci-cd-pull` for backward compatibility.

## 2. Server Model

A valid SSH target:

- Is reachable over SSH.
- Provides a Linux shell.
- Can install or already has Node.js, npm, PM2, Nginx, and Git.
- Can access the configured repository when using CI/CD Pull mode.

Roles:

- `bootstrapUser`: usually root; installs packages and creates users/directories.
- `runtimeUser`: default `deploy`; app processes run as this user and never as root.

Server-side layout:

```text
/var/www/<project>/
  releases/
    <release-id>/
  shared/
    .env.production
    deploy-metadata.json
  current -> releases/<release-id>
  deploy-logs/
```

`shared/.env.production` must be mode `600` and owned by the runtime user.

## 3. First-Run Configuration Wizard

Flow: deployment mode → collect → validate → confirm → persist.

Collect:

1. SSH server host/port, bootstrap user, runtime user, auth method.
2. Repository access only for `ci-cd-pull`: Git URL, branch, deploy-key or other auth.
3. App configuration: app id, path, package manager, install/build/start commands, blue/green port pair, health checks.
4. Environment variables: scan source for env references, ask for values or storage strategy.
5. Persist `deploy.config.json` and `deploy.md`.

Validate SSH immediately with a harmless connectivity command before collecting deeper config. If SSH fails, stop and fix connectivity first.

## 4. Bootstrap

Before privileged bootstrap, present an action plan listing:

- packages to install
- users/groups to create
- SSH keys to generate
- Nginx config files to create/update
- directories and permissions
- services that may restart

Rules:

- User gives one explicit approval for the bootstrap plan.
- If the plan changes during execution, pause and ask again.
- Bootstrap operations must be idempotent.
- Existing config files must be backed up before modification.
- Failed bootstrap stops before deployment and provides recovery instructions.

Read `references/ssh-bootstrap-flow.md` for the detailed bootstrap procedure. It routes to `references/firewall-setup.md` and `references/database-setup.md` when those branches are selected.

## 5. Strategy-Specific Setup

Direct upload:
- Build locally and transfer artifacts.
- No Git operation is required on the server.
- Read `references/direct-upload.md`.

CI/CD push or pull:
- Generate `.github/workflows/deploy.yml` from `references/ci-cd-workflows.md`.
- Verify the first push to the configured branch will trigger deployment.
- Pull mode requires a deploy key on the server; show the public key and wait for the user to add it to GitHub Deploy Keys before verifying clone access.

After a successful direct-upload deployment, offer CI/CD setup so future `git push` can deploy automatically.

## 6. DNS and SSL

Before SSL, ask whether the user has a domain for the project.

- If no domain, skip DNS + SSL and note it in `deploy.md`.
- If a domain exists, check DNS before SSL.
- Read `references/dns-setup.md` for DNS instructions.
- Read `references/ssl-setup.md` for Let's Encrypt / certificate guidance.

Always verify certificate renewal when Let's Encrypt is configured.

## 7. Deployment Execution

Read `references/ssh-execution-flow.md` for the full pipeline.

Core sequence:

1. Pre-flight and prepare release.
2. Fetch/build or receive artifact.
3. Stage new process on inactive blue/green port.
4. Health-check inactive port.
5. Switch Nginx upstream only after staged health checks pass.
6. Verify public endpoint.
7. Stop old process, cleanup old releases, record history.

Failure rules:

- If any step before traffic switch fails, stop and leave the live version unchanged.
- If a public health check fails after traffic switch, rollback immediately.
- Do not delete failed release logs; preserve them for debugging.

## 8. Blue/Green PM2 + Nginx Invariants

- Default ports: blue `3101`, green `3102`.
- Active color is persisted in `shared/deploy-metadata.json`.
- PM2 process name: `<project>-<app>-<color>`.
- Nginx managed blocks include `# PrizmKit Managed: <project> — DO NOT EDIT MANUALLY`.
- First creation or modification of non-PrizmKit Nginx config requires user confirmation.
- Always run `nginx -t` before reload.

Read `references/nginx-blue-green.md` for config templates and traffic switch details.

## 9. Rollback

Rollback can be automatic or manual.

Manual command:

```text
/prizmkit-deploy rollback --app <id> [--to <releaseId>]
```

Steps:

1. Identify target release.
2. Verify build artifacts exist.
3. Start PM2 on the target release/port.
4. Update Nginx upstream.
5. Run `nginx -t` and reload.
6. Run health checks.
7. Write rollback event.

If no previous release exists, state clearly that rollback is not possible.

## 10. Operations Commands

- `status`: PM2 list, active release, active color/port, last deploy.
- `logs --app <id>`: recent PM2 logs for active process.
- `restart --app <id>`: restart active PM2 process and run health checks.
- `health --app <id>`: run configured health checks.
- `history`: list deploy history events chronologically.

Run app commands as `runtimeUser`.

## 11. Secrets Management

Supported storage modes:

- `ask-every-time`
- `encrypted-local`
- `plaintext-local`
- `user-managed-on-server-only`

Rules:

- `plaintext-local` must be gitignored; stop if tracked by git.
- Server runtime secrets live in `shared/.env.production` with mode `600`.
- Deploy history records secret presence metadata only.
- Never record raw secret values, passphrases, decryption keys, or unsalted hashes.

## 12. Existing Deployment Takeover

When the target server already has deployment assets, read `references/ssh-takeover.md`.

Record takeover decisions and validation results in config and history.

Before modifying non-PrizmKit-managed Nginx config, ask for confirmation.

## 13. Multi-App Coordination

An all-app deploy creates one release group.

Rules:

- Pre-traffic phases must complete for all selected apps before any app switches traffic.
- If any app fails before traffic switch, no app switches traffic.
- If any app fails after traffic switch, default to group rollback.
- Single-app deploys do not affect unrelated apps.

## 14. History and Validation

Write a deploy-history record for every deploy, rollback, takeover, validation, user-abort, failed deploy, or adapter gap.

Read:

- `references/deploy-history-schema.md`
- `references/deploy-config-schema.md`
- `references/live-validation-notes.md` when troubleshooting bootstrap or deploy failures

Validation is mandatory before production deploy.
