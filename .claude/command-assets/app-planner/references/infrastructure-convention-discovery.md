# Infrastructure Convention Discovery

Detailed Q&A flows for database, deployment, and cloud services conventions during app planning.

## Infrastructure Section Check

Check `AGENTS.md` / `CLAUDE.md` / `CODEBUDDY.md` for `### Infrastructure` section:

- If `### Infrastructure` section does not exist → this project was not initialized with prizmkit-init's Phase 4.6. Treat as if both database and deployment are undecided — run full inquiry below.
- If `<!-- infrastructure: deferred -->` → user explicitly skipped at init time. Ask: "During project init you deferred infrastructure decisions. Would you like to configure them now?" (options: "Yes — configure now (Recommended)", "Skip — decide later")
- If `<!-- database: deferred -->` → only database was deferred, run database inquiry only
- If `<!-- deployment: deferred -->` or deployment section is missing → run deployment inquiry only
- If both sections exist with real values → read existing config, present as "Already decided", ask: "Anything to change?" If no → skip to next phase.

## Database Convention Deep Inquiry

AI-driven, context-aware — select from pool based on project. AI analyzes the detected database type, ORM, and tech stack, then selects relevant questions from this pool. Do NOT ask all questions — only those that matter for THIS project:

1. **Table naming convention**: snake_case / camelCase / PascalCase; prefix convention (e.g., `t_`, `tbl_`, none). For brownfield: detect from existing migration files or schema and present as "Already decided" with override option.
2. **Field naming convention**: snake_case / camelCase; common fields convention — are `created_at`, `updated_at`, `deleted_at` (soft delete) required on all tables? What about `id` vs `uuid` column naming?
3. **Migration conventions**:
   - File storage directory (e.g., `db/migrations/`, `prisma/migrations/`, `alembic/versions/`)
   - Naming rule (timestamp prefix `20240101_create_users`, sequence prefix `001_create_users`, ORM auto-generated)
   - Migration tool (ORM built-in / Flyway / Liquibase / golang-migrate / manual SQL)
   - For brownfield: detect existing migration directory and naming pattern, present as "Already decided"
4. **Primary key strategy**: Auto-increment integer / UUID v4 / ULID / Snowflake ID / Other
5. **Index naming convention**: e.g., `idx_{table}_{column}`, `ix_{table}_{column}`, or ORM default
6. **Environment separation**: dev/test/prod database separation strategy; connection config management (env vars / config files / secret manager)

Use `AskUserQuestion` for each batch (up to 4 questions per call). For brownfield projects, show detected patterns as recommended options. Each question MUST include a "Skip — decide later" option.

## Deployment Configuration Deep Inquiry

AI-driven, context-aware. Read the existing `### Infrastructure` → `#### Deployment` section for the deployment target, then ask relevant follow-up questions:

1. **Deployment target refinement**:
   - Own server: SSH access method (key-based / password), OS (Ubuntu / CentOS / other), Docker installed?
   - SaaS platform: specific platform confirmation, existing account and project? Already deployed before?
   - Container: orchestration method (Docker Compose / K8s / ECS / Cloud Run)
2. **Existing infrastructure**:
   - Remote machine availability — IP/domain? Existing server configuration?
   - Existing CI/CD pipeline — GitHub Actions / GitLab CI / Jenkins / other? Already configured?
   - Domain name and SSL — already owned? DNS provider? SSL management (Let's Encrypt / platform-managed / other)?
3. **AI-assisted deployment**:
   - Whether AI should help execute deploy commands (via SaaS CLI like `vercel deploy`, `fly deploy`, `railway up`, `docker push`, or SSH remote commands)
   - If yes: collect necessary info — API token storage method (env var name, e.g., `VERCEL_TOKEN`), project name/ID on the platform, target environment (production / staging)
   - Explicitly inform: "AI will show each command and wait for your confirmation before executing"
4. **Environment variable management**: production env var strategy (SaaS platform dashboard / `.env.production` committed to repo / secret manager like AWS Secrets Manager, Vault / CI/CD secrets)

Use `AskUserQuestion` for each batch. Each question MUST include a "Skip — decide later" option.

## Cloud Services Deep Inquiry

Two-round AskUserQuestion.

*Round 1 — Cloud Vendors* (multi-select via `AskUserQuestion`):
- "Which cloud vendors will this project integrate with?"
- Options: `AWS`, `Aliyun`, `Tencent Cloud`, `Cloudflare`, `Vercel`, `Other` (free text), `None — skip`
- If `None — skip`, write `<!-- cloud-services: none -->` to the `#### Cloud Services` subsection and exit this inquiry.

*Round 2 — Service Types* (multi-select, only if Round 1 returned any vendor):
- "Which types of cloud services will you use?"
- Options: `Object Storage (COS/S3/OSS)`, `CDN`, `Managed Database`, `Functions/Serverless`, `Auth (OAuth/JWT/IDaaS)`, `Domain & DNS`, `Email`, `SMS`, `Payment`, `AI API (OpenAI/Anthropic/...)`, `Other`
- The list is multi-select. Skip the question entirely if user picks "None" in Round 1.

*After both rounds, write to `#### Cloud Services`*:
- For each chosen (vendor x service) pair, append a row to the subsection
- **Do NOT** prompt for env var names, credentials, region, or SDK details — those belong to `prizmkit-deploy`'s scope, not planning
- If the user is unsure of the mapping, store the vendors and service types separately; deploy skill can refine later

## Output Format

After infrastructure inquiry, update the `### Infrastructure` section in the project instruction file:

```markdown
### Infrastructure

#### Database
- **Type**: [database type]
- **ORM**: [ORM name]
- **Table naming**: [convention, e.g., snake_case, no prefix]
- **Field naming**: [convention]; common fields: [list]
- **Primary key**: [strategy]
- **Migration directory**: [path]
- **Migration naming**: [rule]
- **Index naming**: [convention]
- **Environment separation**: [strategy]

#### Deployment
- **Target**: [platform/method]
- **AI-assisted deploy**: [yes/no]
- **Domain**: [domain or "not configured"]
- **SSL**: [management method]
- **CI/CD**: [tool or "not configured"]
- **Env var management**: [strategy]

#### Deployment Credentials Reference
- [platform]: [token/auth method description]

#### Cloud Services
- **Vendors**: [comma-separated list, e.g., "AWS, Cloudflare" or "none"]
- **Services**:
  - [vendor]: [service type] — [optional one-line note, e.g., "user-upload images"]
  - [vendor]: [service type]
<!-- If user picked "None" in Round 1, replace this block with: cloud-services: none -->
```

Items still marked "Skip — decide later" remain as `<!-- [topic]: deferred -->` in the selected project instruction file for `prizmkit-deploy` to pick up later.
