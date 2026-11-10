# SPDX-License-Identifier: GPL-2.0-or-later
"""The launcher's smaller player reports (Discord audit 2026-11-10, task A15):

- the host's co-op server kept running after the launcher was closed (Provi 2026-10-21, Omegadash
  2026-10-30): it now goes with the launcher, or with the game when that outlives the launcher;
- Bloodborne.exe and the Steam shortcut started the game without the co-op settings, so it could not
  reach the server (LeWhiske 2026-11-05);
- a Game of the Year edition showed The Old Hunters as "Not installed" (Dinkles 2026-10-31);
- PLAY stopped on "[Errno 13] Permission denied" for a stray entry in the game folder (Xenix005
  2026-10-30)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from paths import ROOT

sys.path.insert(0, str(ROOT / 'launcher'))

import bbport_coop as coop  # noqa: E402
from test_coop_launcher import make_game  # noqa: E402

spec = importlib.util.spec_from_file_location('bbmods_leftovers', ROOT / 'scripts/mods.py')
mods = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mods)

if sys.platform == 'win32':
    import bbport_launcher_win as launcher

INSTALL = 'C:\\Games\\Yharnam Together'
LAUNCHER_EXE = INSTALL + '\\BLauncher.exe'


def row(pid, name, path, arguments=''):
    return pid, name, path, f'"{path}" {arguments}'.strip()


class ServerGoesWithTheLauncherTests(unittest.TestCase):
    def test_who_still_uses_the_install(self):
        rows = [row(1, 'BLauncher.exe', LAUNCHER_EXE),  # a launcher window
                row(2, 'BLauncher.exe', LAUNCHER_EXE, '--run'),  # run.py: the game's launch
                row(3, 'bb-probe.exe', INSTALL + '\\bin\\bb-probe.exe'),  # the game
                row(4, 'BLauncher.exe', LAUNCHER_EXE, '--play'),  # Bloodborne.exe, a Steam shortcut
                row(5, 'BLauncher.exe', LAUNCHER_EXE, '--script C:\\x\\mods.py'),  # a preparation step
                row(6, 'BLauncher.exe', LAUNCHER_EXE, coop.STOP_WHEN_UNUSED),  # another watcher
                row(7, 'BLauncher.exe', LAUNCHER_EXE),  # this process
                row(8, 'shadnet.exe', INSTALL + '\\server\\shadnet.exe', '--watchdog'),
                row(9, 'BLauncher.exe', 'D:\\Other\\BLauncher.exe'),  # another install
                row(10, 'bb-probe.exe', 'D:\\Other\\bin\\bb-probe.exe')]
        self.assertEqual(coop.install_users(rows, INSTALL, own_pid=7), [1, 2, 3, 4])
        self.assertEqual(coop.install_users(rows[4:], INSTALL, own_pid=7), [])

    def test_a_folder_that_only_starts_like_the_install_is_another_install(self):
        rows = [row(1, 'BLauncher.exe', INSTALL + ' 2\\BLauncher.exe')]
        self.assertEqual(coop.install_users(rows, INSTALL), [])

    def test_the_server_stops_once_the_game_and_the_launcher_are_gone(self):
        # The launcher closes while the game runs ("Close the launcher when the game starts"): the
        # server stays for the game and stops after it.
        game = [row(2, 'BLauncher.exe', LAUNCHER_EXE, '--run'), row(3, 'bb-probe.exe', INSTALL + '\\bin\\bb-probe.exe')]
        scans = [game, [row(20, 'BLauncher.exe', LAUNCHER_EXE)], []]  # the game, then a launcher opened again
        alive = {2: 2, 3: 3, 20: 1}  # how many more checks each process lives through
        events = []

        def scan():
            events.append('scan')
            return scans.pop(0)

        def is_alive(pid):
            alive[pid] -= 1
            return alive[pid] >= 0

        def stop(install):
            events.append('stop')
            return 2
        stopped = coop.stop_servers_when_unused(INSTALL, scan=scan, alive=is_alive, sleep=lambda _s: None,
                                                stop=stop, own_pid=99, router=lambda: events.append('router'))
        self.assertEqual(stopped, 2)
        self.assertEqual(events, ['scan', 'scan', 'scan', 'router', 'stop'])

    def test_a_scan_that_fails_never_stops_a_server_someone_may_play_on(self):
        stop = mock.Mock()
        stopped = coop.stop_servers_when_unused(INSTALL, scan=lambda: None, alive=lambda _pid: False,
                                                sleep=lambda _s: None, stop=stop, own_pid=99, router=lambda: None)
        self.assertEqual(stopped, 0)
        stop.assert_not_called()

    def test_the_watcher_starts_only_for_a_running_server(self):
        command = ['BLauncher.exe', coop.STOP_WHEN_UNUSED]
        with mock.patch.object(coop, 'servers_running', return_value=False), \
                mock.patch.object(coop.subprocess, 'Popen') as popen:
            self.assertFalse(coop.stop_servers_later(INSTALL, command))
        popen.assert_not_called()
        with mock.patch.object(coop, 'servers_running', return_value=True), \
                mock.patch.object(coop.subprocess, 'Popen') as popen:
            self.assertTrue(coop.stop_servers_later(INSTALL, command))
        self.assertEqual(popen.call_args[0][0], command)

    def test_stop_server_ends_the_watchers_too_but_never_itself(self):
        # An update's setup replaces BLauncher.exe: no watcher of this install may hold the file.
        rows = [row(8, 'shadnet.exe', INSTALL + '\\server\\shadnet.exe', '--watchdog'),
                row(6, 'BLauncher.exe', LAUNCHER_EXE, coop.STOP_WHEN_UNUSED),
                row(7, 'BLauncher.exe', LAUNCHER_EXE, coop.STOP_WHEN_UNUSED),
                row(1, 'BLauncher.exe', LAUNCHER_EXE)]
        with mock.patch.object(coop.os, 'getpid', return_value=7):
            found = coop.our_processes(INSTALL, rows=rows)
        self.assertEqual(sorted(pid for pid, _name, _command in found), [6, 8])
        self.assertEqual(coop.stop_order(found)[0][0], 8, 'the watchdog still goes first')


class PlayWithoutTheWindowTests(unittest.TestCase):
    """Bloodborne.exe and the Steam shortcut (BLauncher.exe --play) go the way PLAY goes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.install = Path(self.tmp.name) / 'install'
        self.install.mkdir()
        self.settings = dict(coop.DEFAULTS, game='C:/game', host_ip='26.1.2.3', account='p0123', password='secret')

    def launch(self, settings=None, **patches):
        patched = {'needs_prepare': mock.Mock(return_value=False), 'copy_events': mock.Mock(),
                   'view_root': mock.Mock(return_value=self.install / 'coop-game'), **patches}
        with mock.patch.multiple(coop, **patched):
            return coop.launch_settings(self.install, settings or self.settings, say=lambda _text: None)

    def test_a_local_server_gets_its_address_the_account_and_the_game_server_override(self):
        played, root, note = self.launch()
        self.assertEqual((played['host_ip'], played['server'], played['account'], played['password']),
                         ('26.1.2.3', '26.1.2.3', 'p0123', 'secret'))
        self.assertEqual((root, note), (self.install / 'coop-game', ''))
        overrides = json.loads((self.install / 'user' / 'host_overrides.custom.json').read_text(encoding='utf-8'))
        self.assertEqual(overrides, {coop.GAME_SERVER: 'http://26.1.2.3:20443'})
        env = coop.game_environment({}, played, self.install, root)
        self.assertEqual(env['BB_SHADNET_SERVER'], '26.1.2.3:31314')
        self.assertEqual(env['SHADPS4_BLOODBORNE_SEAMLESS_COOP'], '1')

    def test_a_game_folder_not_prepared_yet_is_prepared_and_remembered(self):
        remembered = []
        prepare = mock.Mock(return_value=(self.install / 'elsewhere', 'a note'))
        with mock.patch.multiple(coop, needs_prepare=mock.Mock(return_value=True), prepare=prepare):
            played, root, note = coop.launch_settings(self.install, self.settings, say=lambda _text: None,
                                                      on_prepared=remembered.append)
        self.assertEqual((root, note), (self.install / 'elsewhere', 'a note'))
        self.assertEqual(remembered, [coop.prepared_key(self.settings)])
        self.assertEqual(played['prepared'], coop.prepared_key(self.settings))

    def test_a_server_name_nobody_knows_stops_the_start(self):
        settings = dict(self.settings, host_ip='no-such-server.example')
        with mock.patch.object(coop, 'resolve_host', return_value=''):
            with self.assertRaises(coop.UnknownServer) as stop:
                self.launch(settings)
        self.assertEqual(stop.exception.host, 'no-such-server.example')  # the launcher says it in its language
        self.assertIn('no-such-server.example', str(stop.exception))
        self.assertFalse((self.install / 'user' / 'host_overrides.custom.json').exists())

    def test_only_complete_settings_start_without_the_window(self):
        self.assertTrue(coop.can_play_unattended(dict(self.settings, confirmed='1')))
        self.assertFalse(coop.can_play_unattended(self.settings), 'the co-op setup was never finished')
        self.assertFalse(coop.can_play_unattended(dict(self.settings, confirmed='1', host_ip='')))
        signed_out = dict(self.settings, confirmed='1', server_type='global')
        self.assertFalse(coop.can_play_unattended(signed_out), 'the public server needs a sign-in first')

    @unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
    def test_the_shortcut_starts_the_co_op_game(self):
        settings = {**launcher.APP_DEFAULTS}
        saved = dict(self.settings, confirmed='1')
        with mock.patch.object(launcher, 'COOP_INSTALL', True), \
                mock.patch.object(launcher, 'load_app_settings', lambda: settings), \
                mock.patch.object(bbport_coop_of(launcher), 'load_settings', return_value=saved), \
                mock.patch.object(launcher, 'play_coop_without_window', return_value=0) as play, \
                mock.patch.object(launcher, 'play_without_window') as plain, \
                mock.patch.object(sys, 'argv', ['BLauncher.exe', '--play']):
            with self.assertRaises(SystemExit) as stop:
                launcher.start_launcher()
        self.assertEqual(stop.exception.code, 0)
        play.assert_called_once()
        plain.assert_not_called()

    @unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
    def test_the_shortcuts_game_gets_the_co_op_environment(self):
        started = {}

        class Game:
            def wait(self):
                return 0

        def start_game(command, env, log_path):
            started.update(env=env, log=log_path)
            return Game()
        saved = dict(self.settings, confirmed='1')
        with mock.patch.object(launcher, 'PORT_DIR', self.install), \
                mock.patch.object(bbport_coop_of(launcher), 'load_settings', return_value=saved), \
                mock.patch.object(bbport_coop_of(launcher), 'needs_prepare', return_value=False), \
                mock.patch.object(bbport_coop_of(launcher), 'copy_events'), \
                mock.patch.object(bbport_coop_of(launcher), 'back_up_saves'), \
                mock.patch.object(bbport_coop_of(launcher), 'view_root', return_value=self.install / 'coop-game'), \
                mock.patch.object(launcher, 'start_game', start_game):
            self.assertEqual(launcher.play_coop_without_window({**launcher.APP_DEFAULTS}), 0)
        self.assertEqual(started['env']['BB_SHADNET_SERVER'], '26.1.2.3:31314')
        self.assertEqual(started['env']['BB_SHADNET_NPID'], 'p0123')
        self.assertEqual(started['log'], self.install / 'user' / 'log' / 'console.txt')

    @unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
    def test_a_failed_start_from_the_shortcut_says_why(self):
        shown = []
        saved = dict(self.settings, confirmed='1')
        with mock.patch.object(launcher, 'PORT_DIR', self.install), \
                mock.patch.object(bbport_coop_of(launcher), 'load_settings', return_value=saved), \
                mock.patch.object(bbport_coop_of(launcher), 'back_up_saves'), \
                mock.patch.object(bbport_coop_of(launcher), 'launch_settings',
                                  side_effect=RuntimeError('No Bloodborne game folder')), \
                mock.patch.object(launcher, 'show_error_box', shown.append), \
                mock.patch.object(launcher, 'start_game') as start_game:
            self.assertEqual(launcher.play_coop_without_window({**launcher.APP_DEFAULTS}), 1)
        start_game.assert_not_called()
        self.assertEqual(shown, ['No Bloodborne game folder'])


