# SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""How long the rig's runs may take, and which runs make up each tier (Kaniel 2026-10-15: "add
tests for the recent bugs, keep scenarios short, and use lanes to run rigs in parallel").

- A scenario's timeout is at most SCENARIO_MAX_S, a suite chapter's budget at most CHAPTER_MAX_S,
  plus BOOT_S for each time a game in it starts again (a restart's boot, title and join: rig
  2026-10-15, restart chapters took 120-145 s). The game gives up a chapter still going after its
  budget (chapter <name> <seconds>), so one stuck chapter costs its budget, not the suite.
- No fixed wait over WAIT_MAX_S: a sync, or a wait on a condition (wait-members, wait-vital,
  wait-flag, wait-map...) instead. A wait is how long something might take, not how long it
  usually does.
- Whatever cannot fit is in LONG, the tier run before a local release, with its reason.

Tiers (run_scenario.py --tier <name> [more names]):
- quick: smoke, plus the suites of the code being changed (named after it), on every change.
- full: every suite and every single scenario that fits the budget, before a PR merges.
- long: LONG, before a local release.

The rig rework (Kaniel 2026-11-01, tools/rig/REWORK.md): every test is in a tier; probes
(scenarios.PROBES: measurements and pictures) are in none.
"""
import re

SCENARIO_MAX_S = 300
CHAPTER_MAX_S = 120
WAIT_MAX_S = 30
# What a game's start costs before its script's own steps count: the boot, the title, the team
# and the join (the rig's join scenarios pass in 72-99 s, join3 once in 135 s). A game started
# again (a stage) pays it again.
BOOT_S = 100
# A suite's games boot and join once (its join chapter's budget is its own); this is the rest.
SUITE_BOOT_S = 150

# Single scenarios that do not fit the budget (their own boot plus fixed waits over 30 s, or
# runs measured near or over 300 s), each kept for the long tier until it becomes a suite
# chapter. Most are older versions of a suite chapter (named after the arrow).
LONG = {
    "boss-death-spectate": "#414: a boss fight to a teammate's death and the fight after (600 s)",
    "boss-death-wipe": "#414: a boss fight to the whole party's deaths (600 s)",
    "boss-tempo-party": "Kaniel 2026-10-28 boss tempo: a join, then 60 s of Paarl's fight at the leader's Relentless",
    "boss-targets-host": "Kaniel 2026-10-28 passive bosses: a boss fight held a minute",
    "boss-targets-guest": "Kaniel 2026-10-28 passive bosses: a boss fight held a minute",
    "boss-targets-runner-dies": "Kaniel 2026-10-28 passive bosses: a boss fight held a minute, a death and the walk back",
    "boss-targets-teammate-revived": "Kaniel 2026-10-28 passive bosses: a boss fight held a minute, a down and its revive",
    "logarius-spells": "Kaniel 2026-10-25 boss spells: a trip to the boss and a phase of its fight",
    "logarius-runner-leaves": "Kaniel 2026-10-25 boss spells: a trip to the boss and a phase of its fight",
    "shadows-spells": "Kaniel 2026-10-25 boss spells: a trip to the boss and a phase of its fight",
    "shadows-runner-leaves": "Kaniel 2026-10-25 boss spells: a trip to the boss and a phase of its fight",
    "doll-walk-guest": "Kaniel 2026-11-03 Doll level up: a team join, two level ups and their walks (about 260 s)",
    "doll-walk-alone": "Kaniel 2026-11-03 Doll level up: a team join, two level ups and their walks (about 280 s)",
    "doll-walk-host": "Kaniel 2026-11-03 Doll level up: a team join, two level ups and their walks (about 265 s)",
    "story-hostless": "the 10-20 case #286: a team join and a trip",
    "key-items-kept": "the 10-19 playtest case #267: a join, two trips",
    "gesture-own": "the 10-23 gestures case: a join, two trips",
    "key-items-silent": "Kaniel 2026-10-23: a join, two trips",
    "team-world-other-block": "the 10-19 playtest case #266: two team sessions",
    "npc-progress-after-trip": "the 10-19 playtest case #269: a join, two trips",
    "wipe-one-map": "the 10-19 playtest case #270: three games, a death and a wake",
    "boss-hp-after-wipe": "the 10-19 playtest case #272: a wipe and a wake",
    "boss-hp-staggered-wipe": "the 10-25 playtest case: three games, deaths one by one and a wake",
    "paarl-after-wipe": "Kaniel's playtest 2026-10-22: three games, a wipe, a wake and a walk back",
    "kill-reaches-arrival": "the 10-19 playtest case #278: three games, two trips",
    "soak": "a long session by design",
    "teams-apart": "Kaniel 2026-10-31: four games in three worlds, two trips each",
    "teams-apart3": "Kaniel 2026-10-31: three games in three worlds, two trips each",
    "team-switch": "Kaniel 2026-10-31: three teams, a team change and a trip",
    "invade-solo": "Kaniel 2026-10-31: an invader's search (up to 5 min), its 10 s notice and its trip home",
    "five-hunters": "Amanises 2026-10-29: five games, a trip each",
    "chalice-team": "two rituals and two dungeon loads, measured 313 s",
    "chalice-load-inside-guest": "Kaniel 2026-10-24: a ritual, two dungeon loads, a restart",
    "chalice-load-inside-host": "Kaniel 2026-10-24: a ritual, two dungeon loads, a restart",
    "chalice-altar-same": "Kaniel 2026-10-24: a ritual and six dungeon loads",
    "chalice-remove-team-host": "Kaniel 2026-10-30: two rituals and four dungeon loads",
    "chalice-remove-team-guest": "Kaniel 2026-10-30: two rituals and four dungeon loads",
    "chalice-altar-host": "a ritual and two dungeon loads, measured 315 s",
    "chalice-altar-team": "a ritual and two dungeon loads, measured 315 s",
    "chalice-altar-no-chalice": "a ritual and two dungeon loads, measured 353 s",
    "chalice-root-team": "a root ritual and two dungeon loads, waits for the ritual",
    "chalice-team3": "a ritual, three dungeon loads and three trips back, one at a time",
    "chalice-wipe": "A6 audit: a ritual, two dungeon loads, a wipe and its respawn",
    "chalice-wipe-layer2": "A6 audit: a ritual, four dungeon loads, a wipe and its respawn",
    "chalice-death-apart": "A6 audit: a ritual, a dungeon load, a death and its respawn",
    "chalice-death-solo": "A6 audit: a ritual, a dungeon load, a death and its reload",
    "chalice-door-shared": "A6 audit: a ritual, three dungeon loads and a trip",
    "chalice-layers-kept": "A6 audit: a ritual, four dungeon loads and two trips",
    "guest-drops": "a 70 s wait for the drops (Kaniel's playtest 2026-10-16)",
    "boss-guest-runs": "50 s and 90 s waits by the boss (Kaniel's playtest 2026-10-16)",
    "witch-summons": "a 90 s wait for the Witch of Hemwick to summon her Mad Ones",
    "boss-whole-fight": "a lamp trip, then 70 s of fixed waits in the fight (#292)",
    "team-guest-restart": "two stages (two boots), the guest's game starts again",
    "team-host-restart": "two stages (two boots), the host's game starts again",
    "host-quits-title": "Kaniel 2026-10-25: a team load, a quit to the title and a second load",
    "host-quits-title3": "Kaniel 2026-10-25: three games, a quit to the title and a second load",
    "team-wipe-host-restart": "two stages (two boots), a wipe first, then the host's game starts again",
    "cutscene-skip": "two stages (two boots), the opening cutscene played in between",
    "dead-in-host-save": "two stages (two boots): the host's game starts again after its kill",
    "team-load-beside-host": "two stages (two boots), a 45 s wait for the guest to leave the Dream",
    "team-world-pickups": "two stages (two boots): the guest's save takes the team world again",
    "ward-door": "a 420 s wait for the Ward door",
    "save-backups": "waits out the save backups' 150 s timer",
    "guest-lamp-rest": "a 200 s wait for the rest",
    "guest-talk-gilbert": "a 230 s wait for the talk",
    "iosefka-gift": "a 90 s wait for her gift",
    "guest-far-positions": "a 75 s wait for the mob",
    "guest-alone-hits": "a 75 s wait for the mob",
    "guests-pair-mobs": "an 80 s wait for the mob",
    "guest-mobs-host-comes": "40 s waits for the mob",
    "guest-hits-host-comes": "a 50 s wait for the mob",
    "guest-mobs-host-near": "40 s waits for the mob",
    "guest-acts-for-two": "a 70 s wait for the mob",
    "early-trip": "a 60 s wait",
    "clinic": "a 40 s wait",
    "gascoigne-together": "a 40 s wait",
    "echoes-apart": "an 80 s wait",
    "team-world": "a 60 s wait, measured 472 s",
    "team-world-lamps": "two team loads for the guest, a trip and a 20 s wait",
    "pickup-after-reload": "an 80 s wait",
    "dead-before-session": "a 60 s wait",
    "border-fight": "a 60 s wait",
    "host-death-boss": "a 60 s wait",
}

WAIT = re.compile(r"wait (\d+(?:\.\d+)?)$")


def fixed_waits(steps) -> list[float]:
    """The seconds of every fixed `wait <s>` in a script (or a list of stages)."""
    found = []
    for step in steps or []:
        if isinstance(step, list):
            found += fixed_waits(step)
        elif match := WAIT.match(step):
            found.append(float(match.group(1)))
    return found


def stages(script) -> list:
    return script if script and isinstance(script[0], list) else [script]


def scenario_need(scenario: dict) -> float:
    """The least time a scenario's slowest game needs: a boot per stage and its fixed waits."""
    return max(BOOT_S * len(stages(script)) + sum(fixed_waits(script))
               for script in scenario["roles"].values())


