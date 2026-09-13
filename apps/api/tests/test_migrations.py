from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings


def test_migration_upgrades_empty_database(tmp_path, monkeypatch) -> None:
    database = tmp_path / "migration.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert {
        "articles",
        "admin_sessions",
        "categories",
        "tags",
        "article_tags",
        "projects",
        "project_articles",
        "book_notes",
        "media_assets",
        "search_index",
        "profiles",
        "alembic_version",
        "article_revisions",
        "article_revision_tags",
        "project_revisions",
        "project_revision_articles",
        "book_note_revisions",
        "article_revision_public_references",
        "article_working_references",
        "content_links",
        "assistant_index_tasks",
        "assistant_index_generations",
        "assistant_index_pointers",
        "assistant_chunks",
        "assistant_chunk_fts",
        "assistant_daily_metrics",
        "assistant_index_embedding_budgets",
        "assistant_index_embedding_attempts",
    } <= tables
    assert not any(
        table.startswith("incubator_")
        or table.startswith("article_index_")
        or table in {"article_embeddings", "zvec_generation_requests"}
        for table in tables
    )
    get_settings.cache_clear()


def test_historical_migration_chain_downgrades_and_reupgrades(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cycle.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "20260814_0019")
    engine = create_engine(url)
    tables_after_upgrade = set(inspect(engine).get_table_names())
    assert "incubator_jobs" in tables_after_upgrade
    engine.dispose()
    command.downgrade(config, "20260801_0007")
    engine = create_engine(url)
    tables_after_downgrade = set(inspect(engine).get_table_names())
    assert "incubator_jobs" not in tables_after_downgrade
    assert "articles" in tables_after_downgrade
    engine.dispose()
    command.upgrade(config, "20260814_0019")
    engine = create_engine(url)
    assert "incubator_jobs" in set(inspect(engine).get_table_names())
    engine.dispose()
    get_settings.cache_clear()


def test_retirement_migration_preserves_core_data_and_drops_incubator(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "retirement.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "20260814_0019")

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE profiles SET title = 'Preserved core data' WHERE id = 1"))
        conn.execute(
            text(
                "INSERT INTO incubator_batches "
                "(item_count, file_count, url_count, total_bytes, created_at) "
                "VALUES (1, 1, 0, 12, '2026-08-26 00:00:00')"
            )
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT title FROM profiles WHERE id = 1")) == "Preserved core data"
    assert "article_revisions" in tables
    assert "article_revision_public_references" in tables
    assert "content_links" in tables
    assert "incubator_batches" not in tables
    assert "article_index_statuses" not in tables
    engine.dispose()
    get_settings.cache_clear()


def test_assistant_index_migration_round_trips_without_qdrant(tmp_path, monkeypatch) -> None:
    database = tmp_path / "assistant-index.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()

    def forbid_qdrant(*_args, **_kwargs):
        raise AssertionError("assistant index migration must not connect to Qdrant")

    monkeypatch.setattr("qdrant_client.QdrantClient.__init__", forbid_qdrant)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert "assistant_index_tasks" in tables
    assert "assistant_chunks" in tables
    assert "assistant_chunk_fts" in tables
    with engine.connect() as conn:
        pointer = conn.execute(
            text(
                "SELECT id, active_generation_id, previous_generation_id "
                "FROM assistant_index_pointers"
            )
        ).one()
        search_count = conn.scalar(text("SELECT COUNT(*) FROM search_index"))
        article_count = conn.scalar(text("SELECT COUNT(*) FROM articles"))
    assert pointer.id == 1
    assert pointer.active_generation_id is None
    assert search_count == 0
    assert article_count == 0
    engine.dispose()

    command.downgrade(config, "20260826_0020")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert "assistant_index_tasks" not in tables
    assert "assistant_chunks" not in tables
    assert "assistant_chunk_fts" not in tables
    assert "articles" in tables
    assert "search_index" in tables
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(url)
    assert "assistant_chunk_fts" in set(inspect(engine).get_table_names())
    engine.dispose()
    get_settings.cache_clear()


def test_retirement_migration_requires_archive_for_downgrade(tmp_path, monkeypatch) -> None:
    database = tmp_path / "irreversible.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")

    with pytest.raises(RuntimeError, match="intentionally irreversible"):
        command.downgrade(config, "20260814_0019")
    get_settings.cache_clear()


def test_migration_seeds_default_profile_row(tmp_path, monkeypatch) -> None:
    database = tmp_path / "seed.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT name, title, bio, skills_json, avatar_url, city, city_visible, "
                "github_url, website_url, email, email_visible, resume_url, version "
                "FROM profiles WHERE id = 1"
            )
        ).one()
    engine.dispose()
    get_settings.cache_clear()

    assert row.name == "Gavin"
    assert row.title == "后端工程师 / AI 应用开发者"
    assert row.bio == "这里记录工程实践、问题排查与项目复盘，只留下持续校准过的技术笔记。"
    assert row.skills_json == "[]"
    assert row.avatar_url is None
    assert row.city is None
    assert not row.city_visible
    assert row.github_url is None
    assert row.website_url is None
    assert row.email is None
    assert not row.email_visible
    assert row.resume_url is None
    assert row.version == 1


