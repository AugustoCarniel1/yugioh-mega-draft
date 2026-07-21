from collections import Counter

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CardRestriction, CollectionProgress, DeckCard, InventoryItem, Player
from app.services.deck import card_copies_in_deck, trim_card_from_deck
from app.services.pricing import sell_price_for_rarity
from app.services.ydk import parse_ydk
from app.services.ygoprodeck import best_card_rarity, get_or_fetch_card


def create_player(session: Session, name: str) -> Player:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Informe um nome para o jogador.")

    existing_player = session.execute(
        select(Player).where(Player.name == clean_name)
    ).scalar_one_or_none()
    if existing_player:
        raise ValueError("Ja existe um jogador com esse nome.")

    player = Player(name=clean_name)
    session.add(player)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("Ja existe um jogador com esse nome.") from exc
    session.refresh(player)
    return player


def delete_player(session: Session, player_id: int) -> None:
    player = session.get(Player, player_id)
    if not player:
        raise ValueError("Jogador nao encontrado.")

    session.query(DeckCard).filter(DeckCard.player_id == player_id).delete(synchronize_session=False)
    session.query(InventoryItem).filter(InventoryItem.player_id == player_id).delete(synchronize_session=False)
    session.query(CardRestriction).filter(CardRestriction.player_id == player_id).delete(synchronize_session=False)
    session.delete(player)
    session.commit()


def import_ydk_to_inventory(session: Session, player_id: int, content: str) -> int:
    player = session.get(Player, player_id)
    if not player:
        raise ValueError("Jogador nao encontrado.")

    deck = parse_ydk(content)
    card_counts = Counter(deck.main + deck.extra + deck.side)
    imported = 0

    for card_id, quantity in card_counts.items():
        card = get_or_fetch_card(session, card_id)
        item = session.execute(
            select(InventoryItem).where(
                InventoryItem.player_id == player_id,
                InventoryItem.card_id == card_id,
            )
        ).scalar_one_or_none()
        if item:
            item.quantity += quantity
        else:
            item = InventoryItem(
                player_id=player_id,
                card_id=card_id,
                quantity=quantity,
                rarity=best_card_rarity(card),
            )
        session.add(item)
        imported += quantity

    session.commit()
    return imported


def sell_inventory_card(session: Session, player_id: int, inventory_id: int) -> float:
    player = session.get(Player, player_id)
    item = session.get(InventoryItem, inventory_id)
    if not player or not item or item.player_id != player_id:
        raise ValueError("Carta do inventario nao encontrada.")
    if item.quantity <= 0:
        raise ValueError("Nao ha copias para vender.")

    next_quantity = item.quantity - 1
    used_in_deck = card_copies_in_deck(session, player_id, item.card_id)
    if used_in_deck > next_quantity:
        trim_card_from_deck(session, player_id, item.card_id, used_in_deck - next_quantity)

    price = sell_price_for_rarity(item.rarity)
    item.quantity = next_quantity
    player.gold += price
    session.add(player)
    if item.quantity == 0:
        session.delete(item)
    else:
        session.add(item)
    session.commit()
    return price


def advance_round(session: Session, player_id: int) -> tuple[Player, CollectionProgress | None]:
    player = session.get(Player, player_id)
    if not player:
        raise ValueError("Jogador nao encontrado.")

    player.gold += 10
    player.current_collection_index += 1
    session.add(player)
    session.commit()
    session.refresh(player)

    collection = session.execute(
        select(CollectionProgress).where(CollectionProgress.position == player.current_collection_index)
    ).scalar_one_or_none()
    return player, collection
