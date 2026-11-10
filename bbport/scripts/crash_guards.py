#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Crash guards: the game's own code, where it reads through a pointer it never checks (game version
01.09; BB_CRASH_GUARDS=0 turns them off).

From Supermedo's bloodborne_pc (Supermedo/bloodborne_pc f1999924, "Crash guard: an online event
without its data no longer crashes the game"), GPL-2.0-or-later; the cave is at the same address as
there (code_cave.py).

- Online event without its data (0x1EB3D10, case 0). The game describes an event (r13: the event, its
  type the switch's value; r12: its data) and returns whether it could, the low byte of r12; an event
  type it does not know goes to 0x1EB3DD0: r12 = 0, "could not". Case 0 copies a string from r12 + 0x80
  without checking r12: a player online crashed there ("read access to 00000000000000a0
  at guest offset 0x1eb56b7") right after the server's ss.info request timed out. Case 0 with no data now
  goes the same way as an unknown event.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import code_cave as quit_menu  # noqa: E402

CAVE = quit_menu.CAVE + 0x1C0      # 0x50D98C0: there, the free tail of Quit to Desktop's cave
CAVE_END = quit_menu.CAVE + 0x200  # 0x50D9900: there, Rebirth's cave
EVENT_CASE = 0x1EB3DE8             # sub r12, -0x80; lea rdi, [rbp-0xa0]
EVENT_CASE_BYTES = bytes.fromhex('4983ec80488dbd60ffffff')
EVENT_UNKNOWN = 0x1EB3DD0          # xor r12d, r12d; jmp (the function's end): "could not"


def code_writes():
    cave = quit_menu.Code(CAVE)
    cave.raw('4d85e4')                                   # test r12, r12
    cave.data += b'\x0f\x84' + struct.pack('<i', EVENT_UNKNOWN - (cave.here + 6))   # jz: as unknown
    cave.data += EVENT_CASE_BYTES                        # the case's own first instructions
    cave.jmp(EVENT_CASE + len(EVENT_CASE_BYTES))
    if cave.here > CAVE_END:
        raise ValueError('crash guards do not fit')
    site = quit_menu.Code(EVENT_CASE)
    site.jmp(CAVE)
    site.data += b'\x90' * (len(EVENT_CASE_BYTES) - len(site.data))
    return [(cave.offset, bytes(cave.data)), (site.offset, bytes(site.data))]


def check_original(image_bytes):
    if image_bytes(EVENT_CASE, EVENT_CASE + len(EVENT_CASE_BYTES)) != EVENT_CASE_BYTES:
        raise ValueError(f'Crash guards: unexpected code at {EVENT_CASE + quit_menu.EBOOT_BASE:#x}')
