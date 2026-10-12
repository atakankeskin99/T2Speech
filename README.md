# T2Speech

[![Release](https://img.shields.io/badge/release-v0.1.0-374151?style=flat-square)](https://github.com/atakankeskin99/T2Speech/releases/tag/v0.1.0)
![Windows Portable](https://img.shields.io/badge/Windows-portable-6b7280?style=flat-square)
![Preview](https://img.shields.io/badge/status-preview-9a6700?style=flat-square)
[![MIT License](https://img.shields.io/badge/license-MIT-6b7280?style=flat-square)](LICENSE)

**A local-first, open-source flashcard app with text-to-speech and audio-assisted study.**

Create flashcards, study at your own pace, and keep your learning materials on your device. No account or cloud service is required.

<details>
<summary><strong>Development</strong> — history, roadmap, architecture, and contributor information</summary>

### Development Journey

T2Speech started as a local-first flashcard application built with Python, FastAPI, Jinja2, and SQLite. Development progressed from deck and card management to interactive study sessions, speech playback, and CSV/XLSX data portability.

**v0.1.0** marks the first Windows portable preview. It provides a desktop window without requiring users to manually start the development server.

### Roadmap

| Milestone | Status |
|---|---|
| Deck and card management | Completed |
| Study Mode and session management | Completed |
| Text-to-speech and audio-assisted study | Completed |
| CSV/XLSX import and export | Completed |
| Windows portable ZIP (`v0.1.0`) | Released — preview |
| Validation on another Windows computer | Pending |
| Docker self-hosting | Planned |
| Linux compatibility testing | Planned |
| Additional desktop packaging | Planned |

The roadmap describes current priorities, not fixed delivery dates.

### Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| ASGI server | Uvicorn |
| Database | SQLite |
| Templates | Jinja2 |
| Frontend | HTML, CSS, vanilla JavaScript |
| Text-to-speech | Web Speech API |
| CSV processing | Python standard library |
| XLSX processing | openpyxl |
| Testing | unittest |
| Desktop integration | pywebview |

T2Speech favors a small, maintainable stack and local data storage over external infrastructure.

### Project Structure

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
│   │   └── js/
│   └── templates/
├── tests/
├── desktop_smoke.py
├── requirements.txt
├── requirements-desktop.txt
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

Run the automated test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

Tests cover CSV/XLSX processing, Unicode and file validation, duplicate detection, import staging, SQLite transaction rollback, and study-session isolation during imports.

For the **v0.1.0** release, 43 automated tests passed. The Windows portable archive was extracted and launched on the development PC, with deck creation, deletion, persistence, and clean shutdown checked manually.

### Platform Compatibility

| Platform | Status |
|---|---|
| Windows portable ZIP | Available — preview |
| Windows local web application | Tested during development |
| Linux local web application | Not yet validated |
| Windows installer | Not available |
| Linux desktop package | Planned |
| Docker deployment | Planned |

### Technical Limitations

- The Windows portable release has not yet been validated on a separate Windows computer.
- Linux compatibility and Docker-based deployment have not yet been verified or released.
- Speech playback depends on the voices available on the user's system.
- CSV/XLSX exports contain card content, not full application backups or study-session history.
- Native Anki `.apkg` import and cloud synchronization are not supported.
- `desktop_smoke.py` is an experimental pywebview integration test, not a standalone application launcher. Optional desktop dependencies are listed in `requirements-desktop.txt`.

### Contributing

Bug reports, suggestions, and contributions are welcome through [GitHub Issues](https://github.com/atakankeskin99/T2Speech/issues) and Pull Requests. Keep changes focused, describe their purpose, and run the relevant tests before submitting a PR.

</details>

## Download & Installation

**Windows — v0.1.0 portable preview**

**[Download T2Speech for Windows (.zip)](https://github.com/atakankeskin99/T2Speech/releases/download/v0.1.0/T2Speech-Windows-Portable.zip)** · [Release notes](https://github.com/atakankeskin99/T2Speech/releases/tag/v0.1.0)

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
