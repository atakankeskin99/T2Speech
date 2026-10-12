from fastapi import FastAPI, Request, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from urllib.parse import quote
from fastapi.responses import Response
from app.paths import get_resource_path
from app.services.csv_export import build_csv_export
from app.services.xlsx_export import build_xlsx_export
from app.services.xlsx_import import get_xlsx_sheet_names
from app.services.csv_import import (
    MAX_FILE_SIZE_BYTES,
    analyze_import,
    parse_csv,
)
from app.services.xlsx_import import get_xlsx_sheet_names, parse_xlsx
from app.services.import_staging import (
    delete_staged_csv,
    load_staged_csv,
    load_staged_file,
    save_staged_csv,
    save_staged_file,
    delete_staged_file,

)

from app.database import (
initialize_database,
get_decks,
create_deck,
get_deck,
get_cards,
create_card,
get_card,
update_card,
delete_card,
delete_deck,
update_deck,
get_active_study_session,
get_study_session_state,
ActiveStudySessionExists,
create_study_session,
rate_current_study_card,
update_study_session_settings,
import_cards_transaction,

)

app = FastAPI()
LANGUAGES = [
    ("de-DE", "German"),
    ("en-GB", "English (UK)"),
    ("en-US", "English (US)"),
    ("es-ES", "Spanish"),
    ("fr-FR", "French"),
    ("it-IT", "Italian"),
    ("ja-JP", "Japanese"),
    ("ko-KR", "Korean"),
    ("nl-NL", "Dutch"),
    ("pl-PL", "Polish"),
    ("pt-BR", "Portuguese (Brazil)"),
    ("ru-RU", "Russian"),
    ("tr-TR", "Turkish"),
    ("zh-CN", "Chinese (Mandarin)"),
]

initialize_database()
app.mount(
    "/static",
    StaticFiles(directory=str(get_resource_path("static"))),
    name="static",
)

templates = Jinja2Templates(directory=str(get_resource_path("templates")))

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    decks = get_decks()

    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={"decks": decks, "languages": LANGUAGES}
)

@app.get("/imports/csv", response_class=HTMLResponse)
def select_csv_import(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="import_csv_select.html",
        context={},
    )

@app.get("/imports/xlsx", response_class=HTMLResponse)
def select_xlsx_import(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="import_xlsx_select.html",
        context={},
    )

@app.post("/imports/csv/configure", response_class=HTMLResponse)
async def configure_csv_import(
    request: Request,
    file: UploadFile = File(...),
):
    filename = file.filename or ""

    try:
        if not filename.lower().endswith(".csv"):
            raise ValueError("Please select a CSV file.")

        file_bytes = await file.read(MAX_FILE_SIZE_BYTES + 1)
        parsed_csv = parse_csv(file_bytes)
        token = save_staged_csv(file_bytes)

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="import_csv_select.html",
            context={"error": str(error)},
            status_code=400,
        )

    finally:
        await file.close()

    return templates.TemplateResponse(
        request=request,
        name="import_csv_configure.html",
        context={
            "filename": filename,
            "token": token,
            "headers": parsed_csv.headers,
            "data_row_count": len(parsed_csv.rows),
            "default_front_index": 0,
            "default_back_index": (
                1 if len(parsed_csv.headers) > 1 else None

            ),
            "decks": get_decks(),
            "languages": LANGUAGES,
        },
    )

@app.post("/imports/xlsx/configure", response_class=HTMLResponse)
async def configure_xlsx_import(
    request: Request,
    file: UploadFile = File(...),
):
    filename = file.filename or ""

    try:
        if not filename.lower().endswith(".xlsx"):
            raise ValueError("Please select an XLSX file.")

        file_bytes = await file.read(MAX_FILE_SIZE_BYTES + 1)
        sheet_names = get_xlsx_sheet_names(file_bytes)
        token = save_staged_file(file_bytes, "xlsx")

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="import_xlsx_select.html",
            context={"error": str(error)},
            status_code=400,
        )

    finally:
        await file.close()

    return templates.TemplateResponse(
        request=request,
        name="import_xlsx_sheet.html",
        context={
            "filename": filename,
            "token": token,
            "sheet_names": sheet_names,
        },
    )
