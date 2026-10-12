import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import database


class ImportCardsTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        test_database_path = Path(self.temp_directory.name) / "decks.db"

        self.database_path_patch = patch.object(
            database,
            "DATABASE_PATH",
            test_database_path,
        )
        self.database_path_patch.start()
        database.initialize_database()

    def tearDown(self):
        self.database_path_patch.stop()
        self.temp_directory.cleanup()

    def test_imports_cards_and_skips_duplicates(self):
        deck_id = database.create_deck("German")
        database.create_card(deck_id, "saved", "word")

        imported_deck_id, imported_count = (
            database.import_cards_transaction(
                (
                    (" saved ", "word "),
                    ("new", "one"),
                    ("new", "one"),
                    ("New", "one"),
                ),
                deck_id=deck_id,
            )
        )

        self.assertEqual(imported_deck_id, deck_id)
        self.assertEqual(imported_count, 2)
        self.assertEqual(len(database.get_cards(deck_id)), 3)

    def test_creates_new_deck_and_cards(self):
        deck_id, imported_count = database.import_cards_transaction(
            (("Hallo", "Hello"),),
            new_deck_name="German basics",
            front_language="de-DE",
            back_language="en-GB",
        )

        deck = database.get_deck(deck_id)

        self.assertEqual(imported_count, 1)
        self.assertEqual(deck[1], "German basics")
        self.assertEqual(deck[4], "de-DE")
        self.assertEqual(deck[5], "en-GB")
        self.assertEqual(len(database.get_cards(deck_id)), 1)

    def test_rolls_back_new_deck_and_cards_after_insert_failure(self):
        connection = database.get_connection()
        try:
            connection.execute(
                """
                CREATE TRIGGER reject_test_card
                BEFORE INSERT ON cards
                WHEN NEW.front = 'trigger-failure'
                BEGIN
                    SELECT RAISE(ABORT, 'forced test failure');
                END
                """
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(sqlite3.IntegrityError):
            database.import_cards_transaction(
                (
                    ("this card would be inserted first", "one"),
                    ("trigger-failure", "two"),
                ),
                new_deck_name="Should roll back",
            )

        self.assertEqual(database.get_decks(), [])

    def test_import_does_not_change_active_session_snapshot(self):
        deck_id = database.create_deck("German")
        database.create_card(deck_id, "eins", "one")
        database.create_card(deck_id, "zwei", "two")

        session_id = database.create_study_session(
            deck_id,
            shuffle=False,
        )

        database.import_cards_transaction(
            (("drei", "three"),),
            deck_id=deck_id,
        )

        session = database.get_study_session_state(session_id)

        self.assertEqual(session["total_cards"], 2)

        connection = database.get_connection()
        try:
            session_card_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM study_session_cards
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(session_card_count, 2)

    def test_rejects_empty_import_without_creating_deck(self):
        with self.assertRaises(ValueError):
            database.import_cards_transaction(
                (),
                new_deck_name="Must not remain",
            )

        self.assertEqual(database.get_decks(), [])


if __name__ == "__main__":
    unittest.main()