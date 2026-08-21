from collections import Counter

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Card, DeckCard, InventoryItem, Player, SavedDeck
from app.services.restrictions import can_add_copy, restriction_status_map
from app.services.ydk import YdkDeck
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


def _normalized_deck_name(name: str) -> str:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Informe um nome para o deck.")
    return clean_name


def _player_or_error(session: Session, player_id: int) -> Player:
    player = session.get(Player, player_id)
    if not player:
        raise ValueError("Jogador nao encontrado.")
    return player


def get_or_create_active_deck(session: Session, player_id: int) -> SavedDeck:
    player = _player_or_error(session, player_id)
    if player.active_deck_id:
        active_deck = session.get(SavedDeck, player.active_deck_id)
        if active_deck and active_deck.player_id == player_id:
            return active_deck

    active_deck = session.execute(
        select(SavedDeck).where(SavedDeck.player_id == player_id).order_by(SavedDeck.id)
    ).scalars().first()
    if not active_deck:
        active_deck = SavedDeck(player_id=player_id, name="Deck Principal")
        session.add(active_deck)
        session.flush()

    player.active_deck_id = active_deck.id
    session.add(player)
    session.commit()
    session.refresh(active_deck)
    session.refresh(player)
    return active_deck


def list_saved_decks(session: Session, player_id: int) -> tuple[Player, list[SavedDeck]]:
    player = _player_or_error(session, player_id)
    active_deck = get_or_create_active_deck(session, player_id)
    if player.active_deck_id != active_deck.id:
        player = session.get(Player, player_id)
    decks = list(
        session.execute(select(SavedDeck).where(SavedDeck.player_id == player_id).order_by(SavedDeck.id)).scalars().all()
    )
    return player, decks


