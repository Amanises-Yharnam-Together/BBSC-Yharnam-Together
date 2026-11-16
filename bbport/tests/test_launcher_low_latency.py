"""The launcher's low latency setting (NVIDIA Reflex / AMD Anti-Lag 2, vk_low_latency.h) is the key and the
values the game reads from bbport.ini (gpu/shim/bbport_settings.cpp, bbport_latency_frames.h), with the same
default. Read from the sources: no window.

Run: python -m pytest -q tests/test_launcher_low_latency.py"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = (ROOT / 'launcher' / 'bbport_launcher_win.py').read_text(encoding='utf-8')
SETTINGS = (ROOT / 'gpu' / 'shim' / 'bbport_settings.cpp').read_text(encoding='utf-8')
SETTINGS_H = (ROOT / 'gpu' / 'shim' / 'bbport_settings.h').read_text(encoding='utf-8')
FRAMES_H = (ROOT / 'gpu' / 'shim' / 'bbport_latency_frames.h').read_text(encoding='utf-8')


def launcher_value(name):
    """A module-level assignment of the launcher, evaluated (a literal)."""
    for node in ast.parse(LAUNCHER).body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


class LowLatencySettings(unittest.TestCase):
    def test_the_key_the_game_reads(self):
        self.assertIn('key == "low_latency"', SETTINGS)
        self.assertIn('{"BB_LOW_LATENCY", "low_latency"}', SETTINGS)
        self.assertIn("'low_latency': 'auto'", LAUNCHER)

    def test_the_values_the_game_takes(self):
        names = re.search(r'SettingNames\[\] = \{([^}]*)\}', FRAMES_H).group(1)
        game = [word.strip().strip('"') for word in names.split(',')]
        self.assertEqual([value for value, _texts in launcher_value('LOW_LATENCY')], game)

    def test_the_default_is_auto_in_both(self):
        self.assertIn('std::atomic<int> low_latency{BbLatencyFrames::SettingAuto};', SETTINGS_H)
        self.assertIn('return SettingAuto;', FRAMES_H)  # an unknown word
        self.assertEqual(launcher_value('LOW_LATENCY')[1][0], 'auto')


if __name__ == '__main__':
    unittest.main()
