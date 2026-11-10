"""Seamless co-op is for every retail release of Bloodborne, not the EU Game of the Year edition alone.

The game's co-op code asked for the title id CUSA03173 (bloodborne_patches.cpp IsSeamlessCoopGame) while the
launcher and the game check took all nine releases, which share one 1.09 executable: the US CUSA00900 and the
others started without co-op under the party HUD made for it, and the HUD's sprites, which nothing then stopped,
flashed their placeholders ("test", three players, 99 vials; about 13 players on Discord, 2026-10-25 to
2026-11-07). The list is kept in one header and no co-op code names a single edition."""
from paths import ROOT
import re
import sys
import unittest

import game_check

sys.path.insert(0, str(ROOT / 'launcher'))
import bbport_coop  # noqa: E402

CORE = ROOT.parent / 'emulator/src/core'
TITLES = CORE / 'bloodborne_titles.h'


class EditionTests(unittest.TestCase):
    def test_the_games_list_is_the_launchers_and_the_game_checks(self):
        text = TITLES.read_text(encoding='utf-8')
        table = text[text.index('RetailTitles{'):]
        titles = re.findall(r'"(CUSA\d{5})"', table[:table.index('};')])
        self.assertEqual(len(titles), 9)
        self.assertEqual(sorted(titles), sorted(game_check.SUPPORTED_TITLES))
        self.assertEqual(sorted(titles), sorted(bbport_coop.TITLE_IDS))

    def test_no_co_op_code_asks_for_one_edition(self):
        asks = []
        for folder in (CORE, ROOT / 'gpu/bbcoop', ROOT / 'gpu/bbnet'):
            for path in sorted(folder.glob('*.cpp')) + sorted(folder.glob('*.h')):
                for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                    if re.search(r'g_game_serial\s*[!=]=\s*"CUSA', line):
                        asks.append(f'{path.name}:{number}: {line.strip()}')
        self.assertEqual(asks, [])

    def test_the_seamless_patches_go_by_the_list(self):
        text = (CORE / 'bloodborne_patches.cpp').read_text(encoding='utf-8')
        gate = text[text.index('bool IsSeamlessCoopGame()'):]
        gate = gate[:gate.index('\n}\n')]
        self.assertIn('SeamlessCoopGameFor(MemoryPatcher::g_game_serial', gate)
        self.assertIn('GetsSeamlessCoop(', gate)


if __name__ == '__main__':
    unittest.main()