def bbport_coop_of(module):
    return module.bbport_coop


class EditionWithTheOldHuntersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_the_editions_sold_with_the_old_hunters_have_it(self):
        for title in ('CUSA03173', 'CUSA03179', 'CUSA03014', 'CUSA03023'):
            make_game(self.root / title, title=title)
            self.assertEqual(coop.edition_addcont(self.root / title), 'SPEXPANSIONDLC03', title)
        for title in ('CUSA00207', 'CUSA00900'):
            make_game(self.root / title, title=title)
            self.assertEqual(coop.edition_addcont(self.root / title), '', title)
        self.assertEqual(coop.edition_addcont(self.root / 'nothing here'), '')
        self.assertEqual(coop.edition_addcont(''), '')

    def test_the_co_op_game_is_told_about_it(self):
        make_game(self.root / 'CUSA03173')
        settings = dict(coop.DEFAULTS, host_ip='26.1.2.3')
        env = coop.game_environment({}, settings, self.root, self.root)
        self.assertEqual(env['BB_ADDCONT'], 'SPEXPANSIONDLC03')
        env = coop.game_environment({'BB_ADDCONT': 'MYLABEL'}, settings, self.root, self.root)
        self.assertEqual(env['BB_ADDCONT'], 'MYLABEL', "the player's own DLC package wins")

    def test_the_base_game_still_needs_its_dlc_package(self):
        make_game(self.root / 'CUSA03173', title='CUSA00207')
        env = coop.game_environment({}, dict(coop.DEFAULTS, host_ip='26.1.2.3'), self.root, self.root)
        self.assertNotIn('BB_ADDCONT', env)

    @unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
    def test_the_plain_launchers_game_is_told_too(self):
        make_game(self.root / 'game')
        settings = {**launcher.APP_DEFAULTS, 'game_dir': str(self.root / 'game')}
        self.assertEqual(launcher.game_environment(settings)['BB_ADDCONT'], 'SPEXPANSIONDLC03')
        self.assertEqual(launcher.dlc_text(settings['game_dir'], ''), ('Included in this edition', True))
        self.assertEqual(launcher.dlc_text(settings['game_dir'], 'MYLABEL'), ('MYLABEL', True))
        make_game(self.root / 'base', title='CUSA00207')
        self.assertEqual(launcher.dlc_text(str(self.root / 'base'), ''), ('Not installed', False))


