import random
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "data" / "decks.db"

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection

def initialize_database():
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY,
                deck_id INTEGER NOT NULL,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
            )
        """)

        version = cursor.execute("PRAGMA user_version").fetchone()[0]

        if version > 2:
            raise RuntimeError(
                f"Database schema version {version} is newer than this application supports."
            )

        if version == 0:
            deck_columns = {
                row[1] for row in cursor.execute("PRAGMA table_info(decks)")
            }

            if "front_language" not in deck_columns:
                cursor.execute("""
                    ALTER TABLE decks
                    ADD COLUMN front_language TEXT NOT NULL DEFAULT 'und'
                """)

            if "back_language" not in deck_columns:
                cursor.execute("""
                    ALTER TABLE decks
                    ADD COLUMN back_language TEXT NOT NULL DEFAULT 'und'
                """)

            cursor.execute("PRAGMA user_version = 1")
                # v1 language migration ran above. Read the version again so a fresh
        # database can continue directly to v2 during this startup.
        version = cursor.execute("PRAGMA user_version").fetchone()[0]

        if version == 1:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_sessions (
                    id INTEGER PRIMARY KEY,
                    deck_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'completed', 'abandoned')),
                    shuffle INTEGER NOT NULL DEFAULT 1
                        CHECK (shuffle IN (0, 1)),
                    reverse INTEGER NOT NULL DEFAULT 0
                        CHECK (reverse IN (0, 1)),
                    auto_reveal INTEGER NOT NULL DEFAULT 0
                        CHECK (auto_reveal IN (0, 1)),
                    reveal_delay_seconds INTEGER NOT NULL DEFAULT 5
                        CHECK (reveal_delay_seconds > 0),
                    auto_speak TEXT NOT NULL DEFAULT 'off'
                        CHECK (auto_speak IN ('off', 'front', 'front_back')),
                    speech_rate REAL NOT NULL DEFAULT 1.0
                        CHECK (speech_rate > 0),
                    total_cards INTEGER NOT NULL
                        CHECK (total_cards >= 0),
                    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY (deck_id)
                        REFERENCES decks(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                    one_active_study_session_per_deck
                ON study_sessions(deck_id)
                WHERE status = 'active'
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_session_cards (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    card_id INTEGER,
                    front_snapshot TEXT NOT NULL,
                    back_snapshot TEXT NOT NULL,
                    initial_order INTEGER NOT NULL,
                    queue_position INTEGER,
                    result TEXT NOT NULL DEFAULT 'pending'
                        CHECK (result IN ('pending', 'good')),
                    FOREIGN KEY (session_id)
                        REFERENCES study_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (card_id)
                        REFERENCES cards(id) ON DELETE SET NULL,
                    UNIQUE (session_id, initial_order)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    study_session_cards_queue_order
                ON study_session_cards(session_id, queue_position)
                WHERE result = 'pending'
            """)

            cursor.execute("PRAGMA user_version = 2")

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def create_deck(
    name: str,
    description: str = "",
    front_language: str = "und",
    back_language: str = "und"
) -> int:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO decks (
            name, description, front_language, back_language
        )
        VALUES (?, ?, ?, ?)
    """, (name, description, front_language, back_language))

    connection.commit()
    deck_id = cursor.lastrowid
    connection.close()

    return deck_id


def get_decks():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT id, name, description, created_at
    FROM decks
    ORDER BY id
    """)
    decks = cursor.fetchall()
    connection.close()

    return decks

def get_deck(deck_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, description, created_at,
               front_language, back_language
        FROM decks
        WHERE id = ?
    """, (deck_id,))   

    deck = cursor.fetchone()
    connection.close()

    return deck

def update_deck(
    deck_id: int,
    name: str,
    description: str,
    front_language=None,
    back_language=None
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE decks
        SET name = ?,
            description = ?,
            front_language = COALESCE(?, front_language),
            back_language = COALESCE(?, back_language)
        WHERE id = ?
    """, (
        name,
        description,
        front_language,
        back_language,
        deck_id
    ))

    connection.commit()
    connection.close()

