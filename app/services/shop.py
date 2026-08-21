from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Card, CardPrinting, CollectionProgress, InventoryItem, Player
from app.services.pricing import buy_price_for_rarity
from app.services.ygoprodeck import ensure_card_image, ensure_collection_cards_synced


RARITY_ORDER = {
    "Common": 0,
    "Rare": 1,
    "Super Rare": 2,
    "Ultra Rare": 3,
    "Secret Rare": 4,
}


def get_shop_cards(session: Session, player_id: int) -> dict:
    player = session.get(Player, player_id)
    if not player:
        raise ValueError("Jogador nao encontrado.")
    if player.current_collection_index < 0:
        return {"collection_name": None, "collection_position": None, "cards": []}

    collection = session.execute(
        select(CollectionProgress).where(CollectionProgress.position == player.current_collection_index)
    ).scalar_one_or_none()
    if not collection:
        return {"collection_name": None, "collection_position": None, "cards": []}

    sync_result = ensure_collection_cards_synced(session, collection)
    if sync_result["error"]:
        raise ValueError(f"Nao foi possivel sincronizar {collection.set_name}: {sync_result['error']}")

    rows = session.execute(
        select(CardPrinting, Card)
        .join(Card, CardPrinting.card_id == Card.id)
        .where(CardPrinting.collection_id == collection.id)
        .order_by(Card.name, CardPrinting.set_code)
    ).all()
    cards = []
    seen_cards: set[int] = set()
    for printing, card in rows:
        # Alternate print codes still represent one purchasable card in this collection.
        if card.id in seen_cards:
            continue
        seen_cards.add(card.id)
        rarity = printing.set_rarity or "Common"
        cards.append(
            {
                "card_id": card.id,
                "name": card.name,
                "type": card.type,
                "desc": card.desc,
                "race": card.race,
                "archetype": card.archetype,
                "rarity": rarity,
                "price": buy_price_for_rarity(rarity),
                "set_code": printing.set_code or None,
                "image_url": ensure_card_image(card, session),
            }
        )

    cards.sort(key=lambda item: (RARITY_ORDER.get(item["rarity"], 5), item["name"]))
    return {
        "collection_name": collection.set_name,
        "collection_position": collection.position,
        "cards": cards,
    }


def buy_shop_card(session: Session, player_id: int, card_id: int, rarity: str) -> int:
    player = session.get(Player, player_id)
    card = session.get(Card, card_id)
    if not player or not card:
        raise ValueError("Jogador ou carta nao encontrado.")

    price = buy_price_for_rarity(rarity)
    if player.gold < price:
        raise ValueError("Gold insuficiente.")

    item = session.execute(
        select(InventoryItem).where(
            InventoryItem.player_id == player_id,
            InventoryItem.card_id == card_id,
        )
    ).scalar_one_or_none()
    if item:
        item.quantity += 1
        if item.rarity == "Common" and rarity != "Common":
            item.rarity = rarity
    else:
        item = InventoryItem(
            player_id=player_id,
            card_id=card_id,
            quantity=1,
            rarity=rarity,
            source="shop",
        )

    player.gold -= price
    session.add(player)
    session.add(item)
    session.commit()
    return price
