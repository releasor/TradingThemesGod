# MySQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the project's PostgreSQL-only persistence layer with MySQL 8.0 while preserving API behavior and supporting local non-Docker startup.

**Architecture:** Keep SQLAlchemy's async session boundary and replace asyncpg with asyncmy. Use portable SQLAlchemy JSON columns plus a small MySQL-specific JSON predicate helper, and rewrite the empty-database Alembic history as MySQL-compatible DDL. Keep runtime, migration, examples, and optional Compose configuration on one MySQL contract.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x async, asyncmy, Alembic, MySQL 8.0, pytest

---

## File Map

- `backend/app/core/config.py`: MySQL defaults and safely rendered SQLAlchemy URL.
- `backend/app/core/database.py`: asyncmy-compatible engine connection arguments.
- `backend/app/models/theme.py`: portable JSON tag column.
- `backend/app/models/industry_chain.py`: portable JSON company column.
- `backend/app/repositories/theme.py`: MySQL JSON array membership and LIKE search.
- `backend/alembic/env.py`: use the async MySQL URL.
- `backend/alembic/versions/001_create_themes.py`: MySQL JSON columns and table options.
- `backend/alembic/versions/002_create_scraper_runs.py`: MySQL table options.
- `backend/alembic/versions/003_add_filter_indexes.py`: unchanged logical indexes, MySQL execution validation.
- `backend/alembic/versions/004_add_query_indexes.py`: replace PostgreSQL-only indexes.
- `backend/alembic/versions/005_add_text_search_indexes.py`: replace pg_trgm with MySQL-compatible name index behavior.
- `backend/tests/unit/test_config.py`: MySQL config and credential encoding tests.
- `backend/tests/unit/test_theme_repository.py`: MySQL JSON predicate compilation tests.
- `backend/tests/unit/test_models.py`: portable JSON type assertions.
- `backend/pyproject.toml`: replace asyncpg with asyncmy.
- `.env.example`, `backend/.env.example`: MySQL environment examples.
- `docker-compose.yml`, `Makefile`: optional MySQL deployment commands.

### Task 1: MySQL Connection Contract

**Files:**
- Modify: `backend/tests/unit/test_config.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/database.py`
- Modify: `backend/alembic/env.py`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Write failing configuration tests**

Assert defaults `DB_PORT == 3306`, `DB_USER == "root"`; assert `str(settings.database_url)` uses `mysql+asyncmy`, `charset=utf8mb4`, and percent-encodes `p@ss:wrd!`; remove the obsolete sync URL test.

- [ ] **Step 2: Verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_config.py -q`

Expected: failures showing PostgreSQL defaults and URL.

- [ ] **Step 3: Implement the connection contract**

Build a `sqlalchemy.engine.URL` with `URL.create("mysql+asyncmy", ..., query={"charset": "utf8mb4"})`; return its hidden-password-disabled string. Update Alembic to use `settings.database_url`. Replace asyncpg with asyncmy and retain only asyncmy's `connect_timeout` engine argument.

- [ ] **Step 4: Install and verify GREEN**

Run: `backend\.venv\Scripts\python.exe -m pip install -e backend[dev]`

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_config.py -q`

Expected: all configuration tests pass.

### Task 2: Portable JSON Models and MySQL Tag Filtering

**Files:**
- Modify: `backend/tests/unit/test_models.py`
- Modify: `backend/tests/unit/test_theme_repository.py`
- Modify: `backend/app/models/theme.py`
- Modify: `backend/app/models/industry_chain.py`
- Modify: `backend/app/repositories/theme.py`

- [ ] **Step 1: Write failing model and query tests**

Assert both JSON columns are instances of SQLAlchemy `JSON`. Compile a tagged list query with `mysql.dialect(paramstyle="named")` and assert it contains `json_contains`, `json_quote`, and bound tag parameters but not PostgreSQL operators.

- [ ] **Step 2: Verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_models.py backend/tests/unit/test_theme_repository.py -q`

Expected: failures because columns are JSONB and the predicate compiles as PostgreSQL containment.

- [ ] **Step 3: Implement portable JSON and predicates**

Import `JSON` from `sqlalchemy`. Add `_tag_contains(tag)` returning `func.json_contains(Theme.tags, func.json_quote(tag)) == 1`, and apply one condition per normalized tag. Replace `ilike` with escaped `like` because the selected MySQL collation is case-insensitive.

- [ ] **Step 4: Verify GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_models.py backend/tests/unit/test_theme_repository.py -q`

