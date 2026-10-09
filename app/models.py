from dataclasses import dataclass

@dataclass
class Deck:
    id: int
    name: str
    description: str
    created_at: str

@dataclass
class Card:
    id: int
    deck_id: int
    front: str
    back: str
    created_at: str

