# Data Safety Examples

Few-shot examples for the Data Safety Gate in `/prizmkit-deploy`. Read this file when a dangerous command pattern is detected — it shows the correct confirmation flow and illustrates what happens when the gate is skipped.

## Example 1: Prisma Force Reset (the incident)

**Context:** User runs `/prizmkit-deploy` to deploy a Next.js + Prisma project. During database setup, the model needs to sync the Prisma schema with the database.

**Wrong — skipping the gate:**
```
Model: I'll sync your database schema now.
$ prisma db push --force-reset --accept-schema
→ All tables dropped. All production data lost. No backup. No confirmation.
```
This happened in production. `--force-reset` drops and recreates every table. `--accept-schema` bypasses Prisma's own confirmation prompt. The model ran both flags without asking the user whether existing data should be preserved.

**Correct — with the safety gate:**
```
Model: I detected that your database needs a schema sync. However, before I do anything:

WARNING: The Prisma schema has changes that could affect existing data.
- New tables to create: 0
- Tables that may be modified: 2 (users, orders)
- If I run `prisma db push --force-reset`, ALL existing data will be DESTROYED.

Options:
1. prisma db push (safe — only adds missing tables/columns, no data loss)
2. prisma db push --force-reset (DANGEROUS — drops and recreates all tables, all data lost)
3. prisma migrate dev (creates a migration file you can review first)

Which approach do you want? (1/2/3)
```

The `--accept-schema` flag should never be used — it suppresses Prisma's own built-in safety prompts that protect the user.

## Example 2: Prisma Migrate Reset

**Context:** User wants to reset their dev database to a clean state for testing.

**Correct detection and confirmation:**
```
Model: `prisma migrate reset` will:
- Drop the entire database
- Recreate it from scratch
- Run all migrations

This is a DESTRUCTIVE operation. All data in the database will be permanently lost.

Are you sure this is a dev/test database with no important data? (yes/no)
```

In production or any environment with real data: refuse immediately. This command should only run in dev with explicit user confirmation.

## Example 3: Raw SQL Data Modification

**Context:** During deployment, the model considers running a SQL command to fix a data issue.

**Correct detection and confirmation:**
```
Model: To fix the duplicate user records, I would run:
```sql
DELETE FROM users WHERE email IS NULL AND created_at < '2025-01-01';
```

This would delete approximately 340 user records. BEFORE I run this:

1. Would you like me to run a SELECT first to show you exactly which rows would be deleted?
2. Do you want to back up the users table before deletion?
3. Confirm: Delete these 340 records? (yes/no)

I will not proceed without your explicit confirmation.
```

## Example 4: Overwriting Production Configuration

**Context:** During bootstrap, the model needs to write an Nginx config, but one already exists at the target path.

**Correct detection and confirmation:**
```
Model: Found existing Nginx config at /etc/nginx/sites-enabled/myapp.

This file is NOT managed by PrizmKit (no `# PrizmKit Managed:` marker).
Overwriting it could break existing site configuration.

Options:
1. Back up the existing config to /etc/nginx/sites-enabled/myapp.bak, then write new config
2. Create new config alongside existing one with a different name
3. Skip — keep the existing config as-is

Which approach? (1/2/3)
```

## Example 5: Confirmation Dialogue Template

When the gate triggers, use this dialogue structure:

```
============================================================
DATA SAFETY GATE — DESTRUCTIVE OPERATION DETECTED
============================================================

Command: <the dangerous command>
Risk level: HIGH / CRITICAL
What will be lost: <plain-language description of affected data>

Current state:
- Database: <name>, <size>, <table count>
- Affected tables: <list>
- Last backup: <date if known, or "unknown — backup recommended">

Recommended safe approach:
<alternative if one exists>

Do you want to proceed with this destructive operation?
Type "yes, I understand the data will be lost" to confirm.
Any other response will abort.
============================================================
```

This format forces the user to read and acknowledge the risk before proceeding.
