import typing

from BaseClasses import MultiWorld, Region, Entrance
from worlds.hades import location_table
from worlds.hades.Locations import HadesLocation


def create_regions(world, player: int, active_locations):
    menu_region = create_region(world, player, active_locations, 'Menu', None)
    run_region = create_region(world, player, active_locations, 'Run', location_table)

    world.regions += [
        menu_region,
        run_region
    ]


def connect_regions(world: MultiWorld, player: int):
    names: typing.Dict[str, int] = {}

    connect(world, player, names, "Menu", 'Run')


def create_region(world: MultiWorld, player: int, active_locations, name: str, locations=None):
    ret = Region(name, player, world)
    if locations:
        counter = 0
        for location in locations:
            loc_id = active_locations.get(location, 0)
            if loc_id:
                location = HadesLocation(player, location, loc_id, ret)
                ret.locations.append(location)
                counter += 1

    return ret


def connect(world: MultiWorld, player: int, used_names: typing.Dict[str, int], source: str, target: str,
            rule: typing.Optional[typing.Callable] = None):
    source_region = world.get_region(source, player)
    target_region = world.get_region(target, player)

    if target not in used_names:
        used_names[target] = 1
        name = target
    else:
        used_names[target] += 1
        name = target + (' ' * used_names[target])

    connection = Entrance(player, name, source_region)

    if rule:
        connection.access_rule = rule

    source_region.exits.append(connection)
    connection.connect(target_region)
