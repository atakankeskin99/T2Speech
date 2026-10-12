# T2Speech

![Release](https://img.shields.io/badge/release-v0.1.0%20preview-6b7280)
![Python](https://img.shields.io/badge/Python-3.13-6b7280)
![License](https://img.shields.io/badge/license-MIT-6b7280)

**A local-first, open-source flashcard application with text-to-speech and audio-assisted study.**

T2Speech is a free flashcard application designed for creating, organizing, and studying flashcards with speech support.

Built with Python, FastAPI, and SQLite, it focuses on a straightforward learning experience, local data storage, and data portability without requiring an external account or cloud service.

T2Speech is under active development. **v0.1.0** is a Windows portable preview release; Linux desktop packaging and Docker-based self-hosting are not available yet.

<details>
<summary><strong>Development Journey</strong> — milestones and technical evolution</summary>

### From prototype to the first portable preview

T2Speech began as a local-first flashcard application built with Python, FastAPI, Jinja2, and SQLite. Its initial milestone was deck and card management, followed by study sessions, keyboard controls, speech playback, and CSV/XLSX data portability.

The Windows desktop preview packages the application as a portable ZIP. The backend and local storage remain part of the architecture; the desktop experience uses a WebView2-based window rather than requiring users to start the development server manually.

### Milestones

| Milestone | Status |
|---|---|
| Deck and card management | Completed |
| Study sessions and progress tracking | Completed |
| Text-to-speech and audio-assisted study | Completed |
| CSV/XLSX import and export | Completed |
| Windows portable preview (`v0.1.0`) | Released — pre-release |
| Independent Windows machine validation | Pending |
| Docker self-hosting | Planned |
| Linux compatibility verification | Planned |

This is a development history, not a promise of release dates. Further technical details are available in the developer sections below.

</details>

## Download & Installation

**Windows portable preview — v0.1.0 (pre-release)**

**[Download T2Speech for Windows (Portable ZIP)](https://github.com/atakankeskin99/T2Speech/releases/download/v0.1.0/T2Speech-Windows-Portable.zip)** · [View release notes](https://github.com/atakankeskin99/T2Speech/releases/tag/v0.1.0)

1. Download `T2Speech-Windows-Portable.zip` from the release link above.
2. Extract the entire ZIP archive to a folder of your choice.
3. Launch `T2Speech.exe` from the extracted folder.

**Requirement:** Microsoft Edge WebView2 Runtime must be installed on Windows. You do not need Python, Git, or a development environment for the portable release.

**Local data:** Database files and logs are stored at `%LOCALAPPDATA%\T2Speech\data`. They are not stored inside the extracted ZIP folder.

**Preview status:** The package was launched and tested on the development PC. Testing on an independent Windows computer remains pending. The release passed 43 automated tests and basic packaged-app smoke checks.

For contributors or users who want to run from source, see [Development Setup](#development-setup) below.

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

## Development Setup

These instructions are for development or running the local web version from source. **For regular Windows use, download the portable release above instead.**

### Development prerequisites

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

When running from source, the local `data/` directory contains the SQLite database and is excluded from version control. The Windows portable build stores database files and logs under `%LOCALAPPDATA%\T2Speech\data`.

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
| Windows Portable ZIP (`v0.1.0`) | Available — pre-release |
| Windows installer | Not available |
| Linux Desktop Package | Planned |
| Docker Deployment | Planned |

Platform support will be updated as testing and packaging progress.

## Desktop Development

The repository includes `desktop_smoke.py`, an experimental pywebview integration test.

It is intended for development only and does not provide a standalone desktop launcher or installer.

Optional desktop dependencies are listed in `requirements-desktop.txt`.

A Windows portable preview is now available. `desktop_smoke.py` remains a development-only test; it is not the packaged application itself.

## Roadmap

| Milestone | Status |
|---|---|
| Core Application — Deck & Card Management | Completed |
| Study Mode & Session Management | Completed |
| Text-to-Speech & Audio-Assisted Study | Completed |
| CSV/XLSX Import & Export | Completed |
| Windows Portable ZIP (`v0.1.0`) | Released — pre-release |
| Windows installer / Linux packaging | Planned |
| Docker & Self-Hosting | Planned |
| Cross-Platform Testing | Planned |
| v0.1.0 release documentation | Completed |

The roadmap reflects current priorities rather than fixed release commitments.

## Current Limitations

- A Windows portable ZIP is available, but no installer is provided. Testing on a separate Windows PC remains pending.
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