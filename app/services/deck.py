from collections import Counter

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Card, DeckCard, InventoryItem, Player
from app.services.ydk import YdkDeck
from app.services.restrictions import can_add_copy, restriction_status_map
from app.services.ygoprodeck import ensure_card_image


MAIN_MIN = 40
MAIN_MAX = 60
EXTRA_MAX = 15
SIDE_MAX = 15
VALID_ZONES = {"main", "extra", "side"}


def card_category(card_type: str | None) -> str:
    card_type = card_type or ""
    if "Spell" in card_type:
        return "spell"
    if "Trap" in card_type:
        return "trap"
    return "monster"


def is_extra_deck_card(card_type: str | None) -> bool:
    card_type = card_type or ""
    return any(extra_type in card_type for extra_type in ("Fusion", "Synchro", "Xyz", "Link"))


def zone_limit(zone: str) -> int:
    if zone == "main":
        return MAIN_MAX
    if zone == "extra":
        return EXTRA_MAX
    if zone == "side":
        return SIDE_MAX
    raise ValueError("Zona de deck invalida.")


def normalize_zone(zone: str) -> str:
    zone = zone.strip().lower()
    if zone not in VALID_ZONES:
        raise ValueError("Zona de deck invalida.")
    return zone


def deck_zone_count(session: Session, player_id: int, zone: str) -> int:
    return session.execute(
        select(func.coalesce(func.sum(DeckCard.quantity), 0)).where(
            DeckCard.player_id == player_id,
            DeckCard.zone == zone,
        )
    ).scalar_one()


def card_copies_in_deck(session: Session, player_id: int, card_id: int) -> int:
    return session.execute(
        select(func.coalesce(func.sum(DeckCard.quantity), 0)).where(
            DeckCard.player_id == player_id,
            DeckCard.card_id == card_id,
        )
    ).scalar_one()


def inventory_quantity(session: Session, player_id: int, card_id: int) -> int:
    quantity = session.execute(
        select(InventoryItem.quantity).where(
            InventoryItem.player_id == player_id,
            InventoryItem.card_id == card_id,
        )
    ).scalar_one_or_none()
    return quantity or 0


def add_card_to_deck(session: Session, player_id: int, card_id: int, zone: str) -> DeckCard:
    zone = normalize_zone(zone)
    player = session.get(Player, player_id)
    card = session.get(Card, card_id)
    if not player or not card:
        raise ValueError("Jogador ou carta nao encontrado.")
    if deck_zone_count(session, player_id, zone) >= zone_limit(zone):
        raise ValueError("Essa zona do deck ja esta no limite.")
    if card_copies_in_deck(session, player_id, card_id) >= inventory_quantity(session, player_id, card_id):
        raise ValueError("Todas as copias dessa carta ja estao em uso no deck.")
    current_copies = card_copies_in_deck(session, player_id, card_id)
    allowed, reason = can_add_copy(session, player_id, card_id, current_copies)
    if not allowed:
        raise ValueError(reason)
    if zone == "extra" and not is_extra_deck_card(card.type):
        raise ValueError("Apenas Fusion, Synchro, Xyz e Link podem entrar no Extra Deck.")
    if zone == "main" and is_extra_deck_card(card.type):
        raise ValueError("Cartas de Extra Deck nao entram no Main Deck.")

    deck_card = session.execute(
        select(DeckCard).where(
            DeckCard.player_id == player_id,
            DeckCard.card_id == card_id,
            DeckCard.zone == zone,
        )
    ).scalar_one_or_none()
    if deck_card:
        deck_card.quantity += 1
    else:
        deck_card = DeckCard(player_id=player_id, card_id=card_id, zone=zone, quantity=1)
    session.add(deck_card)
    session.commit()
    session.refresh(deck_card)
    return deck_card


