# T2Speech

[![Release](https://img.shields.io/badge/release-v0.1.0-374151?style=flat-square)](https://github.com/atakankeskin99/T2Speech/releases/tag/v0.1.0)
![Windows Portable](https://img.shields.io/badge/Windows-portable-6b7280?style=flat-square)
![Preview](https://img.shields.io/badge/status-preview-9a6700?style=flat-square)
[![MIT License](https://img.shields.io/badge/license-MIT-6b7280?style=flat-square)](LICENSE)

**A local-first, open-source flashcard app with text-to-speech and audio-assisted study.**

T2Speech is a small, local-first project built around flashcards, text-to-speech, and a straightforward study workflow. It keeps data on the user's machine and avoids unnecessary external services.

<details>
<summary><strong>Development</strong> — history, roadmap, architecture, and contributor information</summary>

### Development Journey

I was looking for a flashcard app that suited the way I wanted to study. I tried a few, but none felt quite right, so I decided to build my own. T2Speech started as a personal project, and I eventually made it open-source for anyone who might find it useful.

**v0.1.0** is the first Windows portable preview, providing a desktop window without requiring users to start the development server manually.

**Post-v0.1.0 source development** has focused on refining the study experience and making its behavior more reliable:

- **Study workspace:** A distraction-free layout with a centered flashcard, inline Prompt/Answer reveal, separate Again/Good actions, a compact progress indicator, and keyboard shortcuts.
- **Session lifecycle:** Persistent sessions with card snapshots, Resume, Shuffle, Reverse Cards, explicit confirmation before replacing an active session, and a dedicated completion screen with Study Again.
- **Session settings:** A compact Settings popover with immediately applied options and automatic SQLite persistence for auto-speak, speech rate, auto-reveal, and reveal delay. Failed saves can be retried.
- **Reliability:** Transactional Again/Good evaluation, stale or duplicate rating-request protection, correct handling of abandoned sessions, and stricter speech-rate validation.
- **Deck navigation:** A single Export dropdown for CSV and XLSX instead of separate export buttons. Library-level importing remains available through its existing Import dropdown.
- **Regression coverage:** A reusable pytest/Playwright Study Mode suite in addition to the original unittest-based tests.

These improvements describe the current development source; the existing **v0.1.0 portable download** should not be assumed to include changes made after that release.

### Roadmap

| Milestone | Status |
|---|---|
| Deck and card management | Completed |
| Study Mode, persistent sessions, and session lifecycle | Completed |
| Study workspace refinement and automatic session-settings persistence | Completed — development source |
| Text-to-speech and audio-assisted study | Completed |
| CSV/XLSX import and export | Completed |
| Study Mode regression suite (pytest + Chromium) | Completed — 48 tests passed on Windows |
| Windows portable ZIP (`v0.1.0`) | Released — preview |
| Validation of the portable build on another Windows computer | Pending |
| Docker self-hosting | Planned |
| Linux compatibility testing | Planned |
| Additional desktop packaging | Planned |

The roadmap describes current priorities, not fixed delivery dates.

### Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.13, FastAPI |
| ASGI server | Uvicorn |
| Database and session persistence | SQLite |
| Templates | Jinja2 |
| Frontend | HTML, CSS, vanilla JavaScript |
| Text-to-speech | Browser Web Speech API (available local voices) |
| CSV processing | Python standard library |
| XLSX processing | openpyxl |
| Automated testing | unittest, pytest, FastAPI TestClient, Playwright (Chromium) |
| Desktop integration | pywebview |

T2Speech favors a small, maintainable stack and local data storage over external infrastructure. Study Mode settings and progress use the existing SQLite session tables rather than a separate persistence service.

### Project Structure

Selected files and directories relevant to development (other templates and tests omitted):

```text
T2Speech/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── services/
│   │   ├── csv_import.py
│   │   ├── csv_export.py
│   │   ├── xlsx_import.py
│   │   ├── xlsx_export.py
│   │   └── import_staging.py
│   ├── static/
│   │   ├── css/
│   │   │   └── app.css
│   │   └── js/
│   │       ├── app.js
│   │       └── study.js
│   └── templates/
│       ├── deck.html
│       ├── study.html
│       ├── study_setup.html
│       └── study_complete.html
├── tests/
│   ├── baseline_theme_tokens.json
│   └── study_mode/
│       ├── conftest.py
│       ├── test_study_assets.py
│       ├── test_study_browser.py
│       └── test_study_routes.py
├── desktop_smoke.py
├── requirements.txt
├── requirements-desktop.txt
├── requirements-test.txt
├── LICENSE
└── README.md
```

For source-based development, `data/decks.db` contains the local SQLite database; the `data/` directory is excluded from version control. The Windows portable build uses `%LOCALAPPDATA%\T2Speech\data` for its database and logs.

### Development Setup

These instructions are for contributors and anyone who wants to run the local web version from source. The Windows portable release below does **not** require Python or Git.

**Prerequisites:** Python 3.13 (current development target), Git, pip, virtual environment support, and a modern web browser.

**Windows — tested during development**

```cmd
git clone https://github.com/atakankeskin99/T2Speech.git
cd T2Speech
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if not exist data mkdir data
python -m uvicorn app.main:app --reload
```

For PowerShell, activate the environment using `.\.venv\Scripts\Activate.ps1` instead.

**Linux — not yet validated**

```bash
git clone https://github.com/atakankeskin99/T2Speech.git
cd T2Speech
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p data
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` after starting the server. The `--reload` option is for development only. Linux instructions are preliminary and may require adjustment.

### Testing

Two complementary test suites are maintained. Run these commands from the repository root with the project virtual environment activated.

**Existing unittest suite:**

```bash
python -m unittest discover -s tests -v
```

This suite covers CSV/XLSX processing, Unicode and file validation, duplicate detection, import staging, SQLite transaction rollback, and study-session isolation during imports. At the **v0.1.0** release milestone, 43 automated unittest tests passed; that figure is a historical release result, not a combined current total.

**Study Mode regression suite (pytest + Playwright):**

Install the test-only dependencies and Chromium once:

```bash
python -m pip install -r requirements-test.txt
python -m playwright install chromium
```

Then run the complete Study Mode suite:

```bash
python -m pytest tests/study_mode -v
```

To run subsets independently:

```bash
python -m pytest tests/study_mode -m "not browser" -q
python -m pytest tests/study_mode -m browser -q
```

The Study Mode suite covers session creation, resumption and replacement; Again/Good queue behavior and duplicate-request protection; card snapshots; settings persistence and validation; keyboard controls; TTS fallback behavior; Light/Dark theme tokens; and Chromium layout checks across desktop and mobile widths. Tests use isolated temporary SQLite data, not the user's normal `data/decks.db`.

**Latest local result (Windows, Python 3.13): 48 passed, 1 non-blocking Starlette/httpx deprecation warning.** The test result applies to the Study Mode suite, not the complete set of legacy and new tests together. Browser tests do not replace manual checks with real system speech voices. CSV/XLSX import and export were also manually verified during this development cycle.

### Platform Compatibility

| Platform | Status |
|---|---|
| Windows portable ZIP | Available — preview (`v0.1.0`) |
| Windows local web application | Tested during development |
| Linux local web application | Not yet validated |
| Windows installer | Not available |
| Linux desktop package | Planned |
| Docker deployment | Planned |

### Technical Limitations

- The Windows portable release has not yet been validated on a separate Windows computer; post-release source improvements are not yet part of a new published portable build.
- Linux compatibility and Docker-based deployment have not yet been verified or released.
- Speech playback depends on the voices available on the user's system.
- CSV/XLSX exports contain card content, not full application backups or study-session history.
- Native Anki `.apkg` import and cloud synchronization are not supported.
- `desktop_smoke.py` is an experimental pywebview integration test, not a standalone application launcher. Optional desktop dependencies are listed in `requirements-desktop.txt`.

### Contributing

Bug reports, suggestions, and contributions are welcome through [GitHub Issues](https://github.com/atakankeskin99/T2Speech/issues) and Pull Requests. Keep changes focused, describe their purpose, and run both the existing unittest suite and the relevant pytest tests before submitting a PR.

</details>

## Download & Installation

**Windows — v0.1.0 portable preview**

**[Download T2Speech for Windows (.zip)](https://github.com/user-attachments/files/33364917/T2Speech-v0.2.0-windows-x64.zip)** · [Release notes](https://github.com/atakankeskin99/T2Speech/releases/tag/v0.2.0)

1. Download the ZIP file.
2. Extract it to a folder of your choice.
3. Open the extracted folder and run `T2Speech.exe`.

**Requirement:** Microsoft Edge WebView2 Runtime must be installed. No Python or Git installation is needed.

> **Preview release:** T2Speech has been tested on its development PC, but not yet on a separate Windows computer.

## Features

- **Flashcard management:** Create, edit, and organize decks and cards.
- **Study Mode:** Flip cards, shuffle or reverse them, track progress, and resume unfinished sessions.
- **Text-to-speech:** Listen to your cards, adjust playback speed, and use automatic speech playback with available system voices.
- **CSV & XLSX:** Import cards from spreadsheets, preview them before importing, and export your decks.

## How to Use

1. **Create a deck** in your Library.
2. **Add cards** manually or import them from CSV/XLSX.
3. **Start studying:** reveal answers, choose **Again** or **Good**, and use speech playback when available.

## License

T2Speech is free and open-source software distributed under the [MIT License](LICENSE).
