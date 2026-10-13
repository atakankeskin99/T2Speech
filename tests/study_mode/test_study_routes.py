"""Real FastAPI + SQLite integration tests for Study Mode."""
from __future__ import annotations

import math
from zipfile import is_zipfile

import pytest

from conftest import rate, start_study


def test_empty_deck_cannot_start(app_client):
    client, db = app_client
    deck_id = db.create_deck("Empty")
    assert client.post(f"/decks/{deck_id}/study/start").status_code == 400


def test_session_is_persistent_with_initially_hidden_answer(seeded_deck):
    client, db, deck_id = seeded_deck
    session_id = start_study(client, deck_id)
    state = db.get_study_session_state(session_id)
    assert (state["good_count"], state["total_cards"], state["progress"]) == (0, 6, 0)
    assert state["current_card"][2] == "Frage 0"
    assert db.get_active_study_session(deck_id)[0] == session_id
    assert "id=\"answer\"" in client.get(f"/study/{session_id}").text
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(client.get(f"/study/{session_id}").text, "html.parser")
    assert soup.select_one("#answer").has_attr("hidden")
    with db.get_connection() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM study_session_cards WHERE session_id=?", (session_id,)
        ).fetchone()[0] == 6


def test_again_places_card_after_three_others_without_increment(seeded_deck):
    client, db, deck_id = seeded_deck
    session_id = start_study(client, deck_id)
    first = db.get_study_session_state(session_id)["current_card"][0]
    assert rate(client, session_id, first, "again").status_code == 303
    with db.get_connection() as connection:
        ids = [r[0] for r in connection.execute(
            "SELECT id FROM study_session_cards WHERE session_id=? "
            "AND result='pending' ORDER BY queue_position", (session_id,)
        )]
    assert ids.index(first) == 3
    assert db.get_study_session_state(session_id)["good_count"] == 0
    assert rate(client, session_id, first, "again").status_code == 409


def test_good_increments_unique_progress_and_rejects_invalid_post(seeded_deck):
    client, db, deck_id = seeded_deck
    sid = start_study(client, deck_id)
    first = db.get_study_session_state(sid)["current_card"][0]
    assert rate(client, sid, first, revealed="false").status_code == 400
    assert rate(client, sid, first, "invalid").status_code == 400
    assert rate(client, sid, first).status_code == 303
    assert db.get_study_session_state(sid)["good_count"] == 1
    assert rate(client, sid, first).status_code == 409
    assert db.get_study_session_state(sid)["good_count"] == 1


def test_snapshot_survives_original_card_edit_and_delete(seeded_deck):
    client, db, deck_id = seeded_deck
    sid = start_study(client, deck_id)
    initial = db.get_study_session_state(sid)["current_card"]
    db.update_card(initial[1], "changed prompt", "changed answer")
    assert db.get_study_session_state(sid)["current_card"][2:4] == initial[2:4]
    db.delete_card(initial[1])
    current = db.get_study_session_state(sid)["current_card"]
    assert current[1] is None
    assert current[2:4] == initial[2:4]
    assert "changed prompt" not in client.get(f"/study/{sid}").text


def test_settings_autosave_json_round_trip_and_reveal_remains_hidden(seeded_deck):
    client, db, deck_id = seeded_deck
    sid = start_study(client, deck_id)
    before = db.get_study_session_state(sid)["current_card"]
    result = client.post(f"/study/{sid}/settings", data={
        "auto_speak": "front_back", "auto_reveal": "true",
        "reveal_delay_seconds": "8", "speech_rate": "1.6",
    }, headers={"Accept": "application/json"})
    assert result.status_code == 200 and result.json()["saved"] is True
    assert result.headers.get("cache-control") == "no-store"
    state = db.get_study_session_state(sid)
    assert state["auto_speak"] == "front_back"
    assert state["auto_reveal"] is True or state["auto_reveal"] == 1
    assert state["reveal_delay_seconds"] == 8
    assert state["speech_rate"] == 1.6
    assert state["current_card"] == before
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(client.get(f"/study/{sid}").text, "html.parser")
    assert soup.select_one("#answer").has_attr("hidden")
    assert soup.select_one("#auto-speak option[selected]")["value"] == "front_back"


@pytest.mark.parametrize("invalid", [0, -1, 0.05, 11, math.inf, -math.inf, math.nan])
def test_speech_rate_validation_in_database(seeded_deck, invalid):
    client, db, deck_id = seeded_deck
    sid = start_study(client, deck_id)
    with pytest.raises(ValueError):
        db.update_study_session_settings(
            sid, auto_reveal=False, reveal_delay_seconds=5,
            auto_speak="off", speech_rate=invalid,
        )
    assert db.get_study_session_state(sid)["speech_rate"] == 1.0