def remove_card_from_deck(session: Session, player_id: int, deck_id: int) -> None:
    deck_card = session.get(DeckCard, deck_id)
    if not deck_card or deck_card.player_id != player_id:
        raise ValueError("Carta do deck nao encontrada.")
    deck_card.quantity -= 1
    if deck_card.quantity <= 0:
        session.delete(deck_card)
    else:
        session.add(deck_card)
    session.commit()


def trim_card_from_deck(session: Session, player_id: int, card_id: int, copies_to_remove: int) -> int:
    if copies_to_remove <= 0:
        return 0

    removed = 0
    rows = session.execute(
        select(DeckCard)
        .where(
            DeckCard.player_id == player_id,
            DeckCard.card_id == card_id,
        )
        .order_by(
            case(
                (DeckCard.zone == "side", 0),
                (DeckCard.zone == "extra", 1),
                else_=2,
            ),
            DeckCard.id.desc(),
        )
    ).scalars().all()

    for deck_card in rows:
        if removed >= copies_to_remove:
            break
        removable = min(deck_card.quantity, copies_to_remove - removed)
        deck_card.quantity -= removable
        removed += removable
        if deck_card.quantity <= 0:
            session.delete(deck_card)
        else:
            session.add(deck_card)
    return removed


def export_deck_as_ydke(session: Session, player_id: int) -> YdkDeck:
    rows = session.execute(
        select(DeckCard.card_id, DeckCard.zone, DeckCard.quantity)
        .where(DeckCard.player_id == player_id)
        .order_by(DeckCard.zone, DeckCard.id)
    ).all()

    deck = {"main": [], "extra": [], "side": []}
    for card_id, zone, quantity in rows:
        deck[zone].extend([card_id] * quantity)

    return YdkDeck(
        main=deck["main"],
        extra=deck["extra"],
        side=deck["side"],
    )


def deck_rows(session: Session, player_id: int) -> list[tuple[DeckCard, Card, str]]:
    inventory_rarity = {
        item.card_id: item.rarity
        for item in session.execute(
            select(InventoryItem).where(InventoryItem.player_id == player_id)
        ).scalars()
    }
    rows = session.execute(
        select(DeckCard, Card)
        .join(Card, DeckCard.card_id == Card.id)
        .where(DeckCard.player_id == player_id)
        .order_by(DeckCard.zone, Card.type, Card.name)
    ).all()
    return [(deck_card, card, inventory_rarity.get(card.id, "Common")) for deck_card, card in rows]


def deck_counts_by_card(session: Session, player_id: int) -> Counter[int]:
    counts: Counter[int] = Counter()
    rows = session.execute(
        select(DeckCard.card_id, DeckCard.quantity).where(DeckCard.player_id == player_id)
    ).all()
    for card_id, quantity in rows:
        counts[card_id] += quantity
    return counts


def build_deck_response(session: Session, player_id: int) -> dict:
    zones = {"main": [], "extra": [], "side": []}
    restrictions = restriction_status_map(session, player_id)
    for deck_card, card, rarity in deck_rows(session, player_id):
        zones[deck_card.zone].append(
            {
                "deck_id": deck_card.id,
                "card_id": card.id,
                "name": card.name,
                "type": card.type,
                "desc": card.desc,
                "race": card.race,
                "archetype": card.archetype,
                "rarity": rarity,
                "quantity": deck_card.quantity,
                "category": card_category(card.type),
                "restriction_status": restrictions.get(card.id),
                "image_url": ensure_card_image(card, session),
            }
        )

    main_count = sum(card["quantity"] for card in zones["main"])
    extra_count = sum(card["quantity"] for card in zones["extra"])
    side_count = sum(card["quantity"] for card in zones["side"])
    return {
        **zones,
        "main_count": main_count,
        "extra_count": extra_count,
        "side_count": side_count,
        "is_main_valid": MAIN_MIN <= main_count <= MAIN_MAX,
        "is_extra_valid": 0 <= extra_count <= EXTRA_MAX,
        "is_side_valid": 0 <= side_count <= SIDE_MAX,
    }
