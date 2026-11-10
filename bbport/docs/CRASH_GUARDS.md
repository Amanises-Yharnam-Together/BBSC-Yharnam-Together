# Crash guards

Places in the game's own code (version 01.09) that read through a pointer they never check, and
crashed players. `scripts/patches.py` (`crash_guards`) adds a check to each, at any frame rate.
`BB_CRASH_GUARDS=0` turns them off; a guard whose site holds other code (another game version, an
external patch) is skipped and named in the log.

| Guard | Script | What crashed | What happens now |
| --- | --- | --- | --- |
| Online event without its data | `crash_guards.py` | the game describes an online event (0x1EB3D10) and, for event type 0, copies a string from the event's data without checking that there is any: "read access to 00000000000000a0 at guest offset 0x1eb56b7", right after the server's `ss.info` request timed out | type 0 with no data goes the way an unknown event type goes: "could not describe", no crash |

The code lies in the code segment's last page (`code_cave.py`), at 0x50D98C0, and touches no co-op
site.

## Credit

From [Supermedo/bloodborne_pc](https://github.com/Supermedo/bloodborne_pc) commit f1999924
("Crash guard: an online event without its data no longer crashes the game"), GPL-2.0-or-later. The
cave keeps the same address here. Thanks to Supermedo.
