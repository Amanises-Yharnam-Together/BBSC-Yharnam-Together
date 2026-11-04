"""Kaniel 2026-11-04 ("remove cheats in production mode"): a release's launcher (package.sh writes
scripts/build_info.json {"production": true}) offers no cheats and no debug menu or camera; a dev
build's (no such file) keeps them."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))

if sys.platform == 'win32':
    import bbport_launcher_win as launcher


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class ProductionBuildTests(unittest.TestCase):
    def install(self, text=None):
        root = Path(tempfile.mkdtemp())
        (root / 'scripts').mkdir()
        if text is not None:
            (root / 'scripts' / 'build_info.json').write_text(text, encoding='utf-8')
        return root

    def test_the_mark_makes_a_release(self):
        self.assertTrue(launcher.production_build(self.install('{"production": true}\n')))

    def test_no_mark_or_another_is_a_dev_build(self):
        for text in (None, '{"production": false}', '[]', 'not json'):
            with self.subTest(text=text):
                self.assertFalse(launcher.production_build(self.install(text)))

    def test_this_checkout_is_a_dev_build(self):
        self.assertFalse(launcher.PRODUCTION)

    def test_the_hidden_extras_are_the_debug_tools(self):
        keys = {key for key, _title, _on in launcher.EXTRAS}
        self.assertEqual(set(launcher.DEV_TOOL_EXTRAS), keys & {'debug_camera', 'debug_menu'})


if __name__ == '__main__':
    unittest.main()
