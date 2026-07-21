from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    gold: Mapped[float] = mapped_column(Float, default=0)
    current_collection_index: Mapped[int] = mapped_column(Integer, default=-1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    deck_cards: Mapped[list["DeckCard"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    card_restrictions: Mapped[list["CardRestriction"]] = relationship(back_populates="player", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    desc: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    race: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    archetype: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    card_images: Mapped[list[dict]] = mapped_column(JSON, default=list)
    card_sets: Mapped[list[dict]] = mapped_column(JSON, default=list)
    cached_image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="card")
    deck_cards: Mapped[list["DeckCard"]] = relationship(back_populates="card")
    card_restrictions: Mapped[list["CardRestriction"]] = relationship(back_populates="card")


class InventoryItem(Base):
    __tablename__ = "inventoryitem"
    __table_args__ = (UniqueConstraint("player_id", "card_id", name="uq_inventory_player_card"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("card.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    rarity: Mapped[str] = mapped_column(String, default="Common")
    source: Mapped[str] = mapped_column(String, default="starter_deck")

    player: Mapped[Player] = relationship(back_populates="inventory_items")
    card: Mapped[Card] = relationship(back_populates="inventory_items")


class DeckCard(Base):
    __tablename__ = "deckcard"
    __table_args__ = (UniqueConstraint("player_id", "card_id", "zone", name="uq_deck_player_card_zone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("card.id"), index=True)
    zone: Mapped[str] = mapped_column(String, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    player: Mapped[Player] = relationship(back_populates="deck_cards")
    card: Mapped[Card] = relationship(back_populates="deck_cards")


class CardRestriction(Base):
    __tablename__ = "cardrestriction"
    __table_args__ = (UniqueConstraint("player_id", "card_id", name="uq_restriction_player_card"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("card.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="limited", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    player: Mapped[Player] = relationship(back_populates="card_restrictions")
    card: Mapped[Card] = relationship(back_populates="card_restrictions")


class CollectionProgress(Base):
    __tablename__ = "collectionprogress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    set_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    set_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tcg_date: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    card_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position: Mapped[int] = mapped_column(Integer, index=True)
