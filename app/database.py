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
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '' ,
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


    connection.commit()
    connection.close()

def create_deck(name: str, description: str = "") -> int:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO decks (name, description) VALUES (?, ?)",
        (name, description)
    )

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
        SELECT id, name, description, created_at
        FROM decks
        WHERE id = ?
    """, (deck_id,))

    deck = cursor.fetchone()
    connection.close()

    return deck

def update_deck(deck_id: int, name: str, description: str):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE decks SET name = ?, description = ? WHERE id = ?",
        (name, description, deck_id)
    )

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