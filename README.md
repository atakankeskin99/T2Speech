# T2Speech

A local-first flashcard application built with Python, FastAPI, and SQLite.

## Development Notes

The Windows pywebview smoke test (`desktop_smoke.py`) is intended
for development and testing only. It is not a standalone desktop launcher.

Start the FastAPI server separately before running the smoke test:

python -m uvicorn app.main:app --reload
python desktop_smoke.py

## License

This project is licensed under the MIT License.
See the [LICENSE](LICENSE) file for details.
