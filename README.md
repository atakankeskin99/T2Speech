# T2Speech

![Development Status](https://img.shields.io/badge/status-active%20development-6b7280)
![Python](https://img.shields.io/badge/Python-3.13-6b7280)
![License](https://img.shields.io/badge/license-MIT-6b7280)

**A local-first, open-source flashcard application with text-to-speech and audio-assisted study.**

T2Speech is a free flashcard application designed for creating, organizing, and studying flashcards with speech support.

Built with Python, FastAPI, and SQLite, it focuses on a straightforward learning experience, local data storage, and data portability without requiring an external account or cloud service.

> **Development status:** T2Speech is under active development. The application has been tested locally on Windows. Linux compatibility has not yet been verified. Standalone desktop packages and Docker-based self-hosting are planned.

## Features

### Flashcard Management

- Create, edit, and delete decks and flashcards.
- Organize cards into individual decks.
- Configure front and back languages for each deck.
- Store decks, cards, and study sessions in a local SQLite database.

### Study Mode

- Interactive front-and-back flashcards.
- **Again** and **Good** controls for card progression.
- Shuffle and reverse card options.
- Session progress tracking.
- Resume unfinished study sessions.
- Keyboard shortcuts for common study actions.

### Text-to-Speech & Audio Study

- Speech playback for either side of a flashcard.
- Automatic speech playback during study sessions.
- Adjustable speech rate.
- Configurable automatic answer reveal.
- Deck-level language configuration.

T2Speech uses the Web Speech API and locally available system voices. Speech availability depends on the operating system, browser, and installed voices.

### CSV & XLSX Import/Export

- Import flashcards from CSV and XLSX files.
- Select worksheets when importing XLSX files.
- Map file columns to Front and Back.
- Preview and validate data before importing.
- Import into an existing deck or create a new one.
- Detect duplicates and report invalid entries.
- Export individual decks as CSV or XLSX.

Database imports use SQLite transactions to protect against partially committed operations.

## Getting Started

T2Speech currently runs as a local web application using FastAPI and Uvicorn.

### Prerequisites

- Python 3.13 (current development target)
- Git
- pip and Python virtual environment support
- A modern web browser

### Windows — Tested

Clone the repository:

```cmd
git clone https://github.com/atakankeskin99/T2Speech.git
cd T2Speech
```

Create and activate a virtual environment in Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

Install dependencies:

```cmd
python -m pip install -r requirements.txt
```

Create the local data directory:

```cmd
if not exist data mkdir data
```

Start T2Speech:

```cmd
python -m uvicorn app.main:app --reload
```

If using PowerShell, activate the virtual environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Linux — Not Yet Tested

Linux setup has not yet been validated. The following instructions are provided as a preliminary development reference and may require adjustments.

```bash
git clone https://github.com/atakankeskin99/T2Speech.git
cd T2Speech

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt

mkdir -p data

python -m uvicorn app.main:app --reload
```

Ensure a compatible Python version and virtual environment support are installed.

Linux compatibility will be verified during a later development milestone.

### Accessing the Application

Once the server starts, open:

**http://127.0.0.1:8000**

The application initializes its SQLite database at `data/decks.db`.

The `--reload` flag is intended for development rather than production deployment.

## Basic Usage

1. **Create a deck.** Open the Library, enter a name, and configure its languages.
2. **Add cards.** Create flashcards manually or import CSV/XLSX files.
3. **Start a session.** Choose shuffle or reverse settings and begin studying.
4. **Review cards.** Reveal answers, use Again/Good, and enable speech playback when local voices are available.
5. **Export content.** Download decks in CSV or XLSX format.

### Data Import Limitations

CSV and XLSX import currently supports text-based Front and Back fields, subject to file-size and row-count limits.

Exported spreadsheets contain card content, not full application backups or study session history.

Native Anki `.apkg` import is not currently supported.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| ASGI Server | Uvicorn |
| Database | SQLite |
| Templates | Jinja2 |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Text-to-Speech | Web Speech API |
| CSV Processing | Python standard library |
| XLSX Processing | openpyxl |
| Testing | unittest |
| Desktop Exploration | pywebview |

T2Speech intentionally uses a small technology stack, prioritizing local functionality, maintainability, and minimal infrastructure requirements.

## Project Structure

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

The local `data/` directory contains the SQLite database and is excluded from version control.

## Testing

T2Speech uses Python's built-in `unittest` framework.

Run the test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

Current automated tests cover:

- CSV/XLSX parsing and export
- Unicode handling and file validation
- Duplicate detection
- Import staging and expiration
- SQLite transactions and rollback
- Study session isolation during imports

The project also undergoes manual testing of application workflows. Broader integration and cross-platform verification remain ongoing development goals.

## Platform Support

| Platform | Status |
|---|---|
| Windows — Local Web Application | Tested during development |
| Linux — Local Web Application | Not yet tested |
| Windows Desktop Package | Planned |
| Linux Desktop Package | Planned |
| Docker Deployment | Planned |

Platform support will be updated as testing and packaging progress.

## Desktop Development

The repository includes `desktop_smoke.py`, an experimental pywebview integration test.

It is intended for development only and does not provide a standalone desktop launcher or installer.

Optional desktop dependencies are listed in `requirements-desktop.txt`.

Desktop integration and packaging are not yet supported release features.

## Roadmap

| Milestone | Status |
|---|---|
| Core Application — Deck & Card Management | Completed |
| Study Mode & Session Management | Completed |
| Text-to-Speech & Audio-Assisted Study | Completed |
| CSV/XLSX Import & Export | Completed |
| Desktop Packaging — Windows/Linux | Planned |
| Docker & Self-Hosting | Planned |
| Cross-Platform Testing | Planned |
| Documentation & Release Preparation | In Progress |

The roadmap reflects current priorities rather than fixed release commitments.

## Current Limitations

- No standalone desktop installer or packaged release is available.
- Linux compatibility has not yet been verified.
- Docker deployment is not yet implemented.
- Text-to-speech depends on locally available system voices.
- CSV/XLSX exports do not preserve full application state.
- Native Anki package import and cloud synchronization are not supported.

## Contributing

T2Speech is an open-source project under active development.

Bug reports, suggestions, and contributions are welcome through GitHub Issues and Pull Requests.

Before submitting a pull request, please keep changes focused, explain their purpose, and run the available tests when applicable.

## License

T2Speech is distributed under the **MIT License**.

See the [LICENSE](LICENSE) file for details.