def test_about_page_migration_seeds_published_snapshot(tmp_path, monkeypatch) -> None:
    database = tmp_path / "about-page.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "20260829_0023")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE profiles SET bio = 'migration-copied-statement' WHERE id = 1")
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert {"about_pages", "about_page_revisions"} <= tables
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT p.version, p.status, p.current_revision_id, r.revision_number, "
                "r.content_json, p.published_at FROM about_pages p "
                "JOIN about_page_revisions r ON r.id = p.current_revision_id "
                "WHERE p.id = 1"
            )
        ).one()
    engine.dispose()
    get_settings.cache_clear()

    assert row.version == 1
    assert row.status == "published"
    assert row.revision_number == 1
    assert row.published_at is not None
    assert "migration-copied-statement" in row.content_json


def test_migration_creates_unique_baseline_revisions_for_published_articles(
    tmp_path,
    monkeypatch,
) -> None:
    database = tmp_path / "baseline.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "20260803_0008")

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO categories (name, slug, description, created_at, updated_at) "
                "VALUES ('Archive', 'archive', '', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO tags (name, slug, description, created_at, updated_at) "
                "VALUES ('Retro', 'retro', '', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
        )
        for index, (status, published_at) in enumerate(
            [
                ("published", "2026-02-01 00:00:00"),
                ("published", "2026-02-02 00:00:00"),
                ("draft", None),
            ]
        ):
            conn.execute(
                text(
                    "INSERT INTO articles (title, slug, summary, content, status, version, "
                    "published_at, created_at, updated_at, category_id) "
                    "VALUES (:title, :slug, '', '# body', :status, 1, :published_at, "
                    "'2026-01-01 00:00:00', '2026-01-01 00:00:00', "
                    "CASE WHEN :status = 'published' THEN 1 ELSE NULL END)"
                ),
                {
                    "title": f"Article {index}",
                    "slug": f"baseline-{index}",
                    "status": status,
                    "published_at": published_at,
                },
            )
        conn.execute(
            text(
                "INSERT INTO article_tags (article_id, tag_id) "
                "SELECT id, 1 FROM articles WHERE slug = 'baseline-0'"
            )
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT a.slug, a.current_revision_id, r.revision_number, r.source, "
                "r.category_slug "
                "FROM articles a LEFT JOIN article_revisions r "
                "ON r.id = a.current_revision_id ORDER BY a.slug"
            )
        ).all()
    engine.dispose()
    get_settings.cache_clear()

    by_slug = {row[0]: row for row in rows}
    assert by_slug["baseline-0"][1] is not None
    assert by_slug["baseline-0"][2] == 1
    assert by_slug["baseline-0"][3] == "editor"
    assert by_slug["baseline-0"][4] == "archive"
    assert by_slug["baseline-1"][1] is not None
    assert by_slug["baseline-1"][2] == 1
    assert by_slug["baseline-2"][1] is None
    assert by_slug["baseline-2"][2] is None

    with engine.connect() as conn:
        tag_snapshot = conn.execute(
            text(
                "SELECT t.name FROM article_revision_tags t "
                "JOIN article_revisions r ON r.id = t.revision_id "
                "WHERE r.slug = 'baseline-0'"
            )
        ).all()
    assert [row[0] for row in tag_snapshot] == ["Retro"]
    engine.dispose()


