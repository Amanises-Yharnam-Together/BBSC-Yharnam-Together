# SPDX-License-Identifier: GPL-2.0-or-later
"""Every text the launcher's window shows has every launcher language (bbport_lang.py): a public release
shows no English in a translated window. Russian may sit next to the English in the code instead."""
import ast
import string
import sys
import unittest
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[1] / 'launcher'
sys.path.insert(0, str(LAUNCHER))
import bbport_lang  # noqa: E402

WARN = '  \u26a0'  # the launcher's mark of a risky choice; the text before it is translated
# Names the same in every language: products and their presets (as the drivers name them), numbers, and
# the game's languages, each written in itself.
SAME_EVERYWHERE = {
    'FSR 4', 'DLSS', 'HDR', 'FPS', 'V-Sync', 'DLSS (NVIDIA GeForce RTX)', 'Native AA (\xd71.0)',
    'Quality (\xd71.5)', 'Balanced (\xd71.7)', 'Performance (\xd72)', 'Ultra Performance (\xd73)',
    '60 FPS', '90 FPS', '120 FPS', '144 FPS', '165 FPS', '240 FPS', '2', '2\xd7',
    '3\xd7 (DLSS, GeForce RTX 50)', '4\xd7 (DLSS, GeForce RTX 50)', 'FIFO (VSync)', 'FIFO Relaxed',
    'English (UK)', 'Fran\xe7ais', 'Espa\xf1ol', 'Espa\xf1ol (Latinoam\xe9rica)', 'Deutsch', 'Italiano',
    'Nederlands', 'Portugu\xeas', 'Portugu\xeas (Brasil)', 'Suomi', 'Svenska', 'Dansk', 'Norsk', 'Polski',
    'T\xfcrk\xe7e', '\u0420\u0443\u0441\u0441\u043a\u0438\u0439', '\u65e5\u672c\u8a9e', '\ud55c\uad6d\uc5b4',
    '\u7e41\u9ad4\u4e2d\u6587', '\u7b80\u4f53\u4e2d\u6587', '\u0627\u0644\u0639\u0631\u0628\u064a\u0629 (mod)',
}


def fields(text):
    """How many values a text takes ({} and {0}, {1}... alike: a translation may reorder them)."""
    return sum(1 for _literal, name, _spec, _conv in string.Formatter().parse(text) if name is not None)


def window_texts():
    """(English, Russian or None) of each _() call with a written text in bbport_launcher_win.py."""
    tree = ast.parse((LAUNCHER / 'bbport_launcher_win.py').read_text(encoding='utf-8'))
    found = {}
    for call in ast.walk(tree):
        if (isinstance(call, ast.Call) and getattr(call.func, 'id', '') == '_' and call.args
                and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)):
            ru = call.args[1].value if len(call.args) > 1 and isinstance(call.args[1], ast.Constant) else None
            if ru or call.args[0].value not in found:
                found[call.args[0].value] = ru
    # The choice lists' labels: (value, (english, russian?)) pairs, put through _() as they are shown.
    for node in ast.walk(tree):
        if (isinstance(node, ast.Tuple) and len(node.elts) == 2 and isinstance(node.elts[1], ast.Tuple)
                and 1 <= len(node.elts[1].elts) <= 2
                and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts[1].elts)):
            texts = [e.value.removesuffix(WARN) for e in node.elts[1].elts]
            if texts[0] not in found or len(texts) > 1:
                found[texts[0]] = texts[1] if len(texts) > 1 else None
    return found


class LanguageTests(unittest.TestCase):
    def test_every_window_text_has_every_language(self):
        texts = window_texts()
        self.assertGreater(len(texts), 500)
        languages = [code for code, _names in bbport_lang.LANGUAGE_NAMES if code not in ('', 'en')]
        for language in languages:
            table = bbport_lang.table(language)
            for english, russian in texts.items():
                if english in SAME_EVERYWHERE:
                    continue
                with self.subTest(language=language, text=english[:60]):
                    if language == 'ru' and russian:
                        continue
                    self.assertTrue(table.get(english), 'no translation')
                    self.assertEqual(fields(english), fields(table[english]))

    def test_the_tables_line_up(self):
        for language in bbport_lang.LAUNCHER:
            self.assertEqual(len(bbport_lang.LAUNCHER[language]), len(bbport_lang.LAUNCHER_KEYS), language)


if __name__ == '__main__':
    unittest.main()
