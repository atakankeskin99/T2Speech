import re
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from app.services.csv_import import MAX_FILE_SIZE_BYTES


STAGING_DIRECTORY = Path(tempfile.gettempdir()) / "t2speech-imports"
STAGING_TTL_SECONDS = 60 * 60
TOKEN_PATTERN = re.compile(r"^[a-f0-9]{32}$")
ALLOWED_FILE_EXTENSIONS = {"csv", "xlsx"}


def _normalize_extension(file_extension: str) -> str:
    extension = file_extension.lower().lstrip(".")

    if extension not in ALLOWED_FILE_EXTENSIONS:
        raise ValueError("Unsupported staged file type.")

    return extension


def _path_for_token(token: str, file_extension: str) -> Path:
    if not TOKEN_PATTERN.fullmatch(token):
        raise ValueError("Invalid import token.")

    extension = _normalize_extension(file_extension)
    return STAGING_DIRECTORY / f"{token}.{extension}"


def _remove_expired_files() -> None:
    if not STAGING_DIRECTORY.exists():
        return

    current_time = time.time()

    for path in STAGING_DIRECTORY.iterdir():
        if path.suffix.lower().lstrip(".") not in ALLOWED_FILE_EXTENSIONS:
            continue

        try:
            expired = (
                current_time - path.stat().st_mtime
                > STAGING_TTL_SECONDS
            )
            if expired:
                path.unlink()
        except FileNotFoundError:
            continue


def save_staged_file(file_bytes: bytes, file_extension: str) -> str:
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError("The staged file exceeds the 5 MB limit.")

    extension = _normalize_extension(file_extension)
    STAGING_DIRECTORY.mkdir(parents=True, exist_ok=True)
    _remove_expired_files()

    token = uuid4().hex
    _path_for_token(token, extension).write_bytes(file_bytes)

    return token


def load_staged_file(token: str, file_extension: str) -> bytes:
    path = _path_for_token(token, file_extension)

    try:
        modified_at = path.stat().st_mtime
    except FileNotFoundError as error:
        raise FileNotFoundError("The import preview has expired.") from error

    if time.time() - modified_at > STAGING_TTL_SECONDS:
        path.unlink(missing_ok=True)
        raise FileNotFoundError("The import preview has expired.")

    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
        path.unlink(missing_ok=True)
        raise ValueError("The staged file exceeds the 5 MB limit.")

    return path.read_bytes()


def delete_staged_file(token: str, file_extension: str) -> None:
    _path_for_token(token, file_extension).unlink(missing_ok=True)


def save_staged_csv(file_bytes: bytes) -> str:
    return save_staged_file(file_bytes, "csv")


def load_staged_csv(token: str) -> bytes:
    return load_staged_file(token, "csv")


def delete_staged_csv(token: str) -> None:
    delete_staged_file(token, "csv")