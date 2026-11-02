# SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""The rig rework's runner pieces (Kaniel 2026-11-01): the run history, the CPU guard and the
games' priority, and --tier starting the ping proxies.

Run: py -3.12 -m unittest discover -s tools\\rig\\tests
"""
import os
import pathlib
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import build_lock  # noqa: E402
import history  # noqa: E402
import run_scenario  # noqa: E402


class HistoryTest(unittest.TestCase):
    def test_a_run_is_one_line_read_back_as_written(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "rig" / "results.jsonl"
            history.record(path, "smoke", False, 812.4, failed=["wipe"], lane=1,
                           build="2026-11-01 22:10", when=0)
            history.record(path, "smoke", True, 790, when=60)
            runs = history.read(path)
        self.assertEqual([run["passed"] for run in runs], [False, True])
        self.assertEqual(runs[0]["seconds"], 812)
        self.assertEqual(runs[0]["failed"], ["wipe"])
        self.assertEqual(runs[0]["lane"], 1)

    def test_a_broken_line_is_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "results.jsonl"
            path.write_text('{"name": "join", "passed": true, "seconds": 80}\nnot json\n[]\n',
                            encoding="utf-8")
            self.assertEqual([run["name"] for run in history.read(path)], ["join"])

    def test_no_history_is_no_runs(self):
        self.assertEqual(history.read(pathlib.Path("/no/such/results.jsonl")), [])

    def test_the_summary_puts_the_most_failing_first_with_their_chapters(self):
        runs = ([{"name": "smoke", "passed": True, "seconds": s} for s in (700, 800, 900)] +
                [{"name": "trips", "passed": False, "seconds": 1500, "failed": ["dog"]},
                 {"name": "trips", "passed": False, "seconds": 1400, "failed": ["dog", "trip"]},
                 {"name": "trips", "passed": True, "seconds": 1300}])
        lines = history.summary(runs)
        self.assertTrue(lines[0].startswith("trips: 1/3 passed --+, median 1400 s, failed: "
                                            "dog x2, trip x1"), lines[0])
        self.assertTrue(lines[1].startswith("smoke: 3/3 passed +++, median 800 s"), lines[1])

    def test_the_summary_keeps_the_named_and_the_recent(self):
        runs = [{"name": "join", "passed": i % 2 == 0, "seconds": 80} for i in range(15)]
        runs.append({"name": "smoke", "passed": True, "seconds": 800})
        lines = history.summary(runs, names=["join"], recent=4)
        self.assertEqual(len(lines), 1)
        self.assertIn("join: 2/4 passed", lines[0])


class CpuGuardTest(unittest.TestCase):
    def test_busy_is_the_share_of_time_not_idle(self):
        samples = iter([(100, 1000), (150, 1200)])  # 200 ticks, 50 of them idle
        self.assertAlmostEqual(build_lock.cpu_busy(read=lambda: next(samples),
                                                   sleep=lambda s: None), 75.0)

    def test_off_windows_nothing_is_measured(self):
        self.assertIsNone(build_lock.cpu_busy(read=lambda: None, sleep=lambda s: None))

    def test_a_run_waits_while_the_cpu_is_busy(self):
        loads = iter([95.0, 80.0, 40.0])
        slept = []
        with unittest.mock.patch.dict(os.environ, {"BB_MAX_CPU_BUSY": "70"}):
            build_lock.wait_for_cpu("smoke", busy=lambda: next(loads), sleep=slept.append,
                                    now=lambda: 0)
        self.assertEqual(len(slept), 2)

    def test_a_run_starts_anyway_after_the_longest_wait(self):
        clock = iter(range(0, 10000, 600))
        slept = []
        with unittest.mock.patch.dict(os.environ, {"BB_MAX_CPU_BUSY": "70"}):
            build_lock.wait_for_cpu("smoke", busy=lambda: 99.0, sleep=slept.append,
                                    now=lambda: next(clock), longest=1800)
        self.assertLessEqual(len(slept), 4)

    def test_the_guard_can_be_switched_off(self):
        with unittest.mock.patch.dict(os.environ, {"BB_CPU_GUARD": "0"}):
            build_lock.wait_for_cpu("smoke", busy=lambda: self.fail("measured"))


class PriorityTest(unittest.TestCase):
    def test_rig_processes_start_below_normal_on_windows(self):
        with unittest.mock.patch.object(build_lock.os, "name", "nt"), \
                unittest.mock.patch.dict(os.environ, {"BB_RIG_PRIORITY": ""}):
            self.assertEqual(build_lock.priority_flags(), build_lock.BELOW_NORMAL_PRIORITY_CLASS)
        with unittest.mock.patch.object(build_lock.os, "name", "nt"), \
                unittest.mock.patch.dict(os.environ, {"BB_RIG_PRIORITY": "normal"}):
            self.assertEqual(build_lock.priority_flags(), 0)


class TierProxiesTest(unittest.TestCase):
    def test_a_tier_alone_starts_the_ping_proxies(self):
        started = []
        with unittest.mock.patch.object(run_scenario, "start_delay_proxies",
                                        side_effect=lambda: started.append(1) or []), \
                unittest.mock.patch.object(run_scenario, "act", return_value=0) as act:
            run_scenario.main(["--engine", "port", "--tier", "quick"])
        self.assertEqual(started, [1])
        self.assertEqual(act.call_args[0][0].scenarios[:1], ["smoke"])

    def test_a_tier_in_lanes_leaves_the_proxies_to_each_lane(self):
        started = []
        with unittest.mock.patch.object(run_scenario, "start_delay_proxies",
                                        side_effect=lambda: started.append(1) or []), \
                unittest.mock.patch.object(run_scenario, "act", return_value=0):
            run_scenario.main(["--engine", "port", "--tier", "quick", "--lanes", "2"])
        self.assertEqual(started, [])


class HeldPortsTest(unittest.TestCase):
    def test_a_server_left_from_an_earlier_run_is_named_with_its_pid(self):
        # Rig 2026-11-02: an old shadNet still listened, and the run said "too old".
        port = run_scenario.SHADNET_PORT
        netstat = (f"  TCP    0.0.0.0:{port}    0.0.0.0:0    LISTENING    53880\n"
                   f"  TCP    127.0.0.1:{port}    127.0.0.1:5000    ESTABLISHED    1\n")
        self.assertEqual(run_scenario.held_server_ports(netstat, set()), f"{port} (pid 53880)")
        self.assertEqual(run_scenario.held_server_ports("", set()), "")

    def test_an_open_port_netstat_misses_is_held_all_the_same(self):
        # Rig 2026-11-02 (Windows 26300): a listening shadNet shown as CLOSED, or not at all.
        port = run_scenario.SHADNET_PORT
        netstat = f"  TCP    127.0.0.1:{port}    0.0.0.0:0    CLOSED    94308\n"
        with unittest.mock.patch.object(run_scenario, "lane_server_pids", return_value={94308}):
            self.assertEqual(run_scenario.held_server_ports(netstat, {port}),
                             f"{port} (pid unknown), this lane's servers: pid 94308")


class LaneServerPidsTest(unittest.TestCase):
    def test_the_lanes_servers_are_found_by_what_they_run(self):
        shadnet = run_scenario.lane_dir() / "server" / "shadnet.exe"
        other = run_scenario.lane_dir(5) / "server" / "shadnet.exe"
        port = run_scenario.BACKEND_PORT
        listing = (f"94308\t{str(shadnet).upper()}\t\"{shadnet}\"\n"
                   f"777\t{other}\t\"{other}\"\n"
                   f"812\tC:\\py\\python.exe\tpython bb_dummy_server.py --address 127.0.0.1 "
                   f"--port {port} --shadnet-webapi x\n"
                   f"813\tC:\\py\\python.exe\tpython bb_dummy_server.py --port {port + 1}\n"
                   "not a pid\tx\ty\n")
        self.assertEqual(run_scenario.lane_server_pids(listing), {94308, 812})


if __name__ == "__main__":
    unittest.main()
