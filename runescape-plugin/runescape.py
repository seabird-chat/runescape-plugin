from typing import Callable, Dict, NamedTuple, Optional, Tuple
import re
import math

import requests

import seabird_pb2
import seabird_pb2_grpc


SKILL_NAMES = [
    "total",
    "attack",
    "defence",
    "strength",
    "hitpoints",
    "ranged",
    "prayer",
    "magic",
    "cooking",
    "woodcutting",
    "fletching",
    "fishing",
    "firemaking",
    "crafting",
    "smithing",
    "mining",
    "herblore",
    "agility",
    "thieving",
    "slayer",
    "farming",
    "runecraft",
    "hunter",
    "construction",
    "combat",
]

SKILL_ALIASES = {
    "overall": "total",
    "cmb": "combat",
    "atk": "attack",
    "att": "attack",
    "def": "defence",
    "defense": "defence",
    "str": "strength",
    "hp": "hitpoints",
    "range": "ranged",
    "ranging": "ranged",
    "pray": "prayer",
    "mage": "magic",
    "cook": "cooking",
    "wc": "woodcutting",
    "fletch": "fletching",
    "fish": "fishing",
    "fm": "firemaking",
    "craft": "crafting",
    "herb": "herblore",
    "agi": "agility",
    "farm": "farming",
    "runecrafting": "runecraft",
    "rc": "runecraft",
    "con": "construction",
}

HISCORE_URL = (
    "https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws" "?player={player}"
)

IGN_MATCH = re.compile('("([a-zA-Z_ ]+)"|([a-zA-Z_]+))')


class LevelMetadata(NamedTuple):
    """Represents level data for a player"""

    rank: int
    level: int
    experience: Optional[int] = None

    @classmethod
    def from_entry(cls, entry: str) -> "LevelMetadata":
        """Builds level metadata from a comma-separated string of integers"""
        return cls(*[int(p) for p in entry.split(",")])


def get_combat_level(attack, defence, strength, hitpoints, ranged, prayer, magic):
    # Formula was taken from https://oldschool.runescape.wiki/w/Combat_level#Mathematics
    base = 0.25 * (float(defence) + float(hitpoints) + math.floor(float(prayer) / 2.0))
    melee_option = 0.325 * (float(attack) + float(strength))
    ranged_float = float(ranged)
    ranged_option = 0.325 * (math.floor(ranged_float / 2.0) + ranged_float)
    magic_float = float(magic)
    magic_option = 0.325 * (math.floor(magic_float / 2.0) + magic_float)

    return int(math.floor(base + max(melee_option, max(ranged_option, magic_option))))


def pretty_suffix(number: int) -> str:
    """Formats a number as an SI-suffixed string"""
    suffixes = [
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ]
    for threshold, suffix in suffixes:
        if number >= threshold:
            return f"{number / threshold:.1f}{suffix}"
    return str(number)


def pretty_thousands(number: int) -> str:
    """Formats a number with comma-separated thousands places"""
    ret = ""
    while number >= 1000:
        if ret:
            ret = f",{ret}"
        ret = f"{number % 1000:03d}{ret}"
        number //= 1000

    if number > 0:
        if ret:
            ret = f",{ret}"
        ret = f"{number}{ret}"

    return ret


def level_callback(
    stub,
    identity,
    command,
    prop: str,
    response_format: str,
    value_format: Callable[[int], str],
) -> None:
    if not command.arg:
        reply_to(stub, identity, command, f"Usage: {prop} <player> <skill>")
        return

    m = IGN_MATCH.match(command.arg)
    if not m:
        reply_to(stub, identity, command, "Unable to parse IGN out of command")
        return

    ign = m.group(0)
    skills_str = command.arg.replace(f"{ign} ", "")
    if not skills_str:
        reply_to(stub, identity, command, "Must pass at least one skill")
        return

    skills = []
    for skill in skills_str.split(" "):
        skill = skill.lower()
        skills.append(SKILL_ALIASES.get(skill, skill))

    levels = get_player_levels(ign)
    if levels is None:
        reply_to(
            stub, identity, command, f"Error getting level information for {args[0]}",
        )
        return

    messages = []
    for skill in skills:
        if skill not in levels:
            reply_to(stub, identity, command, f'Unknown skill "{skill}"')
            return

        value = getattr(levels[skill], prop)
        if value is None or value < 0:
            reply_to(
                stub, identity, command, f"{args[0]}'s {prop} in {skill} is unknown",
            )
            return

        value_str = value_format(value)
        messages.append(response_format.format(skill=skill, value=value_str,))

    reply_to(
        stub, identity, command, "{} has {}".format(ign, ", ".join(messages),),
    )


def get_player_levels(player: str,) -> Optional[Dict[str, LevelMetadata]]:
    resp = requests.get(HISCORE_URL.format(player=player))

    if resp.status_code != 200:
        return None

    data = resp.text
    levels = {}
    counter = 0
    for line in data.split("\n"):
        line = line.strip()
        if not line:
            continue

        metadata = LevelMetadata.from_entry(line)
        if metadata.experience is None:
            continue

        levels[SKILL_NAMES[counter]] = metadata
        counter += 1

    levels["combat"] = LevelMetadata(
        rank=-1,
        level=get_combat_level(
            levels["attack"].level,
            levels["defence"].level,
            levels["strength"].level,
            levels["hitpoints"].level,
            levels["ranged"].level,
            levels["prayer"].level,
            levels["magic"].level,
        ),
        experience=None,
    )

    return levels


def reply_to(stub, identity, event, message):
    stub.SendMessage.with_call(
        seabird_pb2.SendMessageRequest(
            identity=identity,
            target=event.replyTo,
            message=f"{event.sender}: {message}",
        )
    )
