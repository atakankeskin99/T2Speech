import os
import sys
from pathlib import Path


APP_PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_PACKAGE_DIR.parent


def get_resource_path(*parts: str) -> Path:
    """Return a path to a bundled application resource."""
    return APP_PACKAGE_DIR.joinpath(*parts)


def get_data_directory() -> Path:
    """Return the writable directory for persistent application data."""
    configured_directory = os.environ.get("T2SPEECH_DATA_DIR")
    if configured_directory:
        return Path(configured_directory).expanduser().resolve()

    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError(
                "LOCALAPPDATA is not set; cannot determine the packaged "
                "T2Speech data directory."
            )
        return Path(local_app_data) / "T2Speech" / "data"

    return PROJECT_ROOT / "data"


def get_database_path() -> Path:
    return get_data_directory() / "decks.db"
