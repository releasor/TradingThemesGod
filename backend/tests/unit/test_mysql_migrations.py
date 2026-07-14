"""MySQL migration and deployment configuration contract tests."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = ROOT / "backend" / "alembic" / "versions"


def _migration_source(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding="utf-8")


def test_migrations_do_not_contain_postgresql_only_ddl():
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in MIGRATIONS.glob("*.py")
    ).lower()

    forbidden = (
        "jsonb",
        "postgresql_",
        "using gin",
        "pg_trgm",
        "create extension",
        "where deleted_at is null",
    )
    for marker in forbidden:
        assert marker not in source


def test_created_tables_use_mysql_innodb_and_utf8mb4():
    for name in ("001_create_themes.py", "002_create_scraper_runs.py"):
        source = _migration_source(name)
        table_count = source.count("op.create_table(")

        assert table_count > 0
        assert source.count('mysql_engine="InnoDB"') == table_count
        assert source.count('mysql_charset="utf8mb4"') == table_count
        assert source.count('mysql_collate="utf8mb4_0900_ai_ci"') == table_count


def test_query_index_migrations_use_mysql_compatible_indexes():
    query_indexes = _migration_source("004_add_query_indexes.py")
    text_indexes = _migration_source("005_add_text_search_indexes.py")

    assert '"idx_theme_deleted_at"' in query_indexes
    assert '"idx_theme_heat_ranking"' in query_indexes
    assert '"idx_event_stock_published_at"' in query_indexes
    assert '"idx_scraper_run_started"' in query_indexes
    assert '"idx_theme_description_prefix"' in text_indexes
    assert "mysql_length=191" in text_indexes


def test_alembic_revision_chain_is_contiguous():
    revision_002 = _migration_source("002_create_scraper_runs.py")
    revision_003 = _migration_source("003_add_filter_indexes.py")
    revision_004 = _migration_source("004_add_query_indexes.py")
    revision_005 = _migration_source("005_add_text_search_indexes.py")

    assert 'revision: str = "002_create_scraper_runs"' in revision_002
    assert 'down_revision: Union[str, None] = "002_create_scraper_runs"' in revision_003
    assert 'down_revision: Union[str, None] = "003_add_filter_indexes"' in revision_004
    assert 'down_revision: Union[str, None] = "004_add_query_indexes"' in revision_005


def test_environment_examples_use_mysql_defaults():
    root_env = (ROOT / ".env.example").read_text(encoding="utf-8")
    backend_env = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
    combined = f"{root_env}\n{backend_env}"

    assert "MYSQL_ROOT_PASSWORD=" in root_env
    assert "MYSQL_DATABASE=trading_themes" in root_env
    assert "DB_PORT=3306" in combined
    assert "DB_USER=root" in backend_env
    assert "POSTGRES_" not in combined
    assert "DB_PORT=5432" not in combined


def test_application_metadata_does_not_advertise_postgresql():
    main_source = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")

    assert "PostgreSQL" not in main_source
    assert "MySQL" in main_source


def test_compose_and_makefile_use_mysql():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "image: mysql:8.0" in compose
    assert "mysqladmin ping" in compose
    assert "mysql_data:" in compose
    assert "context: ./frontend" in compose
    assert 'CORS_ORIGINS: \'${CORS_ORIGINS:-["http://localhost"]}\'' in compose
    assert "mysql -u" in makefile
    assert "postgres" not in compose.lower()
    assert "psql" not in makefile.lower()
