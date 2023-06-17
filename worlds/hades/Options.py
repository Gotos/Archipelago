import typing

from Options import Option, Range


class BonusBoons(Range):
    """Generate additional boons that will be granted at the start of a run (or when they are collected)."""
    display_name = "Number of bonus boons."
    range_start = 0
    range_end = 100
    default = 10


class ShuffledDarkness(Range):
    """Shuffle this many darkness room rewards into the item pool."""
    display_name = "Amount of Darkness room rewards in the item pool."
    range_start = 0
    range_end = 100
    default = 10


Hades_Options: typing.Dict[str, type(Option)] = {
    "BonusBoons":             BonusBoons,
    "ShuffledDarkness":       ShuffledDarkness,

}