def wait_problems(where: str, steps) -> list[str]:
    return [f"{where}: a fixed wait of {seconds:g} s (at most {WAIT_MAX_S} s: sync or wait on "
            "a condition)" for seconds in fixed_waits(steps) if seconds > WAIT_MAX_S]


def scenario_problems(name: str, scenario: dict) -> list[str]:
    """What breaks the budget in a single scenario (a LONG one may)."""
    if name in LONG:
        return []
    problems = []
    timeout = scenario.get("timeout", 600)
    if timeout > SCENARIO_MAX_S:
        problems.append(f"{name}: timeout {timeout} s (at most {SCENARIO_MAX_S} s, or LONG)")
    if (need := scenario_need(scenario)) > timeout:
        problems.append(f"{name}: needs {need:g} s (boots and fixed waits), timeout {timeout} s")
    for role, script in scenario["roles"].items():
        problems += wait_problems(f"{name} {role}", script)
    return problems


def restarts(steps: list[str]) -> int:
    return sum(1 for step in steps if step.startswith("<restart"))


def chapter_budget(chapter: dict) -> int:
    """A chapter's time: its own budget, and a boot for each restart of its games (one game's
    restarts follow each other; the others wait for them). "boots_in": the boots of a restart
    that ended the chapter before, which go on in this one."""
    boots = sum(restarts(steps) for steps in chapter["steps"].values()) + chapter.get("boots_in", 0)
    return chapter.get("budget", CHAPTER_MAX_S) + BOOT_S * boots


