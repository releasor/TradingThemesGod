# SSH: Deployment Execution Flow

Pipeline runs in strict order. Each group must complete before the next begins. If any step before traffic switch fails, STOP — do not touch the live version.

## Pre-flight — Change Summary

Show what will be deployed using `git log --oneline <last-deployed-commit>..HEAD`. If first deployment, show last 5 commits. If no new commits, warn "No new code changes. Are you sure you want to redeploy?"

## Group 1 — Pre-flight & Prepare

- Verify SSH, runtime user, tools, deploy key, port availability.
- Generate `releaseId`: `YYYYMMDD-<short-commit-sha>`. Create `releases/<releaseId>`.
- Determine target color: read `activeColor` from `shared/deploy-metadata.json` and use the opposite. If first deploy (no metadata, no `current` symlink), default to blue (port 3101).

## Group 2 — Fetch & Build

- **CI/CD Pull mode** (server-side build): git clone → install → copy `.env.production` before build (NEXT_PUBLIC_* vars are baked at build time) → build. If build fails: STOP.
- **CI/CD Push mode** (runner-side build): extract tarball, skip install/build.
- **Direct-upload mode**: build was already done locally and SCP'd. Skip this group.

## Group 3 — Stage & Health Check

- Start new version on inactive port via PM2: `pm2 start npm --name <project>-<app>-<color> -- run start -- -p <inactivePort>`.
- PM2 process naming: `<project>-<app>-<color>` (e.g., `prizm-ideas-web-green`).
- Wait 3-5 seconds, run health checks against new port. If any fails: STOP, do NOT switch traffic.

## Group 4 — Switch & Verify

- Update Nginx upstream to new port. Run `nginx -t` — abort on failure.
- `systemctl reload nginx`. Update `current` symlink to new release.
- Write `shared/deploy-metadata.json` with new `activeColor`, `activePort`, `lastReleaseId`.
- Run health checks against public endpoint. If any fails: rollback immediately.

## Group 5 — Cleanup & Record

- Stop old PM2 process. Remove oldest releases beyond `releaseRetention` count. `pm2 save`.
- Write deploy-history JSON. Update `deploy.config.json` validation status.

## Post-deploy — Completion Summary

Output a summary (project, URL, version, duration, health status) and append to deploy.md. If `deployStrategy` is `"direct-upload"`, offer CI/CD upgrade (see §SSH: Post-Deploy CI/CD Upgrade).