def create_card(deck_id: int, front: str, back: str) -> int:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO cards (deck_id, front, back) VALUES (?, ?, ?)",
        (deck_id, front, back)
    )

    connection.commit()
    card_id = cursor.lastrowid
    connection.close()

    return card_id

def get_cards(deck_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, front, back, created_at
        FROM cards
        WHERE deck_id = ?
        ORDER BY id
    """, (deck_id,))

    cards = cursor.fetchall()
    connection.close()   

    return  cards

def get_card(card_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, deck_id, front, back, created_at
        FROM cards
        WHERE id = ?
    """, (card_id,))

    card = cursor.fetchone()
    connection.close()

    return card

def update_card(card_id: int, front: str, back: str):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE cards SET front = ?, back = ? WHERE id = ?",
        (front, back, card_id)
    )

    connection.commit()
    connection.close()

def delete_card(card_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM cards WHERE id = ?",
        (card_id,)
    )

    connection.commit()
    connection.close()

def delete_deck(deck_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM decks WHERE id = ?",
        (deck_id,)
    )

    connection.commit()
    connection.close()

class ActiveStudySessionExists(Exception):
    pass


def get_active_study_session(deck_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, total_cards, started_at
            FROM study_sessions
            WHERE deck_id = ? AND status = 'active'
        """, (deck_id,))

        return cursor.fetchone()
    finally:
        connection.close()


def create_study_session(
    deck_id: int,
    shuffle: bool = True,
    reverse: bool = False,
    replace_active: bool = False
) -> int:
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        deck_exists = cursor.execute(
            "SELECT 1 FROM decks WHERE id = ?",
            (deck_id,)
        ).fetchone()

        if deck_exists is None:
            raise ValueError("Deck not found.")

        cards = cursor.execute("""
            SELECT id, front, back
            FROM cards
            WHERE deck_id = ?
            ORDER BY id
        """, (deck_id,)).fetchall()

        if not cards:
            raise ValueError("Cannot start a study session with an empty deck.")

        active_session = cursor.execute("""
            SELECT id
            FROM study_sessions
            WHERE deck_id = ? AND status = 'active'
        """, (deck_id,)).fetchone()

        if active_session is not None and not replace_active:
            raise ActiveStudySessionExists(
                "This deck already has an active study session."
            )

        if shuffle:
            random.shuffle(cards)

        if active_session is not None:
            cursor.execute("""
                UPDATE study_sessions
                SET status = 'abandoned',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (active_session[0],))

        cursor.execute("""
            INSERT INTO study_sessions (
                deck_id, shuffle, reverse, total_cards
            )
            VALUES (?, ?, ?, ?)
        """, (deck_id, int(shuffle), int(reverse), len(cards)))

        session_id = cursor.lastrowid

        cursor.executemany("""
            INSERT INTO study_session_cards (
                session_id,
                card_id,
                front_snapshot,
                back_snapshot,
                initial_order,
                queue_position
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (session_id, card_id, front, back, position, position)
            for position, (card_id, front, back) in enumerate(cards)
        ])

        connection.commit()
        return session_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_current_study_card(session_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        session = cursor.execute("""
            SELECT status
            FROM study_sessions
            WHERE id = ?
        """, (session_id,)).fetchone()

        if session is None:
            return None

        if session[0] != "active":
            return None

        return cursor.execute("""
            SELECT
                id,
                card_id,
                front_snapshot,
                back_snapshot,
                initial_order,
                queue_position
            FROM study_session_cards
            WHERE session_id = ?
              AND result = 'pending'
            ORDER BY queue_position
            LIMIT 1
        """, (session_id,)).fetchone()

    finally:
        connection.close()
        
def rate_current_study_card(session_id: int, rating: str):
    if rating not in ("again", "good"):
        raise ValueError("Rating must be 'again' or 'good'.")

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        session = cursor.execute("""
            SELECT status, total_cards
            FROM study_sessions
            WHERE id = ?
        """, (session_id,)).fetchone()

        if session is None:
            raise ValueError("Study session not found.")

        status, total_cards = session

        if status != "active":
            raise ValueError("Study session is not active.")

        pending_cards = cursor.execute("""
            SELECT id
            FROM study_session_cards
            WHERE session_id = ?
              AND result = 'pending'
            ORDER BY queue_position
        """, (session_id,)).fetchall()

        if not pending_cards:
            raise RuntimeError("Active session has no pending cards.")

        current_card_id = pending_cards[0][0]
        remaining_card_ids = [row[0] for row in pending_cards[1:]]

        if rating == "good":
            cursor.execute("""
                UPDATE study_session_cards
                SET result = 'good',
                    queue_position = NULL
                WHERE id = ?
            """, (current_card_id,))
        else:
            
            insert_position = min(3, len(remaining_card_ids))
            remaining_card_ids.insert(insert_position, current_card_id)

        for position, card_id in enumerate(remaining_card_ids):
            cursor.execute("""
                UPDATE study_session_cards
                SET queue_position = ?
                WHERE id = ?
            """, (position, card_id))

        good_count = cursor.execute("""
            SELECT COUNT(*)
            FROM study_session_cards
            WHERE session_id = ? AND result = 'good'
        """, (session_id,)).fetchone()[0]

        if good_count == total_cards:
            cursor.execute("""
                UPDATE study_sessions
                SET status = 'completed',
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (session_id,))
        else:
            cursor.execute("""
                UPDATE study_sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (session_id,))

        connection.commit()

        return {
            "status": "completed" if good_count == total_cards else "active",
            "good_count": good_count,
            "total_cards": total_cards,
            "progress": good_count / total_cards,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_study_session_state(session_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        session = cursor.execute("""
            SELECT
                id,
                deck_id,
                status,
                shuffle,
                reverse,
                auto_reveal,
                reveal_delay_seconds,
                auto_speak,
                speech_rate,
                total_cards,
                started_at,
                updated_at,
                completed_at
            FROM study_sessions
            WHERE id = ?
        """, (session_id,)).fetchone()

        if session is None:
            return None

        good_count = cursor.execute("""
            SELECT COUNT(*)
            FROM study_session_cards
            WHERE session_id = ? AND result = 'good'
        """, (session_id,)).fetchone()[0]

        current_card = None

        if session[2] == "active":
            current_card = cursor.execute("""
                SELECT
                    id,
                    card_id,
                    front_snapshot,
                    back_snapshot,
                    initial_order,
                    queue_position
                FROM study_session_cards
                WHERE session_id = ?
                  AND result = 'pending'
                ORDER BY queue_position
                LIMIT 1
            """, (session_id,)).fetchone()

        total_cards = session[9]

        return {
            "id": session[0],
            "deck_id": session[1],
            "status": session[2],
            "shuffle": bool(session[3]),
            "reverse": bool(session[4]),
            "auto_reveal": bool(session[5]),
            "reveal_delay_seconds": session[6],
            "auto_speak": session[7],
            "speech_rate": session[8],
            "total_cards": total_cards,
            "good_count": good_count,
            "progress": good_count / total_cards if total_cards else 0,
            "started_at": session[10],
            "updated_at": session[11],
            "completed_at": session[12],
            "current_card": current_card,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def update_study_session_settings(
    session_id: int,
    auto_reveal: bool,
    reveal_delay_seconds: int,
    auto_speak: str,
    speech_rate: float
):
    if not isinstance(auto_reveal, bool):
        raise ValueError("auto_reveal must be True or False.")

    if not isinstance(reveal_delay_seconds, int) or reveal_delay_seconds <= 0:
        raise ValueError("reveal_delay_seconds must be a positive integer.")

    if auto_speak not in ("off", "front", "front_back"):
        raise ValueError(
            "auto_speak must be 'off', 'front', or 'front_back'."
        )

    if speech_rate <= 0:
        raise ValueError("speech_rate must be greater than 0.")

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        session = cursor.execute("""
            SELECT status
            FROM study_sessions
            WHERE id = ?
        """, (session_id,)).fetchone()

        if session is None:
            raise ValueError("Study session not found.")

        if session[0] != "active":
            raise ValueError("Study session is not active.")

        cursor.execute("""
            UPDATE study_sessions
            SET auto_reveal = ?,
                reveal_delay_seconds = ?,
                auto_speak = ?,
                speech_rate = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            int(auto_reveal),
            reveal_delay_seconds,
            auto_speak,
            speech_rate,
            session_id
        ))

        connection.commit()
        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()        