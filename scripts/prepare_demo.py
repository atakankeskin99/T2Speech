"""Package only allowlisted static demo files and unmodified shared UI assets.

No compilation, third-party packages, application imports, or user data access.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEMO_FILES = (
    "index.html", "deck.html", "study_setup.html", "study.html", "study_complete.html",
    "data/sample-decks.json", "css/demo.css", "js/demo-app.js", "js/demo-session.js",
    "js/demo-storage.js", "js/demo-study.js",
)
SHARED_ASSETS = {"assets/app.css": "app/static/css/app.css", "assets/app.js": "app/static/js/app.js"}


def prepare(output: Path) -> Path:
    output = output.resolve()
    if output == ROOT or ROOT / "demo" == output or output in (ROOT / "demo").parents:
        raise ValueError("Choose a dedicated artifact directory, not the repository or demo source.")
    expected = set(DEMO_FILES) | set(SHARED_ASSETS) | {".nojekyll"}
    if output.exists():
        extras = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()} - expected
        if extras:
            raise ValueError(f"Artifact directory contains unexpected files: {sorted(extras)}")
    for relative, source in [(name, f"demo/{name}") for name in DEMO_FILES] + list(SHARED_ASSETS.items()):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, target)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/demo")
    arguments = parser.parse_args()
    print(prepare(arguments.output))
