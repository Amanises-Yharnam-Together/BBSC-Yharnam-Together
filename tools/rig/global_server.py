# SPDX-FileCopyrightText: Copyright 2026 shadNet Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""A Global server on the rig (docs/HOSTED_SERVER.md, "Sign in with Discord"): the lane's shadNet
hosted, a fake Discord, and a local TLS proxy in front of its WebAPI as Caddy stands on a public
server. Each game signs in the way the launcher does (bbport_discord.py, the same code), each its
own Discord user, and plays with what the server answered."""
import http.client
import http.server
import pathlib
import ssl
import subprocess
import sys
import threading
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bbport" / "launcher"))
sys.path.insert(0, str(ROOT / "server" / "tests"))
import bbport_discord  # noqa: E402
from fake_discord import CLIENT_ID, CLIENT_SECRET, FakeDiscord  # noqa: E402

OPENSSL = r"C:\Program Files\Git\mingw64\bin\openssl.exe"


class _Proxy(http.server.BaseHTTPRequestHandler):
    """HTTPS to the WebAPI's plain port, adding the client's address as Caddy does."""

    def log_message(self, *_args):
        pass

    def forward(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
        headers["X-Forwarded-For"] = self.client_address[0]
        target = http.client.HTTPConnection("127.0.0.1", self.server.webapi, timeout=20)
        target.request(self.command, self.path, body, headers)
        answer = target.getresponse()
        data = answer.read()
        self.send_response(answer.status)
        self.send_header("Content-Type", answer.getheader("Content-Type", "application/json"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        target.close()

    do_GET = do_POST = forward


def make_certificate(folder: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    cert, key = folder / "tls-cert.pem", folder / "tls-key.pem"
    subprocess.run([OPENSSL, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
                    "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
                    "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True)
    return cert, key


class GlobalServer:
    def __init__(self, webapi_port: int, folder: pathlib.Path):
        self.webapi_port = webapi_port
        self.folder = folder
        self.fake = FakeDiscord().start()
        self.proxy = None
        self.url = ""

    def settings(self) -> dict[str, str]:
        """shadnet.cfg for it (the rig's run_scenario SERVER_SETTINGS)."""
        return {"Hosted": "true", "DiscordClientId": CLIENT_ID, "DiscordClientSecret": CLIENT_SECRET,
                "DiscordApiBase": self.fake.base, "DiscordProxied": "true"}

    def start(self):
        cert, key = make_certificate(self.folder)
        self.proxy = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Proxy)
        self.proxy.webapi = self.webapi_port
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        self.proxy.socket = context.wrap_socket(self.proxy.socket, server_side=True)
        threading.Thread(target=self.proxy.serve_forever, daemon=True).start()
        self.url = f"https://localhost:{self.proxy.server_address[1]}"
        self.client = ssl.create_default_context(cafile=str(cert))

    def stop(self):
        if self.proxy:
            self.proxy.shutdown()
            self.proxy.server_close()
        self.fake.stop()

    def browser(self, address: str) -> bool:
        """What the player's browser does: Discord's page, the user agrees, the redirect lands."""
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        threading.Thread(target=lambda: opener.open(address, timeout=20).read(), daemon=True).start()
        return True

    def sign_in(self, user: tuple[str, str, str]) -> dict[str, str]:
        self.fake.user = user
        return bbport_discord.sign_in(self.url, open_browser=self.browser, timeout=30, context=self.client,
                                      authorize=self.fake.base + "/oauth2/authorize")

    def sign_in_roles(self, roles: list[str]) -> dict[str, tuple[str, str]]:
        """Each role its own Discord user: role -> (id, secret)."""
        out = {}
        for number, role in enumerate(roles):
            account = self.sign_in((str(900000000000000000 + number), f"rig{number}", role))
            again = self.sign_in((str(900000000000000000 + number), f"rig{number}", role))
            if again["id"] != account["id"]:
                raise RuntimeError("a second sign-in gave another account")
            print(f"rig: {role} signed in with Discord as {again['id']} (twice, one account)")
            out[role] = (again["id"], again["secret"])
        return out
