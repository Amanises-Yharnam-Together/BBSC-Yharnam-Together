"""run.py's frame rate mode: the in-game FPS limit (bbport.ini fps_limit) needs the unlocked mode."""
from paths import ROOT
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('bbport_run', ROOT / 'run.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


class FramePacingTests(unittest.TestCase):
    """The in-game restart inherits the previous start's environment (Supermedo's cedc28b)."""

    def test_a_frame_rate_changed_in_the_menu_gets_its_own_pacing_after_the_restart(self):
        env = {}
        run.frame_pacing(env, 'uncap')
        self.assertEqual(env['BB_VBLANK_HZ'], '480')
        run.frame_pacing(env, '30')
        self.assertEqual(env['BB_VBLANK_HZ'], '60')
        run.frame_pacing(env, '90')
        self.assertEqual(env['BB_VBLANK_HZ'], '90')
        run.frame_pacing(env, 'uncap')
        self.assertEqual(env['BB_VBLANK_HZ'], '480')

    def test_a_rate_set_before_the_first_start_is_used_as_given(self):
        env = {'BB_VBLANK_HZ': '120'}
        run.frame_pacing(env, 'uncap')
        run.frame_pacing(env, '30')
        self.assertEqual(env['BB_VBLANK_HZ'], '120')
        self.assertNotIn('BB_AUTO_VBLANK', env)


class CoopTraceSettingTests(unittest.TestCase):
    """A player's game runs without the co-op trace; bbport.ini turns it on for a bug report."""

    def trace_with(self, ini_text, env):
        with tempfile.TemporaryDirectory() as folder:
            ini = Path(folder) / 'bbport.ini'
            ini.write_text(ini_text, encoding='utf-8')
            run.coop_trace(env, ini)
        return env.get('BB_COOP_TRACE')

    def test_off_unless_asked_for(self):
        self.assertIsNone(self.trace_with('fov=43\n', {}))
        self.assertIsNone(self.trace_with('coop_trace=0\n', {}))

    def test_the_ini_turns_it_on(self):
        self.assertEqual(self.trace_with('coop_trace=1\n', {}), '1')

    def test_a_setting_given_at_the_start_stays(self):
        self.assertEqual(self.trace_with('coop_trace=1\n', {'BB_COOP_TRACE': '0'}), '0')


class FrameModeTests(unittest.TestCase):
    def test_an_fps_limit_unlocks_the_frame_rate(self):
        # Kaniel 2026-10-10: 240 set in the game's menu, still 60 on top (the kit's 60 FPS mode is
        # the game's own fixed 60 FPS timestep, which no cap can raise).
        self.assertEqual(run.frame_mode('60', '240'), 'uncap')
        self.assertEqual(run.frame_mode('60', '144'), 'uncap')

    def test_no_limit_keeps_the_chosen_mode(self):
        self.assertEqual(run.frame_mode('60', None), '60')
        self.assertEqual(run.frame_mode('60', '0'), '60')
        self.assertEqual(run.frame_mode('uncap', None), 'uncap')
        self.assertEqual(run.frame_mode('60', 'nonsense'), '60')

    def test_the_30_fps_mode_stays(self):
        # 30 is chosen for the shadPS4-like timing or an unpatched game: a cap does not change it.
        self.assertEqual(run.frame_mode('30', '240'), '30')


    def test_online_play_runs_at_60(self):
        # Kaniel 2026-10-13: hosting uncapped (100-200 FPS) made the guests see everyone freeze and
        # fly and their hits land late; the host at 60 fixed it. Online, the high frame rate modes
        # and an FPS limit give the fixed 60 FPS mode; 30 stays.
        self.assertEqual(run.frame_mode('uncap', None, online=True), '60')
        self.assertEqual(run.frame_mode('90', None, online=True), '60')
        self.assertEqual(run.frame_mode('60', '240', online=True), '60')
        self.assertEqual(run.frame_mode('60', None, online=True), '60')
        self.assertEqual(run.frame_mode('30', '240', online=True), '30')
        self.assertEqual(run.frame_mode('uncap', None, online=False), 'uncap')

    def test_online_unlocked_frame_rate_is_opt_in(self):
        # Kaniel 2026-10-22: an opt-in unlocked frame rate online. With it the chosen mode stays
        # (the send pace holds the game's packets to the 60 FPS mode's rates); 30 still stays.
        self.assertEqual(run.frame_mode('uncap', None, online=True, online_unlocked=True), 'uncap')
        # Kaniel 2026-10-22: a guest in the 90 mode made the enemies lag for everyone (90 FPS++ is a
        # fixed 90 FPS step: a PC that cannot hold 90 runs its game slower). Online it is the
        # unlocked mode (real frame time) capped at 90 instead.
        self.assertEqual(run.frame_mode('90', None, online=True, online_unlocked=True), 'uncap')
        self.assertEqual(run.frame_mode('60', '144', online=True, online_unlocked=True), 'uncap')
        self.assertEqual(run.frame_mode('60', None, online=True, online_unlocked=True), '60')
        self.assertEqual(run.frame_mode('30', None, online=True, online_unlocked=True), '30')
        # Offline the switch changes nothing.
        self.assertEqual(run.frame_mode('90', None, online=False, online_unlocked=True), '90')

    def test_online_unlocked_environment(self):
        # The game's frame cap online (at most 120: the movement timing breaks above it) and the
        # send pace, only for the modes above 60 FPS.
        self.assertEqual(run.online_frame_env('uncap', online=True, online_unlocked=True),
                         {'BB_ONLINE_FPS_CAP': '120', 'SHADPS4_BLOODBORNE_SEND_PACE': '1'})
        self.assertEqual(run.online_frame_env('uncap', online=True, online_unlocked=True, asked='90'),
                         {'BB_ONLINE_FPS_CAP': '90', 'SHADPS4_BLOODBORNE_SEND_PACE': '1'})
        self.assertEqual(run.online_frame_env('60', online=True, online_unlocked=True), {})
        self.assertEqual(run.online_frame_env('uncap', online=True, online_unlocked=False), {})
        self.assertEqual(run.online_frame_env('uncap', online=False, online_unlocked=True), {})
        # BB_SEND_PACE=0: the cap without the pace, for comparisons (the rig's fps-pace runs).
        self.assertEqual(run.online_frame_env('uncap', online=True, online_unlocked=True, pace='0'),
                         {'BB_ONLINE_FPS_CAP': '120'})


if __name__ == '__main__':
    unittest.main()
