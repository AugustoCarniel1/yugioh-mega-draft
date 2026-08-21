from datetime import datetime
from pathlib import Path
import time
from urllib.parse import urlparse

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import IMAGE_CACHE_DIR, YGOPRODECK_BASE_URL
from app.data.core_boosters import CORE_BOOSTERS
from app.models import Card, CardPrinting, CollectionProgress


# The public API allows 20 requests/second. Keep historical imports below that limit.
CATALOG_REQUEST_INTERVAL_SECONDS = 0.08
CATALOG_UNAVAILABLE_SET_NAMES = {
    item["set_name"]
    for item in CORE_BOOSTERS
    if item.get("set_name") and not item.get("api_available", True)
}


def _card_from_payload(payload: dict) -> Card:
    return Card(
        id=payload["id"],
        name=payload["name"],
        type=payload.get("type"),
        frame_type=payload.get("frameType"),
        desc=payload.get("desc"),
        race=payload.get("race"),
        archetype=payload.get("archetype"),
        attribute=payload.get("attribute"),
        atk=_optional_int(payload.get("atk")),
        defense=_optional_int(payload.get("def")),
        level=_optional_int(payload.get("level")),
        linkval=_optional_int(payload.get("linkval")),
        scale=_optional_int(payload.get("scale")),
        card_images=payload.get("card_images", []),
        card_sets=payload.get("card_sets", []),
    )


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def save_card_payload(session: Session, payload: dict) -> Card:
    """Insert or refresh one card's searchable data without committing the session."""
    card = session.get(Card, payload["id"])
    if not card:
        card = _card_from_payload(payload)
        session.add(card)
        return card

    card.name = payload["name"]
    card.type = payload.get("type")
    card.frame_type = payload.get("frameType")
    card.desc = payload.get("desc")
    card.race = payload.get("race")
    card.archetype = payload.get("archetype")
    card.attribute = payload.get("attribute")
    card.atk = _optional_int(payload.get("atk"))
    card.defense = _optional_int(payload.get("def"))
    card.level = _optional_int(payload.get("level"))
    card.linkval = _optional_int(payload.get("linkval"))
    card.scale = _optional_int(payload.get("scale"))
    card.card_images = payload.get("card_images", [])
    card.card_sets = payload.get("card_sets", [])
    session.add(card)
    return card


def _matching_set_entries(payload: dict, set_name: str) -> list[dict]:
    return [
        entry for entry in payload.get("card_sets", [])
        if entry.get("set_name") == set_name
    ]


def save_collection_payloads(session: Session, collection: CollectionProgress, payloads: list[dict]) -> int:
    """Persist cards once and one row per physical set printing for this collection."""
    existing_printings = {
        (printing.card_id, printing.set_code, printing.set_rarity, printing.set_rarity_code)
        for printing in session.execute(
            select(CardPrinting).where(CardPrinting.collection_id == collection.id)
        ).scalars()
    }
    printings_saved = 0
    for payload in payloads:
        card = save_card_payload(session, payload)
        for set_info in _matching_set_entries(payload, collection.set_name):
            identity = (
                card.id,
                set_info.get("set_code") or "",
                set_info.get("set_rarity") or "Common",
                set_info.get("set_rarity_code") or "",
            )
            if identity in existing_printings:
                continue
            session.add(
                CardPrinting(
                    card_id=card.id,
                    collection_id=collection.id,
                    set_code=identity[1],
                    set_rarity=identity[2],
                    set_rarity_code=identity[3],
                    set_price=_optional_float(set_info.get("set_price")),
                )
            )
            existing_printings.add(identity)
            printings_saved += 1
    collection.card_count = len(payloads)
    collection.cards_synced_at = datetime.utcnow()
    collection.cards_sync_error = None
    session.add(collection)
    return printings_saved


def fetch_card_payload(card_id: int) -> dict:
    response = requests.get(f"{YGOPRODECK_BASE_URL}/cardinfo.php", params={"id": card_id}, timeout=20)
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data:
        raise ValueError(f"Carta {card_id} nao encontrada na YGOProDeck API.")
    return data[0]


