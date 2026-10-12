import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import import_staging as staging
from app.services.csv_import import MAX_FILE_SIZE_BYTES


class ImportStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.staging_directory = Path(self.temp_directory.name) / "staged"

        self.directory_patch = patch.object(
            staging,
            "STAGING_DIRECTORY",
            self.staging_directory,
        )
        self.directory_patch.start()

    def tearDown(self):
        self.directory_patch.stop()
        self.temp_directory.cleanup()

    def test_saves_loads_and_deletes_csv(self):
        content = b"Front,Back\nHallo,Hello\n"

        token = staging.save_staged_csv(content)
        path = self.staging_directory / f"{token}.csv"

        self.assertEqual(staging.load_staged_csv(token), content)
        self.assertTrue(path.exists())

        staging.delete_staged_csv(token)

        self.assertFalse(path.exists())
        with self.assertRaises(FileNotFoundError):
            staging.load_staged_csv(token)

    def test_saves_loads_and_deletes_xlsx(self):
        content = b"sample XLSX bytes"

        token = staging.save_staged_file(content, "xlsx")
        path = self.staging_directory / f"{token}.xlsx"

        self.assertEqual(
            staging.load_staged_file(token, "xlsx"),
            content,
        )
        self.assertTrue(path.exists())

        staging.delete_staged_file(token, "xlsx")

        self.assertFalse(path.exists())
        with self.assertRaises(FileNotFoundError):
            staging.load_staged_file(token, "xlsx")

    def test_rejects_invalid_token(self):
        with self.assertRaises(ValueError):
            staging.load_staged_csv("../not-a-token.csv")

    def test_removes_and_rejects_expired_file(self):
        token = staging.save_staged_csv(b"Front,Back\nA,B\n")
        path = self.staging_directory / f"{token}.csv"
        expired_time = time.time() - staging.STAGING_TTL_SECONDS - 1

        os.utime(path, (expired_time, expired_time))

        with self.assertRaises(FileNotFoundError):
            staging.load_staged_csv(token)

        self.assertFalse(path.exists())

    def test_rejects_file_over_size_limit(self):
        content = b"x" * (MAX_FILE_SIZE_BYTES + 1)

        with self.assertRaises(ValueError):
            staging.save_staged_csv(content)


if __name__ == "__main__":
    unittest.main()