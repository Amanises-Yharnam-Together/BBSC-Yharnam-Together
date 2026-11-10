"""The launcher's frame generation settings (Supermedo's 026f8ff, 389124d) are the keys and values the
game reads from bbport.ini (gpu/shim/bbport_settings.cpp), with the same defaults.

Run: python -m pytest -q tests/test_launcher_frame_gen.py"""
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'launcher'))
SETTINGS = (ROOT / 'gpu' / 'shim' / 'bbport_settings.cpp').read_text(encoding='utf-8')
SETTINGS_H = (ROOT / 'gpu' / 'shim' / 'bbport_settings.h').read_text(encoding='utf-8')

if sys.platform == 'win32':
    import bbport_launcher_win as launcher


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class FrameGenSettings(unittest.TestCase):
    def test_keys_the_game_reads(self):
        for key in ('frame_generation', 'frame_gen_provider', 'frame_gen_multiplier', 'frame_gen_fit_display'):
            self.assertIn(f'key == "{key}"', SETTINGS, key)
            self.assertIn(key, launcher.INI_DEFAULTS, key)

    def test_defaults_match_the_game(self):
        self.assertEqual(launcher.INI_DEFAULTS['frame_generation'], '0')
        self.assertEqual(launcher.INI_DEFAULTS['frame_gen_provider'], 'fsr3')
        self.assertEqual(launcher.INI_DEFAULTS['frame_gen_multiplier'], '2')
        self.assertEqual(launcher.INI_DEFAULTS['frame_gen_fit_display'], '1')
        self.assertIn('std::atomic<int> frame_gen_provider{FrameGenFsr3};', SETTINGS_H)
        self.assertIn('std::atomic<int> frame_gen_multiplier{2};', SETTINGS_H)
        self.assertIn('std::atomic<bool> frame_gen_fit_display{true};', SETTINGS_H)

    def test_values_the_game_takes(self):
        self.assertEqual([v for v, _t in launcher.FRAME_GEN_PROVIDERS], ['fsr3', 'dlss'])
        self.assertIn('value == "dlss" ? FrameGenDlss : FrameGenFsr3', SETTINGS)
        self.assertEqual([v for v, _t in launcher.FRAME_GEN_MULTIPLIERS], ['2', '3', '4'])
        self.assertTrue(re.search(r'frame_gen_multiplier = std::clamp\(i, 2, 4\)', SETTINGS))
        self.assertIn('frame_gen_fit_display', launcher.INI_FLAGS)
        self.assertNotIn('frame_gen_provider', launcher.INI_FLAGS)


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class FrameGenIsExperimental(unittest.TestCase):
    """Discord 2026-10-21..11-01: toggling frame generation crashed the game, DLSS Frame Generation failed
    on cards without it, and at co-op's 60 FPS it did nothing. Hidden until it works: only with
    Experimental features on does the game offer it (BB_FRAME_GEN_HIDDEN, bbport_settings.cpp)."""

    def environment(self, experimental, inherited=None):
        settings = {**launcher.APP_DEFAULTS, 'game_dir': 'G', 'experimental': experimental}
        ini = {'frame_generation': '1', 'upscaler': 'fsr3'}
        with mock.patch.dict(launcher.os.environ), \
                mock.patch.object(launcher, 'load_ini', return_value=(ini, [])), \
                mock.patch.object(launcher, 'display_refresh', return_value=144):
            for key in ('BB_FRAME_GEN_HIDDEN', 'BB_FPS_LIMIT'):
                launcher.os.environ.pop(key, None)
            launcher.os.environ.update(inherited or {})
            return launcher.game_environment(settings)

    def test_the_game_hides_it_without_experimental_features(self):
        env = self.environment(False)
        self.assertEqual(env['BB_FRAME_GEN_HIDDEN'], '1')
        # No frame cap for a frame generation that does not run (Auto would halve a 144 Hz screen's frames).
        self.assertNotIn('BB_FPS_LIMIT', env)

    def test_experimental_features_offer_it(self):
        env = self.environment(True, inherited={'BB_FRAME_GEN_HIDDEN': '1'})
        self.assertNotIn('BB_FRAME_GEN_HIDDEN', env)
        self.assertEqual(env['BB_FPS_LIMIT'], '72')

    def test_experimental_features_are_off_by_default(self):
        self.assertIs(launcher.APP_DEFAULTS['experimental'], False)

    def test_the_game_reads_the_variable(self):
        self.assertIn('"BB_FRAME_GEN_HIDDEN"', SETTINGS)

    def test_the_experimental_note_names_it(self):
        with mock.patch.object(launcher, 'LANG', 'en'):
            english = launcher.experimental_hint()
        self.assertIn('frame generation', english)
        import bbport_lang
        for language, _names in bbport_lang.LANGUAGE_NAMES:
            if language not in ('', 'en'):
                with mock.patch.object(launcher, 'LANG', language):
                    self.assertNotEqual(launcher.experimental_hint(), english, language)


if __name__ == '__main__':
    unittest.main()
