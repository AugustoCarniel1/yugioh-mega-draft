RARITY_BUY_PRICES = {
    "Common": 1,
    "Rare": 2,
    "Super Rare": 3,
    "Ultra Rare": 4,
    "Secret Rare": 5,
    "Prismatic Secret Rare": 5,
}


def normalize_rarity(rarity: str | None) -> str:
    if not rarity:
        return "Common"
    rarity = rarity.strip()
    return rarity or "Common"


def buy_price_for_rarity(rarity: str | None) -> int:
    rarity = normalize_rarity(rarity)
    if rarity == "Common":
        return 1
    if rarity == "Rare":
        return 2
    if rarity == "Super Rare":
        return 3
    if rarity == "Ultra Rare":
        return 4
    return 5


def sell_price_for_rarity(rarity: str | None) -> float:
    return buy_price_for_rarity(rarity) / 2
