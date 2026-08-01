import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.core_boosters import CORE_BOOSTERS
from app.models import Card, CollectionProgress, InventoryItem, Player
from app.services.ygoprodeck import ensure_card_image, fetch_cardset_payload

BASE_YEAR = 2002
BASE_ROUND_GOLD = 10
YEAR_PICK_QUOTA = 2
YEAR_PICK_BUCKETS = ("common", "rare", "super", "ultra", "secret", "prismatic", "other")
YEAR_PICK_LABELS = {
    "common": "Common",
    "rare": "Rare",
    "super": "Super",
    "ultra": "Ultra",
    "secret": "Secret",
    "prismatic": "Prismatic",
    "other": "Outras",
}


def collection_year(collection: CollectionProgress | None) -> int | None:
    if not collection or not collection.tcg_date:
        return None
    try:
        return int(str(collection.tcg_date))
    except ValueError:
        return None


def get_collection_by_position(session: Session, position: int) -> CollectionProgress | None:
    return session.execute(
        select(CollectionProgress).where(CollectionProgress.position == position)
    ).scalar_one_or_none()


def round_gold_for_player(session: Session, player: Player) -> int:
    current_collection = get_collection_by_position(session, player.current_collection_index)
    year = collection_year(current_collection)
    if year is None:
        return BASE_ROUND_GOLD
    return BASE_ROUND_GOLD + max(year - BASE_YEAR, 0)


def empty_year_pick_state() -> dict:
    return {bucket: 0 for bucket in YEAR_PICK_BUCKETS}


def normalize_year_pick_claims(raw_claims: dict | None) -> dict[str, int]:
    claims = empty_year_pick_state()
    if not isinstance(raw_claims, dict):
        return claims
    for bucket in YEAR_PICK_BUCKETS:
        try:
            claims[bucket] = max(0, int(raw_claims.get(bucket, 0)))
        except (TypeError, ValueError):
            claims[bucket] = 0
    return claims


def year_pick_quotas() -> dict[str, int]:
    return {bucket: YEAR_PICK_QUOTA for bucket in YEAR_PICK_BUCKETS}


def year_pick_bucket_for_rarity(rarity: str | None) -> str:
    normalized = (rarity or "").strip().lower()
    if "quarter century" in normalized or "prismatic" in normalized:
        return "prismatic"
    if normalized == "common":
        return "common"
    if normalized == "rare":
        return "rare"
    if "super rare" in normalized and "ultra" not in normalized and "secret" not in normalized:
        return "super"
    if "ultra rare" in normalized:
        return "ultra"
    if normalized == "secret rare":
        return "secret"
    return "other"


def effective_year_pick_quotas(cards: list[dict]) -> dict[str, int]:
    quotas = {bucket: 0 for bucket in YEAR_PICK_BUCKETS}
    present_buckets = {card["rarity_bucket"] for card in cards}
    for bucket in present_buckets:
        quotas[bucket] = YEAR_PICK_QUOTA
    return quotas


def pending_year_pick(session: Session, player_id: int) -> dict:
    player = session.get(Player, player_id)
    if not player:
        raise ValueError("Jogador nao encontrado.")

    claims = normalize_year_pick_claims(player.year_pick_claims)
    quotas = year_pick_quotas()
    if not player.pending_year_pick_year:
        return {"pending": False, "year": None, "claims": claims, "quotas": quotas, "cards": []}

    allowed_set_names = {
        item["set_name"]
        for item in CORE_BOOSTERS
        if item.get("year") == player.pending_year_pick_year and item.get("set_name")
    }
    collections = session.execute(
        select(CollectionProgress)
        .where(CollectionProgress.tcg_date == str(player.pending_year_pick_year))
        .order_by(CollectionProgress.position)
    ).scalars().all()
    collections = [collection for collection in collections if collection.set_name in allowed_set_names]

    cards_by_id: dict[int, dict] = {}
    for collection in collections:
        try:
            payloads = fetch_cardset_payload(collection.set_name)
        except requests.RequestException:
            continue

        for payload in payloads:
            card = session.get(Card, payload["id"])
            if not card:
                card = Card(
                    id=payload["id"],
                    name=payload["name"],
                    type=payload.get("type"),
                    desc=payload.get("desc"),
                    race=payload.get("race"),
                    archetype=payload.get("archetype"),
                    card_images=payload.get("card_images", []),
                    card_sets=payload.get("card_sets", []),
                )
                session.add(card)
                session.commit()
                session.refresh(card)

            if card.id in cards_by_id:
                continue

            rarity = "Common"
            for card_set in payload.get("card_sets", []):
                if card_set.get("set_name") == collection.set_name:
                    rarity = card_set.get("set_rarity") or "Common"
                    break

            bucket = year_pick_bucket_for_rarity(rarity)
            cards_by_id[card.id] = {
                "card_id": card.id,
                "name": card.name,
                "type": card.type,
                "rarity": rarity,
                "rarity_bucket": bucket,
                "image_url": ensure_card_image(card, session),
            }

    bucket_order = {bucket: index for index, bucket in enumerate(YEAR_PICK_BUCKETS)}
    cards = sorted(
        cards_by_id.values(),
        key=lambda item: (
            bucket_order.get(item["rarity_bucket"], len(bucket_order)),
            item["name"],
        ),
    )
    quotas = effective_year_pick_quotas(cards)
    if all(claims[bucket] >= quotas[bucket] for bucket in YEAR_PICK_BUCKETS):
        player.pending_year_pick_year = None
        player.year_pick_claims = empty_year_pick_state()
        session.add(player)
        session.commit()
        return {"pending": False, "year": None, "claims": empty_year_pick_state(), "quotas": quotas, "cards": []}
    return {
        "pending": True,
        "year": player.pending_year_pick_year,
        "claims": claims,
        "quotas": quotas,
        "cards": cards,
    }


def claim_year_pick_card(session: Session, player_id: int, card_id: int) -> dict:
    player = session.get(Player, player_id)
    if not player:
        raise ValueError("Jogador nao encontrado.")
    if not player.pending_year_pick_year:
        raise ValueError("Nao ha pick anual pendente.")

    state = pending_year_pick(session, player_id)
    if not state["pending"]:
        return state
    card = next((item for item in state["cards"] if item["card_id"] == card_id), None)
    if not card:
        raise ValueError("Carta indisponivel para este pick anual.")

    bucket = card["rarity_bucket"]
    claims = normalize_year_pick_claims(player.year_pick_claims)
    if claims[bucket] >= state["quotas"].get(bucket, YEAR_PICK_QUOTA):
        raise ValueError(f"Limite da raridade {YEAR_PICK_LABELS[bucket]} ja atingido.")

    item = session.execute(
        select(InventoryItem).where(
            InventoryItem.player_id == player_id,
            InventoryItem.card_id == card_id,
        )
    ).scalar_one_or_none()
    if item:
        item.quantity += 1
        if item.rarity == "Common" and card["rarity"] != "Common":
            item.rarity = card["rarity"]
    else:
        item = InventoryItem(
            player_id=player_id,
            card_id=card_id,
            quantity=1,
            rarity=card["rarity"],
            source="year_pick",
        )

    claims[bucket] += 1
    player.year_pick_claims = claims
    if all(claims[current_bucket] >= state["quotas"].get(current_bucket, 0) for current_bucket in YEAR_PICK_BUCKETS):
        player.pending_year_pick_year = None
        player.year_pick_claims = empty_year_pick_state()

    session.add(player)
    session.add(item)
    session.commit()
    return pending_year_pick(session, player_id)
