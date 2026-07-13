# Database Setup

Read this file when Discovery detected a database driver and the user wants AI-assisted database installation on the server.

## Entry condition

During Discovery Step 1 (Project Detection), database drivers were already scanned. If a driver was detected, ask after bootstrap tools are installed:

> "Detected the project uses <PostgreSQL/MySQL/Redis>. Want me to install and configure it on the server?"
> - **Yes** → proceed with database installation
> - **No** → skip, record in deploy.md with note "database must be configured by user"

## Secrets file safety

Before writing `.prizmkit/deploy/secrets.local.json`:

1. Verify `.gitignore` or an equivalent ignore rule covers `.prizmkit/deploy/secrets.local.json` and any `.prizmkit/deploy/*.local.json` pattern used by the project.
2. If the ignore rule is missing, pause and add or request the ignore rule before writing secrets.
3. Set the secrets file permissions to current-user read/write only, for example `chmod 600 .prizmkit/deploy/secrets.local.json` on POSIX systems.
4. Record only presence metadata in deploy config, docs, reports, and history. Never copy raw passwords, connection strings, passphrases, decryption keys, unsalted hashes, or full env var values into committed files.

```
apt-get install -y postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE DATABASE <project>;"
sudo -u postgres psql -c "CREATE USER <project> WITH PASSWORD '<random-password>';"
sudo -u postgres psql -c "GRANT ALL ON DATABASE <project> TO <project>;"
```

- Generate a secure random password (32 chars, alphanumeric + symbols).
- Write the connection string to `.prizmkit/deploy/secrets.local.json`: `DATABASE_URL=postgresql://<project>:<password>@localhost:5432/<project>`.
- Set `.prizmkit/deploy/secrets.local.json` permissions to current-user read/write only after writing.
- In deploy.md, write: "PostgreSQL installed, connection info recorded in `.prizmkit/deploy/secrets.local.json` (gitignored; raw value not committed)".

## MySQL setup (future)

Similar flow. Not implemented in first version — if project uses MySQL, direct user to documentation fallback.

## Redis setup

```
apt-get install -y redis-server
redis-cli CONFIG SET requirepass "<random-password>"
redis-cli CONFIG REWRITE
```

- Bind to localhost only (modify `/etc/redis/redis.conf` if needed).
- Write `REDIS_URL=redis://:<password>@localhost:6379` to `.prizmkit/deploy/secrets.local.json`.
- Set `.prizmkit/deploy/secrets.local.json` permissions to current-user read/write only after writing.

## Security notes

- Never write database passwords to deploy.md, because deploy.md may be committed to git and passwords would leak.
- Passwords stored in `.prizmkit/deploy/secrets.local.json` only after verifying the file is ignored by git and locked down to current-user read/write permissions.
- Default: database binds to localhost, no external access, because most indie projects only need local connections.
- Record a `"database-setup"` event in deploy history (presence metadata only, no passwords).