def create_saved_deck(session: Session, player_id: int, name: str, copy_active_deck: bool = False) -> SavedDeck:
    _player_or_error(session, player_id)
    active_deck = get_or_create_active_deck(session, player_id)
    deck_name = _normalized_deck_name(name)
    existing = session.execute(
        select(SavedDeck).where(SavedDeck.player_id == player_id, SavedDeck.name == deck_name)
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Ja existe um deck com esse nome.")

    new_deck = SavedDeck(player_id=player_id, name=deck_name)
    session.add(new_deck)
    session.flush()

    if copy_active_deck:
        rows = session.execute(
            select(DeckCard).where(DeckCard.saved_deck_id == active_deck.id)
        ).scalars().all()
        for row in rows:
            session.add(
                DeckCard(
                    player_id=player_id,
                    saved_deck_id=new_deck.id,
                    card_id=row.card_id,
                    zone=row.zone,
                    quantity=row.quantity,
                )
            )

    player = session.get(Player, player_id)
    player.active_deck_id = new_deck.id
    session.add(player)
    session.commit()
    session.refresh(new_deck)
    return new_deck


def rename_saved_deck(session: Session, player_id: int, saved_deck_id: int, name: str) -> SavedDeck:
    deck = session.get(SavedDeck, saved_deck_id)
    if not deck or deck.player_id != player_id:
        raise ValueError("Deck nao encontrado.")
    deck_name = _normalized_deck_name(name)
    existing = session.execute(
        select(SavedDeck).where(
            SavedDeck.player_id == player_id,
            SavedDeck.name == deck_name,
            SavedDeck.id != saved_deck_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Ja existe um deck com esse nome.")
    deck.name = deck_name
    session.add(deck)
    session.commit()
    session.refresh(deck)
    return deck


def set_active_deck(session: Session, player_id: int, saved_deck_id: int) -> SavedDeck:
    player = _player_or_error(session, player_id)
    deck = session.get(SavedDeck, saved_deck_id)
    if not deck or deck.player_id != player_id:
        raise ValueError("Deck nao encontrado.")
    player.active_deck_id = deck.id
    session.add(player)
    session.commit()
    session.refresh(deck)
    return deck


def deck_zone_count(session: Session, player_id: int, zone: str, saved_deck_id: int | None = None) -> int:
    saved_deck = get_or_create_active_deck(session, player_id) if saved_deck_id is None else session.get(SavedDeck, saved_deck_id)
    if not saved_deck:
        return 0
    return session.execute(
        select(func.coalesce(func.sum(DeckCard.quantity), 0)).where(
            DeckCard.saved_deck_id == saved_deck.id,
            DeckCard.zone == zone,
        )
    ).scalar_one()


def card_copies_in_deck(session: Session, player_id: int, card_id: int, saved_deck_id: int | None = None) -> int:
    saved_deck = get_or_create_active_deck(session, player_id) if saved_deck_id is None else session.get(SavedDeck, saved_deck_id)
    if not saved_deck:
        return 0
    return session.execute(
        select(func.coalesce(func.sum(DeckCard.quantity), 0)).where(
            DeckCard.saved_deck_id == saved_deck.id,
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
    _player_or_error(session, player_id)
    saved_deck = get_or_create_active_deck(session, player_id)
    card = session.get(Card, card_id)
    if not card:
        raise ValueError("Jogador ou carta nao encontrado.")
    if deck_zone_count(session, player_id, zone, saved_deck.id) >= zone_limit(zone):
        raise ValueError("Essa zona do deck ja esta no limite.")
    if card_copies_in_deck(session, player_id, card_id, saved_deck.id) >= inventory_quantity(session, player_id, card_id):
        raise ValueError("Todas as copias dessa carta ja estao em uso no deck atual.")
    current_copies = card_copies_in_deck(session, player_id, card_id, saved_deck.id)
    allowed, reason = can_add_copy(session, player_id, card_id, current_copies)
    if not allowed:
        raise ValueError(reason)
    if zone == "extra" and not is_extra_deck_card(card.type):
        raise ValueError("Apenas Fusion, Synchro, Xyz e Link podem entrar no Extra Deck.")
    if zone == "main" and is_extra_deck_card(card.type):
        raise ValueError("Cartas de Extra Deck nao entram no Main Deck.")

    deck_card = session.execute(
        select(DeckCard).where(
            DeckCard.saved_deck_id == saved_deck.id,
            DeckCard.card_id == card_id,
            DeckCard.zone == zone,
        )
    ).scalar_one_or_none()
    if deck_card:
        deck_card.quantity += 1
    else:
        deck_card = DeckCard(
            player_id=player_id,
            saved_deck_id=saved_deck.id,
            card_id=card_id,
            zone=zone,
            quantity=1,
        )
    session.add(deck_card)
    session.commit()
    session.refresh(deck_card)
    return deck_card


def remove_card_from_deck(session: Session, player_id: int, deck_id: int) -> None:
    saved_deck = get_or_create_active_deck(session, player_id)
    deck_card = session.get(DeckCard, deck_id)
    if not deck_card or deck_card.player_id != player_id or deck_card.saved_deck_id != saved_deck.id:
        raise ValueError("Carta do deck nao encontrada.")
    deck_card.quantity -= 1
    if deck_card.quantity <= 0:
        session.delete(deck_card)
    else:
        session.add(deck_card)
    session.commit()


def trim_card_from_deck(
    session: Session,
    player_id: int,
    card_id: int,
    copies_to_remove: int,
    saved_deck_id: int | None = None,
) -> int:
    if copies_to_remove <= 0:
        return 0

    saved_deck = get_or_create_active_deck(session, player_id) if saved_deck_id is None else session.get(SavedDeck, saved_deck_id)
    if not saved_deck:
        return 0

    removed = 0
    rows = session.execute(
        select(DeckCard)
        .where(
            DeckCard.saved_deck_id == saved_deck.id,
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
    saved_deck = get_or_create_active_deck(session, player_id)
    rows = session.execute(
        select(DeckCard.card_id, DeckCard.zone, DeckCard.quantity)
        .where(DeckCard.saved_deck_id == saved_deck.id)
        .order_by(DeckCard.zone, DeckCard.id)
    ).all()

    deck = {"main": [], "extra": [], "side": []}
    for card_id, zone, quantity in rows:
        deck[zone].extend([card_id] * quantity)

    return YdkDeck(main=deck["main"], extra=deck["extra"], side=deck["side"])


def deck_rows(session: Session, player_id: int) -> tuple[SavedDeck, list[tuple[DeckCard, Card, str]]]:
    saved_deck = get_or_create_active_deck(session, player_id)
    inventory_rarity = {
        item.card_id: item.rarity
        for item in session.execute(
            select(InventoryItem).where(InventoryItem.player_id == player_id)
        ).scalars()
    }
    rows = session.execute(
        select(DeckCard, Card)
        .join(Card, DeckCard.card_id == Card.id)
        .where(DeckCard.saved_deck_id == saved_deck.id)
        .order_by(DeckCard.zone, Card.type, Card.name)
    ).all()
    return saved_deck, [(deck_card, card, inventory_rarity.get(card.id, "Common")) for deck_card, card in rows]


def deck_counts_by_card(session: Session, player_id: int) -> Counter[int]:
    saved_deck = get_or_create_active_deck(session, player_id)
    counts: Counter[int] = Counter()
    rows = session.execute(
        select(DeckCard.card_id, DeckCard.quantity).where(DeckCard.saved_deck_id == saved_deck.id)
    ).all()
    for card_id, quantity in rows:
        counts[card_id] += quantity
    return counts


def build_deck_response(session: Session, player_id: int) -> dict:
    saved_deck, rows = deck_rows(session, player_id)
    zones = {"main": [], "extra": [], "side": []}
    restrictions = restriction_status_map(session, player_id)
    for deck_card, card, rarity in rows:
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
        "active_deck_id": saved_deck.id,
        "active_deck_name": saved_deck.name,
        **zones,
        "main_count": main_count,
        "extra_count": extra_count,
        "side_count": side_count,
        "is_main_valid": MAIN_MIN <= main_count <= MAIN_MAX,
        "is_extra_valid": 0 <= extra_count <= EXTRA_MAX,
        "is_side_valid": 0 <= side_count <= SIDE_MAX,
    }
