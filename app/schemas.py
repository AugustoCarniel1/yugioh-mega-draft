from pydantic import BaseModel, ConfigDict, field_validator


class PlayerCreate(BaseModel):
    name: str


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gold: float
    current_collection_index: int
    boss_pick_pending: bool = False
    pending_year_pick_year: int | None = None
    active_deck_id: int | None = None

    @field_validator("pending_year_pick_year", mode="before")
    @classmethod
    def normalize_pending_year_pick_year(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip().lower()
            if cleaned in {"", "null", "none"}:
                return None
            return int(cleaned)
        return int(value)


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
    source: str = "starter_deck"
    sell_price: float
    restriction_status: str | None = None
    image_url: str | None = None


class DeckMutation(BaseModel):
    card_id: int
    zone: str


class SavedDeckCreate(BaseModel):
    name: str
    copy_active_deck: bool = False


class SavedDeckRename(BaseModel):
    name: str


class SavedDeckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    player_id: int
    name: str


class DeckListRead(BaseModel):
    active_deck_id: int | None = None
    decks: list[SavedDeckRead]


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
    active_deck_id: int | None = None
    active_deck_name: str | None = None
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
    gold_gain: int = 0


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


class BossPickRequest(BaseModel):
    card_id: int
    start_year: int


class YearPickCardRead(BaseModel):
    card_id: int
    name: str
    type: str | None = None
    rarity: str
    rarity_bucket: str
    image_url: str | None = None


class YearPickRead(BaseModel):
    pending: bool
    year: int | None = None
    claims: dict[str, int]
    quotas: dict[str, int]
    cards: list[YearPickCardRead]


class YearPickClaimRequest(BaseModel):
    card_id: int