@app.post("/imports/xlsx/configure-columns", response_class=HTMLResponse)
def configure_xlsx_columns(
    request: Request,
    token: str = Form(...),
    filename: str = Form("XLSX file"),
    sheet_name: str = Form(...),
):
    try:
        file_bytes = load_staged_file(token, "xlsx")
        parsed_xlsx = parse_xlsx(file_bytes, sheet_name)

    except (FileNotFoundError, ValueError) as error:
        return templates.TemplateResponse(
            request=request,
            name="import_xlsx_select.html",
            context={"error": str(error)},
            status_code=400,
        )

    return templates.TemplateResponse(
        request=request,
        name="import_xlsx_configure.html",
        context={
            "filename": filename,
            "token": token,
            "sheet_name": sheet_name,
            "headers": parsed_xlsx.headers,
            "data_row_count": len(parsed_xlsx.rows),
            "default_front_index": 0,
            "default_back_index": (
                1 if len(parsed_xlsx.headers) > 1 else None
            ),
            "decks": get_decks(),
            "languages": LANGUAGES,
        },
    )

@app.post("/imports/xlsx/preview", response_class=HTMLResponse)
def preview_xlsx_import(
    request: Request,
    token: str = Form(...),
    filename: str = Form("XLSX file"),
    sheet_name: str = Form(...),
    front_index: int = Form(...),
    back_index: int = Form(...),
    destination: str = Form(...),
    new_deck_name: str = Form(""),
    description: str = Form(""),
    front_language: str = Form(""),
    back_language: str = Form(""),
    deck_id: str = Form(""),
    has_header: bool = Form(False),
):
    try:
        file_bytes = load_staged_file(token, "xlsx")
        parsed_xlsx = parse_xlsx(
            file_bytes,
            sheet_name,
            has_header=has_header,
        )
    except (FileNotFoundError, ValueError) as error:
        return templates.TemplateResponse(
            request=request,
            name="import_xlsx_select.html",
            context={"error": str(error)},
            status_code=400,
        )

    selected_deck_id = None
    destination_name = ""
    existing_cards = ()

    if destination == "new":
        if not new_deck_name.strip():
            raise HTTPException(
                status_code=400,
                detail="Enter a name for the new deck.",
            )

        available_languages = {code for code, _ in LANGUAGES}
        if (
            front_language not in available_languages
            or back_language not in available_languages
        ):
            raise HTTPException(
                status_code=400,
                detail="Choose a language for both sides.",
            )

        destination_name = new_deck_name.strip()

    elif destination == "existing":
        try:
            selected_deck_id = int(deck_id)
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="Choose an existing deck.",
            ) from error

        deck = get_deck(selected_deck_id)
        if deck is None:
            raise HTTPException(
                status_code=404,
                detail="Destination deck not found.",
            )

        destination_name = deck[1]
        existing_cards = tuple(
            (card[1], card[2])
            for card in get_cards(selected_deck_id)
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Choose an import destination.",
        )

    try:
        analysis = analyze_import(
            parsed_xlsx,
            front_index=front_index,
            back_index=back_index,
            existing_cards=existing_cards,
            has_header=has_header,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return templates.TemplateResponse(
        request=request,
        name="import_xlsx_preview.html",
        context={
            "filename": filename,
            "sheet_name": sheet_name,
            "token": token,
            "analysis": analysis,
            "destination": destination,
            "destination_name": destination_name,
            "new_deck_name": new_deck_name,
            "description": description,
            "front_language": front_language,
            "back_language": back_language,
            "deck_id": selected_deck_id or "",
            "front_index": front_index,
            "back_index": back_index,
            "has_header": has_header,


        },
    )


@app.post("/imports/csv/preview", response_class=HTMLResponse)
def preview_csv_import(
    request: Request,
    token: str = Form(...),
    filename: str = Form("CSV file"),
    front_index: int = Form(...),
    back_index: int = Form(...),
    destination: str = Form(...),
    new_deck_name: str = Form(""),
    description: str = Form(""),
    front_language: str = Form(""),
    back_language: str = Form(""),
    deck_id: str = Form(""),
    has_header: bool = Form(False),
):
    try:
        file_bytes = load_staged_csv(token)
        parsed_csv = parse_csv(file_bytes, has_header=has_header)

    except (FileNotFoundError, ValueError) as error:
        return templates.TemplateResponse(
            request=request,
            name="import_csv_select.html",
            context={"error": str(error)},
            status_code=400,
        )

    selected_deck_id = None
    destination_name = ""
    existing_cards = ()

    if destination == "new":
        if not new_deck_name.strip():
            raise HTTPException(
                status_code=400,
                detail="Enter a name for the new deck.",
            )

        available_languages = {code for code, _ in LANGUAGES}
        if (
            front_language not in available_languages
            or back_language not in available_languages
        ):
            raise HTTPException(
                status_code=400,
                detail="Choose a language for both sides.",
            )

        destination_name = new_deck_name.strip()

    elif destination == "existing":
        try:
            selected_deck_id = int(deck_id)
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="Choose an existing deck.",
            ) from error

        deck = get_deck(selected_deck_id)
        if deck is None:
            raise HTTPException(
                status_code=404,
                detail="Destination deck not found.",
            )

        destination_name = deck[1]
        existing_cards = tuple(
            (card[1], card[2])
            for card in get_cards(selected_deck_id)
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Choose an import destination.",
        )

    try:
        analysis = analyze_import(
            parsed_csv,
            front_index=front_index,
            back_index=back_index,
            existing_cards=existing_cards,
            has_header=has_header,
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return templates.TemplateResponse(
        request=request,
        name="import_csv_preview.html",
        context={
            "filename": filename,
            "token": token,
            "analysis": analysis,
            "destination": destination,
            "destination_name": destination_name,
            "new_deck_name": new_deck_name,
            "description": description,
            "front_language": front_language,
            "back_language": back_language,
            "deck_id": selected_deck_id or "",
            "front_index": front_index,
            "back_index": back_index,
        },
    )

@app.post("/imports/csv/confirm", response_class=HTMLResponse)
def confirm_csv_import(
    request: Request,
    token: str = Form(...),
    filename: str = Form("CSV file"),
    destination: str = Form(...),
    new_deck_name: str = Form(""),
    description: str = Form(""),
    front_language: str = Form(""),
    back_language: str = Form(""),
    deck_id: str = Form(""),
    front_index: int = Form(...),
    back_index: int = Form(...),
    has_header: bool = Form(False),
):
    try:
        file_bytes = load_staged_csv(token)
        parsed_csv = parse_csv(file_bytes, has_header=has_header)
    except (FileNotFoundError, ValueError) as error:
        return templates.TemplateResponse(
            request=request,
            name="import_csv_select.html",
            context={"error": str(error)},
            status_code=400,
        )

    selected_deck_id = None
    destination_name = ""
    existing_cards = ()

    if destination == "new":
        if not new_deck_name.strip():
            raise HTTPException(
                status_code=400,
                detail="Enter a name for the new deck.",
            )

        available_languages = {code for code, _ in LANGUAGES}
        if (
            front_language not in available_languages
            or back_language not in available_languages
        ):
            raise HTTPException(
                status_code=400,
                detail="Choose a language for both sides.",
            )

        destination_name = new_deck_name.strip()

    elif destination == "existing":
        try:
            selected_deck_id = int(deck_id)
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="Choose an existing deck.",
            ) from error

        deck = get_deck(selected_deck_id)
        if deck is None:
            raise HTTPException(
                status_code=404,
                detail="Destination deck not found.",
            )

        destination_name = deck[1]
        existing_cards = tuple(
            (card[1], card[2])
            for card in get_cards(selected_deck_id)
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Choose an import destination.",
        )

    try:
        analysis = analyze_import(
            parsed_csv,
            front_index=front_index,
            back_index=back_index,
            existing_cards=existing_cards,
            has_header=has_header,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    cards_to_import = tuple(
        (row.front, row.back)
        for row in analysis.rows
        if row.status == "ready"
    )

    if not cards_to_import:
        raise HTTPException(
            status_code=409,
            detail="There are no new cards to import.",
        )

    try:
        destination_deck_id, imported_count = import_cards_transaction(
            cards_to_import,
            deck_id=selected_deck_id,
            new_deck_name=(
                new_deck_name.strip()
                if destination == "new"
                else None
            ),
            description=description,
            front_language=front_language,
            back_language=back_language,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    delete_staged_csv(token)

    return templates.TemplateResponse(
        request=request,
        name="import_csv_summary.html",
        context={
            "filename": filename,
            "deck_id": destination_deck_id,
            "deck_name": destination_name,
            "imported_count": imported_count,
            "skipped_at_commit": len(cards_to_import) - imported_count,
            "analysis": analysis,
        },
    )

@app.post("/imports/xlsx/confirm", response_class=HTMLResponse)
def confirm_xlsx_import(
    request: Request,
    token: str = Form(...),
    filename: str = Form("XLSX file"),
    sheet_name: str = Form(...),
    destination: str = Form(...),
    new_deck_name: str = Form(""),
    description: str = Form(""),
    front_language: str = Form(""),
    back_language: str = Form(""),
    deck_id: str = Form(""),
    front_index: int = Form(...),
    back_index: int = Form(...),
    has_header: bool = Form(False),
):
    try:
        file_bytes = load_staged_file(token, "xlsx")
        parsed_xlsx = parse_xlsx(
            file_bytes,
            sheet_name,
            has_header=has_header,
        )
    except (FileNotFoundError, ValueError) as error:
        return templates.TemplateResponse(
            request=request,
            name="import_xlsx_select.html",
            context={"error": str(error)},
            status_code=400,
        )

    selected_deck_id = None
    destination_name = ""
    existing_cards = ()

    if destination == "new":
        if not new_deck_name.strip():
            raise HTTPException(
                status_code=400,
                detail="Enter a name for the new deck.",
            )

        available_languages = {code for code, _ in LANGUAGES}
        if (
            front_language not in available_languages
            or back_language not in available_languages
        ):
            raise HTTPException(
                status_code=400,
                detail="Choose a language for both sides.",
            )

        destination_name = new_deck_name.strip()

    elif destination == "existing":
        try:
            selected_deck_id = int(deck_id)
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="Choose an existing deck.",
            ) from error

        deck = get_deck(selected_deck_id)
        if deck is None:
            raise HTTPException(
                status_code=404,
                detail="Destination deck not found.",
            )

        destination_name = deck[1]
        existing_cards = tuple(
            (card[1], card[2])
            for card in get_cards(selected_deck_id)
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Choose an import destination.",
        )

    try:
        analysis = analyze_import(
            parsed_xlsx,
            front_index=front_index,
            back_index=back_index,
            existing_cards=existing_cards,
            has_header=has_header,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    cards_to_import = tuple(
        (row.front, row.back)
        for row in analysis.rows
        if row.status == "ready"
    )

    if not cards_to_import:
        raise HTTPException(
            status_code=409,
            detail="There are no new cards to import.",
        )

    try:
        destination_deck_id, imported_count = import_cards_transaction(
            cards_to_import,
            deck_id=selected_deck_id,
            new_deck_name=(
                new_deck_name.strip()
                if destination == "new"
                else None
            ),
            description=description,
            front_language=front_language,
            back_language=back_language,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    delete_staged_file(token, "xlsx")

    return templates.TemplateResponse(
        request=request,
        name="import_csv_summary.html",
        context={
            "filename": filename,
            "deck_id": destination_deck_id,
            "deck_name": destination_name,
            "imported_count": imported_count,
            "skipped_at_commit": len(cards_to_import) - imported_count,
            "analysis": analysis,
        },
    )



@app.get("/decks/{deck_id}", response_class=HTMLResponse)
def read_deck(request: Request, deck_id: int):
    deck = get_deck(deck_id)
    if deck is None:    
        raise HTTPException(status_code=404, detail="Deck not found")
    cards = get_cards(deck_id)
    active_session = get_active_study_session(deck_id)

    return templates.TemplateResponse(
        request=request,
        name="deck.html",
        context={
    "deck": deck,
    "cards": cards,
    "active_session": active_session
}
    )
@app.get("/decks/{deck_id}/export.csv")
def export_deck_csv(deck_id: int):
    deck = get_deck(deck_id)

    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    cards = get_cards(deck_id)
    front_back_pairs = tuple(
        (card[1], card[2])
        for card in cards
    )
    csv_content = build_csv_export(front_back_pairs)

    encoded_filename = quote(f"{deck[1]}.csv", safe="")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="deck-{deck_id}.csv"; '
                f"filename*=UTF-8''{encoded_filename}"
            )
        },
    )

