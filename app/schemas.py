from pydantic import BaseModel, ConfigDict


class PlayerCreate(BaseModel):
    name: str


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gold: float
    current_collection_index: int


class InventoryCardRead(BaseModel):
    inventory_id: int
    card_id: int
    name: str
    type: str | None = None
    desc: str | None = None
    race: str | None = None
    archetype: str | None = None
    rarity: str
    quantity: int
    available_quantity: int
    sell_price: float
    restriction_status: str | None = None
    image_url: str | None = None


class DeckMutation(BaseModel):
    card_id: int
    zone: str


class DeckCardRead(BaseModel):
    deck_id: int
    card_id: int
    name: str
    type: str | None = None
    desc: str | None = None
    race: str | None = None
    archetype: str | None = None
    rarity: str
    quantity: int
    category: str
    restriction_status: str | None = None
    image_url: str | None = None


class CardSearchRead(BaseModel):
    card_id: int
    name: str
    type: str | None = None
    image_url: str | None = None


class CardRestrictionRead(BaseModel):
    card_id: int
    name: str
    type: str | None = None
    status: str
    image_url: str | None = None


class RestrictCardRequest(BaseModel):
    card_id: int


class DeckRead(BaseModel):
    main: list[DeckCardRead]
    extra: list[DeckCardRead]
    side: list[DeckCardRead]
    main_count: int
    extra_count: int
    side_count: int
    is_main_valid: bool
    is_extra_valid: bool
    is_side_valid: bool


class RoundAdvanceRead(BaseModel):
    player: PlayerRead
    collection_name: str | None = None


class CollectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    set_name: str
    set_code: str | None = None
    tcg_date: str | None = None
    card_count: int | None = None
    position: int


class ShopCardRead(BaseModel):
    card_id: int
    name: str
    type: str | None = None
    desc: str | None = None
    race: str | None = None
    archetype: str | None = None
    rarity: str
    price: int
    set_code: str | None = None
    image_url: str | None = None


class ShopRead(BaseModel):
    collection_name: str | None = None
    collection_position: int | None = None
    cards: list[ShopCardRead]


class ShopBuyRequest(BaseModel):
    card_id: int
    rarity: str
