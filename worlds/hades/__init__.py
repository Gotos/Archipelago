from BaseClasses import Tutorial, Item, ItemClassification
from .Items import item_table, HadesItem
from .Locations import location_table
from .Options import Hades_Options, BonusBoons, ShuffledDarkness
from .Regions import create_regions, connect_regions

from ..AutoWorld import World, WebWorld


class HadesWeb(WebWorld):
    tutorials = [Tutorial(
            "Multiworld Setup Guide",
            "A guide to playing Hades with Archipelago.",
            "English",
            "setup_en.md",
            "setup/en",
            ["gRuFtY"]
    )]

class HadesWorld(World):
    """
    Hades is a story-driven roguelike developed and published by Supergiant Games and released in 2020.
    Try to escape the greek underworld as Zagreus, son of Hades, gaining support from the gods of Olymp.
    """
    game: str = "Hades"
    web = HadesWeb()
    data_version = 1
    required_client_version = (0, 4, 0) # todo: figure out what to put here
    option_definitions = Hades_Options

    item_name_to_id = item_table
    location_name_to_id = location_table

    def create_regions(self):
        create_regions(self.multiworld, self.player, location_table)
        connect_regions(self.multiworld, self.player)

    def create_item(self, name: str, ) -> Item:
        id = item_table[name]
        item_classification = ItemClassification.progression
        if name == "unfilled":
            item_classification = ItemClassification.filler

        created_item = HadesItem(name, item_classification, id, self.player)

        return created_item

    def create_items(self) -> None:
        itempool = [self.create_item("Darkness") for _ in range(self.multiworld.ShuffledDarkness[self.player].value)]
        itempool += [self.create_item("BonusBoon") for _ in range(self.multiworld.BonusBoons[self.player].value)]

        itempool += [self.create_filler()
                     for _ in range(BonusBoons.range_end + ShuffledDarkness.range_end - len(itempool))]

        self.multiworld.itempool += itempool

    def set_excluded_locations(self):
        for i in range(self.multiworld.ShuffledDarkness[self.player].value + self.multiworld.BonusBoons[self.player].value, BonusBoons.range_end + ShuffledDarkness.range_end):
            self.multiworld.exclude_locations[self.player].value.add(f"DarknessRoomReward{i+1}")

    def generate_early(self) -> None:
        self.set_excluded_locations()

    def get_filler_item_name(self) -> str:
        return "unfilled"