class StrayGameFolderEntryTests(unittest.TestCase):
    """Xenix005 2026-10-30: "[Errno 13] Permission denied: ...\\CUSA03173\\CUSA03173-UPDATE" and the game
    exited. The game reads eboot.bin, sce_module, sce_sys and dvdroot_ps4; anything else in its folder
    that cannot be linked is left out of the game view."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.game = self.root / 'CUSA03173'
        (self.game / 'dvdroot_ps4' / 'chr').mkdir(parents=True)
        (self.game / 'eboot.bin').write_bytes(b'executable')
        (self.game / 'dvdroot_ps4' / 'chr' / 'a.dcx').write_bytes(b'original')
        (self.game / 'CUSA03173-UPDATE').write_bytes(b'something the player left here')
        self.mod = self.root / 'mods' / 'A'
        (self.mod / 'dvdroot_ps4' / 'chr').mkdir(parents=True)
        (self.mod / 'dvdroot_ps4' / 'chr' / 'a.dcx').write_bytes(b'mod')

    def refusing(self, name):
        real = mods.make_link

        def make_link(link, target):
            if Path(target).name == name:
                raise PermissionError(13, 'Permission denied', str(target))
            real(link, target)
        return mock.patch.object(mods, 'make_link', make_link)

    def test_an_entry_the_game_does_not_need_is_left_out(self):
        with self.refusing('CUSA03173-UPDATE'):
            overlay = mods.build_overlay(self.game, self.root / 'out', [('A', self.mod)])
        self.assertEqual((overlay / 'dvdroot_ps4' / 'chr' / 'a.dcx').read_bytes(), b'mod')
        self.assertTrue((overlay / 'eboot.bin').exists())
        self.assertFalse((overlay / 'CUSA03173-UPDATE').exists())

    def test_a_part_of_the_game_that_cannot_be_linked_still_stops_the_start(self):
        with self.refusing('eboot.bin'):
            with self.assertRaises(PermissionError):
                mods.build_overlay(self.game, self.root / 'out', [('A', self.mod)])
        self.assertEqual(list((self.root / 'out').iterdir()), [], 'no half-made view stays')


if __name__ == '__main__':
    unittest.main()