@app.get("/decks/{deck_id}/export.xlsx")
def export_deck_xlsx(deck_id: int):
    deck = get_deck(deck_id)

    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    cards = get_cards(deck_id)
    front_back_pairs = tuple(
        (card[1], card[2])
        for card in cards
    )
    xlsx_content = build_xlsx_export(front_back_pairs)

    encoded_filename = quote(f"{deck[1]}.xlsx", safe="")

    return Response(
        content=xlsx_content,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="deck-{deck_id}.xlsx"; '
                f"filename*=UTF-8''{encoded_filename}"
            )
        },
    )


@app.get("/decks/{deck_id}/edit", response_class=HTMLResponse)
def edit_deck(request: Request, deck_id: int):
    deck = get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    return templates.TemplateResponse(
        request=request,
        name="edit_deck.html",
        context={"deck": deck, "languages": LANGUAGES}
    )

@app.post("/decks/{deck_id}/edit")
def save_deck(
    deck_id: int,
    name: str = Form(...),
    description: str = Form(""),
    front_language: str = Form(...),
    back_language: str = Form(...)
):
    deck = get_deck(deck_id)

    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    update_deck(
        deck_id,
        name,
        description,
        front_language,
        back_language
    )

    return RedirectResponse(
        url=f"/decks/{deck_id}",
        status_code=303
    )

