"""Study Mode regression fixtures. Never open the user's data/decks.db.

The production modules are imported only after redirecting the database to a
fresh temporary path. Requests exercise the real FastAPI application; no AST
extraction or private copy of app/ is involved.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "browser: optional Chromium component tests (requires Playwright)"
    )


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """(TestClient, production database module) with an isolated SQLite file."""
    if not (APP_DIR / "main.py").is_file():
        pytest.fail("Run these tests from a T2Speech checkout containing app/main.py")

    monkeypatch.syspath_prepend(str(PROJECT_ROOT))
    monkeypatch.chdir(PROJECT_ROOT)  # StaticFiles uses project-relative paths.
    database = importlib.import_module("app.database")
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test_decks.db")

    # Importing app.main initializes SQLite at module import time. The path is
    # patched *first*, so the real user database cannot be initialized here.
    main = importlib.import_module("app.main")
    database.initialize_database()
    with TestClient(main.app, follow_redirects=False) as client:
        yield client, database


@pytest.fixture
def seeded_deck(app_client):
    client, db = app_client
    deck_id = db.create_deck(
        "Deutsch / English", front_language="de-DE", back_language="en-GB"
    )
    for index in range(6):
        db.create_card(deck_id, f"Frage {index}", f"Answer {index}")
    return client, db, deck_id


def start_study(client, deck_id, **flags):
    response = client.post(
        f"/decks/{deck_id}/study/start",
        data={"shuffle": "false", "reverse": "false", **flags},
    )
    assert response.status_code == 303, response.text
    return int(response.headers["location"].rsplit("/", 1)[-1])


def rate(client, session_id, card_id, value="good", revealed="true"):
    return client.post(
        f"/study/{session_id}/rate",
        data={"rating": value, "revealed": revealed, "study_card_id": card_id},
    )
