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

)

app = FastAPI()
initialize_database()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    decks = get_decks()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"decks": decks}
    )

@app.get("/decks/{deck_id}", response_class=HTMLResponse)
def read_deck(request: Request, deck_id: int):
    deck = get_deck(deck_id)
    if deck is None:    
        raise HTTPException(status_code=404, detail="Deck not found")
    cards = get_cards(deck_id)     

    return templates.TemplateResponse(
        request=request,
        name="deck.html",
        context={"deck": deck, "cards": cards}
    )

@app.get("/decks/{deck_id}/edit", response_class=HTMLResponse)
def edit_deck(request: Request, deck_id: int):
    deck = get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    return templates.TemplateResponse(
        request=request,
        name="edit_deck.html",
        context={"deck": deck}
    )

@app.post("/decks/{deck_id}/edit")
def save_deck(
    deck_id: int,
    name: str = Form(...),
    description: str = Form("")
):
    deck = get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    update_deck(deck_id, name, description)

    return RedirectResponse(
        url=f"/decks/{deck_id}",
        status_code=303
    )

@app.post("/decks")
def add_deck(
    name: str = Form(...),
    description: str = Form("")
):
    create_deck(name, description)

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