def fetch_cardset_payload(cardset_name: str) -> list[dict]:
    response = requests.get(
        f"{YGOPRODECK_BASE_URL}/cardinfo.php",
        params={"cardset": cardset_name},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def get_or_fetch_card(session: Session, card_id: int) -> Card:
    card = session.get(Card, card_id)
    if card:
        return card

    payload = fetch_card_payload(card_id)
    card = save_card_payload(session, payload)
    session.commit()
    session.refresh(card)
    return card


def best_card_rarity(card: Card) -> str:
    if not card.card_sets:
        return "Common"
    rarities = [card_set.get("set_rarity") for card_set in card.card_sets if card_set.get("set_rarity")]
    return rarities[0] if rarities else "Common"


def ensure_card_image(card: Card, session: Session) -> str | None:
    image_path = IMAGE_CACHE_DIR / f"{card.id}.jpg"
    if image_path.exists():
        relative_path = f"/static/images/{card.id}.jpg"
        if card.cached_image_path != relative_path:
            card.cached_image_path = relative_path
            session.add(card)
            session.commit()
        return relative_path

    image_url = None
    if card.card_images:
        image_url = card.card_images[0].get("image_url") or card.card_images[0].get("image_url_cropped")
    if not image_url:
        return None

    response = requests.get(image_url, timeout=30)
    response.raise_for_status()

    parsed = urlparse(image_url)
    suffix = Path(parsed.path).suffix or ".jpg"
    if suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    final_path = IMAGE_CACHE_DIR / f"{card.id}{suffix}"
    final_path.write_bytes(response.content)
    if final_path.name != f"{card.id}.jpg":
        image_path.write_bytes(response.content)

    card.cached_image_path = f"/static/images/{card.id}.jpg"
    session.add(card)
    session.commit()
    return card.cached_image_path


def sync_collections(session: Session) -> int:
    count = 0
    for item in CORE_BOOSTERS:
        set_name = item["set_name"]
        if not set_name:
            continue
        collection = session.execute(
            select(CollectionProgress).where(CollectionProgress.set_name == set_name)
        ).scalar_one_or_none()
        if not collection:
            # Correct renamed API sets in place so an existing run keeps its position.
            collection = session.execute(
                select(CollectionProgress).where(CollectionProgress.position == item["position"])
            ).scalar_one_or_none()
        if not collection:
            collection = CollectionProgress(set_name=set_name, position=item["position"])
        elif collection.set_name != set_name:
            collection.set_name = set_name
            collection.cards_synced_at = None
            collection.cards_sync_error = None
        collection.set_code = item["set_code"]
        collection.tcg_date = str(item["year"])
        collection.card_count = None
        collection.position = item["position"]
        if not item.get("api_available", True):
            # Keep future sets in progression without retrying an API endpoint that does not have them yet.
            collection.cards_synced_at = None
            collection.cards_sync_error = None
        session.add(collection)
        count += 1
    session.commit()
    return count


def sync_collection_cards(session: Session, collection: CollectionProgress) -> dict:
    """Fetch and store one configured collection. Errors are persisted for safe retries."""
    try:
        payloads = fetch_cardset_payload(collection.set_name)
        printings_saved = save_collection_payloads(session, collection, payloads)
        session.commit()
        return {
            "set_name": collection.set_name,
            "cards": len(payloads),
            "printings": printings_saved,
            "error": None,
        }
    except Exception as exc:
        session.rollback()
        failed_collection = session.get(CollectionProgress, collection.id)
        if failed_collection:
            failed_collection.cards_sync_error = str(exc)[:500]
            session.add(failed_collection)
            session.commit()
        return {"set_name": collection.set_name, "cards": 0, "printings": 0, "error": str(exc)}


def ensure_collection_cards_synced(session: Session, collection: CollectionProgress) -> dict:
    if collection.cards_synced_at:
        return {"set_name": collection.set_name, "cards": collection.card_count or 0, "printings": 0, "error": None}
    return sync_collection_cards(session, collection)


def sync_card_catalog(session: Session, retry_failed: bool = False) -> dict:
    """Import all configured collections, resuming safely from prior completed sets."""
    collections = list(
        session.execute(select(CollectionProgress).order_by(CollectionProgress.position)).scalars()
    )
    pending = [
        collection for collection in collections
        if collection.set_name not in CATALOG_UNAVAILABLE_SET_NAMES
        and collection.cards_synced_at is None
        and (retry_failed or not collection.cards_sync_error)
    ]
    synced = 0
    cards = 0
    printings = 0
    errors: list[dict[str, str]] = []
    for index, collection in enumerate(pending):
        result = sync_collection_cards(session, collection)
        if result["error"]:
            errors.append({"set_name": collection.set_name, "error": result["error"]})
        else:
            synced += 1
            cards += result["cards"]
            printings += result["printings"]
        if index < len(pending) - 1:
            time.sleep(CATALOG_REQUEST_INTERVAL_SECONDS)
    return {
        "synced_collections": synced,
        "cards": cards,
        "printings": printings,
        "remaining_collections": len(pending) - synced - len(errors),
        "errors": errors,
    }


def catalog_sync_status(session: Session) -> dict:
    collections = list(session.execute(select(CollectionProgress)).scalars())
    synced = sum(1 for collection in collections if collection.cards_synced_at is not None)
    failed = sum(1 for collection in collections if collection.cards_sync_error)
    unavailable = sum(1 for collection in collections if collection.set_name in CATALOG_UNAVAILABLE_SET_NAMES)
    card_count = session.scalar(select(func.count(Card.id))) or 0
    printing_count = session.scalar(select(func.count(CardPrinting.id))) or 0
    return {
        "total_collections": len(collections),
        "synced_collections": synced,
        "pending_collections": len(collections) - synced - unavailable,
        "failed_collections": failed,
        "unavailable_collections": unavailable,
        "cards": card_count,
        "printings": printing_count,
    }
