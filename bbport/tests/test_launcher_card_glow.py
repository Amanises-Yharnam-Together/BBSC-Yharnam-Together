"""A card whose page was rebuilt under the pointer: lighting it must not raise. Every pointer move
raised "_tkinter.TclError: invalid command name .!frame3.!frame.!frame" from Launcher.light, and a
player's log/launcher-errors.txt grew to 15.8 MB of that one traceback (support bundle
20261112-234320)."""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))

if sys.platform == 'win32':
    import bbport_launcher_win as launcher


class DestroyedCard:
    corners = ()

    def configure(self, **_options):
        raise launcher.tk.TclError('invalid command name ".!frame3.!frame.!frame"')


class LiveCard:
    def __init__(self):
        self.options = {}
        self.corners = ()

    def configure(self, **options):
        self.options.update(options)


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class CardGlowTests(unittest.TestCase):
    def test_destroyed_card_is_forgotten(self):
        card = DestroyedCard()
        owner = types.SimpleNamespace(cards={card}, hot_card=card)
        launcher.Launcher.light(owner, card, 0.5)
        self.assertNotIn(card, owner.cards)
        self.assertIsNone(owner.hot_card)

    def test_live_card_lights(self):
        card = LiveCard()
        owner = types.SimpleNamespace(cards={card}, hot_card=card)
        launcher.Launcher.light(owner, card, 1.0)
        self.assertIn('highlightbackground', card.options)
        self.assertIs(owner.hot_card, card)


if __name__ == '__main__':
    unittest.main()
