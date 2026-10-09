from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    decks = get_decks()

    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={"decks": decks, "languages": LANGUAGES}
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
    else:
        front_text = card[2]
        back_text = card[3]

    return templates.TemplateResponse(
        request=request,
        name="study.html",
        context={
            "deck": deck,
            "session": session_state,
            "front_text": front_text,
            "back_text": back_text
        }
    )

    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    if session_state["reverse"]:
        front_text = card[3]
        back_text = card[2]
    else:
        front_text = card[2]
        back_text = card[3]

    return templates.TemplateResponse(
        request=request,
        name="study.html",
        context={
            "deck": deck,
            "session": session_state,
            "front_text": front_text,
            "back_text": back_text
        }
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