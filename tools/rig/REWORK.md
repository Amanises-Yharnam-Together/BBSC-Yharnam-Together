# Rig rework: analysis and the new scenario set

Kaniel 2026-11-01: "fully analyze our rig scenarios and revise them so they are more purposeful,
less long, more combined and not broken". Read from main 5d2305ee (v1.3.1). Draft PRs #474
(team isolation, invasions) and #486 (fifth game, Global server) add more rig scenarios; they
fold into this plan when they merge.

## What the rig has today

- **243 single scenarios** (tools/rig/scenarios.py, 5,700 lines) and **8 suites** with 107
  chapters (suites.py). Each single scenario boots every game and joins (about 100 s) before it
  tests anything; a suite boots and joins once.
- **91 scenarios are in no tier at all**: nothing ever runs them unless someone names them.
- **120 scenarios are LONG** (budget.py): the long tier's worst case is about **28 hours**. The
  full tier (8 suites + 32 recent-bug scenarios) is about **7.3 hours** worst case.
- **59 scenarios repeat a suite chapter** (budget.py itself says "suite chapter:" for many):
  older copies kept after the suites took them over.
- **25 are not tests**: research probes and "take pictures to look at" runs mixed in with the
  pass/fail tests (fps-pace, the *-look runs, aspect pictures, boss tempo logs, stutter timings,
  altar captures, soak).
- **Many scenarios only differ in a detail**: 8 "who runs this enemy" variants, 9 Hemwick ones,
  4 bloodstain, 4 spectate, 4 boss-targets, 6 Logarius/Shadows, 10 chalice runs each doing its
  own ritual and loads, 6 team-menu ones. Each pays its own boot, join and trip to the place.
- **Long fixed waits**: 102 scenarios have a fixed wait over 30 s (up to 420 s for the Ward
  door) where a wait on a condition or a sync would end as soon as it happened.

### Broken or stale

- **8 suite chapters are marked known_bug since 2026-10-15** (trips/ward-npc, edges/guest-hits-npc,
  party-death/down-by-enemy, down-alone, stain-after-wipe, crashes/owner-crash-fight,
  joins/new-character, joins/first-death-dream) and boss-targets-runner-dies since 10-28. Two
  weeks of fixes later nobody knows which still fail: one run tells.
- **Runner bug: `--tier X` without `--lanes`** starts no ping proxies (main() looks at the
  scenario names before --tier fills them in), so every game times out reaching the server and
  nobody joins (memory 2026-10-25). Still in main.
- **No CPU priority**: the games and servers start at normal priority. Kaniel's rule since
  10-30 is BelowNormal, leave CPU free, no focus stealing. The rig waits for builds and free
  memory, not for CPU.
- **No run history**: the runner prints PASSED/FAILED and keeps the last 27 batches of logs, so
  "which scenarios fail often, which are slow" can't be answered. All but one batch on the PC is
  from Oct 30 - Nov 1.
- Already fixed in main (memory notes are old): servers start with CREATE_NO_WINDOW, and a
  headless game's window stays hidden (bbport window.cpp).
- 4 unit tests fail on Linux only (Windows paths); on the PC they are expected green (not checked).
- The 1.3.1 GPU load deadlock (headless, old memory model) can hang a game's load; the rig then
  waits out the whole timeout. Game bug, not rig; the rig should name it when it sees it.

## The new set

Rules: one boot per theme (a suite), chapters ordered so each leaves the world as the next needs
it, waits on conditions or syncs, at most 120 s a chapter. A single scenario only where a suite
can't do it: its own saves, or a setting every other chapter would feel. Probes are kept but
apart, in probes.py, runnable by name and in no tier.