@app.post("/decks")
def add_deck(
    name: str = Form(...),
    description: str = Form(""),
    front_language: str = Form(...),
    back_language: str = Form(...)
):
    create_deck(
        name,
        description,
        front_language,
        back_language
    )

    return RedirectResponse(url="/", status_code=303)

@app.post("/decks/{deck_id}/cards")
def add_card(
    deck_id: int,
    front: str = Form(...),
    back: str = Form(...)
):
    deck = get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    create_card(deck_id, front, back)

    return RedirectResponse(
        url=f"/decks/{deck_id}",
        status_code=303
    )

@app.get("/cards/{card_id}/edit", response_class=HTMLResponse)
def edit_card(request: Request, card_id: int):
    card = get_card(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    return templates.TemplateResponse(
        request=request,
        name="edit_card.html",
        context={"card": card}
    )

@app.post("/cards/{card_id}")
def save_card(
    request: Request,
    card_id: int,
    front: str = Form(...),
    back: str = Form(...)
):
    card = get_card(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    deck_id = card[1]

    update_card(card_id, front, back)

    return RedirectResponse(
        url=f"/decks/{deck_id}",
        status_code=303
    )

@app.post("/cards/{card_id}/delete")
def remove_card(card_id: int):
    card = get_card(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    deck_id = card[1]

    delete_card(card_id)

    return RedirectResponse(
        url=f"/decks/{deck_id}",
        status_code=303
    )

@app.post("/decks/{deck_id}/delete")
def remove_deck(deck_id: int):
    deck = get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    delete_deck(deck_id)

    return RedirectResponse(url="/", status_code=303)

@app.get(
    "/decks/{deck_id}/study/setup",
    response_class=HTMLResponse
)
def setup_study(
    request: Request,
    deck_id: int,
    session_created: bool = False
):
    deck = get_deck(deck_id)

    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    cards = get_cards(deck_id)
    active_session = get_active_study_session(deck_id)

    return templates.TemplateResponse(
        request=request,
        name="study_setup.html",
        context={
            "deck": deck,
            "total_cards": len(cards),
            "active_session": active_session,
            "confirm_replace": False,
            "shuffle": True,
            "reverse": False,
            "session_created": session_created
        }
    )

@app.post("/decks/{deck_id}/study/start")
def start_study(
    request: Request,
    deck_id: int,
    shuffle: bool = Form(False),
    reverse: bool = Form(False),
    replace_active: bool = Form(False)
):
    deck = get_deck(deck_id)

    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    cards = get_cards(deck_id)

    if not cards:
        raise HTTPException(
            status_code=400,
            detail="Cannot start a session with an empty deck"
        )

    try:
        session_id = create_study_session(
            deck_id,
            shuffle=shuffle,
            reverse=reverse,
            replace_active=replace_active
        )
    except ActiveStudySessionExists:
        active_session = get_active_study_session(deck_id)

        return templates.TemplateResponse(
            request=request,
            name="study_setup.html",
            context={
                "deck": deck,
                "total_cards": len(cards),
                "active_session": active_session,
                "confirm_replace": True,
                "shuffle": shuffle,
                "reverse": reverse,
                "session_created": False
            }
        )

    return RedirectResponse(
    url=f"/study/{session_id}",
    status_code=303
)

@app.get("/study/{session_id}", response_class=HTMLResponse)
def study_session(request: Request, session_id: int):
    session_state = get_study_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=404,
            detail="Study session not found"
        )

    deck = get_deck(session_state["deck_id"])

    if deck is None:
        raise HTTPException(
            status_code=404,
            detail="Deck not found"
        )

    card = session_state["current_card"]

    if card is None:
        return templates.TemplateResponse(
            request=request,
            name="study_complete.html",
            context={
                "deck": deck,
                "session": session_state
            }
        )

    if session_state["reverse"]:
        front_text = card[3]
        back_text = card[2]
        front_language = deck[5]
        back_language = deck[4]
    else:
        front_text = card[2]
        back_text = card[3]
        front_language = deck[4]
        back_language = deck[5]

    return templates.TemplateResponse(
        request=request,
        name="study.html",
        context={
            "deck": deck,
            "session": session_state,
            "front_text": front_text,
            "back_text": back_text,
            "front_language": front_language,
            "back_language": back_language
        }
    )

    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    if session_state["reverse"]:
        front_text = card[3]
        back_text = card[2]
        front_language = card[5]
        back_language = card[4]
    else:
        front_text = card[2]
        back_text = card[3]
        front_language = card[4]
        back_language = card[5]

    return templates.TemplateResponse(
        request=request,
        name="study.html",
        context={
            "deck": deck,
            "card": card,
            "session": session_state,
            "front_text": front_text,
            "back_text": back_text,
            "front_language": front_language,
            "back_language": back_language,

        }
    )

@app.post("/study/{session_id}/settings")
def save_study_session_settings(
    session_id: int,
    auto_reveal: bool = Form(False),
    reveal_delay_seconds: int = Form(5),
    auto_speak: str = Form("off"),
    speech_rate: float = Form(1.0)
):
    session_state = get_study_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=404,
            detail="Study session not found"
        )

    if session_state["status"] != "active":
        raise HTTPException(
            status_code=409,
            detail="Study session is not active"
        )

    try:
        update_study_session_settings(
            session_id=session_id,
            auto_reveal=auto_reveal,
            reveal_delay_seconds=reveal_delay_seconds,
            auto_speak=auto_speak,
            speech_rate=speech_rate
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    return RedirectResponse(
        url=f"/study/{session_id}",
        status_code=303
    )


@app.post("/study/{session_id}/rate")
def rate_study_card(
    session_id: int,
    rating: str = Form(...),
    revealed: bool = Form(False)
):
    if rating not in {"again", "good"}:
        raise HTTPException(status_code=400, detail="Invalid rating")

    if not revealed:
        raise HTTPException(
            status_code=400,
            detail="Reveal the answer before rating the card"
        )

    session_state = get_study_session_state(session_id)

    if session_state is None:
        raise HTTPException(status_code=404, detail="Study session not found")

    if session_state["current_card"] is None:
        return RedirectResponse(
            url=f"/decks/{session_state['deck_id']}",
            status_code=303
        )

    rate_current_study_card(session_id, rating)

    return RedirectResponse(
        url=f"/study/{session_id}",
        status_code=303
    )
