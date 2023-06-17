from typing import Dict

from BaseClasses import Item


class HadesItem(Item):
    game: str = "Hades"


# 4206900 - 4206901
item_table: Dict[str, int] = {
    "unfilled":     4206900,
    "Darkness":     4206901,
    "BonusBoon":    4206902
}
