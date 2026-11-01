# SPDX-FileCopyrightText: Copyright 2026 shadNet Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""A stand-in for Discord's OAuth2 endpoints, for the sign-in's tests: /oauth2/authorize (the user
always agrees), /oauth2/token (client id and secret, single-use codes, expiry, PKCE S256,
redirect_uri) and /users/@me. Run alone with --port for a hand test."""

import argparse
import base64
import hashlib
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

CLIENT_ID = "1234567890"
CLIENT_SECRET = "fake-client-secret"


def challenge_of(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class FakeDiscord(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port=0, user=("80351110224678912", "ada", "Ada")):
        super().__init__(("127.0.0.1", port), Handler)
        self.user = user
        self.codes = {}
        self.tokens = {}
        self.refuse_all = False
        self.exchanges = 0
        self.lock = threading.Lock()

    @property
    def base(self):
        return "http://127.0.0.1:{}".format(self.server_address[1])

    def issue(self, challenge, redirect, user=None, lifetime=60.0):
        code = secrets.token_urlsafe(16)
        with self.lock:
            self.codes[code] = {"challenge": challenge, "redirect": redirect,
                                "user": user or self.user, "until": time.time() + lifetime}
        return code

    def start(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self

    def stop(self):
        self.shutdown()
        self.server_close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def answer(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/oauth2/authorize":
            query = parse_qs(url.query)
            redirect = query["redirect_uri"][0]
            code = self.server.issue(query["code_challenge"][0], redirect)
            self.send_response(302)
            self.send_header("Location", redirect + "?" + urlencode(
                {"code": code, "state": query["state"][0]}))
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif url.path == "/users/@me":
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            user = self.server.tokens.get(token)
            if not user:
                self.answer(401, {"message": "401: Unauthorized"})
                return
            self.answer(200, {"id": user[0], "username": user[1], "global_name": user[2]})
        else:
            self.answer(404, {})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
        server = self.server
        server.exchanges += 1
        if self.path != "/oauth2/token":
            self.answer(404, {})
            return
        if server.refuse_all or form.get("client_id") != CLIENT_ID or \
                form.get("client_secret") != CLIENT_SECRET or \
                form.get("grant_type") != "authorization_code":
            self.answer(401, {"error": "invalid_client"})
            return
        with server.lock:
            issued = server.codes.pop(form.get("code", ""), None)  # single use
        if not issued or issued["until"] < time.time() or \
                issued["redirect"] != form.get("redirect_uri") or \
                challenge_of(form.get("code_verifier", "")) != issued["challenge"]:
            self.answer(400, {"error": "invalid_grant"})
            return
        token = secrets.token_urlsafe(16)
        server.tokens[token] = issued["user"]
        self.answer(200, {"access_token": token, "token_type": "Bearer", "expires_in": 604800,
                          "scope": "identify"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    fake = FakeDiscord(args.port)
    print("fake Discord at", fake.base, flush=True)
    fake.serve_forever()


if __name__ == "__main__":
    main()
