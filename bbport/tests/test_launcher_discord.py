# SPDX-License-Identifier: GPL-2.0-or-later
"""Sign in with Discord in the launcher (bbport_discord.py) against a fake server and a fake
Discord: the authorization code with PKCE, `state` checked, the fixed loopback ports, plain http
refused, and every way it stops."""
import http.server
import json
import ssl
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'server' / 'tests'))
import bbport_coop as coop
import bbport_discord as discord
from fake_discord import challenge_of

BASE = 'https://play.example.com'


class Page(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class Answers:
    """Stands in for urllib: what the server answers, and what was asked."""

    def __init__(self, config=None, account=None, status=200):
        self.config = {'client_id': '123', 'ports': [47231, 47232]} if config is None else config
        self.account = {'id': 'd0123456789abcd', 'secret': 'a' * 32, 'name': 'Ada'} if account is None else account
        self.status = status
        self.asked = []

    def __call__(self, request, timeout=None, context=None):
        self.asked.append(request)
        if request.full_url.endswith('/bb/discord/config'):
            return self.reply(200, self.config)
        if self.status != 200:
            raise urllib.error.HTTPError(request.full_url, self.status, '', {}, None)
        return self.reply(200, self.account)

    @staticmethod
    def reply(status, body):
        answer = mock.MagicMock()
        answer.__enter__.return_value = answer
        answer.status = status
        answer.read.return_value = json.dumps(body).encode()
        return answer


def browser_says(**extra):
    """A browser that lands on the redirect with `extra` (with the right state unless given)."""
    def open_page(address):
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(address).query))
        browser_says.seen = query

        def land():
            answer = dict({'state': query['state']}, **extra)
            url = query['redirect_uri'] + '?' + urllib.parse.urlencode(answer)
            urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=5).read()
        threading.Thread(target=land, daemon=True).start()
        return True
    return open_page


class SignInTests(unittest.TestCase):
    def run_it(self, answers, browser=None, **options):
        with mock.patch.object(discord.urllib.request, 'urlopen', answers):
            return discord.sign_in(BASE, open_browser=browser or browser_says(code='the-code'), timeout=10, **options)

    def test_the_code_with_pkce_goes_to_the_server(self):
        answers = Answers()
        account = self.run_it(answers)
        self.assertEqual(account, {'id': 'd0123456789abcd', 'secret': 'a' * 32, 'name': 'Ada'})
        seen = browser_says.seen
        self.assertEqual(seen['client_id'], '123')
        self.assertEqual(seen['scope'], 'identify')
        self.assertEqual(seen['response_type'], 'code')
        self.assertEqual(seen['code_challenge_method'], 'S256')
        self.assertEqual(seen['redirect_uri'], 'http://127.0.0.1:47231/discord')
        sent = json.loads(answers.asked[-1].data)
        self.assertEqual(sent['code'], 'the-code')
        self.assertEqual(sent['redirect_uri'], seen['redirect_uri'])
        self.assertEqual(challenge_of(sent['code_verifier']), seen['code_challenge'], 'PKCE S256')
        self.assertGreaterEqual(len(sent['code_verifier']), 43)
        self.assertTrue(all(r.full_url.startswith(BASE) for r in answers.asked))

    def test_a_held_port_takes_the_next(self):
        with http.server.HTTPServer(('127.0.0.1', 47231), Page):
            self.run_it(Answers())
        self.assertEqual(browser_says.seen['redirect_uri'], 'http://127.0.0.1:47232/discord')

    def test_plain_http_is_refused_before_anything_is_sent(self):
        answers = Answers()
        with mock.patch.object(discord.urllib.request, 'urlopen', answers):
            for url in ('http://play.example.com', 'play.example.com', '', 'ftp://x'):
                with self.assertRaisesRegex(discord.SignInError, 'HTTPS'):
                    discord.sign_in(url, open_browser=browser_says(code='x'))
        self.assertEqual(answers.asked, [])

    def test_another_pages_state_is_not_the_answer(self):
        with self.assertRaisesRegex(discord.SignInError, 'too long'):
            def open_page(address):
                query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(address).query))

                def land():
                    url = query['redirect_uri'] + '?code=stolen&state=other'
                    try:
                        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=5)
                    except urllib.error.HTTPError:
                        pass
                threading.Thread(target=land, daemon=True).start()
                return True
            with mock.patch.object(discord.urllib.request, 'urlopen', Answers()):
                discord.sign_in(BASE, open_browser=open_page, timeout=1)

    def test_discord_saying_no(self):
        with self.assertRaisesRegex(discord.SignInError, 'did not let'):
            self.run_it(Answers(), browser=browser_says(error='access_denied'))

    def test_a_cancel_stops_the_wait(self):
        stop = threading.Event()
        stop.set()
        with self.assertRaisesRegex(discord.SignInError, 'cancelled'):
            self.run_it(Answers(), browser=lambda _a: True, stop=stop)

    def test_the_servers_refusals(self):
        for status, text in ((401, 'refused'), (400, 'refused'), (429, 'Too many'), (502, 'does not answer')):
            with self.assertRaisesRegex(discord.SignInError, text):
                self.run_it(Answers(status=status))

    def test_a_server_without_discord(self):
        with self.assertRaisesRegex(discord.SignInError, 'no Sign in'):
            self.run_it(Answers(config={}))

    def test_a_server_that_does_not_answer(self):
        with mock.patch.object(discord.urllib.request, 'urlopen', side_effect=ssl.SSLError('bad')):
            with self.assertRaisesRegex(discord.SignInError, 'does not answer'):
                discord.sign_in(BASE, open_browser=browser_says(code='x'))


