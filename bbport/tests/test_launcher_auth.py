# SPDX-License-Identifier: GPL-2.0-or-later
"""A Global server's own accounts in the launcher (bbport_auth.py) against a fake accounts server
behind real TLS: https only, the certificate checked, no redirect followed, the signup's work, what
each refusal says, and the password never in a file or a log."""
import ast
import contextlib
import hashlib
import http.server
import io
import json
import logging
import os
import pathlib
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))
import bbport_auth as auth  # noqa: E402
import bbport_coop as coop  # noqa: E402

OPENSSL = r'C:\Program Files\Git\mingw64\bin\openssl.exe'
PASSWORD = 'a long and fine password'
SECRET = format(int(time.time()), '08x') + 'b' * 24


class Accounts(http.server.BaseHTTPRequestHandler):
    """The server's /bb/auth/* as far as the launcher sees it."""

    def log_message(self, *_args):
        pass

    def reply(self, status, body, headers=()):
        data = json.dumps(body).encode()
        self.send_response(status)
        for key, value in headers:
            self.send_header(key, value)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.server.seen.append((self.path, None))
        if self.path == '/bb/auth/config':
            self.reply(200, {'sign_in': ['password'], 'work_bits': 8})
        else:
            self.reply(404, {})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])) or b'{}')
        self.server.seen.append((self.path, body))
        if self.server.answer:
            self.reply(*self.server.answer)
            return
        if self.path == '/bb/auth/challenge':
            self.reply(200, {'challenge': 'c' * 72, 'bits': 8})
        elif self.path == '/bb/auth/sign-up':
            prefix = b'bb signup v1|' + body['challenge'].encode() + b'|' + body['name'].lower().encode() + b'|'
            digest = hashlib.sha256(prefix + body['nonce'].to_bytes(8, 'little')).digest()
            if digest[0] != 0:
                self.reply(400, {'error': 'work'})
                return
            self.reply(200, {'id': 'u0123456789abcd', 'secret': SECRET, 'name': body['name'],
                             'recovery_code': 'ABCD-EFGH-JKMN-PQRS-TVWX'})
        elif self.path in ('/bb/auth/sign-in', '/bb/auth/change'):
            ok = body.get('password') == PASSWORD
            self.reply(200 if ok else 401, {'id': 'u0123456789abcd', 'secret': SECRET, 'name': 'Kaniel'}
                       if ok else {'error': 'wrong name or password'})
        elif self.path == '/bb/auth/recover':
            self.reply(200, {'id': 'u0123456789abcd', 'secret': SECRET, 'name': 'Kaniel',
                             'recovery_code': 'ZZZZ-EFGH-JKMN-PQRS-TVWX'})
        elif self.path == '/bb/auth/sign-out':
            self.reply(200, {'signed_out': True})
        else:
            self.reply(404, {})


