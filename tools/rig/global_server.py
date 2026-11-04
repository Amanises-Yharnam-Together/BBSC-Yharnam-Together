# SPDX-FileCopyrightText: Copyright 2026 shadNet Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""A Global server on the rig (docs/HOSTED_SERVER.md, "Global servers: accounts"): the lane's shadNet
hosted, and a local TLS proxy in front of its WebAPI as Caddy stands on a public server. Each game's
account is made and signed in the way the launcher does it (bbport_auth.py, the same code: a name and
a password, Kaniel 2026-11-03; the only sign-in, 2026-11-04), and it plays with what the server
answered. On the way the first role goes through what a player can meet: a second install, wrong
passwords and their wait, the recovery code, a sign out."""
import http.client
import http.server
import pathlib
import secrets
import ssl
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bbport" / "launcher"))
import bbport_auth  # noqa: E402

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
        headers["X-Forwarded-Proto"] = "https"
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
        self.proxy = None
        self.url = ""

    def settings(self) -> dict[str, str]:
        """shadnet.cfg for it (the rig's run_scenario SERVER_SETTINGS)."""
        # The hash as on the public server (its own parameters); the signup's work and the limits
        # small enough for one PC's few players.
        return {"Hosted": "true", "SignIn": "password", "SignInProxied": "true",
                "HostedSignupWorkBits": "14", "HostedNewAccountsPerHour": "100",
                "PasswordTriesPerMinute": "600"}

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

    def sign_in_roles(self, roles: list[str]) -> dict[str, tuple[str, str]]:
        """Each role its own account: role -> (id, secret)."""
        return self.accounts(roles)

    # --- the server's own accounts (bbport_auth.py) --------------------------------------------

    def call(self, what, *args):
        return what(self.url, *args, context=self.client)

    def expect_refused(self, text, what, *args):
        try:
            self.call(what, *args)
        except bbport_auth.AuthError as error:
            if error.text() != text:
                raise RuntimeError(f"{what.__name__}: {error.text()!r}, not {text!r}") from None
            return error
        raise RuntimeError(f"{what.__name__} went through: it should be refused ({text})")

    def walk_through(self, name: str, password: str, code: str) -> str:
        """What a player can meet, on the first role's account; its password at the end."""
        first = self.call(bbport_auth.sign_in, name, password)
        print(f"rig: {name}: a second install signed in as {first['id']}")
        # Plain http is never sent anything.
        plain = self.url.replace("https://", "http://")
        try:
            bbport_auth.sign_in(plain, name, password)
            raise RuntimeError("plain http was sent a password")
        except bbport_auth.AuthError as error:
            if error.text() != bbport_auth.PLAIN_HTTP_TEXT:
                raise
        # Wrong passwords: the same answer as a name nobody has, then waits, never a lock.
        self.expect_refused(bbport_auth.WRONG_TEXT, bbport_auth.sign_in, "rig-nobody", "not the password")
        wrong = 0
        while True:
            try:
                self.call(bbport_auth.sign_in, name, "not the password")
                raise RuntimeError("a wrong password went through")
            except bbport_auth.AuthError as error:
                if error.text() == bbport_auth.WAIT_TEXT:
                    break
                if error.text() != bbport_auth.WRONG_TEXT or wrong > 10:
                    raise
                wrong += 1
        # The first wait (1 s) may be over by the next request: after it, one more wrong one gives the
        # second (2 s), and in it even the right password waits.
        waited_from = time.monotonic()
        time.sleep(1.2)
        self.expect_refused(bbport_auth.WRONG_TEXT, bbport_auth.sign_in, name, "not the password")
        wait = self.expect_refused(bbport_auth.WAIT_TEXT, bbport_auth.sign_in, name, password).args[1]
        print(f"rig: {name}: {time.monotonic() - waited_from:.1f} s from the first wait to the second")
        print(f"rig: {name}: {wrong} wrong passwords, then a wait of {wait} s (even for the right one)")
        time.sleep(wait + 0.5)
        self.call(bbport_auth.sign_in, name, password)
        print(f"rig: {name}: the wait ended: signed in (no lock)")
        # Forgot password: the recovery code; every older sign-in dies with it.
        new_password = secrets.token_urlsafe(18)
        recovered = self.call(bbport_auth.recover, name, code.lower().replace("-", " "), new_password)
        if recovered["id"] != first["id"] or recovered["recovery_code"] == code:
            raise RuntimeError("the recovery gave another account or the same code")
        self.expect_refused(bbport_auth.WRONG_TEXT, bbport_auth.sign_in, name, password)
        self.expect_refused(bbport_auth.WRONG_CODE_TEXT, bbport_auth.recover, name, code, secrets.token_urlsafe(18))
        if self.call(bbport_auth.sign_out, first["id"], first["secret"]):
            raise RuntimeError("an older sign-in still lives after the recovery")
        print(f"rig: {name}: recovered with its code: a new password and code, the old ones dead")
        # Sign out: that secret and the older ones die; the next sign-in lives.
        signed = self.call(bbport_auth.sign_in, name, new_password)
        if not self.call(bbport_auth.sign_out, signed["id"], signed["secret"]):
            raise RuntimeError("the sign out was refused")
        if self.call(bbport_auth.sign_out, signed["id"], signed["secret"]):
            raise RuntimeError("a signed-out secret still lives")
        print(f"rig: {name}: signed out: its secret is dead")
        return new_password

    def accounts(self, roles: list[str]) -> dict[str, tuple[str, str]]:
        out = {}
        run = secrets.token_hex(2)  # the lane keeps its accounts from run to run
        for number, role in enumerate(roles):
            name = f"rig-{role}-{run}"[:bbport_auth.NAME_MAX]
            password = secrets.token_urlsafe(18)
            made = self.call(bbport_auth.sign_up, name, password)
            print(f"rig: {role} made the account {name} = {made['id']} (recovery code given)")
            self.expect_refused(bbport_auth.TAKEN_TEXT, bbport_auth.sign_up, name.upper(), secrets.token_urlsafe(18))
            if number == 0:
                password = self.walk_through(name, password, made["recovery_code"])
            # The install the game plays from: its own sign-in.
            account = self.call(bbport_auth.sign_in, name, password)
            if account["id"] != made["id"]:
                raise RuntimeError("a sign-in gave another account")
            out[role] = (account["id"], account["secret"])
            del password
        return out