| Suite | Games | What it covers | From |
|---|---|---|---|
| smoke | 3 | quick tier: join, trip, hits, kills, pickups, rejoin, wipe | as today |
| together, trips, edges, crashes, joins | 2 | as today | + edges takes the Ward door and lamp/talk spots, crashes takes dead-in-host-save |
| party-death | 2 | downs, revives, give-ups, bloodstains, spectate, wipes | + 11 scenarios |
| party3 | 3 | everything with three games | + 10 scenarios |
| **team** | 2 | lobby, team menus, kick/leave/rejoin/insert, solo load, host quits, duel | 11 scenarios |
| **team-worlds** | 2 | a team's world across sessions and restarts | 11 scenarios |
| **world** | 2 | progress, story, gifts, key items, gestures across worlds and lone trips | 23 scenarios |
| **enemies** | 2 | who runs which enemy, hand-overs, drops, echoes, boss runners | 15 scenarios |
| **hud** | 2 | compass, pings, map with a teammate, portraits, button icons | 7 scenarios |
| **hemwick** | 2 | Mad Ones, mist ambush, Abode lamp, Witch (her kill last) | 10 scenarios |
| **far-maps** | 2 | Yahar'gul bells and mummy, Forbidden Woods falls and walls, Cainhurst | 9 scenarios |
| **bosses** | 2 | boss targets, spells, deaths in boss fights | 11 scenarios |
| **trade** | 2 | every kind of trade and its menus | 4 scenarios |
| **rules** | 2 | host rules on: rot, travel together, vote, scaling, tempo | 5 scenarios |
| **menus** | 1 | settings menu, map screen and floors | 3 scenarios |
| **chalice**, chalice-solo | 2 / 1 | one ritual, then every altar case in it (long tier) | 13 scenarios |

Tiers become: **quick** = smoke; **full** = every suite but chalice, plus the ~10 standalone
scenarios; **long** = chalice, soak. (After phase 1 the full tier still holds the 89 scenarios
that wait for phase 2, so it is longer for a while: every test runs, none is skipped.) Recent-bug tests go straight into the suite of their area
instead of a RECENT list.

What it saves: 144 scenarios stop paying their own boot and join (about 100 s each: about 4
hours a full pass), the fixed waits become condition waits, and the 59 duplicates and 25 probes
leave the test list. 243 scenarios + 8 suites become about 10 scenarios + 18 suites, and
everything in them runs in a tier.

## Phases

1. **Cloud, no game runs needed** (first PR): fix the --tier proxy bug; games and servers at
   BelowNormal priority and a CPU-free check before each game starts; a results history
   (rig/results.jsonl: name, pass/fail, seconds, failed chapters, build) with `--history`;
   delete the 59 duplicates (their stronger checks moved into the chapter first: the #403 team
   handover lines in crashes/host-crash and host-crash-apart, the owner take-over in
   owner-crash-fight, the hide line in together/story-hidden, the revive prompt in
   party-death/down-revive, compass and map stains in party-death/stain-after-rejoin); the 25
   probes into scenarios.PROBES; every remaining scenario in a tier (full unless LONG), the
   RECENT list gone; unit tests for all of it. `--play down-revive` is now `--play party-death`
   (`--play party3` for three).
2. **One new suite per PR**, each built from its scenarios, run once on the PC (headless,
   BelowNormal, one lane), then its scenarios are deleted. Order: party-death and party3 (grow
   existing ones), team, world, enemies, hud, bosses, hemwick, far-maps, rules, trade, menus,
   chalice.
3. **Stale known_bug chapters**: one run of the full tier tells which still fail; each one
   then gets fixed in the game, fixed in the test, or dropped.

## Every scenario's place

### Already a suite chapter: the scenario is gone (phase 1) (59)

