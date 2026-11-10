# SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for door_flags.py on small hand-made event files.

Run: py -3.12 -m unittest discover -s tools\\re\\tests
"""
import pathlib
import struct
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import door_flags as tool  # noqa: E402
from test_party_boss_events import build_emevd  # noqa: E402


def start(slot: int, event: int, *args: int) -> tuple[int, int, bytes]:
    return 2000, 0, struct.pack(f'<ii{len(args)}i', slot, event, *args)


def obj_act_done(flag: int) -> tuple[int, int, bytes]:
    return 5, 2, struct.pack('<bxxxi', 0, flag)


def set_flag(flag: int, on: bool) -> tuple[int, int, bytes]:
    return 2003, 2, struct.pack('<iBxxx', flag, int(on))


def gate_event() -> list[tuple[int, int, bytes]]:
    """m28's 12800480: a gate's object (argument 0) opens once its object act flag (argument
    1) is on."""
    return [
        (2005, 7, struct.pack('<ii', 0, 0)),
        obj_act_done(0),
        (1001, 0, struct.pack('<i', 0)),
    ]


class DoorFlags(unittest.TestCase):
    def test_a_started_events_flag_comes_from_each_start(self):
        emevd = build_emevd({0: [start(0, 12800480, 2801200, 12800201),
                                 start(1, 12800480, 2801202, 12800202)],
                             12800480: gate_event()},
                            {12800480: [(0, 0, 0, 4), (1, 4, 4, 4)]})
        doors, cleared = tool.door_flags(emevd)
        # The object acts' flags and each start's "done" flag (event id plus slot).
        self.assertEqual(doors, {12800201, 12800202, 12800480, 12800481})
        self.assertEqual(cleared, set())

    def test_a_flag_the_door_event_sets_counts(self):
        """m24_00's 12400760: Cathedral Ward's gate event sets 12400160 once it opened."""
        emevd = build_emevd({12400760: [obj_act_done(12400170), set_flag(12400160, True)]})
        self.assertEqual(tool.door_flags(emevd), ({12400170, 12400160, 12400760}, set()))

    def test_flags_of_other_events_do_not_count(self):
        emevd = build_emevd({12400100: [set_flag(12400101, True)]})
        self.assertEqual(tool.door_flags(emevd), (set(), set()))

    def test_a_switch_that_turns_back_is_left_out(self):
        files = {'m24_00_00_00.emevd.dcx': build_emevd({
            12400820: [obj_act_done(12400168), set_flag(12400168, False)],
            12400761: [obj_act_done(12400170)],
            12400762: [obj_act_done(12400172)],
            12400763: [set_flag(12400172, False)]})}
        self.assertEqual(tool.map_door_flags(files), [12400170, 12400761, 12400762])

    def test_only_the_maps_flags_of_map_files(self):
        files = {'m24_00_00_00.emevd.dcx': build_emevd({1: [obj_act_done(12400170),
                                                            obj_act_done(1)]}),
                 'common.emevd.dcx': build_emevd({12400191: [obj_act_done(12400190)]})}
        self.assertEqual(tool.map_door_flags(files), [12400170])


    def test_a_chalice_layout_starts_m29s_door_events(self):
        """Discord audit A6: m29.emevd holds the dungeons' door events, each layout's file starts
        them with its own flags; a flag one layout's switch clears is left out of every one."""
        m29 = build_emevd({12900315: gate_event(),
                           12900400: [obj_act_done(12900520), set_flag(12900520, False)]},
                          {12900315: [(0, 0, 0, 4), (1, 4, 4, 4)]})
        story = build_emevd({0: [start(0, 12900315, 2901019, 12900516),
                                 start(1, 12900315, 2901020, 12900520)]})
        root = build_emevd({0: [start(0, 12900315, 2901019, 12900530),
                                start(0, 12904700, 2901019, 12904701)]})
        self.assertEqual(tool.chalice_door_flags(m29, {'m29_10_90_00.emevd.dcx': story,
                                                       'm29_10_00_00.emevd.dcx': root}),
                         [12900315, 12900316, 12900516, 12900530])


    def test_a_chalice_chest_or_trap_is_each_players_own(self):
        """Loot is each player's own: a chest's or coffin's event (12900000: its object act, then
        the treasure 2005:4) and a trap's (12904338: an enemy woken 2004:1) give no door, and
        their flags stay out even where another layout's door uses them. Neither is another
        event's own id (the bell-ringing woman's 12901000). What stays (ChaliceDoorFlags): doors
        and gates (12900089-12900356), lever doors (12900189, 12901705), a passage (12904374),
        the doors that join the navmesh (12901447) and barriers (12901697-12901717)."""
        m29 = build_emevd({12900000: [obj_act_done(0), (2005, 4, struct.pack('<ii', 0, 1))],
                           12904338: [obj_act_done(0), (2004, 1, struct.pack('<ii', 0, 1))],
                           12900323: gate_event(),
                           12901000: [set_flag(12901001, True)]},
                          {12900000: [(0, 4, 0, 4)], 12904338: [(0, 4, 0, 4)],
                           12900323: [(0, 0, 0, 4), (1, 4, 4, 4)]})
        chests = build_emevd({0: [start(0, 12900000, 12900009), start(0, 12904338, 12900557),
                                  start(0, 12900323, 2901019, 12900400)]})
        doors = build_emevd({0: [start(0, 12900323, 2901020, 12900009),
                                 start(1, 12900323, 2901021, 12901000)]})
        self.assertEqual(tool.chalice_door_flags(m29, {'m29_10_00_00.emevd.dcx': chests,
                                                       'm29_10_90_00.emevd.dcx': doors}),
                         [12900323, 12900324, 12900400])


if __name__ == '__main__':
    unittest.main()