def chapter_problems(suite: str, chapter: dict) -> list[str]:
    """What breaks the budget in a suite chapter: its budget, a fixed wait over the limit, or a
    game whose restarts and fixed waits alone take longer than its budget."""
    where = f"{suite}/{chapter['name']}"
    budget = chapter.get("budget", CHAPTER_MAX_S)
    problems = []
    if budget > CHAPTER_MAX_S:
        problems.append(f"{where}: budget {budget} s (at most {CHAPTER_MAX_S} s)")
    for role, steps in chapter["steps"].items():
        problems += wait_problems(f"{where} {role}", steps)
        if (need := sum(fixed_waits(steps))) > budget:
            problems.append(f"{where} {role}: needs {need:g} s of fixed waits, budget {budget} s")
    return problems


def suite_timeout(suite: dict) -> int:
    """A suite's whole time: its games' boot and every chapter's budget."""
    return SUITE_BOOT_S + sum(chapter_budget(chapter) for chapter in suite["chapters"])


def tiers(suites: dict, scenarios: dict) -> dict[str, list[str]]:
    """Each tier's runs, the longest first (lanes take them in turn)."""
    full = sorted(suites, key=lambda name: -suite_timeout(suites[name]))
    # "draws": the scenario needs drawn frames (portraits, the port's menus), which a headless
    # game never makes: the "drawn" tier, for visible games (rig 2026-11-02).
    drawn = [name for name in scenarios if scenarios[name].get("draws")]
    singles = sorted((name for name in scenarios if name not in LONG and name not in drawn),
                     key=lambda name: -scenarios[name].get("timeout", 600))
    return {
        "quick": ["smoke"],
        "full": full + singles,
        "long": [name for name in LONG if name in scenarios and name not in drawn],
        "drawn": drawn,
    }


def describe(name: str, scenario: dict) -> str:
    """--list: a scenario's timeout and scripted waits."""
    waits = [sum(fixed_waits(script)) for script in scenario["roles"].values()]
    tier = " LONG" if name in LONG else ""
    return f"timeout {scenario.get('timeout', 600)} s, waits {max(waits):g} s{tier}"