| Where | Scenarios |
|---|---|
| crashes (same name) | resume, crash-apart, host-crash-apart, host-crash |
| crashes/after-resume | pickup-after-crash, lamp-after-crash, crash-rejoin-hp |
| crashes/deaths | host-death, guest-death, guest-death-seen |
| crashes/kill-apart-pays | echoes-after-crash |
| crashes/leave | pickup-after-leave |
| crashes/owner-crash-fight | owner-crash |
| joins (same name) | hurt-before-join, join-after-trip, hp-across-blocks, join-ward, join-apart |
| party-death (same name) | down-revive, give-up, down-alone, down-by-enemy, wipe |
| party-death/down-no-kneel | down-wait |
| party-death/stain-after-rejoin (its compass/map lines go into that chapter) | bloodstain-rejoin |
| party3 (same name) | trip3, guest-trip3, down-revive3, crash3 |
| party3/crash3 | pickup-after-leave3 |
| party3/two-away | away-unseen3 |
| party3/wipe | wipe3 |
| smoke/hit3, party3/hit3 | hit3 |
| smoke/join (every suite starts with it) | join, join3 |
| smoke/kill-apart, trips/kill-apart | kill-apart |
| smoke/rejoin, crashes/resume | guest-crash |
| smoke/trip, trips/trip | trip |
| together (same name) | story-hidden, phantom-look, guest-flags-stay, lamp-share, hp-together, boss-kill, boss-refight, pickup |
| together/apart-fight | guest-alone-mobs |
| together/talk-by-the-lamp | guest-talk-at-lamp, guest-talk-by-the-lamp |
| trips (same name) | dog, hp-apart, ward-npc, boss-putdown, lone-guest, pickup-after-trip, hit-after-host-trip, guest-hit-once |
| trips/guest-hit-once + trips/hp-apart | hp-after-guest-trip |
| trips/hit-after-host-trip + trips/hp-apart | hp-after-host-trip |

### Moved to scenarios.PROBES (phase 1: runnable by name, in no tier) (25)

| Where | Scenarios |
|---|---|
| 2026-10-10/11 investigations; mine/prey use whatever saves the games have now | iosefka-look, iosefka-new, iosefka-mine, prey-replay |
| altar record captures (RE) | altar-record-capture, chalice-remove-record |
| boss tempo tuning logs | boss-tempo-vanilla, boss-tempo-aggressive, boss-tempo-relentless |
| known failure kept for the uncapped-FPS summon bug | join3-uncap |
| packet trace for tools/re/packet_summary.py | fps-pace |
| perf measurements for player reports | solo-death-tick, guest-follower-stutter, guest-follower-stutter-harder |
| pictures to look at (visible runs) | frame-gen-look, logarius-look, shadows-look, aspect-hud-wide, aspect-hud-16x9, aspect-team-43, team-load-art, team-screen, portrait-dressed |
| rig tools (make the baseline saves, boot check) | setup, boot |

### Becomes a chapter (phase 2) (148)

