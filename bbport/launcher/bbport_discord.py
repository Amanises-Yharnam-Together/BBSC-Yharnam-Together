# SPDX-License-Identifier: GPL-2.0-or-later
"""Sign in with Discord for a Global server (docs/HOSTED_SERVER.md): OAuth2 authorization code with
PKCE, scope identify, in the player's own browser, the answer caught on a fixed loopback port. The
server, over HTTPS only, turns the code into the player's one account: this launcher never sees a
Discord token, and there is no login or password anywhere."""
import base64
import hashlib
import html
import http.server
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

AUTHORIZE_URL = 'https://discord.com/oauth2/authorize'
SIGN_IN_SECONDS = 180

PLAIN_HTTP_TEXT = 'A Global server must be reached over HTTPS: its address has to start with https://.'
NO_SERVER_TEXT = 'The server does not answer: try again in a minute.'
NOT_GLOBAL_TEXT = 'This server has no Sign in with Discord.'
NO_PORT_TEXT = 'Another program holds every port the sign-in uses: close it and try again.'
TIMED_OUT_TEXT = 'The sign-in took too long: try again.'
CANCELLED_TEXT = 'The sign-in was cancelled.'
DENIED_TEXT = 'Discord did not let the sign-in through.'
REFUSED_TEXT = 'The server refused the sign-in: try again.'
BUSY_TEXT = 'Too many sign-ins: try again in a minute.'
PAGE = ('<!doctype html><meta charset="utf-8"><title>Yharnam Together</title>'
        '<body style="background:#14110f;color:#d8cfc0;font-family:serif;text-align:center;padding-top:20vh">'
        '<h2>{}</h2><p>You can close this page and go back to the launcher.</p>')


class SignInError(RuntimeError):
    """What the sign-in stopped on, in words for the player."""


def https_base(url):
    """The server's address without the slash at its end; SignInError unless it is https."""
    url = (url or '').strip().rstrip('/')
    if not url.lower().startswith('https://') or len(url) <= len('https://'):
        raise SignInError(PLAIN_HTTP_TEXT)
    return url


def pkce_pair():
    """(verifier, S256 challenge)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')


def authorize_address(client_id, redirect, state, challenge, authorize=AUTHORIZE_URL):
    return authorize + '?' + urllib.parse.urlencode({
        'client_id': client_id, 'response_type': 'code', 'scope': 'identify', 'redirect_uri': redirect,
        'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256', 'prompt': 'none'})


class _Loopback(http.server.HTTPServer):
    allow_reuse_address = False  # on Windows it would share a port another program holds


class _Catcher(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(url.query)
        if url.path != '/discord' or query.get('state', [''])[0] != self.server.state:
            self.send_error(404)  # a page that is not the answer (or not to this sign-in)
            return
        self.server.answer = {key: values[0] for key, values in query.items()}
        said = 'Signed in.' if 'code' in self.server.answer else 'Not signed in.'
        data = PAGE.format(html.escape(said)).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def listen(ports, state):
    """A one-page server on the first free port of `ports`, loopback only."""
    for port in ports:
        try:
            server = _Loopback(('127.0.0.1', port), _Catcher)
        except OSError:
            continue
        server.timeout = 0.25
        server.state, server.answer = state, None
        return server
    raise SignInError(NO_PORT_TEXT)


def _json(request, context):
    try:
        with urllib.request.urlopen(request, timeout=20, context=context) as answer:
            return answer.status, json.loads(answer.read())
    except urllib.error.HTTPError as error:
        return error.code, {}
    except (OSError, ValueError) as error:
        raise SignInError(NO_SERVER_TEXT) from error


def sign_in(url, open_browser=webbrowser.open, stop=None, timeout=SIGN_IN_SECONDS, context=None,
            authorize=AUTHORIZE_URL):
    """The player's account on the Global server at `url`: {'id', 'secret', 'name'}. Waits for the
    browser; `stop` (a threading.Event) cancels. SignInError says why not."""
    base = https_base(url)
    status, config = _json(urllib.request.Request(base + '/bb/discord/config'), context)
    if status != 200 or not config.get('client_id') or not config.get('ports'):
        raise SignInError(NOT_GLOBAL_TEXT)
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(24)
    catcher = listen(config['ports'], state)
    try:
        redirect = f'http://127.0.0.1:{catcher.server_address[1]}/discord'
        open_browser(authorize_address(config['client_id'], redirect, state, challenge, authorize))
        ends = time.monotonic() + timeout
        while catcher.answer is None:
            if stop is not None and stop.is_set():
                raise SignInError(CANCELLED_TEXT)
            if time.monotonic() >= ends:
                raise SignInError(TIMED_OUT_TEXT)
            catcher.handle_request()
        code = catcher.answer.get('code')
    finally:
        catcher.server_close()
    if not code:
        raise SignInError(DENIED_TEXT)
    request = urllib.request.Request(
        base + '/bb/discord/sign-in', method='POST',
        data=json.dumps({'code': code, 'code_verifier': verifier, 'redirect_uri': redirect}).encode('utf-8'),
        headers={'Content-Type': 'application/json'})
    status, account = _json(request, context)
    if status == 429:
        raise SignInError(BUSY_TEXT)
    if status != 200 or not account.get('id') or not account.get('secret'):
        raise SignInError(REFUSED_TEXT if status in (400, 401) else NO_SERVER_TEXT)
    return {'id': account['id'], 'secret': account['secret'], 'name': account.get('name', '')}


def sign_in_thread(url, done, **options):
    """sign_in off the window's thread: done(account, None) or done(None, text); the Event cancels."""
    stop = threading.Event()

    def run():
        try:
            done(sign_in(url, stop=stop, **options), None)
        except SignInError as error:
            done(None, str(error))
    threading.Thread(target=run, daemon=True).start()
    return stop
