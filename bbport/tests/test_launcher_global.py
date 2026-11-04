# SPDX-License-Identifier: GPL-2.0-or-later
"""The launcher's Local / Global step (bbport_coop.py): what Global needs, what it plays with, how the
signed secret is kept, ages and is forgotten."""
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))
import bbport_coop as coop  # noqa: E402

BASE = 'https://play.example.com'


class ServerTypeTests(unittest.TestCase):
    """The launcher's Local / Global step (bbport_coop.py)."""

    SECRET = format(int(time.time()), '08x') + 'a' * 24

    def signed(self, **more):
        return coop.signed_in_global(dict(coop.DEFAULTS, game='x', server_type='global', global_server=BASE, **more),
                                     {'id': 'u0123456789abcd', 'secret': self.SECRET, 'name': 'Kaniel'})

    def test_local_is_the_default_and_stays_as_it_was(self):
        self.assertEqual(coop.DEFAULTS['server_type'], 'local')
        settings = dict(coop.DEFAULTS, game='x', host_ip='26.1.2.3', account='p0123456789abcd', password='b' * 32)
        self.assertEqual(coop.missing(settings), [])
        self.assertEqual(coop.missing(dict(settings, host_ip='')), ['host_ip'])
        self.assertEqual(coop.played_settings(settings), settings)
        self.assertEqual(coop.player_id_for(settings, '26.1.2.3'), ('p0123456789abcd', 'b' * 32))

    def test_global_needs_a_sign_in_not_an_ip(self):
        settings = dict(coop.DEFAULTS, game='x', server_type='global', global_server=BASE)
        self.assertEqual(coop.missing(settings), ['sign_in'])
        self.assertEqual(coop.missing(self.signed()), [])

    def test_global_plays_as_the_account_never_as_host(self):
        played = coop.played_settings(self.signed(role='host', host_ip='26.1.2.3'))
        self.assertEqual((played['host_ip'], played['role']), (BASE, 'guest'))
        self.assertEqual(coop.player_id_for(played, BASE), ('u0123456789abcd', self.SECRET))

    def test_an_old_secret_asks_for_a_new_sign_in(self):
        settings = self.signed()
        issued = int(self.SECRET[:8], 16)
        self.assertTrue(coop.is_signed_in_global(settings, now=issued + 28 * 86400))
        self.assertFalse(coop.is_signed_in_global(settings, now=issued + 29 * 86400 + 1))
        self.assertFalse(coop.is_signed_in_global(coop.signed_in_global(
            settings, {'id': 'u0123456789abcd', 'secret': 'not-hex-at-all'})))

    def test_sign_in_survives_in_coop_json_and_sign_out_forgets_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            coop.save_settings(Path(folder), self.signed())
            loaded = coop.read_settings(Path(folder))
            self.assertEqual(loaded['server_type'], 'global')
            self.assertEqual(loaded['global_name'], 'Kaniel')
            self.assertEqual(coop.player_id_for(loaded, BASE), ('u0123456789abcd', self.SECRET))
            out = coop.signed_out_global(loaded)
            self.assertEqual(out['global_name'], '')
            self.assertEqual(coop.missing(dict(out, game='x')), ['sign_in'])
            self.assertNotEqual(coop.player_id_for(out, BASE)[0], 'u0123456789abcd')

    def test_signing_in_keeps_the_players_home_server_id(self):
        settings = self.signed(account='p0123456789abcd', password='b' * 32)
        self.assertEqual((settings['account'], settings['password']), ('p0123456789abcd', 'b' * 32))

    def test_no_global_server_yet(self):
        with mock.patch.object(coop, 'GLOBAL_SERVER', ''):
            self.assertEqual(coop.global_url(dict(coop.DEFAULTS)), '')
        with mock.patch.object(coop, 'GLOBAL_SERVER', BASE):
            self.assertEqual(coop.global_url(dict(coop.DEFAULTS)), BASE)
        self.assertEqual(coop.global_url(dict(coop.DEFAULTS, global_server='https://other.example.com/')),
                         'https://other.example.com')

    def test_a_lone_public_server_has_no_directory(self):
        settings = coop.played_settings(self.signed())
        seen = coop.global_game_settings(settings, fetch=lambda _url: None, lookup=lambda _name: '203.0.113.7')
        self.assertEqual(seen['host_ip'], '203.0.113.7')
        self.assertEqual((seen['account'], seen['password']), ('u0123456789abcd', self.SECRET))
        self.assertEqual(seen['server'], BASE)

    def test_a_region_names_the_shard(self):
        settings = coop.played_settings(self.signed())
        shards = {'shards': [{'name': 'eu-1', 'address': '203.0.113.9:31314', 'key': 'ab' * 32, 'players': 3,
                              'capacity': 350}]}

        def fetch(url):
            return shards if url.endswith('/v1/shards') else None
        seen = coop.global_game_settings(settings, fetch=fetch)
        self.assertEqual((seen['host_ip'], seen['link_port']), ('203.0.113.9', '31314'))
        self.assertEqual(seen['account'], 'u0123456789abcd')

    def test_the_servers_refusal_of_a_new_id(self):
        line = 'x [Lib.Net] <Error> ' + coop.REFUSED_LINE + 'account: sign in in the launcher first'
        self.assertTrue(coop.needs_sign_in(line))
        self.assertFalse(coop.needs_sign_in(coop.REFUSED_LINE + 'address taken: something'))


if __name__ == '__main__':
    unittest.main()