@pytest.mark.parametrize("rate_value", ["11", "Infinity", "NaN"])
def test_speech_rate_validation_at_http_boundary(seeded_deck, rate_value):
    client, db, deck_id = seeded_deck
    sid = start_study(client, deck_id)
    response = client.post(f"/study/{sid}/settings", data={
        "speech_rate": rate_value, "auto_speak": "off",
    }, headers={"Accept": "application/json"})
    assert response.status_code in (400, 422)
    assert db.get_study_session_state(sid)["speech_rate"] == 1.0


def test_single_card_again_then_good(app_client):
    client, db = app_client
    deck_id = db.create_deck("Single")
    db.create_card(deck_id, "One", "Uno")
    sid = start_study(client, deck_id)
    first = db.get_study_session_state(sid)["current_card"][0]
    assert rate(client, sid, first, "again").status_code == 303
    assert db.get_study_session_state(sid)["current_card"][0] == first
    assert rate(client, sid, first).status_code == 303
    assert db.get_study_session_state(sid)["status"] == "completed"


def test_replacement_cancel_and_abandoned_redirect(seeded_deck):
    client, db, deck_id = seeded_deck
    old = start_study(client, deck_id)
    first = db.get_study_session_state(old)["current_card"][0]
    assert rate(client, old, first).status_code == 303
    response = client.post(f"/decks/{deck_id}/study/start", data={
        "shuffle": "true", "reverse": "true",
    })
    assert response.status_code == 200 and "Replace" in response.text
    assert db.get_study_session_state(old)["status"] == "active"
    # Navigating back represents cancellation; it must not modify the session.
    assert client.get(f"/decks/{deck_id}/study/setup").status_code == 200
    assert db.get_study_session_state(old)["good_count"] == 1
    new = start_study(client, deck_id, reverse="true", replace_active="true")
    assert old != new
    assert db.get_study_session_state(old)["status"] == "abandoned"
    assert client.get(f"/study/{old}").status_code == 303
    assert db.get_study_session_state(new)["reverse"] is True
    assert "Answer 0" in client.get(f"/study/{new}").text
    settings = client.post(f"/study/{old}/settings", headers={"Accept": "application/json"})
    assert settings.status_code == 409


def test_completion_and_study_again_link(seeded_deck):
    client, db, deck_id = seeded_deck
    sid = start_study(client, deck_id)
    while (state := db.get_study_session_state(sid))["status"] == "active":
        assert rate(client, sid, state["current_card"][0]).status_code == 303
    state = db.get_study_session_state(sid)
    assert state["good_count"] == state["total_cards"] == 6
    assert state["progress"] == 1
    response = client.get(f"/study/{sid}")
    assert response.status_code == 200
    assert "Session complete" in response.text
    assert f"/decks/{deck_id}/study/setup" in response.text
    assert client.post(f"/study/{sid}/settings").status_code == 409


def test_card_and_deck_crud_routes_and_cascade(app_client):
    client, db = app_client
    deck_id = db.create_deck("CRUD", front_language="de-DE", back_language="en-GB")
    add = client.post(f"/decks/{deck_id}/cards", data={"front": "Q", "back": "A"})
    assert add.status_code == 303
    card_id = db.get_cards(deck_id)[0][0]
    assert client.post(f"/cards/{card_id}", data={"front": "Q2", "back": "A2"}).status_code == 303
    assert db.get_card(card_id)[2:4] == ("Q2", "A2")
    assert client.post(f"/decks/{deck_id}/edit", data={
        "name": "Renamed", "description": "Updated", "front_language": "de-DE",
        "back_language": "en-GB",
    }).status_code == 303
    assert db.get_deck(deck_id)[1:3] == ("Renamed", "Updated")
    sid = start_study(client, deck_id)
    assert client.post(f"/cards/{card_id}/delete").status_code == 303
    assert db.get_card(card_id) is None
    assert db.get_study_session_state(sid) is not None
    assert client.post(f"/decks/{deck_id}/delete").status_code == 303
    assert db.get_study_session_state(sid) is None


def test_import_transaction_deduplicates(app_client):
    _client, db = app_client
    deck_id = db.create_deck("Import destination")
    _, count = db.import_cards_transaction(
        (("  A  ", " B "), ("A", "B"), ("C", "D")), deck_id=deck_id
    )
    assert count == 2
    assert len(db.get_cards(deck_id)) == 2


def test_export_routes_produce_files(seeded_deck):
    client, _db, deck_id = seeded_deck
    csv = client.get(f"/decks/{deck_id}/export.csv")
    xlsx = client.get(f"/decks/{deck_id}/export.xlsx")
    assert csv.status_code == 200 and "text/csv" in csv.headers["content-type"]
    assert b"Frage" in csv.content
    assert xlsx.status_code == 200 and is_zipfile(__import__("io").BytesIO(xlsx.content))
