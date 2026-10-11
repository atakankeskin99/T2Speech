import re
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from app.services.csv_import import MAX_FILE_SIZE_BYTES


STAGING_DIRECTORY = Path(tempfile.gettempdir()) / "t2speech-imports"
STAGING_TTL_SECONDS = 60 * 60
TOKEN_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def _path_for_token(token: str) -> Path:
    if not TOKEN_PATTERN.fullmatch(token):
        raise ValueError("Invalid import token.")

    return STAGING_DIRECTORY / f"{token}.csv"


def _remove_expired_files() -> None:
    if not STAGING_DIRECTORY.exists():
        return

    current_time = time.time()

    for path in STAGING_DIRECTORY.glob("*.csv"):
        try:
            expired = (
                current_time - path.stat().st_mtime
                > STAGING_TTL_SECONDS
            )
            if expired:
                path.unlink()
        except FileNotFoundError:
            # Another request may have removed the file already.
            continue


def save_staged_csv(file_bytes: bytes) -> str:
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError("The CSV file exceeds the 5 MB limit.")

    STAGING_DIRECTORY.mkdir(parents=True, exist_ok=True)
    _remove_expired_files()

    token = uuid4().hex
    path = _path_for_token(token)
    path.write_bytes(file_bytes)

    return token


def load_staged_csv(token: str) -> bytes:
    path = _path_for_token(token)

    try:
        modified_at = path.stat().st_mtime
    except FileNotFoundError as error:
        raise FileNotFoundError("The import preview has expired.") from error

    if time.time() - modified_at > STAGING_TTL_SECONDS:
        path.unlink(missing_ok=True)
        raise FileNotFoundError("The import preview has expired.")

    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
        path.unlink(missing_ok=True)
        raise ValueError("The staged CSV file exceeds the 5 MB limit.")

    return path.read_bytes()


def delete_staged_csv(token: str) -> None:
    path = _path_for_token(token)
    path.unlink(missing_ok=True)