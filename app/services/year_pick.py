from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.core_boosters import CORE_BOOSTERS
from app.models import Card, CardPrinting, CollectionProgress, InventoryItem, Player
from app.services.ygoprodeck import ensure_card_image, ensure_collection_cards_synced

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


def rarity_priority(rarity: str | None) -> int:
    """Choose one annual printing per card, favoring the highest available rarity."""
    normalized = (rarity or "").strip().lower()
    if "quarter century" in normalized or "prismatic" in normalized or "starlight" in normalized:
        return 70
    if "ghost" in normalized:
        return 60
    if "ultimate" in normalized:
        return 55
    if "secret" in normalized:
        return 50
    if "ultra" in normalized:
        return 40
    if "super" in normalized:
        return 30
    if normalized == "rare" or normalized.endswith(" rare"):
        return 20
    if "common" in normalized:
        return 10
    return 25


def effective_year_pick_quotas(cards: list[dict]) -> dict[str, int]:
    quotas = {bucket: 0 for bucket in YEAR_PICK_BUCKETS}
    for bucket in {card["rarity_bucket"] for card in cards}:
        quotas[bucket] = YEAR_PICK_QUOTA
    return quotas


def _year_collections(session: Session, year: int) -> list[CollectionProgress]:
    allowed_set_names = {
        item["set_name"]
        for item in CORE_BOOSTERS
        if item.get("year") == year and item.get("set_name") and item.get("api_available", True)
    }
    collections = session.execute(
        select(CollectionProgress)
        .where(CollectionProgress.tcg_date == str(year))
        .order_by(CollectionProgress.position)
    ).scalars().all()
    return [collection for collection in collections if collection.set_name in allowed_set_names]


def _ensure_year_catalog(session: Session, collections: list[CollectionProgress]) -> None:
    errors = []
    for collection in collections:
        result = ensure_collection_cards_synced(session, collection)
        if result["error"]:
            errors.append(collection.set_name)
    if errors:
        raise ValueError(f"Falha ao sincronizar as colecoes do pick anual: {', '.join(errors)}")


def _best_year_cards(session: Session, collections: list[CollectionProgress]) -> list[dict]:
    if not collections:
        return []
    collection_ids = [collection.id for collection in collections]
    rows = session.execute(
        select(CardPrinting, Card, CollectionProgress)
        .join(Card, CardPrinting.card_id == Card.id)
        .join(CollectionProgress, CardPrinting.collection_id == CollectionProgress.id)
        .where(CardPrinting.collection_id.in_(collection_ids))
        .order_by(CardPrinting.card_id, CollectionProgress.position, CardPrinting.set_code)
    ).all()

    best_by_card: dict[int, tuple[CardPrinting, Card, CollectionProgress]] = {}
    for printing, card, collection in rows:
        current = best_by_card.get(card.id)
        if current is None or rarity_priority(printing.set_rarity) > rarity_priority(current[0].set_rarity):
            best_by_card[card.id] = (printing, card, collection)

    bucket_order = {bucket: index for index, bucket in enumerate(YEAR_PICK_BUCKETS)}
    cards = [
        {
            "card_id": card.id,
            "name": card.name,
            "type": card.type,
            "rarity": printing.set_rarity or "Common",
            "rarity_bucket": year_pick_bucket_for_rarity(printing.set_rarity),
            "image_url": ensure_card_image(card, session),
        }
        for printing, card, _collection in best_by_card.values()
    ]
    return sorted(
        cards,
        key=lambda item: (bucket_order.get(item["rarity_bucket"], len(bucket_order)), item["name"]),
    )


def pending_year_pick(session: Session, player_id: int) -> dict:
    player = session.get(Player, player_id)
    if not player:
        raise ValueError("Jogador nao encontrado.")

    claims = normalize_year_pick_claims(player.year_pick_claims)
    quotas = year_pick_quotas()
    if not player.pending_year_pick_year:
        return {"pending": False, "year": None, "claims": claims, "quotas": quotas, "cards": []}

    collections = _year_collections(session, player.pending_year_pick_year)
    _ensure_year_catalog(session, collections)
    cards = _best_year_cards(session, collections)
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
