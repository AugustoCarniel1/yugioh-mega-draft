from pathlib import Path
from urllib.parse import urlparse

import requests
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import IMAGE_CACHE_DIR, YGOPRODECK_BASE_URL
from app.data.core_boosters import CORE_BOOSTERS
from app.models import Card, CollectionProgress


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
    card = _card_from_payload(payload)
    session.add(card)
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
    session.execute(delete(CollectionProgress))
    count = 0
    for item in CORE_BOOSTERS:
        set_name = item["set_name"]
        if not set_name:
            continue
        collection = session.execute(
            select(CollectionProgress).where(CollectionProgress.set_name == set_name)
        ).scalar_one_or_none()
        if not collection:
            collection = CollectionProgress(set_name=set_name, position=item["position"])
        collection.set_code = item["set_code"]
        collection.tcg_date = str(item["year"])
        collection.card_count = None
        collection.position = item["position"]
        session.add(collection)
        count += 1
    session.commit()
    return count