def test_project_and_book_snapshot_migration_preserves_revisions_across_cycle(
    tmp_path,
    monkeypatch,
) -> None:
    database = tmp_path / "publishing-snapshot-cycle.db"
    url = "sqlite:///" + database.as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "20260809_0014")

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO articles(title, slug, summary, content, status, version, "
                "published_at, created_at, updated_at) VALUES "
                "('Published article', 'published-article', '', '# article', 'published', 1, "
                "'2026-08-01 00:00:00', '2026-08-01 00:00:00', '2026-08-01 00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO projects(title, slug, summary, content, status, version, "
                "published_at, created_at, updated_at) VALUES "
                "('Published project', 'published-project', 'project snapshot', '# project', "
                "'published', 3, '2026-08-02 00:00:00', '2026-08-01 00:00:00', "
                "'2026-08-02 00:00:00'), "
                "('Draft project', 'draft-project', '', '', 'draft', 1, NULL, "
                "'2026-08-01 00:00:00', '2026-08-01 00:00:00')"
            )
        )
        conn.execute(text("INSERT INTO project_articles(project_id, article_id) VALUES (1, 1)"))
        conn.execute(
            text(
                "INSERT INTO book_notes(book_title, author, slug, reading_status, summary, "
                "content, status, version, published_at, created_at, updated_at) VALUES "
                "('Published book', 'Author', 'published-book', 'completed', 'book snapshot', "
                "'# book', 'published', 4, '2026-08-03 00:00:00', "
                "'2026-08-01 00:00:00', '2026-08-03 00:00:00'), "
                "('Draft book', 'Author', 'draft-book', 'planned', '', '', 'draft', 1, NULL, "
                "'2026-08-01 00:00:00', '2026-08-01 00:00:00')"
            )
        )
    engine.dispose()

    command.upgrade(config, "20260814_0019")
    engine = create_engine(url)
    with engine.connect() as conn:
        projects = conn.execute(
            text(
                "SELECT p.slug, p.current_revision_id, r.revision_number, r.summary "
                "FROM projects p LEFT JOIN project_revisions r "
                "ON r.id = p.current_revision_id ORDER BY p.slug"
            )
        ).all()
        books = conn.execute(
            text(
                "SELECT b.slug, b.current_revision_id, r.revision_number, r.summary "
                "FROM book_notes b LEFT JOIN book_note_revisions r "
                "ON r.id = b.current_revision_id ORDER BY b.slug"
            )
        ).all()
        assert conn.scalar(text("SELECT COUNT(*) FROM project_revision_articles")) == 1
    engine.dispose()

    by_project = {row.slug: row for row in projects}
    by_book = {row.slug: row for row in books}
    assert by_project["published-project"].current_revision_id is not None
    assert by_project["published-project"].revision_number == 1
    assert by_project["published-project"].summary == "project snapshot"
    assert by_project["draft-project"].current_revision_id is None
    assert by_book["published-book"].current_revision_id is not None
    assert by_book["published-book"].revision_number == 1
    assert by_book["published-book"].summary == "book snapshot"
    assert by_book["draft-book"].current_revision_id is None

    command.downgrade(config, "20260809_0014")
    engine = create_engine(url)
    inspector = inspect(engine)
    assert "project_revisions" not in inspector.get_table_names()
    assert "book_note_revisions" not in inspector.get_table_names()
    assert "current_revision_id" not in {
        column["name"] for column in inspector.get_columns("projects")
    }
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT COUNT(*) FROM _backup_project_revisions")) == 1
        assert conn.scalar(text("SELECT COUNT(*) FROM _backup_project_revision_articles")) == 1
        assert conn.scalar(text("SELECT COUNT(*) FROM _backup_book_note_revisions")) == 1
    engine.dispose()

    command.upgrade(config, "20260814_0019")
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT COUNT(*) FROM project_revisions")) == 1
        assert conn.scalar(text("SELECT COUNT(*) FROM project_revision_articles")) == 1
        assert conn.scalar(text("SELECT COUNT(*) FROM book_note_revisions")) == 1
        assert (
            conn.scalar(
                text("SELECT current_revision_id FROM projects WHERE slug = 'published-project'")
            )
            is not None
        )
        assert (
            conn.scalar(
                text("SELECT current_revision_id FROM book_notes WHERE slug = 'published-book'")
            )
            is not None
        )
    assert "_backup_project_revisions" not in inspect(engine).get_table_names()
    engine.dispose()
    get_settings.cache_clear()
