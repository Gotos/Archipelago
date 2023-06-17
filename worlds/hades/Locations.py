from typing import Dict

from BaseClasses import Location
from worlds.hades.Options import ShuffledDarkness, BonusBoons


class HadesLocation(Location):
    game: str = "Hades"


hades_locations_start_id = 6942000


def get_item_pickups(name: str, n: int, offset: int = 0) -> Dict[str, int]:
    """Get n ItemPickups, capped at the max value for TotalLocations"""
    return {f"{name}{i+1+offset}": hades_locations_start_id + i + offset for i in range(n)}


def get_all_item_pickups() -> Dict[str, int]:
    darkness_pickups = get_item_pickups("DarknessRoomReward", ShuffledDarkness.range_end)
    offset = ShuffledDarkness.range_end
    bonus_boon_pickup = get_item_pickups("DarknessRoomReward", BonusBoons.range_end, offset)

    return {
        **darkness_pickups,
        **bonus_boon_pickup
    }


location_table = get_all_item_pickups()

lookup_id_to_name: Dict[int, str] = {id: name for name, id in location_table.items()}
