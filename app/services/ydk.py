import base64
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class YdkDeck:
    main: list[int]
    extra: list[int]
    side: list[int]


def parse_ydk(content: str) -> YdkDeck:
    section = "main"
    cards: dict[str, list[int]] = {"main": [], "extra": [], "side": []}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#created"):
            continue
        if line == "#main":
            section = "main"
            continue
        if line == "#extra":
            section = "extra"
            continue
        if line == "!side":
            section = "side"
            continue
        if line.startswith("#"):
            continue
        try:
            cards[section].append(int(line))
        except ValueError:
            continue

    return YdkDeck(main=cards["main"], extra=cards["extra"], side=cards["side"])


def export_ydke(deck: YdkDeck) -> str:
    return (
        "ydke://"
        f"{_encode_ydke_section(deck.main)}!"
        f"{_encode_ydke_section(deck.extra)}!"
        f"{_encode_ydke_section(deck.side)}!"
    )


def _encode_ydke_section(card_ids: list[int]) -> str:
    payload = b"".join(struct.pack("<I", int(card_id)) for card_id in card_ids)
    return base64.b64encode(payload).decode("ascii")
