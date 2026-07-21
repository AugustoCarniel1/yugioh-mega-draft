from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Card, CollectionProgress, InventoryItem, Player
from app.services.pricing import buy_price_for_rarity
from app.services.ygoprodeck import ensure_card_image, fetch_cardset_payload


RARITY_ORDER = {
    "Common": 0,
    "Rare": 1,
    "Super Rare": 2,
    "Ultra Rare": 3,
    "Secret Rare": 4,
}


def _card_from_payload(payload: dict) -> Card:
    return Card(
        id=payload["id"],
        name=payload["name"],
        type=payload.get("type"),
        desc=payload.get("desc"),
        race=payload.get("race"),
        archetype=payload.get("archetype"),
        card_images=payload.get("card_images", []),
        card_sets=payload.get("card_sets", []),
    )


def _matching_set(card_payload: dict, collection_name: str) -> dict:
    for card_set in card_payload.get("card_sets", []):
        if card_set.get("set_name") == collection_name:
            return card_set
    return {}


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

    payloads = fetch_cardset_payload(collection.set_name)
    cards = []
    for payload in payloads:
        card = session.get(Card, payload["id"])
        if not card:
            card = _card_from_payload(payload)
            session.add(card)
            session.commit()
            session.refresh(card)

        set_info = _matching_set(payload, collection.set_name)
        rarity = set_info.get("set_rarity") or "Common"
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
                "set_code": set_info.get("set_code"),
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
