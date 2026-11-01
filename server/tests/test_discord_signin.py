# SPDX-FileCopyrightText: Copyright 2026 shadNet Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""POST /bb/discord/sign-in against a fake Discord (fake_discord.py): a good code gives the one
account of that Discord user; a replayed, expired or wrong code, a wrong verifier and a redirect
that is not ours give nothing; an address's sign-ins are limited; a server without Discord has no
such route.

Needs a built shadnet: SHADNET_EXE=<path to shadnet>. Skipped without it."""

import contextlib
import http.client
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

from fake_discord import CLIENT_ID, CLIENT_SECRET, FakeDiscord, challenge_of

SHADNET = os.environ.get("SHADNET_EXE", "")
REDIRECT = "http://127.0.0.1:47231/discord"
VERIFIER = "v" * 64


def free_port(kind=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET, kind) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, home, **settings):
        self.webapi = free_port()
        config = {"Host": "127.0.0.1", "UnsecuredPort": free_port(),
                  "MatchingUdpPort": free_port(socket.SOCK_DGRAM), "WebApiPort": self.webapi,
                  "StatsEnabled": "false", "BloodborneSeamlessCoop": "true",
                  "BloodborneBackend": "false", "Hosted": "true"}
        config.update(settings)
        with open(os.path.join(home, "shadnet.cfg"), "w", encoding="utf-8") as f:
            f.write("[General]\n")
            for key, value in config.items():
                f.write("{}={}\n".format(key, value))
        self.log = open(os.path.join(home, "shadnet.log"), "wb")
        self.proc = subprocess.Popen([SHADNET], cwd=home, env=dict(os.environ, SHADNET_HOME=home),
                                     stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.time() + 20
        while time.time() < deadline:
            with contextlib.suppress(OSError):
                socket.create_connection(("127.0.0.1", self.webapi), timeout=0.5).close()
                return
            time.sleep(0.1)
        raise RuntimeError("shadnet did not start")

    def stop(self):
        self.proc.terminate()
        self.proc.wait(10)
        self.log.close()

    def call(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.webapi, timeout=15)
        data = None if body is None else json.dumps(body)
        conn.request(method, path, data, dict({"Content-Type": "application/json"}, **(headers or {})))
        answer = conn.getresponse()
        text = answer.read()
        conn.close()
        return answer.status, json.loads(text) if text[:1] == b"{" else text


@unittest.skipUnless(SHADNET, "needs SHADNET_EXE")
class SignInTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="shadnet-discord-")
        self.fake = FakeDiscord().start()
        self.server = Server(self.home, DiscordClientId=CLIENT_ID, DiscordClientSecret=CLIENT_SECRET,
                             DiscordApiBase=self.fake.base, DiscordSignInsPerMinute=1000)

    def tearDown(self):
        self.server.stop()
        self.fake.stop()
        shutil.rmtree(self.home, ignore_errors=True)

    def sign_in(self, code, verifier=VERIFIER, redirect=REDIRECT):
        return self.server.call("POST", "/bb/discord/sign-in", {
            "code": code, "code_verifier": verifier, "redirect_uri": redirect})

    def code(self, **options):
        return self.fake.issue(challenge_of(VERIFIER), REDIRECT, **options)

    def test_the_launcher_reads_what_it_needs(self):
        status, body = self.server.call("GET", "/bb/discord/config")
        self.assertEqual(status, 200)
        self.assertEqual(body["client_id"], CLIENT_ID)
        self.assertEqual(body["ports"], [47231, 47232, 47233, 47234])
        self.assertNotIn(CLIENT_SECRET, json.dumps(body))

    def test_one_discord_user_is_one_account(self):
        status, first = self.sign_in(self.code())
        self.assertEqual(status, 200, first)
        self.assertRegex(first["id"], r"^d[0-9a-f]{14}$")
        self.assertRegex(first["secret"], r"^[0-9a-f]{32}$")
        self.assertEqual(first["name"], "Ada")
        # Another PC, a later day: the same account.
        status, again = self.sign_in(self.code())
        self.assertEqual((status, again["id"], again["secret"]), (200, first["id"], first["secret"]))
        status, other = self.sign_in(self.code(user=("2", "bo", None)))
        self.assertEqual(status, 200)
        self.assertNotEqual(other["id"], first["id"])
        self.assertEqual(other["name"], "bo", "no global name: the username")

    def test_a_code_works_once(self):
        code = self.code()
        self.assertEqual(self.sign_in(code)[0], 200)
        status, body = self.sign_in(code)
        self.assertEqual(status, 401)
        self.assertNotIn("id", body)

    def test_an_expired_code_is_refused(self):
        self.assertEqual(self.sign_in(self.code(lifetime=-1))[0], 401)

    def test_a_wrong_code_or_verifier_is_refused(self):
        self.assertEqual(self.sign_in("no-such-code")[0], 401)
        self.assertEqual(self.sign_in(self.code(), verifier="w" * 64)[0], 401)

    def test_only_our_loopback_redirect(self):
        before = self.fake.exchanges
        for redirect in ("http://evil.example.com/discord", "http://127.0.0.1:1234/discord", ""):
            self.assertEqual(self.sign_in(self.code(), redirect=redirect)[0], 400, redirect)
        self.assertEqual(self.fake.exchanges, before, "not even asked")

    def test_a_broken_request_is_refused(self):
        self.assertEqual(self.server.call("POST", "/bb/discord/sign-in", {"code": "x"})[0], 400)
        conn = http.client.HTTPConnection("127.0.0.1", self.server.webapi, timeout=5)
        conn.request("POST", "/bb/discord/sign-in", b"not json")
        self.assertEqual(conn.getresponse().status, 400)
        conn.close()

    def test_nothing_of_it_in_the_log(self):
        code = self.code()
        self.sign_in(code)
        self.server.log.flush()
        with open(os.path.join(self.home, "shadnet.log"), "rb") as f:
            text = f.read()
        for secret in (CLIENT_SECRET.encode(), code.encode(), VERIFIER.encode()):
            self.assertNotIn(secret, text)


@unittest.skipUnless(SHADNET, "needs SHADNET_EXE")
class LimitTests(unittest.TestCase):
    def test_an_addresses_sign_ins_are_limited(self):
        home = tempfile.mkdtemp(prefix="shadnet-discord-")
        fake = FakeDiscord().start()
        server = Server(home, DiscordClientId=CLIENT_ID, DiscordClientSecret=CLIENT_SECRET,
                        DiscordApiBase=fake.base, DiscordSignInsPerMinute=3)
        try:
            answers = [server.call("POST", "/bb/discord/sign-in", {
                "code": "x", "code_verifier": VERIFIER, "redirect_uri": REDIRECT})[0]
                for _i in range(5)]
            self.assertEqual(answers[:3], [401] * 3)
            self.assertEqual(answers[3:], [429] * 2)
        finally:
            server.stop()
            fake.stop()
            shutil.rmtree(home, ignore_errors=True)


@unittest.skipUnless(SHADNET, "needs SHADNET_EXE")
class NoDiscordTests(unittest.TestCase):
    def test_a_server_without_discord_has_no_sign_in(self):
        home = tempfile.mkdtemp(prefix="shadnet-discord-")
        server = Server(home)
        try:
            self.assertEqual(server.call("GET", "/bb/discord/config")[0], 404)
            self.assertEqual(server.call("POST", "/bb/discord/sign-in", {"code": "x"})[0], 404)
        finally:
            server.stop()
            shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
