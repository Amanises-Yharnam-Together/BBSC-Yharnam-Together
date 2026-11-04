# Cheats in releases, and the cheat watch

Kaniel 2026-11-04: "remove cheats in production mode, and track if any people are cheating or using
any save edit in the server multiplayer".

## Release builds have no cheats

`make-release.ps1` always builds a **production** port: `BB_PRODUCTION=1 bash build.sh` sets the CMake
option `BB_PRODUCTION=ON`, so every target is compiled with `BB_PRODUCTION=1`. `build.sh` writes
`out/build-mode.txt` (`production` or `dev`). `package.sh` with `BB_PRODUCTION=1` writes
`scripts/build_info.json` (`{"production": true}`). `check_release.py` refuses a release without
it, and `make-release.ps1 -SkipPortBuild` refuses a dev build in `bbport\out`.

| What | Dev / rig build | Release build |
| --- | --- | --- |
| Cheat patches (never die, stealth, silent, Rally never fades, enemy control) | Launcher's Cheats page, in-game menus | Not offered. `patches.py` leaves them out even when `bbport.ini` says `1`, and so does the game's own settings load |
| Game debug menu and debug camera patches | Launcher's Extras, in-game menus | Not offered, never applied |
| Save editor page (echoes, insight, attributes, give items) | Insert menu, last tab | No tab, and its changes do nothing |
| Rig autoplay scripts (`SHADPS4_BLOODBORNE_AUTOPLAY`: godmode, teleport, poke, raise-stat, ...) | Run | Not run (logged) |
| Gameplay tweaks (no Rally, camera distance, ragdoll, ...), free camera setting | Yes | Yes (no cheats) |

Code: `BbSettings::DevTools` / `IsDevToolKey` (bbport/gpu/shim/bbport_settings.h),
`patches.DEV_TOOL_KEYS` / `is_production`, the launcher's `PRODUCTION`, `#if BB_PRODUCTION` in
bbport_save_editor.cpp and bloodborne_autoplay.cpp.

Anyone can still change a release's Python scripts or memory. That is why the server watches too.

## The cheat watch on the server

Every port game sends shadNet a `CharacterSheet` (server/coop/coop.proto) when it changes, and at
least every 30 seconds. It holds the character's name, level, six attributes, echoes, insight and
HP, and how the game was built and started: production or dev, its cheat patches, debug tools, how
many save editor changes this run, and whether a rig script drives it. The server alone sees it.
It is never sent on to other players.

`server/coop/cheat_watch.h` (`CheatWatch`, one per linked game) judges the sheets, the vitals and
the trade offers. It reports what no unmodified game can show:

| Kind | Level | What |
| --- | --- | --- |
| `cheats` | certain | Cheat patches on (on a release build, the patches were added back by hand) |
| `save-editor` | certain | The save editor changed the character this run |
| `dev-tools` | likely (certain on a release) | Debug menu or debug camera on |
| `attribute-range`, `level-range`, `echoes-range`, `insight-range` | certain | Past the game's limits (attributes 1-99, level up to 544, echoes up to 999,999,999, insight up to 99) |
| `level-mismatch` | certain | The level is not the attributes' sum less 50, which holds for every origin |
| `attribute-down` | certain | An attribute went down within a run (Bloodborne has no respec) |
| `level-apart` | certain | Level and attributes changed by different amounts |
| `free-level` | likely | Levelled up without spending any echoes |
| `echoes-jump` | likely | Echoes rose by more than 2,000,000 at once above what the character had before this run (its bloodstain) and what trades gave it |
| `insight-jump` | likely | Insight rose by more than 10 at once |
| `vials`, `bullets`, `hp-max` | likely | More than 20 vials, 25 bullets, or max HP over 5000 |
| `trade-echoes`, `trade-count` | certain / likely | Offers past the limits, or far more echoes than the character had |
| `dev-build`, `autoplay` | info | A development build, a rig script |

Each kind is reported once per run of a game. A restart, a new character or another save starts
over. Changes are judged only within a run, because players play offline between sessions.

Each finding is a server log line (`cheat watch: <id> (<name>, <character>) <level>: <text>`), and a
JSON line in `bloodborne_worlds/suspects.jsonl`. The operator's `suspects [id|name]` command
(server/hosting/README.md) lists the players found since the server started, the surest first.

**Nobody is refused, kicked or banned for a finding.** The operator decides, for example with
`ban`.
