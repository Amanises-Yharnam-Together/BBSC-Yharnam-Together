# Ludwig's fog (m34_00): event files and host log

Files: 1.09 = CUSA03173-patch\dvdroot_ps4\event; patched = Kaniel's install coop-game\CUSA03173-mods (launcher, 2026-11-03 21:38).
Made by ludwig_fog.py (party_boss_events.parse). `*.walls.txt`: every event with 2005:x / 2006:x / 2004:2 / 3:6 instructions and every InitializeEvent of common 7600-7699. `*.arena.txt`: in full, events 13404700-13404899, 13401800-13401804 and every event naming 13404742/13404799/13404800-13404811/13401800.

## 1. Multiplayer walls and fog objects
- m34 has **no** InitializeEvent of 7600-7699 (1.09 and patched): no multiplayer wall, so MultiplayerWalls() rightly has no 34xxxxx object. The same script finds m35's (event 0 line 19: `2000:0 [71, 7600, 3501990, 3503990]`).
- common.emevd: no 7600-7699 init either; 6 events with object/SFX instructions (common.*.walls.txt).
- Ludwig's fog is object **3401800** with SFX **3403800**. Only two events touch them:
  - 13404800 (the host's fog event): line 3/4 `2005:3 [3401800, 0]`, `2006:1 [3403800, 0]` (fog open, skipped for a client by line 2 `1003:5 [258]`); line 8/9 `2005:3 [3401800, 1]`, `2006:2 [3403800]` (fog shut) once 13401800 or 13401801 is on (lines 5-7).
  - 13401800 (the boss): line 5/6 and 16/17 `2005:3 [3401800, 0]`, `2006:1 [3403800, 1]` (fog gone).
- The other m34 fog, object 3401850 / SFX 3403850 (events 13404850/13404851), belongs to the boss of 13401850/13401851, not Ludwig.

## 2. The arena events and what keeps the fog
- Ludwig's "defeated" flag is the common flag **9471** (the boss event sets it with 3400-3403 at the kill; 13401800 is that event's own flag).
- 13401800, 1.09: line 0 `1003:101 [0, 9471]`: with 9471 on, at every load it runs lines 1-6 (Ludwig's two characters 3400800/3400801 disabled and killed, fog 3401800 off, SFX 3403800 deleted) and ends. With 9471 off it waits for both dead (lines 9-13), then removes the fog (16/17) and sets 9471, 3400-3403 (38-42).
- 13404800, 1.09: line 0 `1003:2 [256, 9471]` ends it at once with 9471 on: it never shuts the fog after the kill. Before the kill it shuts the fog (8/9) when the fight starts (13401801) and offers the walk-through (3:24 on 3400800/3401800, only while 13401800 is off, line 11-14).
- So in the files nothing keeps the fog up once 9471 is on: the fog comes back only if a game loads m34 with **9471 off** (13404800 runs and shuts it at 13401801, or the fog object keeps its map default while 13401800's load block is skipped).
- Patched differences (diff of the arena files):
  - 13404800 line 2 `1003:5 [258]` -> `[32514]` (the client skip never matches: the fog opens for a client too) and 13404801 line 4 `3:0 [257, 13404808]` -> `[263, ...]`, line 16 `2003:2 [13404809, 1]` -> `2003:22 [13404808, 13404809, 1]` (open_boss_fog_for_guests). Same for 13404850/13404851.
  - 13401800 lines 25/26 `1003:105 [257]` -> `[32513]`, `4:3 [0, 10000, 0]` -> `[7, ...]`, line 53 `4:3 [0, 10000, 1]` -> `[7, ...]`, lines 35/37 `2003:4` -> `2003:36` (item lots 3401800/3401802 for everyone). None touches 9471, 3401800 or 3403800.

## 3. Host log (C:\bb\cg1103\host\shad_log.txt)
- 67663: the kill sets `3400 3401 3402 4000 4047 4092 6674 7057 9471 13401800 13404805 13500000`. 9471 appears in no other line of the host's log: never cleared there.
- No line in 67600-68100 or 86490-86700 names a fog, wall, SFX or boss-fog patch; the 34xxxxx ids there are item lot 3401800 (67654 HoldGuestBossItem, "its flag 6674 off"), lamp 3401952 (67658, 67709) and return point 3402952 (67705, 86495).
- 86573/86575: at the next load the host's game kills 0x10038078/0x10038079 at once, which is 13401800's 9471-on block (lines 1-4) running, so on the host 9471 was on at that load and the same block removes the fog (lines 5/6).
- Open: whether 9471 was on in each guest's game at its loads (9471 is a common, per-save flag: a guest that did not own the kill may not have it), and whether the fog seen was 3401800 at all. The guests' logs are the place to check 9471.