| Where | Scenarios |
|---|---|
| NEW bosses | logarius-spells, logarius-runner-leaves, shadows-spells, shadows-runner-leaves, boss-targets-host, boss-targets-guest, boss-targets-runner-dies, boss-targets-teammate-revived, boss-death-spectate, boss-death-wipe, host-death-boss |
| NEW chalice (3rd game) or party3, long tier | chalice-team3 |
| NEW chalice (long tier) | chalice-team, chalice-altar-team, chalice-altar-host, chalice-altar-no-chalice, chalice-altar-same, chalice-root-team, chalice-remove-team-host, chalice-remove-team-guest, chalice-load-inside-guest, chalice-load-inside-host |
| NEW chalice-solo (1 game, file trace) | chalice-ritual, chalice-enter-broken |
| NEW enemies | guest-alone-hits, guest-mobs-host-comes, guest-hits-host-comes, guest-far-positions, guest-mobs-host-near, guest-drops, clinic, owner-leaves, host-arrives-hurt-enemy, guest-kill-pays-host, echoes-apart, border-fight, gascoigne-together, boss-guest-runs, boss-whole-fight |
| NEW far-maps | yahargul-bell-summons, yahargul-downed-bell-area, yahargul-mummy-guest, yahargul-mummy-host, void-fall-respawn, downed-void-fall, walls-woods-stairs, guest-cutscene-cainhurst, skip-vote |
| NEW hemwick (Witch's kill last) | mad-one-back, mad-one-back-near, witch-summons, witch-flicker, mist-ambush-guest, mist-ambush-unarmed, abode-lamp-far, abode-lamp-host-leaves, abode-lamp-broken, join-during-trip |
| NEW hud | compass, compass-down, pings, map-team, portrait, portrait-auto, button-icons |
| NEW menus (1 game) | settings-menu, map-screen, map-floors |
| NEW rules (host rules on) | rot-death-lamp, travel-together, travel-vote-no, scale-team-size, boss-tempo-party |
| NEW team | team-join, team-menu-kick, team-menu-leave, team-menu-insert, team-menu-rejoin, team-menu-join, team-solo-load, team-load-cover, team-load-apart, host-quits-title, duel |
| NEW team-worlds (restarts: a team's world across sessions) | team-worlds, team-world, team-world-lamps, team-world-pickups, team-world-other-block, team-load-beside-host, team-guest-restart, team-host-restart, team-wipe-host-restart, cutscene-skip, dream-headstones-team |
| NEW trade | trade, trade-any, trade-echoes, trade-menus |
| NEW world | lone-guest-progress, lone-guest-kill, dog-alone, team-story-trip, team-world-trip, team-time-of-day-trip, npc-progress-after-trip, story-hostless, dead-before-session, story-npc-trips, story-switched-on, early-trip, doll-talk-arrival, key-items-kept, key-items-silent, gesture-own, impurity-rune, nightmare-flags, dream-headstones-lit, dream-shop-messengers, door-share |
| crashes (the host's restart after a kill) | dead-in-host-save |
| edges (a world kept on the server across its restart: today's chapter checks the drop only) | server-restart |
| edges (the Ward door 3x, lamps by talk spots) | ward-door, guest-lamp-rest, guest-talk-gilbert |
| edges/travel-mid-load (pickups after an in-place reload) | pickup-after-reload |
| party-death | give-up-by-enemy, guest-death-target, bloodstain, bloodstain-alone, bloodstain-far-lamp, bloodstain-trip, boss-hp-after-wipe, spectate-lamp, spectate-give-up, spectate-wipe, spectate-default-down |
| party3 | dog-alone3, lone-guest-progress3, host-progress3, kill-reaches-arrival, wipe-one-map, boss-hp-staggered-wipe, guests-pair-mobs, guest-acts-for-two, host-quits-title3, team-join3 |
| world (each player its own NPC gift) | iosefka-gift |

### Stays a single scenario (11)

| Where | Scenarios |
|---|---|
| a setting of its own that would change every other chapter | save-backups, map-3d, menu-languages, free-camera |
| each game its own settings / release (role_settings): ~105 s each | build-check-version, build-check-harder, build-check-same |
| half an hour by design: the long tier | soak |
| harder enemies on all three games | paarl-after-wipe |
| new-character saves (could share one run: both on rig/saves/new-character) | shop-own-weapons, new-char-cutscene |

## Test audit, 2026-11-10 (before the full run on the release after 1.4.0)

Report: `reports/test-audit-2026-11-10.md` in the project files. What it changed here:

- Deleted, each a strict part of a scenario that stays: `guest-alone-hits` (`guest-hits-host-comes`),
  `key-items-kept` (`key-items-silent`), `logarius-spells` and `shadows-spells` (their
  `-runner-leaves`), `boss-targets-host` (`boss-targets-teammate-revived`), `teams-apart3`
  (`teams-apart`), `dog-alone` (`dog-alone3`), `chalice-team` (stale since the team altars;
  `chalice-altar-team`).
- Merged: `spectate-default-down` into party-death/give-up, `spectate-lamp` into `spectate-follow`,
  joins/join-time into joins/restart-keeps.
- To the probes (no check of their own): `clinic`, `button-icons`, `map-team`.
- Repaired: crashes/resume (the place it comes back to), `dead-before-session` (hidden or put down
  again), `early-trip` (two lines that hang on the PC's timing), `chalice-load-inside-*` (a sync
  before the restart).