Expected: all selected tests pass.

### Task 3: MySQL Alembic History

**Files:**
- Modify: `backend/alembic/versions/001_create_themes.py`
- Modify: `backend/alembic/versions/002_create_scraper_runs.py`
- Modify: `backend/alembic/versions/004_add_query_indexes.py`
- Modify: `backend/alembic/versions/005_add_text_search_indexes.py`
- Create: `backend/tests/unit/test_mysql_migrations.py`

- [ ] **Step 1: Write failing migration tests**

Scan migration modules and assert there are no `JSONB`, `postgresql_`, `GIN`, `pg_trgm`, partial-index `WHERE`, or PostgreSQL extension statements. Assert initial tables specify `mysql_engine="InnoDB"`, `mysql_charset="utf8mb4"`, and `mysql_collate="utf8mb4_0900_ai_ci"`.

- [ ] **Step 2: Verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_mysql_migrations.py -q`

Expected: failures listing PostgreSQL-specific migration constructs.

- [ ] **Step 3: Rewrite migrations**

Use `sa.JSON()` in revision 001 and add MySQL options to every created table. In revision 004, omit the unusable JSON index, create a normal `deleted_at` index, and retain ranking/event/scraper indexes without PostgreSQL options. In revision 005, remove extension/trigram DDL and create only `idx_theme_description_prefix` on a 191-character description prefix using MySQL DDL; retain revision identifiers.

- [ ] **Step 4: Verify GREEN and offline SQL**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_mysql_migrations.py -q`

Run from `backend`: `.\.venv\Scripts\python.exe -m alembic upgrade head --sql`

Expected: tests pass and generated SQL contains MySQL DDL with no PostgreSQL extensions or GIN indexes.

### Task 4: Runtime and Deployment Examples

**Files:**
- Modify: `.env.example`
- Modify: `backend/.env.example`
- Modify: `docker-compose.yml`
- Modify: `Makefile`

- [ ] **Step 1: Add failing static configuration assertions**

Extend `backend/tests/unit/test_mysql_migrations.py` to assert examples contain port 3306 and MySQL variables, Compose uses `mysql:8.0` plus `mysqladmin ping`, and no active PostgreSQL settings remain.

- [ ] **Step 2: Verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_mysql_migrations.py -q`

Expected: failures identifying PostgreSQL examples and Compose service.

- [ ] **Step 3: Update examples and optional Docker path**

Use `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, port 3306, a `mysql_data` volume, and a MySQL shell command. Set backend service credentials from MySQL variables. Correct the frontend Compose build context to `./frontend` while editing the existing broken stanza.

- [ ] **Step 4: Verify GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_mysql_migrations.py -q`

Expected: static configuration tests pass.

### Task 5: Full Regression and Local MySQL Smoke Test

**Files:**
- Create locally, ignored: `backend/.env`
- No committed credential files

- [ ] **Step 1: Run backend regression suite**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: all backend unit/integration tests pass.

- [ ] **Step 2: Run static checks**

Run: `backend\.venv\Scripts\python.exe -m ruff check backend/app backend/tests`

Run: `git diff --check`

Expected: no new lint or whitespace errors.

- [ ] **Step 3: Validate against local MySQL when credentials are available**

Create database with `CREATE DATABASE trading_themes CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;`, configure ignored `backend/.env`, then run from `backend`: `.\.venv\Scripts\python.exe -m alembic upgrade head`.

Expected: Alembic reaches revision `005_add_text_search_indexes` and creates all tables.

- [ ] **Step 4: Start backend and verify health**

Run from `backend`: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

Request: `Invoke-WebRequest http://127.0.0.1:8000/api/v1/health`

Expected: HTTP 200 with healthy application and database status.

- [ ] **Step 5: Review final diff and commit implementation**

Confirm no credentials, generated artifacts, or unrelated user files are staged. Commit only MySQL migration files with message `feat: migrate persistence to MySQL`.
