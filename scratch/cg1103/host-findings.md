# Host log findings: Kaniel's play test of the local 1.3.2 build (cdd01e4a), 2026-11-03

Source: copies in C:\bb\cg1103\host (shad_log.txt 23 MB, console.txt, shadnet.txt: the server ran on Kaniel's PC). Line numbers are shad_log.txt unless marked. Map ids: 0x15000000 Hunter's Dream, 0x1a000000 m26, 0x1d000000 m29 (chalice), 0x22000000 m34 Hunter's Nightmare, 0x23000000 m35 Research Hall; 0x24000000 (Fishing Hamlet) never appears.

## (3) The Ludwig kill (m34, not m35: Ludwig's arena is in the Hunter's Nightmare)

Ludwig's defeat flag is 13401800; his fog-entry flags (BossFogEntryFlags) are 13404808 and 13404858, with the arena's fog events using 13404800/13404802/13404805-13404810.

- Before the kill, the fog flags go on and off with each attempt (wipes): set 13404742 13404800 13404802 13404808 13404810 at 57601, cleared with 4000 4047 at 58229, again 58488/58971, 59268/59819.
- The kill:
  - 67630: `TraceCharacterDeath: Bloodborne boss death: 0x10038079 (the game's kill) hp 0/49975 ... map 0x22000000 in session true`
  - 67663: `flags in session: set 3400 3401 3402 4000 4047 4092 6674 7057 9471 13401800 13404805 13500000 | cleared`
  - 67664: `Co-op server world: applied seq 1544 map flag 13401800 on, seq 1545 map flag 13404805 on`
  - 67665: `Co-op team world: this host's world to the server (6960 flags on)` (then 6963 at 67752)
- The trip to the Dream right after: 67755 `Co-op lifecycle: trip, session epoch 9 (reset: kill visit)`; 68001 `set 9184 12100118 12105045 12105300 | cleared 6009 9187 13404742 13404799 13404800 13404802 13404803 13404804 13404805 13404806 13404807 13404808 ...` (the arena's per-visit flags reset on leaving); team world 6962 flags at 68009.
- **13401800 is never cleared in the host's log**: it appears only at 67663 and 67664 (grep of shad_log and shadnet).
- Back on m34 (86490 map change 0x15000000 -> 0x22000000):
  - 86568: `Co-op server world: applied seq 1730 map state of 0x22000000, seq 1731 map flag 13400100 on, ...` The server world's map state for m34 holds 13400100 13400220 13400221 13400310 13400320 13400902 13400903 and **not 13401800**, nor 13400941/13400944 (set at the kill, 67640/67749). The flags set before the kill made it into the map state; the kill's did not.
  - 86573/86575: `boss death: 0x10038078 ... 0x10038079 (the game's kill) hp 0/49975` right after the load: the host's own game kills Ludwig at load (its save has 13401800), so on the host Ludwig counts as dead.
  - 86652: the host's game sets the arena's fog event flags again (13404799-13404805, 13404811, 13404820...) and shares them (86653 `applied seq 1825 map flag 13404411 on, ...`). The same set/clear pairs repeat on each visit: 87220/87333, 87746/87870, 88435/88539, 88888/88938, 92178/92859, 93194/118616.
- Answer: on the host, the defeat flag came on at the kill and never went off; the host's game treats Ludwig as dead on every load. What a joining or rejoining member gets is the server world's map state of m34 (86568), and it lacks 13401800 (and the kill's 13400941/13400944). A guest loading from that state has Ludwig alive and the arena's fog. That fits "fog blocks everyone, still there after rejoining" for the guests. Who dropped it (the trip's "kill visit" reset at 67755, or the server's map state keeping only an older snapshot) is not in the host log; shadnet.txt logs no flag ids. The guests' bundles should show whether 13401800 reached them.

# Host log findings (items 4, 5, 6, 7, 2): co-op session 2026-11-03

Sources: `C:\bb\cg1103\host\shad_log.txt` (157,370 lines), `console.txt` (4,385), `shadnet.txt` (13,232).
Line numbers are shad_log.txt unless prefixed `shadnet:` or `console:`. Long lines are cut, and the
`[Debug] <Info> (GameMain) file.cpp:NNN Func:` prefix is dropped.
Build: `bloodborne_re.cpp:1349 ... version=1.3.2;revision=cdd01e4aa0d6;protocol=9` (line 106); co-op started 2026-11-03 20:45:16 UTC (line 107).

Member ids: `6b616e69656c` = kaniel (host), `4c6973617261` = Lisara, `703664656639396633373733623434` = "p6def99f3773b44" = krolebord
(shadnet:65 `team lobby: 703664656639396633373733623434 (krolebord) signed in`). Player bodies: 0x10044001 = Lisara's body
(see 34737 board), 0x10044002 = krolebord's.

Map note: chalice dungeons are **0x1d000000** (29 decimal, "m29"). 0x1a000000 is map 26 decimal, a normal map. Both are reported below.
**0x24000000 (Fishing Hamlet) never appears** in shad_log or shadnet (grep `0x24000000`, `24000000`: 0 hits).

---

## (4) Enemy owner hand-overs

Patterns: `party: enemy owner:`, `changes hands`, `jumped`, `-i bring`, `-i "brought back"`, `-i respawn`, `-i "put back"`, `enemy owner on map`.
Totals: `enemy owner:` 1315 lines (most are block-record/hand-out detail), `changes hands` 1000, `jumped` 29, `bring` 0, `brought back` 0, `respawn` 35, `put back` 12.

### Owner role changes per map (`party: enemy owner:` lines; "none" counted against the map the host was on)

| map | runs | follows | none | "runs map again" | "took the map over" |
|---|---|---|---|---|---|
| 0x15000000 (Dream) | 8 | 8 | 9 | 0 | 5 |
| 0x1a000000 | 3 | 1 | 4 | 2 | 0 |
| 0x1d000000 (chalice) | 3 | 3 | 4 | 1 | 1 |
| 0x22000000 (m34) | 15 | 6 | 14 | 6 | 4 |
| 0x23000000 (m35) | 7 | 2 | 10 | 0 | 2 |
| 0x18000000 | 1 | 2 | 2 | 0 | 0 |
| 0x24000000 | not found | | | | |

0x1a000000:
```
34273: party: enemy owner: this game runs map 0x1a000000's enemies (epoch 5) (t=545.4)
37988: party: enemy owner: none (the game's own way) (t=936.0)
37993: party: enemy owner: this game runs map 0x1a000000's enemies (epoch 5) (t=936.5)
37994: party: enemy owner: runs map 0x1a000000 again: its 1 fights go on (t=936.5)
39770: party: enemy owner: none (the game's own way) (t=1179.0)
39779: party: enemy owner: this game runs map 0x1a000000's enemies (epoch 5) (t=1179.5)
39780: party: enemy owner: runs map 0x1a000000 again: its 2 fights go on (t=1179.5)
43740: party: enemy owner: none (the game's own way) (t=1843.9)
43750: party: enemy owner: this game follows 703664656639396633373733623434 on map 0x1a000000 (epoch 15) (t=1844.4)
43752: party: enemy owner: handed 7 enemies on map 0x1a000000 (t=1844.4)
```
The none-then-runs-again pairs at 37988 and 39770 follow host revives (37947, 39723 `revive: respawn point 2602952 is on map 0x1a000000`).

0x22000000. On epoch 20 the owner flips none to "runs again" 4 times, each after a wipe:
```
57230: this game runs map 0x22000000's enemies (epoch 20) (t=2036.1)
58089: none (the game's own way) (t=2161.8)   58093/58094: runs ... again: its 2 fights go on
58866: none (t=2278.3)                         58871/58872: runs ... again
59606: none (t=2425.2)                         59611/59612: runs ... again
60860: none (t=2647.0)                         60864/60865: runs ... again
61108: this game follows 703664656639396633373733623434 on map 0x22000000 (epoch 25) (t=2669.3)
66878: this game runs map 0x22000000's enemies (epoch 30) (t=2796.2)
67765: this game follows 703664656639396633373733623434 on map 0x22000000 (epoch 32) (t=2971.5)
86616: this game runs map 0x22000000's enemies (epoch 37) (t=3273.4)
87823: this game runs map 0x22000000's enemies (epoch 43) / 87824 took the map over with 2 of the last owner's 2 moved enemies put back
88450: this game runs map 0x22000000's enemies (epoch 1) (t=3441.9)   <- epoch restarts at 1 (new party world, see item 6 note)
118579: runs (epoch 29) (t=4629.5) / 118580 took the map over with 0 of the last owner's 3 moved enemies put back
120772/120773, 122324/122325: runs map 0x22000000 again (after revives 120725, 122277)
```
0x23000000. Between 87421 and 88960 the host goes back and forth 0x22 <-> 0x23 (map changes 87369, 87728, 88575, 88801, 88947), and each move logs none/runs:
```
87424: this game runs map 0x23000000's enemies (epoch 38) (t=3339.9)
87642: this game runs map 0x23000000's enemies (epoch 38) (t=3384.5)
88629: this game runs map 0x23000000's enemies (epoch 2) (t=3450.3)
88752: this game runs map 0x23000000's enemies (epoch 2) (t=3469.0)
88960: this game runs map 0x23000000's enemies (epoch 4) (t=3489.9)
92035: this game follows 4c6973617261 on map 0x23000000 (epoch 10) (t=4041.0) / 92037 handed 20 enemies
92181: runs (epoch 11) / 92182 took the map over with 0 of the last owner's 11 moved enemies put back
92618: this game follows 4c6973617261 on map 0x23000000 (epoch 13) (t=4101.8) / 92620 handed 65 enemies
118261: runs (epoch 26) (t=4617.6) / 118262 took the map over with 18 of the last owner's 18 moved enemies put back
```

### Per-enemy "changes hands" (1000 lines, **all on 0x15000000 Hunter's Dream, t=149.0 to t=318.2**, lines 1080 to 16792)
The log stops at exactly 1000 lines, which looks like a log cap: none are logged after t=318.2, and none on 0x1a, 0x1d, 0x22 or 0x23.
24 distinct enemies flip back and forth between "runs here" and "follows". The top handles:
`1000000a` 66, `10000019` 62, `10000013` 60, `10000015` 59, `10000014` 54, `10000009` 54, `10000011` 53, `1000001a` 52.
Flips run at about 14 to 93 per 10 s, the whole time.
```
1087: party: enemy 1000000a (a) changes hands: runs here (t=149.0)
1374: party: enemy 1000000a (a) changes hands: follows (t=158.1)
2309: party: enemy 1000000a (a) changes hands: runs here (t=167.3)
2706: party: enemy 1000000a (a) changes hands: follows (t=170.7)
3234: party: enemy 1000000a (a) changes hands: runs here (t=175.3)
3383: party: enemy 1000000a (a) changes hands: follows (t=176.5)
...
5221: party: enemy 1000001a (1a) changes hands: runs here (t=194.0)
5277: party: enemy 1000001a (1a) changes hands: follows (t=195.0)
16791: party: enemy 10000006 (6) changes hands: runs here (t=318.2)
16792: party: enemy 10000009 (9) changes hands: follows (t=318.2)
```
Hand-out context: `1367: bosses in the hand-out to p6def99f3773b44 ...`, `1840: 3 of 7 enemies for p6def99f3773b44 held here until their hand-out settles (t=163.2)`, `1842: 1 of 6 enemies for Lisara held here ...`.

### "jumped" (29 lines), by map
0x15000000: 4 (plus 1 before the first map change), 0x1a000000: 9, 0x1d000000: 6, 0x22000000: 7, 0x23000000: 2.
- On every Dream load the same enemy logs the same jump: `1000001b jumped 18.7 m in one frame` at 1144 (t=149.0), 61351 (t=2670.9), 124591 (t=5758.9), 138122 (t=6678.9) and 141186 (t=7268.0).
- On 0x1a000000, enemy `10020076` jumps 5 times in 20 s:
```
43213: party: enemy 10020076 jumped 10.3 m in one frame (word 1, t=1771.3)
43240: ... 10020076 jumped 5.1 m (word 1, t=1775.4)
43402: ... 10020076 jumped 8.1 m (t=1781.8)
43422: ... 10020076 jumped 3.0 m (t=1786.8)
43441: ... 10020076 jumped 10.4 m (t=1790.8)
43120: party: enemy 10020075 jumped 21.3 m in one frame (word 1, t=1754.2)
```
- On 0x22000000, enemy `10038079` jumps 103.9 m twice:
```
60597: party: enemy 10038079 jumped 103.9 m in one frame (word 1, t=2577.5)
67368: party: enemy 10038079 jumped 103.9 m in one frame (word 1, t=2899.1)
67367: party: enemy 10038078 jumped 31.3 m in one frame (word ffff, t=2899.1)
```

### Bring-back / respawn / put back
`bring` and `brought back` are not found. The `respawn` hits are all host revives and wipes:
0x1a000000: 2 revives (37947, 39723), 0x22000000: 8 (58046, 58824, 59561, 60817, 87599, 88706, 120725, 122277), 0x1d000000: 1 (136281).
```
58046: revive: respawn point 3402951 is on map 0x22000000; travelling there (reset=true, void fall=false)
58047: live player died in a party session (state 3); revived without a world reload
58274: party wipe: 0 characters left dead by this member's save on map 0x22000000: (world respawn state 0, respawning=false)
```
Every `put back` line is a "took the map over" line: 43811, 66879, 67826, 87824, 92182, 92711, 93755, 118262, 118580, 124807, 138445, 141271.

### Send-rate lines (`enemy owner on map X: N frames/s; sent per s: positions .., AI records ..`), 713 lines
| map | n | AI records = 0.0 | positions = 0.0 |
|---|---|---|---|
| 0x15000000 | 173 | 132 | 0 |
| 0x1a000000 | 128 | 12 | 1 |
| 0x1d000000 | 135 | 7 | 1 |
| 0x22000000 | 203 | 13 | 4 |
| 0x23000000 | 64 | 15 | 10 |

All-zero lines (positions 0, HP 0, AI 0): 38194 (0x1a), 61006 (0x22), 87434, 87455 (0x23), 87861 (0x22), and a run from 88632 to 89121 (0x23 x8, 0x22 x2, during the 0x22/0x23 shuttling right after the epoch reset), plus 136510 (0x1d). Example:
```
88632: party: enemy owner on map 0x23000000: 115 frames/s; sent per s: positions 0.0, HP 0.0, AI records 0.0, per-hit 0.0, hand-over 0.0, hits 0.0
```
On the Dream, AI records are 0.0 in 132 of 173 lines, while positions run at about 28/s.

---

## (5) Duels

`-i duel`: shad_log 119 lines, shadnet 63, console 43.
Duel ids: in party world `d2fda805...` (shadnet) the duels are numbered 1 to 8. In the new party world `ab66afe0...` (created at shadnet:5415, 22:40:50) numbering starts again at **duel 1**.

Host-side duels (shad_log), all in the Dream before 34267:
```
4308: duel: ACCEPT for duel 1        4345: in duel 1 (hp 1240, 73 kinds of goods kept)   4714: duel 1 fights
4715: duel: body 0x10044001 (team 20) is a foe's   4716: body 0x10044002 (team 20) is a foe's
8132: duel 1 is over: WON, this player's side won  8137: body 0x10044002 takes its team 20 back
13585: ACCEPT for duel 2 ... 17873: duel 2 is over: WON, this player's side won  17874: team 2 won duel 2
19090: ACCEPT for duel 3 ... 21749: duel 3 is over: WON, this player's side won
26821: PROPOSE for duel 0 ... 26856: in duel 4 ... 27325: DEFEATED for duel 4  27326: this player is out of duel 4 (no party death)
30200: ACCEPT for duel 5 ... 30507: body 0x10044001 (team 19) is a foe's ... 31800: duel 5 is over: WON, this player's side won  31806: body 0x10044001 takes its team 19 back
34849: duel: DECLINE for duel 6
77374: PROPOSE for duel 0 ... 77646: in duel 7 (hp 1302 ...) 77858/77859: bodies 0x10044001/0x10044002 (team 19) are foe's ... 79697: DEFEATED for duel 7 ... 79703: duel 7 is over
80654: PROPOSE for duel 0 ... 80769: in duel 8 ... 83991: DEFEATED for duel 8 ... 84131: duel 8 is over: WON, this player lost
111857: duel: PROPOSE for duel 0        <- no ACCEPT/"in duel"/countdown/"fights"/SetFoeTeams follows
116634: duel: PROPOSE for duel 0        <- same
```
Team numbers: foe bodies are shown as team 20 (duels 1 to 4) or team 19 (duels 5, 7, 8). The host's side wins as "team 2". No `type N team N` lines were found (pattern `type [0-9]* team`: 0 hits). The only `type 0` line is `33635: party member (type 0) lost a member`.
Downed-team lines (`SetDownedTeams: body 0x1004400x takes team 21` / `team 19`, 35005 to 39557) are party-death, not duel.

**The duel Kaniel reported (no duel state on the host):** this is duel 1 of world ab66.
```
shadnet:6995 22:59:08.238 party world ab66afe0...: duel 1: 6b616e69656c proposes, 2 asked
shadnet:6996 22:59:09.868 duel 1: 4c6973617261 accepts
shadnet:7001 22:59:10.629 duel 1: 703664656639396633373733623434 accepts
shadnet:7002 22:59:10.629 duel 1: 3 in, the countdown runs
shadnet:7006 22:59:13.635 duel 1: the fight starts
shadnet:7037 22:59:42.573 vitals: 4c6973617261 up 15000000, 6b616e69656c down 15000000, ...
shadnet:7038 22:59:43.763 duel 1: 4c6973617261 is out
shadnet:7067 23:00:07.103 6b616e69656c's duel request refused: A duel is already under way.
shadnet:7092 23:00:25.883 duel 1 over: MAP (6b616e69656c)
```
On the host side, the host sends PROPOSE (111857) and then logs nothing else about the duel: no ACCEPT, no `in duel 1`, no countdown, no `SetFoeTeams`, and no "Accept?" box in console.
While the server counts the host as "in", the host is downed 4 times on 0x15000000, and the shadnet vitals flip `6b616e69656c down` at 22:59:42, :51, :58 and 23:00:11:
```
114552: party death: down 627001365 on map 0x15000000, 1328 damage to get up (max HP 1328, pose 0)
115294: party death: down 627001366 on map 0x15000000, 2656 damage to get up
115900: party death: down 627001367 on map 0x15000000, 5312 damage to get up
116976: party death: down 627001368 on map 0x15000000, 5312 damage to get up
```
The host's second PROPOSE (116634) is refused by the server because "A duel is already under way". Console shows `console:2913 Trade menu: box pushed: Nobody else of your team is here to duel.`
The fix: the host changes map, and the server ends the duel as "MAP (kaniel)":
```
118258: Bloodborne map change 0x15000000 -> 0x23000000 at (-318.7, 1553.0, -824.2) trip=false
```
Hypothesis (not proven by the log): the host's duel code may have ignored the new world's "duel 1" because it had already seen duel ids up to 8 in the old world. Once it ignored the start, the host never set duel state for itself. The guests did start the duel and treated the host as a foe.

---

## (6) Lisara's drop and rejoin (early, about t=515, 21:52:05 server time)

Patterns: `-i lisara` (1215 hits), `-i krolebord` (168 in shad_log, mostly nameplates and packet links), `lifecycle`, `session epoch`, `member left/joined`, `-i re-create|recreate|re-made|copy`, `Bloodborne presence:`.

Server:
```
shadnet:892 21:52:04.935 Room 1 "Lisara" left mid= 34
shadnet:893 21:52:05.048 party world d2fda805...: 4c6973617261: leave, its share goes (0 entries)
shadnet:895 21:52:05.336 Room 1 "Lisara" joined mid= 36
shadnet:900 21:52:05.867 party world d2fda805...: 4c6973617261: join, its share goes (0 entries)
```
Host (shad_log):
```
33239: Bloodborne party: a left member's notice not shown
33240: Bloodborne member leave from 0x178d2b3 self=false trip=false map=0x15000000
33285: Matching2 signaling established: ctx=1 room=1 member=36 addr=0xcb07680a:3658
33296: Bloodborne party: a joining member got player number 4
33390: Bloodborne party: the player's stats or face changed; sent its data to the session again
33410: Bloodborne presence: no member on map 0x15000000 by player 0x10044001 at (-6, -1, 6): hidden (0 enemies' targets on it forgotten)
33411: Co-op team load: in the session true, 1 of 2 others seen, cutscene false: not ready
33635: Bloodborne party member (type 0) lost a member; staying where it is map=0x15000000 load wait 1 (action buttons 1) cleared
34191: Co-op lifecycle: trip, session epoch 3 (reset: kill visit)
34192: Bloodborne party trip: 1 remote join tasks saved (1 found): [kind=1 slot=6 flags=0x4c step=6]
34267: map change 0x15000000 -> 0x1a000000 ...
34355: party trip: re-creating p6def99f3773b44 on map 0x1a000000 (1 of 2 members)
34361: party trip: re-creating p6def99f3773b44 Lisara on map 0x1a000000 (2 of 2 members)
34363: RecreateRemotePlayers: party trip: re-creating remote player kind=1
34366: Co-op team load: in the session true, 2 of 2 others seen, cutscene false: ready (settling)
34671: presence: no member on map 0x1a000000 by player 0x10044001 at (138, 1061, -15): hidden
34737: presence: a member stands by player 0x10044001 at (138, 1061, -15) again: shown; board (self 6b616e69656c): [4c6973617261 map 0x1a000000 at (137, 1061, -15)] [6b616e69656c map 0x1a000000 ...] [703664656639396633373733623434 map 0x15000000 at (2, -3, -10)]
```
- **No `Co-op lifecycle: member left` line** is logged for this drop, and no `member joined` line exists anywhere (0 hits).
  Compare the later departure, where LogMemberLeave is followed by lifecycle lines: `86691 LogMemberLeave ...` then `86695: Co-op lifecycle: member left, session epoch 9`.
- Between the rejoin (33296) and the trip (34191) there is **no re-create**, and the team load stays at "1 of 2 others seen".
- **What happened to Lisara's old copy:** body 0x10044001 (Lisara's, per the board at 34737) was **hidden by presence (33410), not deleted**.
  It was only re-created and shown after the party trip to 0x1a000000 (34355 to 34366, 34737). This matches Kaniel's report.
- Later the whole party leaves and rejoins: shadnet:5107 / 5113 (22:38:42) Lisara and krolebord leave Room 1. Host lines:
  86695 / 86698 member left, 87194 `leave, session epoch 10`, 87245 `join, session epoch 11`, 88407 `leave, epoch 12`, 88448 `join, epoch 13`.
  On the server, new party world ab66afe0 starts (shadnet:5415 `a new world 5618838d`). shadnet:5125 onward shows `sent ... to Lisara ..., a game of another team or none: dropped` spam.

---

## (7) Performance

Patterns: `slowest` (241), `CoopWorker` (0), `co-op tick thread` (0), `off the main thread` (0), `BB_COOP` (1), `long frame` (0), `spike` (0), `frame time`/`frametime` (0), `own thread`/`tick thread` (0), `frames/s` (713), console `Perf:` (246).

**Co-op tick thread:** no startup line says the co-op tick runs on its own thread. The only related startup line is
```
136: [Debug] <Info> () bloodborne_trace_diag.cpp:257 StartCoopTrace: Bloodborne co-op trace is off (BB_COOP_TRACE=1 turns it on)
```
All ReportCoopTime, TickEnemyOwner and TickDuel lines are tagged `(GameMain)`. Tick call counts are about 2,250 to 2,500 per 30 s, which is about one per game frame. No "CoopWorker" thread appears in the console "busiest" thread lists either (GameMain 35 to 38%).
**The log therefore shows the co-op tick on GameMain.**
```
3307: Co-op tick slowest parts: TickPlayersOnThisMap avg 0.06 ms max 7.16 ms (2501 calls), TickPartyDeath avg 0.02 ms max 0.72 ms ...
3308: Co-op time: enemy step avg 0.03 ms max 6.46 ms (2502 calls), ..., co-op tick avg 0.12 ms max 12.90 ms (2502 calls)
```
Co-op tick average over 241 reports: 0.12 to 0.31 ms. The highest maximums: 12.90 ms (3308), 5.06 (139192), 4.35 (138522), 2.77 (91324).

**`enemy owner on map ...: N frames/s`** (713 lines), as min / median / max:
| map | n | frames/s |
|---|---|---|
| all | 713 | 6 / 78 / 118 |
| 0x15000000 | 173 | 45 / 76 / 93 |
| 0x1a000000 | 128 | 6 / 78 / 113 |
| 0x1d000000 | 135 | 59 / 84 / 106 |
| 0x22000000 | 203 | 7 / 76 / 118 |
| 0x23000000 | 64 | 14 / 87 / 118 |
| 0x18000000 | 10 | 76 / 79 / 91 |

Lines under 40 frames/s:
```
42969: enemy owner on map 0x1a000000: 6 frames/s; sent per s: positions 1.8, HP 1.9, AI records 0.0 ...
67369: enemy owner on map 0x22000000: 29 frames/s; positions 4.0, HP 12.7 ...
91323: enemy owner on map 0x23000000: 14 frames/s; positions 6.4, HP 5.0, AI records 0.9 ...
120059: enemy owner on map 0x22000000: 7 frames/s; positions 5.3, HP 2.6, AI records 0.2 ...
```
console `Perf:` (30 s windows, 246 lines): average FPS 52.8 / 78.1 / 116.7, 1% low 14.7 / 70.5 / 103.8, worst frame 39.1 / 71.1 / **415.3 ms**. Worst windows:
```
console:1794 Perf: 79.9 FPS over 30 s, 1% low 67.1 FPS, worst frame 415.3 ms, 0 shader/pipeline compiles
console:1572 Perf: 80.3 FPS ..., worst frame 406.9 ms, 0 shader/pipeline compiles
console:3158 Perf: 85.9 FPS ..., worst frame 402.7 ms, 7 shader/pipeline compiles
console:4333 Perf: 52.8 FPS over 30 s, 1% low 14.7 FPS, worst frame 95.1 ms, 72 shader/pipeline compiles
```
Near the end the FPS drops to about 57 (console:4274 to 4371). There are 53 console lines matching `== Stall during rendering at flush N`.
Log noise: `kept flag 12100122 off against the other player's` appears **36,418 times**. A guest toggles flag 12100122 1/0 continuously.

---

## (2) Flags 72100100/72100101/72100102, FollowTeamStory, level-up / kneel / 6700

- `FollowTeamStory`: **not found** in any of the three logs.
- `kneel`: **not found**. `LevelUp` / `level up`: not found. The `level-up` hits are only the ClearStuckDollLevelUpFlag lines below.
- shadnet and console: no 7210010x hits.

`flags in session: set/cleared` with 7210010x. These come in set-then-clear pairs. Several sets coincide with 6700 (the Doll's level-up flag) and with `ResendOwnDataOnChange: the player's stats or face changed`, i.e. the host levelling up:
```
8879:  flags in session: set 72100100 72100101 72100102 | cleared
9160:  flags in session: set | cleared 72100100 72100101 72100102
9396:  set 72100100 72100101 72100102 | cleared
9688:  set | cleared 72100100 72100101
46975: flags in session: set 6700 12100118 72100100 72100101 72100102 72100111 | cleared
49295: the player's stats or face changed; sent its data to the session again
49411: set | cleared 12100118 72100100 72100101 72100102
50234: set 72100100 72100101 72100102 | cleared
50755: set | cleared 12100118 72100100 72100101 72100102
50797: the player's stats or face changed; sent its data to the session again
97322: set 6700 12100118 | cleared
97569: set 72100101 72100102 | cleared
97853: set | cleared 12100118 72100101 72100102
102488: set 72100100 72100101 72100102 | cleared
102630: the player's stats or face changed; sent its data to the session again
102731: set | cleared 12100118 72100100 72100101 72100102
141653: flags in session: set 6700 12100118 72100100 72100101 72100102 | cleared
142028: set | cleared 72100100 72100102
142089: the player's stats or face changed; sent its data to the session again
142251: set | cleared 12100118 72100101
```
Team / server world:
```
34248: SetWorldFlags: Co-op team world: flags set to the world's (-off): 1001 -1003 6009 -6903 -12100101 -12410657 -12410658 -72100102 -72100133
34302: flags in session: set 1001 | cleared 1003 6700 6903 12100101 ... 72100102 72100133
```
Guests sending these flags (`the other player sends flag ...`), 68 lines: 72100100=0 x8, 72100101=0 x15, 72100101=1 x7, 72100102=0 x14, 72100102=1 x7, e.g.
```
1013-1015: the other player sends flag 72100100 = 0 / 72100101 = 0 / 72100102 = 0
8669: the other player sends flag 72100102 = 1     8670: ... 72100101 = 1
```
No `kept flag 7210010x` line exists, so the host never holds these flags locally against the others. The `kept flag` lines cover only 12100122, 6810, 6811, 9306, 6686, 6687, 6695 and 6696.
In this session the host shares 7210010x as ordinary session flags.
6700:
```
34250: the Doll's level-up flag 6700 was on as map 0x1a000000 loaded; cleared
57211: the Doll's level-up flag 6700 was on as map 0x22000000 loaded; cleared
118242: the Doll's level-up flag 6700 was on as map 0x23000000 loaded; cleared
```