class Server:
    def __init__(self, folder):
        cert, key = Path(folder) / 'cert.pem', Path(folder) / 'key.pem'
        subprocess.run([OPENSSL, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2', '-subj',
                        '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Accounts)
        self.httpd.seen, self.httpd.answer = [], None
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        self.httpd.socket = context.wrap_socket(self.httpd.socket, server_side=True)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f'https://localhost:{self.httpd.server_address[1]}'
        self.trusted = ssl.create_default_context(cafile=str(cert))

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@unittest.skipUnless(os.path.exists(OPENSSL), 'needs Git for Windows\' openssl')
class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.server = Server(cls.folder.name)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.folder.cleanup()

    def setUp(self):
        self.server.httpd.seen.clear()
        self.server.httpd.answer = None

    def call(self, call, *args):
        return call(self.server.url, *args, context=self.server.trusted)

    def test_plain_http_is_refused_before_anything_is_sent(self):
        for url in ('http://localhost:1', 'localhost:1', '', 'ftp://x', 'https://'):
            with self.assertRaises(auth.AuthError) as refused:
                auth.sign_in(url, 'kaniel', PASSWORD)
            self.assertEqual(refused.exception.text(), auth.PLAIN_HTTP_TEXT)
        self.assertEqual(self.server.httpd.seen, [])

    def test_a_certificate_that_does_not_hold_is_never_sent_a_password(self):
        # The system's certificates do not know this server's: refused before the request.
        with self.assertRaises(auth.AuthError) as refused:
            auth.sign_in(self.server.url, 'kaniel', PASSWORD)
        self.assertEqual(refused.exception.text(), auth.CERTIFICATE_TEXT)
        # The reason the TLS layer gave goes along, for a report (2026-11-06: 1.4.0 sign-in said only
        # "not valid").
        self.assertTrue(refused.exception.args[1])
        self.assertEqual(self.server.httpd.seen, [])
        # Another host name than the certificate's.
        wrong_host = self.server.url.replace('localhost', '127.0.0.2')
        with self.assertRaises(auth.AuthError):
            auth.sign_in(wrong_host, 'kaniel', PASSWORD, context=self.server.trusted)
        self.assertEqual(self.server.httpd.seen, [])

    def test_a_redirect_is_never_followed(self):
        self.server.httpd.answer = (307, {}, [('Location', 'http://127.0.0.1:9/bb/auth/sign-in')])
        with self.assertRaises(auth.AuthError) as refused:
            self.call(auth.sign_in, 'kaniel', PASSWORD)
        self.assertEqual(refused.exception.text(), auth.REFUSED_TEXT)
        self.assertEqual(len(self.server.httpd.seen), 1)

    def test_sign_up_does_the_work_and_gives_a_recovery_code(self):
        account = self.call(auth.sign_up, 'Kaniel', PASSWORD)
        self.assertEqual(account, {'id': 'u0123456789abcd', 'secret': SECRET, 'name': 'Kaniel',
                                   'recovery_code': 'ABCD-EFGH-JKMN-PQRS-TVWX'})
        paths = [path for path, _body in self.server.httpd.seen]
        self.assertEqual(paths, ['/bb/auth/challenge', '/bb/auth/sign-up'])
        self.assertEqual(self.server.httpd.seen[1][1]['password'], PASSWORD)

    def test_what_the_server_would_refuse_is_never_sent(self):
        for name, password, text in (('ab', PASSWORD, auth.NAME_LENGTH_TEXT),
                                     ('Kan iel', PASSWORD, auth.NAME_CHARACTERS_TEXT),
                                     ('kaniel', 'short one', auth.SHORT_TEXT),
                                     ('kaniel', 'x' * 129, auth.LONG_TEXT),
                                     ('kaniel', 'my KANIEL password', auth.HAS_NAME_TEXT)):
            with self.assertRaises(auth.AuthError) as refused:
                self.call(auth.sign_up, name, password)
            self.assertEqual(refused.exception.text(), text)
        with self.assertRaises(auth.AuthError) as refused:
            self.call(auth.change_password, 'kaniel', PASSWORD, PASSWORD)
        self.assertEqual(refused.exception.text(), auth.SAME_TEXT)
        self.assertEqual(self.server.httpd.seen, [])

    def test_each_refusal_says_why(self):
        cases = [((401, {'error': 'wrong name or password'}), auth.WRONG_TEXT),
                 ((429, {'error': 'wait', 'seconds': 8}), auth.WAIT_TEXT),
                 ((429, {'error': 'signups'}), auth.SIGNUPS_TEXT),
                 ((503, {'error': 'busy'}), auth.BUSY_TEXT),
                 ((409, {'error': 'taken'}), auth.TAKEN_TEXT),
                 ((400, {'error': 'password', 'problem': 'common'}), auth.COMMON_TEXT),
                 ((404, {}), auth.NOT_GLOBAL_TEXT)]
        for answer, text in cases:
            self.server.httpd.answer = answer
            with self.assertRaises(auth.AuthError) as refused:
                self.call(auth.sign_in, 'kaniel', PASSWORD)
            self.assertEqual(refused.exception.text(), text)
        self.server.httpd.answer = (429, {'error': 'wait', 'seconds': 8})
        with self.assertRaises(auth.AuthError) as refused:
            self.call(auth.sign_in, 'kaniel', PASSWORD)
        self.assertEqual(refused.exception.args[1], 8)
        self.server.httpd.answer = (401, {})
        with self.assertRaises(auth.AuthError) as refused:
            self.call(auth.recover, 'kaniel', 'XXXX', 'a new and better password')
        self.assertEqual(refused.exception.text(), auth.WRONG_CODE_TEXT)

    def test_sign_in_change_recover_and_sign_out(self):
        self.assertEqual(self.call(auth.sign_in, 'kaniel', PASSWORD)['id'], 'u0123456789abcd')
        self.assertEqual(self.call(auth.change_password, 'kaniel', PASSWORD, 'a new and better one')['secret'], SECRET)
        recovered = self.call(auth.recover, 'kaniel', 'abcd efgh', 'a new and better one')
        self.assertEqual(recovered['recovery_code'], 'ZZZZ-EFGH-JKMN-PQRS-TVWX')
        self.assertTrue(self.call(auth.sign_out, 'u0123456789abcd', SECRET))
        self.assertFalse(auth.sign_out('http://plain', 'u0123456789abcd', SECRET))
        self.assertEqual(self.call(auth.config)['sign_in'], ['password'])

    def test_the_password_never_reaches_a_file_or_a_log(self):
        with tempfile.TemporaryDirectory() as install:
            out, err, logs = io.StringIO(), io.StringIO(), io.StringIO()
            handler = logging.StreamHandler(logs)
            logging.getLogger().addHandler(handler)
            logging.getLogger().setLevel(logging.DEBUG)
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    settings = dict(coop.DEFAULTS, server_type='global', global_server=self.server.url)
                    account = self.call(auth.sign_up, 'Kaniel', PASSWORD)
                    settings = coop.signed_in_global(settings, account)
                    coop.save_settings(install, settings)
                    settings = coop.signed_in_global(settings, self.call(auth.sign_in, 'Kaniel', PASSWORD))
                    coop.save_settings(install, settings)
                    loaded = coop.load_settings(install)
            finally:
                logging.getLogger().removeHandler(handler)
            self.assertTrue(coop.is_signed_in_global(loaded))
            self.assertEqual(loaded['global_name'], 'Kaniel')
            # Only the signed secret is kept; never the password, never the recovery code.
            for path in pathlib.Path(install).rglob('*'):
                if path.is_file():
                    data = path.read_bytes()
                    self.assertNotIn(PASSWORD.encode(), data, path)
                    self.assertNotIn(b'ABCD-EFGH', data, path)
            for text in (out.getvalue(), err.getvalue(), logs.getvalue()):
                self.assertNotIn(PASSWORD, text)


class NotTls(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.recv(1024)
        self.request.sendall(b'HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n')


class TlsErrorTests(unittest.TestCase):
    """2026-11-06: every TLS failure said "The server's certificate is not valid", the reason lost."""

    def test_a_connection_that_is_not_tls_is_not_called_a_bad_certificate(self):
        server = socketserver.TCPServer(('127.0.0.1', 0), NotTls)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with self.assertRaises(auth.AuthError) as refused:
                auth.sign_in(f'https://127.0.0.1:{server.server_address[1]}', 'kaniel', PASSWORD)
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(refused.exception.text(), auth.CONNECTION_TEXT)
        self.assertTrue(refused.exception.args[1])

    def test_the_reason_goes_into_the_text(self):
        verify = ssl.SSLCertVerificationError(1, 'certificate verify failed')
        verify.verify_message, verify.reason = 'unable to get local issuer certificate', 'CERTIFICATE_VERIFY_FAILED'
        error = auth._tls_error(verify)
        self.assertEqual(error.args, (auth.CERTIFICATE_TEXT, 'unable to get local issuer certificate'))
        alert = ssl.SSLError(1, 'alert')
        alert.reason = 'TLSV1_ALERT_PROTOCOL_VERSION'
        self.assertEqual(auth._tls_error(alert).args, (auth.CONNECTION_TEXT, 'TLSV1_ALERT_PROTOCOL_VERSION'))
        self.assertEqual(auth._tls_error(ssl.SSLEOFError()).args, (auth.CONNECTION_TEXT, 'SSLEOFError'))
        for text in (auth.CERTIFICATE_TEXT, auth.CONNECTION_TEXT):
            self.assertIn('not sent', text.format('x'))


class TrustContext(ssl.SSLContext):
    pass


class SystemCertificateTests(unittest.TestCase):
    """2026-11-06: 1.4.0 sign-in refused seamlesshunt.com on PCs whose Windows store had no ISRG Root X1
    yet: Check for updates went through truststore, sign-in through Python's own store."""

    def tearDown(self):
        urllib.request.install_opener(None)

    @staticmethod
    def contexts(opener):
        return [handler._context for handler in (opener.handlers if opener else ())
                if isinstance(handler, urllib.request.HTTPSHandler)]

    def test_sign_in_checks_certificates_through_truststore(self):
        with mock.patch.dict(sys.modules, {'truststore': mock.Mock(SSLContext=TrustContext)}):
            [context] = self.contexts(auth._opener(None))
        self.assertIsInstance(context, TrustContext)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_without_truststore_sign_in_still_checks_certificates(self):
        for truststore in (None, mock.Mock(SSLContext=mock.Mock(side_effect=FileNotFoundError('none')))):
            with mock.patch.dict(sys.modules, {'truststore': truststore}):
                [context] = self.contexts(auth._opener(None))
            self.assertNotIsInstance(context, TrustContext)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)

    def test_sign_in_and_every_urlopen_take_the_same_truststore_path(self):
        made = []

        def truststore_context():
            made.append(TrustContext(ssl.PROTOCOL_TLS_CLIENT))
            return made[-1]

        with mock.patch.object(auth, 'truststore_context', truststore_context):
            self.assertTrue(coop.use_system_certificates())
            [updates] = self.contexts(urllib.request._opener)
            [sign_in] = self.contexts(auth._opener(None))
        self.assertEqual(made, [updates, sign_in])
        # And with no truststore context, both keep a default that still checks.
        with mock.patch.object(auth, 'truststore_context', lambda: None):
            urllib.request.install_opener(None)
            self.assertFalse(coop.use_system_certificates())
            self.assertIsNone(urllib.request._opener)
            [sign_in] = self.contexts(auth._opener(None))
        self.assertEqual(sign_in.verify_mode, ssl.CERT_REQUIRED)


class OfflineTests(unittest.TestCase):
    def test_every_language_has_every_account_text(self):
        import bbport_lang
        import bbport_lang_auth as lang
        texts = [getattr(auth, key) for key in dir(auth) if key.endswith('_TEXT')] + [coop.GLOBAL_CLOSED_TEXT]
        for text in texts:
            self.assertIn(text, lang.AUTH_KEYS)
        # The Global step's own words (the window's build_coop_accounts and what follows it).
        source = (Path(__file__).resolve().parents[1] / 'launcher' / 'bbport_launcher_win.py').read_text('utf-8')
        part = source[source.index('    def build_coop_server'):source.index('    def coop_rule_var')]
        words = [node.args[0].value for node in ast.walk(ast.parse('class X:\n' + part))
                 if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == '_'
                 and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertGreater(len(words), 25)
        for text in words:
            self.assertIn(text, lang.AUTH_KEYS + ['Password', 'Copy', 'Back'])
        languages = [code for code, _names in bbport_lang.LANGUAGE_NAMES if code not in ('', 'en')]
        self.assertEqual(sorted(lang.AUTH), sorted(languages))
        for language in languages:
            table = bbport_lang.table(language)
            for key in lang.AUTH_KEYS:
                self.assertTrue(table.get(key), (language, key))
                self.assertEqual(key.count('{}'), table[key].count('{}'), (language, key))

    def test_the_strength_hint(self):
        self.assertEqual(auth.strength('short'), 0)
        self.assertEqual(auth.strength('aaaaaaaaaaaaaaaaaaaaaaa'), 1)  # long but one letter
        self.assertEqual(auth.strength('tenletters'), 1)
        self.assertEqual(auth.strength('Ten-letters9'), 2)
        self.assertEqual(auth.strength('correct horse battery staple'), 3)

    def test_the_work_matches_the_servers(self):
        nonce = auth.solve('c' * 72, 'Kaniel', 12)
        digest = hashlib.sha256(b'bb signup v1|' + b'c' * 72 + b'|kaniel|' + nonce.to_bytes(8, 'little')).digest()
        self.assertEqual(int.from_bytes(digest, 'big') >> (256 - 12), 0)
        with self.assertRaises(auth.AuthError):
            auth.solve('c' * 72, 'Kaniel', auth.MAX_WORK_BITS + 1)

    def test_the_servers_refusals_of_a_hello(self):
        line = coop.REFUSED_LINE + 'account: sign in in the launcher first'
        self.assertTrue(coop.needs_sign_in('x [Lib.Net] <Error> ' + line))
        self.assertFalse(coop.needs_sign_in(coop.REFUSED_LINE + 'address taken: something'))

    def test_global_needs_the_sign_in(self):
        self.assertEqual(coop.missing(dict(coop.DEFAULTS, server_type='global', game='x',
                                           global_server='https://play.example.com')), ['sign_in'])


if __name__ == '__main__':
    unittest.main()
