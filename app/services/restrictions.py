from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Card, CardRestriction, DeckCard, Player
from app.services.ygoprodeck import ensure_card_image, get_or_fetch_card


LIMITED = "limited"
BANNED = "banned"
MAX_THREE_COPY_EXCEPTIONS = 2


def search_cards_by_name(session: Session, query: str, limit: int = 20) -> list[Card]:
    query = query.strip()
    if not query:
        return []

    cards_by_id = {
        card.id: card
        for card in session.execute(
            select(Card)
            .where(Card.name.ilike(f"%{query}%"))
            .order_by(Card.name)
            .limit(limit)
        ).scalars()
    }

    try:
        payloads = fetch_card_payloads_by_name(query, limit=limit)
    except Exception:
        payloads = []

    for payload in payloads:
        if payload["id"] not in cards_by_id:
            cards_by_id[payload["id"]] = get_or_fetch_card(session, payload["id"])
        if len(cards_by_id) >= limit:
            break

    return sorted(cards_by_id.values(), key=lambda card: card.name)[:limit]


def local_cards_by_name(session: Session, query: str, limit: int = 20) -> list[Card]:
    return list(
        session.execute(
            select(Card)
            .where(Card.name.ilike(f"%{query}%"))
            .order_by(Card.name)
            .limit(limit)
        ).scalars()
    )


def fetch_card_payloads_by_name(name: str, limit: int = 10) -> list[dict]:
    from app.core.config import YGOPRODECK_BASE_URL
    import requests

    response = requests.get(f"{YGOPRODECK_BASE_URL}/cardinfo.php", params={"fname": name}, timeout=20)
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data:
        raise ValueError("Carta nao encontrada.")
    return data[:limit]


def restriction_status_map(session: Session, player_id: int) -> dict[int, str]:
    rows = session.execute(
        select(CardRestriction).where(CardRestriction.player_id == player_id)
    ).scalars()
    return {row.card_id: row.status for row in rows}


def list_restrictions(session: Session, player_id: int) -> list[dict]:
    rows = session.execute(
        select(CardRestriction, Card)
        .join(Card, CardRestriction.card_id == Card.id)
        .where(CardRestriction.player_id == player_id)
        .order_by(CardRestriction.status, Card.name)
    ).all()
    return [
        {
            "card_id": card.id,
            "name": card.name,
            "type": card.type,
            "status": restriction.status,
            "image_url": ensure_card_image(card, session),
        }
        for restriction, card in rows
    ]


def set_card_limited_or_banned(session: Session, player_id: int, card_id: int) -> str:
    if not session.get(Player, player_id):
        raise ValueError("Jogador nao encontrado.")
    if not session.get(Card, card_id):
        get_or_fetch_card(session, card_id)

    restriction = session.execute(
        select(CardRestriction).where(
            CardRestriction.player_id == player_id,
            CardRestriction.card_id == card_id,
        )
    ).scalar_one_or_none()
    if not restriction:
        restriction = CardRestriction(player_id=player_id, card_id=card_id, status=LIMITED)
    elif restriction.status == LIMITED:
        restriction.status = BANNED
    else:
        restriction.status = BANNED

    session.add(restriction)
    session.commit()
    trim_deck_to_allowed_copies(session, player_id, card_id)
    return restriction.status


def clear_card_restriction(session: Session, player_id: int, card_id: int) -> None:
    restriction = session.execute(
        select(CardRestriction).where(
            CardRestriction.player_id == player_id,
            CardRestriction.card_id == card_id,
        )
    ).scalar_one_or_none()
    if restriction:
        session.delete(restriction)
        session.commit()


def three_copy_exception_count(session: Session, player_id: int) -> int:
    rows = session.execute(
        select(DeckCard.card_id)
        .where(DeckCard.player_id == player_id)
        .group_by(DeckCard.card_id)
        .having(func.sum(DeckCard.quantity) >= 3)
    ).all()
    return len(rows)


def allowed_copies_for_card(session: Session, player_id: int, card_id: int) -> int:
    status = restriction_status_map(session, player_id).get(card_id)
    if status == BANNED:
        return 0
    if status == LIMITED:
        return 1
    return 3


def can_add_copy(session: Session, player_id: int, card_id: int, current_copies: int) -> tuple[bool, str]:
    status = restriction_status_map(session, player_id).get(card_id)
    if status == BANNED:
        return False, "Carta banida."
    if status == LIMITED and current_copies >= 1:
        return False, "Carta limitada: maximo de 1 copia."
    if current_copies >= 3:
        return False, "Maximo de 3 copias."
    if current_copies >= 2:
        exception_cards = session.execute(
            select(DeckCard.card_id)
            .where(DeckCard.player_id == player_id)
            .group_by(DeckCard.card_id)
            .having(func.sum(DeckCard.quantity) >= 3)
        ).scalars().all()
        if card_id not in exception_cards and len(exception_cards) >= MAX_THREE_COPY_EXCEPTIONS:
            return False, "Apenas 2 cartas podem ter 3 copias no deck."
    return True, ""


def trim_deck_to_allowed_copies(session: Session, player_id: int, card_id: int) -> None:
    allowed = allowed_copies_for_card(session, player_id, card_id)
    rows = list(
        session.execute(
            select(DeckCard)
            .where(DeckCard.player_id == player_id, DeckCard.card_id == card_id)
            .order_by(DeckCard.zone)
        ).scalars()
    )
    remaining = allowed
    for row in rows:
        if remaining <= 0:
            session.delete(row)
            continue
        if row.quantity > remaining:
            row.quantity = remaining
            session.add(row)
        remaining -= row.quantity
    session.commit()
