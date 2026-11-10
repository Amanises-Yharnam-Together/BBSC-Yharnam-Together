# SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""Lists the maps' door flags. A map event that waits for an object act (5:2: a door, gate,
lever, kicked ladder) keeps the door open by flags: the object act's own flag, the event's
"done" flag (its id plus the start's slot: the next load reads it and sets the door open at
once) and any flag it sets on (Cathedral Ward's gate event 12400760 sets 12400160). The party
shares them (DoorFlags in emulator/src/core/bloodborne_flags.h): the game only syncs an object
act to players on the same map, so a door a teammate opened elsewhere stayed shut (Kaniel
2026-10-19).

Run: py -3.12 tools\\re\\door_flags.py <folder with the game's event\\*.emevd.dcx>
"""
import pathlib
import struct
import sys

from party_boss_events import EventPatchError, load_dcx, parse

OBJ_ACT_DONE = (5, 2)  # condition group, object act flag
INIT_EVENT = (2000, 0)  # slot, event, the event's arguments
SET_EVENT_FLAG = (2003, 2)  # flag, state (1 on)
# What makes an object act's event a player's own, not a door (Discord audit A6: loot and NPC gifts
# are each player's): a chest or coffin enables its treasure (2005:4) or awards an item lot
# (2003:4), a trap or ambush wakes an enemy (2004:1, its logic switched on).
PERSONAL = {(2005, 4): 'treasure', (2003, 4): 'item lot', (2004, 1): 'an enemy woken'}
MAP_FLAGS = range(12000000, 14000000)


def int_at(data: bytes, at: int) -> int | None:
    return struct.unpack_from('<i', data, at)[0] if 0 <= at and at + 4 <= len(data) else None


def door_flags(emevd: bytes, more_starts: tuple[bytes, ...] = (),
               personal: set[int] | None = None) -> tuple[set[int], set[int]]:
    """(the flags its door events wait for, set or end with, the flags its events clear); an
    event's argument comes from each of its starts (2000:0) in the same file, or in
    `more_starts` (a chalice layout's file starts m29.emevd's events). With `personal`, an
    object act's event that is a player's own (PERSONAL: a chest, a trap) is no door: its flags
    go there instead."""
    events = parse(emevd)['events']
    starts: dict[int, list[tuple[int, bytes]]] = {}
    for source in (events, *(parse(more)['events'] for more in more_starts)):
        for event in source:
            for bank, ident, _, _, args in event['instructions']:
                if (bank, ident) == INIT_EVENT and len(args) >= 8:
                    starts.setdefault(int_at(args, 4), []).append((int_at(args, 0), args[8:]))

    def values(event: dict, index: int, at: int, args: bytes) -> list[int]:
        sources = [source for instruction, target, source, *_ in event['parameters']
                   if instruction == index and target == at]
        if not sources:
            value = int_at(args, at)
            return [] if value is None else [value]
        found = (int_at(start, sources[0]) for _, start in starts.get(event['id'], []))
        return [value for value in found if value is not None]

    doors, cleared = set(), set()
    for event in events:
        instructions = event['instructions']
        waits, sets, clears = set(), set(), set()
        for index, (bank, ident, _, _, args) in enumerate(instructions):
            if (bank, ident) == OBJ_ACT_DONE:
                waits.update(values(event, index, 4, args))
            elif (bank, ident) == SET_EVENT_FLAG and len(args) >= 5:
                (sets if args[4] == 1 else clears).update(values(event, index, 0, args))
        cleared |= clears
        # A switch (its event turns the object act's flag back off) is no door.
        if waits and not waits & clears:
            slots = [slot for slot, _ in starts.get(event['id'], [])] or [0]
            own = {event['id'] + slot for slot in slots} | waits | sets
            if personal is not None and any((bank, ident) in PERSONAL
                                            for bank, ident, *_ in instructions):
                personal |= own
            else:
                doors |= own
    return doors, cleared


def map_door_flags(files: dict[str, bytes]) -> list[int]:
    """The maps' door flags, leaving out any an event clears again (a switch that turns
    back): only a door that stays open is shared."""
    doors, cleared = set(), set()
    for name, data in files.items():
        if not name.startswith('m'):
            continue
        flags, clears = door_flags(data)
        doors |= flags
        cleared |= clears
    return sorted(flag for flag in doors - cleared if flag in MAP_FLAGS)


# A chalice dungeon's flags: the chalice map's view (1290xxxx) of the dungeon's altar. Its door
# events are m29.emevd's, started with their flags by each layout's file (m29_KK_VR_LL). Only
# the view's own part with no load reset (0-3999: doors, levers, ladders, the layers' bosses) is
# kept (the 4xxx/5xxx part resets on each load, the lamps' 7810-8191 are shared by their row).
CHALICE_VIEW = range(12900000, 12904000)


def chalice_door_flags(m29: bytes, layouts: dict[str, bytes]) -> list[int]:
    """The chalice dungeons' door flags (the view's ids) over every layout, leaving out any an
    event clears again in some layout, any a chest's or trap's event uses in some layout (each
    player's own) and the id of any event that waits for no object act (its "done" flag: the
    bell-ringing woman's 12901000, a boss's reward 12901693)."""
    doors, cleared, personal = set(), set(), set()
    for name in sorted(layouts):
        flags, clears = door_flags(m29, (layouts[name],), personal)
        doors |= flags
        cleared |= clears
    others = {event['id'] for data in (m29, *layouts.values()) for event in parse(data)['events']
              if not any((bank, ident) == OBJ_ACT_DONE
                         for bank, ident, *_ in event['instructions'])}
    return sorted(flag for flag in doors - cleared - personal - others if flag in CHALICE_VIEW)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    folder = pathlib.Path(argv[0])
    if len(argv) > 1 and argv[1] == '--chalice':
        layouts = {path.name: load_dcx(path.read_bytes())
                   for path in sorted(folder.glob('m29_*/m29_*.emevd.dcx'))}
        m29 = load_dcx((pathlib.Path(argv[2]) if len(argv) > 2 else folder / 'm29.emevd.dcx')
                       .read_bytes())
        offsets = [flag - CHALICE_VIEW.start for flag in chalice_door_flags(m29, layouts)]
        print(f'inline constexpr std::array<s32, {len(offsets)}> ChaliceDoorFlags{{')
        for at in range(0, len(offsets), 12):
            print('    ' + ' '.join(f'{offset},' for offset in offsets[at:at + 12]))
        print('};')
        return 0
    files = {path.name: path.read_bytes()
             for path in sorted(folder.glob('*.emevd.dcx'))}
    flags = map_door_flags(files)
    print(f'inline constexpr std::array<s32, {len(flags)}> DoorFlags{{')
    for at in range(0, len(flags), 9):
        print('    ' + ' '.join(f'{flag},' for flag in flags[at:at + 9]))
    print('};')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except EventPatchError as error:
        print(f'error: {error}', file=sys.stderr)
        sys.exit(1)
