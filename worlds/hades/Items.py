from typing import Dict

from BaseClasses import Item


class HadesItem(Item):
    game: str = "Hades"


# 4206900 - 4206901
item_table: Dict[str, int] = {
    "unfilled":                     4206900,
    "RoomRewardMetaPointDrop":      4206901,
    "BonusBoon":                    4206902
}

item_id_to_name: Dict[int, str] = {id: item for item, id in item_table.items()}