class ServerTypeTests(unittest.TestCase):
    """The launcher's Local / Global step (bbport_coop.py)."""

    SECRET = format(int(time.time()), '08x') + 'a' * 24

    def signed(self, **more):
        return coop.signed_in_global(dict(coop.DEFAULTS, game='x', server_type='global', global_server=BASE, **more),
                                     {'id': 'd0123456789abcd', 'secret': self.SECRET, 'name': 'Ada'})

    def test_local_is_the_default_and_stays_as_it_was(self):
        self.assertEqual(coop.DEFAULTS['server_type'], 'local')
        settings = dict(coop.DEFAULTS, game='x', host_ip='26.1.2.3', account='p0123456789abcd', password='b' * 32)
        self.assertEqual(coop.missing(settings), [])
        self.assertEqual(coop.missing(dict(settings, host_ip='')), ['host_ip'])
        self.assertEqual(coop.played_settings(settings), settings)
        self.assertEqual(coop.player_id_for(settings, '26.1.2.3'), ('p0123456789abcd', 'b' * 32))

    def test_global_needs_a_sign_in_not_an_ip(self):
        settings = dict(coop.DEFAULTS, game='x', server_type='global', global_server=BASE)
        self.assertEqual(coop.missing(settings), ['discord'])
        self.assertEqual(coop.missing(self.signed()), [])

    def test_global_plays_as_the_discord_account_never_as_host(self):
        played = coop.played_settings(self.signed(role='host', host_ip='26.1.2.3'))
        self.assertEqual((played['host_ip'], played['role']), (BASE, 'guest'))
        self.assertEqual(coop.player_id_for(played, BASE), ('d0123456789abcd', self.SECRET))

    def test_an_old_secret_asks_for_a_new_sign_in(self):
        settings = self.signed()
        issued = int(self.SECRET[:8], 16)
        self.assertTrue(coop.is_signed_in_global(settings, now=issued + 28 * 86400))
        self.assertFalse(coop.is_signed_in_global(settings, now=issued + 29 * 86400 + 1))
        self.assertFalse(coop.is_signed_in_global(coop.signed_in_global(
            settings, {'id': 'd0123456789abcd', 'secret': 'not-hex-at-all'})))

    def test_sign_in_survives_in_coop_json_and_sign_out_forgets_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            coop.save_settings(Path(folder), self.signed())
            loaded = coop.read_settings(Path(folder))
            self.assertEqual(loaded['server_type'], 'global')
            self.assertEqual(loaded['discord_name'], 'Ada')
            self.assertEqual(coop.player_id_for(loaded, BASE), ('d0123456789abcd', self.SECRET))
            out = coop.signed_out_global(loaded)
            self.assertEqual(out['discord_name'], '')
            self.assertEqual(coop.missing(dict(out, game='x')), ['discord'])
            self.assertNotEqual(coop.player_id_for(out, BASE)[0], 'd0123456789abcd')

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
        self.assertEqual((seen['account'], seen['password']), ('d0123456789abcd', self.SECRET))
        self.assertEqual(seen['server'], BASE)

    def test_a_region_names_the_shard(self):
        settings = coop.played_settings(self.signed())
        shards = {'shards': [{'name': 'eu-1', 'address': '203.0.113.9:31314', 'key': 'ab' * 32, 'players': 3,
                              'capacity': 350}]}

        def fetch(url):
            return shards if url.endswith('/v1/shards') else None
        seen = coop.global_game_settings(settings, fetch=fetch)
        self.assertEqual((seen['host_ip'], seen['link_port']), ('203.0.113.9', '31314'))
        self.assertEqual(seen['account'], 'd0123456789abcd')

    def test_the_servers_refusal_of_a_new_id(self):
        line = 'x [Lib.Net] <Error> ' + coop.REFUSED_LINE + coop.DISCORD_FIRST + ' sign in with Discord'
        self.assertTrue(coop.needs_discord(line))
        self.assertFalse(coop.needs_discord(coop.REFUSED_LINE + 'address taken: something'))


if __name__ == '__main__':
    unittest.main()
