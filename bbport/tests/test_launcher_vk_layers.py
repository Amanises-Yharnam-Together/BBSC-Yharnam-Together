"""The Vulkan layers the launcher keeps out of the game: overlays known to crash it while it makes its device."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))

import bbport_support as support  # noqa: E402

if sys.platform == 'win32':
    import bbport_launcher_win as launcher

HUDSIGHT = ('VK_LAYER_HudSight2', r'C:\Program Files\HudSight 2\hudsightvk64.json', True)
DISCORD = ('VK_LAYER_Discord_x64', r'C:\Users\p\AppData\Local\Discord\discord_vk64.json', True)
# Discord 2026-11-01: a friend's game closed on every start until fpsmonvk64.json was renamed.
FPS_MONITOR = ('VK_LAYER_fpsmon', r'C:\Program Files (x86)\FPS Monitor\tools\fpsmonvk64.json', True)
BANDICAM = ('VK_LAYER_bandicam_helper', r'C:\Program Files\Bandicam\bdcamvk64.json', True)
GOG = ('GalaxyOverlayVkLayer', r'C:\ProgramData\GOG.com\Galaxy\redists\overlay\injected\galaxy_overlay_vklayer_x64.json',
       True)
NVIDIA = ('VK_LAYER_NV_optimus', r'C:\WINDOWS\System32\DriverStore\nvoglv64\nv-vk64.json', True)


class LayersToSkipTests(unittest.TestCase):
    """bbport_support.layers_to_skip: the value of VK_LOADER_LAYERS_DISABLE for a game run."""

    def test_every_known_crasher_has_its_glob(self):
        skipped = support.layers_to_skip('', []).split(',')
        for glob in ('*HudSight*', '*fpsmon*', '*bandicam*', '*GalaxyOverlay*'):
            self.assertIn(glob, skipped)

    def test_an_installed_crasher_is_skipped_by_its_own_name(self):
        # A new version may rename its layer: the manifest's folder or file still names the tool.
        renamed = [('VK_LAYER_FM_3', FPS_MONITOR[1], True), ('VK_LAYER_bdc', BANDICAM[1], True),
                   ('VK_LAYER_galaxy', GOG[1], True), ('VK_LAYER_hs3', HUDSIGHT[1], True), DISCORD, NVIDIA]
        skipped = support.layers_to_skip('', renamed).split(',')
        for name in ('VK_LAYER_FM_3', 'VK_LAYER_bdc', 'VK_LAYER_galaxy', 'VK_LAYER_hs3'):
            self.assertIn(name, skipped)
        self.assertNotIn('VK_LAYER_Discord_x64', skipped)
        self.assertNotIn('VK_LAYER_NV_optimus', skipped)

    def test_a_name_a_glob_covers_is_not_listed_twice(self):
        skipped = support.layers_to_skip('', [HUDSIGHT, FPS_MONITOR, BANDICAM, GOG]).split(',')
        self.assertEqual(skipped, list(support.CRASHING_VK_LAYERS))

    def test_layers_off_or_unreadable_add_nothing(self):
        off = ('VK_LAYER_FM_3', FPS_MONITOR[1], False)
        unreadable = ('?', BANDICAM[1], True)
        self.assertEqual(support.layers_to_skip('', [off, unreadable]), ','.join(support.CRASHING_VK_LAYERS))

    def test_an_inherited_list_is_kept_in_front(self):
        self.assertEqual(support.layers_to_skip('~implicit~,*fpsmon*', []).split(',')[:2], ['~implicit~', '*fpsmon*'])
        self.assertEqual(support.layers_to_skip('*fpsmon*', []).count('*fpsmon*'), 1)

    def test_the_log_marks_what_the_loader_skips_whatever_the_case(self):
        # The loader compares its globs without case.
        line = support.overlay_log_line([('VK_LAYER_FPSMON', 'C:/f.json', True)], '*fpsmon*')
        self.assertIn('VK_LAYER_FPSMON (skipped)', line)


class StartHintTests(unittest.TestCase):
    """bbport_support.overlay_suspects: what a game that closed while starting may blame."""

    def test_overlays_still_loaded_are_named(self):
        layers = [DISCORD, FPS_MONITOR, NVIDIA, ('VK_LAYER_RTSS', 'C:/rtss.json', True),
                  ('VK_LAYER_OBS_HOOK', 'C:/obs.json', False), ('?', r'C:\Tools\Some Overlay\x.json', True)]
        disabled = support.layers_to_skip('', layers)
        self.assertEqual(support.overlay_suspects(layers, disabled),
                         ['VK_LAYER_Discord_x64', 'VK_LAYER_RTSS', r'C:\Tools\Some Overlay\x.json'])

    def test_the_graphics_drivers_own_layers_are_not_suspects(self):
        layers = [NVIDIA, ('VK_LAYER_AMD_switchable_graphics', 'C:/amd.json', True),
                  ('VK_LAYER_NV_present', 'C:/nvp.json', True), ('VK_LAYER_INTEL_nullhw', 'C:/i.json', True)]
        self.assertEqual(support.overlay_suspects(layers, ''), [])

    def test_only_a_game_that_closed_by_itself_before_its_window_blames_them(self):
        def blame(code=3221225477, started=True, was_up=False, stopped=False, reshade=False, layers=(DISCORD,)):
            return support.start_crash_suspects(code, started, was_up, stopped, list(layers), '', reshade)
        self.assertEqual(blame(), ['VK_LAYER_Discord_x64'])
        self.assertEqual(blame(code=0), [])
        self.assertEqual(blame(started=False), [], 'the preparation failed: no layer was loaded yet')
        self.assertEqual(blame(was_up=True), [])
        self.assertEqual(blame(stopped=True), [])
        self.assertEqual(blame(layers=()), [])
        self.assertEqual(blame(reshade=True), ['ReShade', 'VK_LAYER_Discord_x64'])

    def test_run_py_says_when_the_game_itself_starts(self):
        run_py = (Path(__file__).resolve().parents[1] / 'run.py').read_text(encoding='utf-8')
        self.assertIn(f"print({support.GAME_STARTING_LINE!r}, flush=True)", run_py)
        self.assertLess(run_py.index(support.GAME_STARTING_LINE), run_py.index('return subprocess.run(command, stdin'))

    def test_everything_skipped_leaves_no_suspect(self):
        self.assertEqual(support.overlay_suspects([DISCORD, FPS_MONITOR], '~implicit~'), [])
        self.assertEqual(support.overlay_suspects([DISCORD], '~all~'), [])


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class CrashingLayerTests(unittest.TestCase):
    def environment_with_layers(self, inherited=None, extra_env=''):
        settings = {**launcher.APP_DEFAULTS, 'game_dir': 'G', 'extra_env': extra_env}
        with mock.patch.dict(launcher.os.environ), mock.patch.object(launcher, 'load_ini', return_value=({}, [])):
            launcher.os.environ.pop('VK_LOADER_LAYERS_DISABLE', None)
            if inherited is not None:
                launcher.os.environ['VK_LOADER_LAYERS_DISABLE'] = inherited
            return launcher.game_environment(settings)

    def environment(self, inherited=None, extra_env=''):
        with mock.patch.object(support, 'vulkan_layers', return_value=[]):
            return self.environment_with_layers(inherited, extra_env)

    def test_the_known_crashers_are_skipped(self):
        self.assertEqual(self.environment()['VK_LOADER_LAYERS_DISABLE'], ','.join(support.CRASHING_VK_LAYERS))

    def test_an_inherited_list_is_kept(self):
        self.assertEqual(self.environment('~implicit~')['VK_LOADER_LAYERS_DISABLE'],
                         ','.join(('~implicit~',) + support.CRASHING_VK_LAYERS))

    def test_a_renamed_layer_of_an_installed_crasher_is_skipped(self):
        with mock.patch.object(support, 'vulkan_layers', return_value=[('VK_LAYER_FM_3', FPS_MONITOR[1], True)]):
            env = self.environment_with_layers()
        self.assertIn('VK_LAYER_FM_3', env['VK_LOADER_LAYERS_DISABLE'].split(','))

    def test_extra_env_has_the_last_word(self):
        env = self.environment(extra_env='VK_LOADER_LAYERS_DISABLE=')
        self.assertEqual(env['VK_LOADER_LAYERS_DISABLE'], '')


if __name__ == '__main__':
    unittest.main()
