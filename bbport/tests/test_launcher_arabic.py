"""Arabic: the game language 'ar' (an Arabic translation mod in the English (UK) slot) starts the game in that slot
with the port's menus in Arabic; any other language leaves the menus to the game's language (or to the launcher's
own language when that is Arabic), whatever the environment the launcher was started with."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))

if sys.platform == 'win32':
    import bbport_launcher_win as launcher


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class ArabicTests(unittest.TestCase):
    def environment(self, language, launcher_language='en', inherited=None):
        settings = {**launcher.APP_DEFAULTS, 'game_dir': 'G', 'language': language}
        with mock.patch.dict(launcher.os.environ), \
                mock.patch.object(launcher, 'load_ini', return_value=({}, [])), \
                mock.patch.object(launcher, 'LANG', launcher_language):
            launcher.os.environ.pop('BB_MENU_LANGUAGE', None)
            if inherited:
                launcher.os.environ['BB_MENU_LANGUAGE'] = inherited
            return launcher.game_environment(settings)

    def test_arabic_plays_in_the_english_uk_slot_with_arabic_menus(self):
        env = self.environment('ar')
        self.assertEqual(env['BB_LANGUAGE'], '18')
        self.assertEqual(env['BB_MENU_LANGUAGE'], 'ar')

    def test_other_languages_keep_their_id_and_no_menu_language(self):
        env = self.environment('2')
        self.assertEqual(env['BB_LANGUAGE'], '2')
        self.assertNotIn('BB_MENU_LANGUAGE', env)

    def test_an_inherited_menu_language_does_not_stay(self):
        self.assertNotIn('BB_MENU_LANGUAGE', self.environment('1', inherited='ar'))

    def test_the_launcher_in_arabic_sets_arabic_menus(self):
        self.assertEqual(self.environment('1', launcher_language='ar')['BB_MENU_LANGUAGE'], 'ar')

    def test_arabic_is_a_game_language_choice(self):
        self.assertIn('ar', [value for value, _names in launcher.LANGUAGES])


if __name__ == '__main__':
    unittest.main()
