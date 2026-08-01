from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import STATIC_DIR, ensure_local_dirs
from app.db import get_session, init_db
from app.models import Card, CollectionProgress, InventoryItem, Player
from app.schemas import BossPickRequest, CardRestrictionRead, CardSearchRead, CollectionRead, DeckMutation, DeckRead, InventoryCardRead, PlayerCreate, PlayerRead, RestrictCardRequest, RoundAdvanceRead, ShopBuyRequest, ShopRead, YearPickClaimRequest, YearPickRead
from app.services.deck import add_card_to_deck, build_deck_response, deck_counts_by_card, export_deck_as_ydke, remove_card_from_deck
from app.services.game import advance_round, claim_boss_pick, create_player, delete_player, import_ydk_to_inventory, sell_inventory_card
from app.services.pricing import sell_price_for_rarity
from app.services.restrictions import clear_card_restriction, list_restrictions, restriction_status_map, search_cards_by_name, set_card_limited_or_banned
from app.services.shop import buy_shop_card, get_shop_cards
from app.services.ydk import export_ydke
from app.services.year_pick import pending_year_pick, claim_year_pick_card
from app.services.ygoprodeck import ensure_card_image, sync_collections


ensure_local_dirs()
init_db()

app = FastAPI(title="Yu-Gi-Oh! Mega Draft API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/players", response_model=PlayerRead)
def create_player_route(payload: PlayerCreate, session: Session = Depends(get_session)) -> Player:
    try:
        return create_player(session, payload.name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/players", response_model=list[PlayerRead])
def list_players(session: Session = Depends(get_session)) -> list[Player]:
    return list(session.execute(select(Player).order_by(Player.name)).scalars().all())


@app.get("/players/{player_id}", response_model=PlayerRead)
def get_player(player_id: int, session: Session = Depends(get_session)) -> Player:
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Jogador nao encontrado.")
    return player


@app.delete("/players/{player_id}")
def delete_player_route(player_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        delete_player(session, player_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": True}


@app.post("/players/{player_id}/import-ydk")
async def import_ydk(player_id: int, file: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
    if not file.filename.lower().endswith(".ydk"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .ydk.")
    content = (await file.read()).decode("utf-8", errors="ignore")
    try:
        imported = import_ydk_to_inventory(session, player_id, content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"imported": imported}


@app.get("/players/{player_id}/inventory", response_model=list[InventoryCardRead])
def get_inventory(player_id: int, session: Session = Depends(get_session)) -> list[InventoryCardRead]:
    rows = session.execute(
        select(InventoryItem, Card)
        .join(Card, InventoryItem.card_id == Card.id)
        .where(InventoryItem.player_id == player_id, InventoryItem.quantity > 0)
        .order_by(Card.name)
    ).all()

    used_counts = deck_counts_by_card(session, player_id)
    restrictions = restriction_status_map(session, player_id)
    inventory = []
    for item, card in rows:
        image_url = ensure_card_image(card, session)
        available_quantity = max(item.quantity - used_counts[card.id], 0)
        inventory.append(
            InventoryCardRead(
                inventory_id=item.id,
                card_id=card.id,
                name=card.name,
                type=card.type,
                desc=card.desc,
                race=card.race,
                archetype=card.archetype,
                rarity=item.rarity,
                quantity=item.quantity,
                available_quantity=available_quantity,
                source=item.source,
                sell_price=sell_price_for_rarity(item.rarity),
                restriction_status=restrictions.get(card.id),
                image_url=image_url,
            )
        )
    return inventory


@app.get("/players/{player_id}/card-search", response_model=list[CardSearchRead])
def search_cards(player_id: int, q: str, monster_only: bool = False, session: Session = Depends(get_session)) -> list[CardSearchRead]:
    if not session.get(Player, player_id):
        raise HTTPException(status_code=404, detail="Jogador nao encontrado.")
    cards = search_cards_by_name(session, q, limit=10, monster_only=monster_only)
    return [
        CardSearchRead(
            card_id=card.id,
            name=card.name,
            type=card.type,
            image_url=ensure_card_image(card, session),
        )
        for card in cards
    ]


@app.post("/players/{player_id}/boss-pick", response_model=PlayerRead)
def choose_boss_pick(player_id: int, payload: BossPickRequest, session: Session = Depends(get_session)) -> Player:
    try:
        return claim_boss_pick(session, player_id, payload.card_id, payload.start_year)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/players/{player_id}/restrictions", response_model=list[CardRestrictionRead])
def get_restrictions(player_id: int, session: Session = Depends(get_session)) -> list[dict]:
    if not session.get(Player, player_id):
        raise HTTPException(status_code=404, detail="Jogador nao encontrado.")
    return list_restrictions(session, player_id)


@app.post("/players/{player_id}/restrictions", response_model=list[CardRestrictionRead])
def restrict_card(player_id: int, payload: RestrictCardRequest, session: Session = Depends(get_session)) -> list[dict]:
    try:
        set_card_limited_or_banned(session, player_id, payload.card_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return list_restrictions(session, player_id)


@app.delete("/players/{player_id}/restrictions/{card_id}", response_model=list[CardRestrictionRead])
def clear_restriction(player_id: int, card_id: int, session: Session = Depends(get_session)) -> list[dict]:
    try:
        clear_card_restriction(session, player_id, card_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return list_restrictions(session, player_id)


@app.get("/players/{player_id}/deck", response_model=DeckRead)
def get_deck(player_id: int, session: Session = Depends(get_session)) -> dict:
    if not session.get(Player, player_id):
        raise HTTPException(status_code=404, detail="Jogador nao encontrado.")
    return build_deck_response(session, player_id)


@app.get("/players/{player_id}/deck/export-ydke")
def export_deck(player_id: int, session: Session = Depends(get_session)) -> dict:
    if not session.get(Player, player_id):
        raise HTTPException(status_code=404, detail="Jogador nao encontrado.")
    return {"ydke": export_ydke(export_deck_as_ydke(session, player_id))}


@app.post("/players/{player_id}/deck/cards", response_model=DeckRead)
def add_deck_card(player_id: int, payload: DeckMutation, session: Session = Depends(get_session)) -> dict:
    try:
        add_card_to_deck(session, player_id, payload.card_id, payload.zone)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_deck_response(session, player_id)


@app.delete("/players/{player_id}/deck/cards/{deck_id}", response_model=DeckRead)
def remove_deck_card(player_id: int, deck_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        remove_card_from_deck(session, player_id, deck_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_deck_response(session, player_id)


@app.post("/players/{player_id}/inventory/{inventory_id}/sell")
def sell_card(player_id: int, inventory_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        gold = sell_inventory_card(session, player_id, inventory_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"gold_earned": gold}


@app.post("/players/{player_id}/advance-round", response_model=RoundAdvanceRead)
def advance_round_route(player_id: int, session: Session = Depends(get_session)) -> RoundAdvanceRead:
    try:
        player, collection, gold_gain = advance_round(session, player_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RoundAdvanceRead(
        player=PlayerRead.model_validate(player),
        collection_name=collection.set_name if collection else None,
        gold_gain=gold_gain,
    )


@app.get("/players/{player_id}/year-pick", response_model=YearPickRead)
def get_year_pick(player_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        return pending_year_pick(session, player_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/players/{player_id}/year-pick/claim", response_model=YearPickRead)
def claim_year_pick(player_id: int, payload: YearPickClaimRequest, session: Session = Depends(get_session)) -> dict:
    try:
        return claim_year_pick_card(session, player_id, payload.card_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/players/{player_id}/shop", response_model=ShopRead)
def get_shop(player_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        return get_shop_cards(session, player_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/players/{player_id}/shop/buy")
def buy_from_shop(player_id: int, payload: ShopBuyRequest, session: Session = Depends(get_session)) -> dict:
    try:
        spent = buy_shop_card(session, player_id, payload.card_id, payload.rarity)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    player = session.get(Player, player_id)
    return {"gold_spent": spent, "player_gold": player.gold if player else 0}


@app.post("/collections/sync")
def sync_collections_route(session: Session = Depends(get_session)) -> dict:
    try:
        count = sync_collections(session)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"synced": count}


@app.get("/collections", response_model=list[CollectionRead])
def list_collections(session: Session = Depends(get_session)) -> list[CollectionProgress]:
    return list(session.execute(select(CollectionProgress).order_by(CollectionProgress.position)).scalars().all())
