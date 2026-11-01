# SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""The rig's run history (Kaniel 2026-11-01, the rig rework: which tests are broken, which are
slow). run_scenario.py appends one JSON line per run to rig/results.jsonl:

  {"when": "2026-11-01 23:59:00", "name": "smoke", "passed": true, "seconds": 812,
   "failed": ["wipe"], "build": "2026-11-01 22:10", "lane": 0, "logs": "C:\\bb\\rig\\runs\\..."}

("failed": a suite's failed chapters; "build": when the game's exe was built.)

  py -3.12 tools/rig/run_scenario.py --history [<name> ...]

shows each run's pass rate and its time, the newest RECENT runs of each.
"""
import json
import pathlib
import time

RECENT = 10


def record(path: pathlib.Path, name: str, passed: bool, seconds: float,
           failed: list[str] | None = None, logs: pathlib.Path | str | None = None,
           lane: int = 0, build: str | None = None, when: float | None = None) -> None:
    """Appends one run's result; a history that can't be written never fails the run."""
    entry = {"when": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when)), "name": name,
             "passed": bool(passed), "seconds": round(seconds), "failed": list(failed or []),
             "build": build, "lane": lane, "logs": str(logs) if logs else None}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(entry) + "\n")
    except OSError as error:
        print(f"  (run history not written: {error})")


def read(path: pathlib.Path) -> list[dict]:
    """Every run in the history, oldest first; lines that don't parse are skipped."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and "name" in entry:
            entries.append(entry)
    return entries


def summary(entries: list[dict], names: list[str] | None = None,
            recent: int = RECENT) -> list[str]:
    """One line per test: its last `recent` runs' passes, median time, and the chapters that
    failed in them (most often first); the ones failing most first."""
    by_name: dict[str, list[dict]] = {}
    for entry in entries:
        if names and entry["name"] not in names:
            continue
        by_name.setdefault(entry["name"], []).append(entry)
    rows = []
    for name, runs in by_name.items():
        last = runs[-recent:]
        passes = sum(1 for run in last if run.get("passed"))
        times = sorted(run.get("seconds", 0) for run in last)
        median = times[len(times) // 2]
        chapters: dict[str, int] = {}
        for run in last:
            for chapter in run.get("failed") or []:
                chapters[chapter] = chapters.get(chapter, 0) + 1
        failing = ", ".join(f"{chapter} x{count}" for chapter, count in
                            sorted(chapters.items(), key=lambda item: -item[1]))
        marks = "".join("+" if run.get("passed") else "-" for run in last)
        rows.append((passes / len(last), name,
                     f"{name}: {passes}/{len(last)} passed {marks}, median {median} s"
                     f"{f', failed: {failing}' if failing else ''}"
                     f" (last {last[-1].get('when', '?')})"))
    return [line for _, _, line in sorted(rows)]
