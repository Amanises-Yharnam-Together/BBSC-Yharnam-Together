# More than five hunters (research, 2026-10-29)

Amanises, for teams past five (BBSC tested five; five was a target, not the game's ceiling).
Read from the EU 01.09 eboot with tools/bloodborne-xref-scan (BBSC offsets, image base 0). Nothing
here is built yet.

## What already allows more

- The HUD has seven remote players' tags (`RemotePCTag0-6`), and a guest's player slot
  (GameMan +0x16F4) runs up to 7: the character side looks made for eight (this player and
  seven). STRONGLY INDICATED, not traced through WorldChrMan yet.
- The server's teams, slots and lists are ours (`TeamSize`, `GuestSigns`).

## The fives in the game

1. **The session's maximum.** The session object (`[0x0553D6D0]`, constructor 0x017875D0) is
   made with `mov dword ptr [r12+0x0C], 0x05` at 0x0178760D. CONFIRMED readers:
   - 0x01788F5B in CreateSession 0x01788ED0: `mov esi, [r14+0x0C]` passed to the session manager
     0x01ECFCD0, the room's member slots (shadNet's log: `max= 5`). One byte to raise.
   - 0x01874B9D in the summon builder 0x01874710 (members `[+0x14]` below it) and 0x018760D3 in
     QueueInsert 0x01876060 (`[+0x18]` below it). Team joins do not go through the summon, so
     these matter for bells only.
2. **A hard-coded 4 in the summon builder** (0x01874BBE: cooperators + invaders + others +
   pending `< 4`). Bells only, as above.
3. **The member list** (GameMan `[0x05556678]` +0x16F8): an object of 0xB0 bytes (allocated at
   0x0156783E, constructor 0x015BA630). Counts at +0x08 (white phantoms), +0x0C (black), +0x10,
   +0x14 (all), +0x18; **five entries of 0x14 bytes inline at +0x1C..+0x7F**, then +0x90, +0x94,
   +0x98 (the guest gate's "in another world" id), +0xA0, +0xA8. It cannot grow in place.
   Its methods sit together at 0x015BAD90-0x015C4F00; several loop exactly five times
   (0x015BADEA `cmp eax, 5`, 0x015BBA33 `cmp r13, 5`, 0x015BBDD3 `cmp r15, 5`). 144 functions
   read GameMan +0x16F8, most of them only the counts or +0x98.

## The way past five

1. Raise the session's maximum (0x0178760D) to N.
2. The member list: give it room for N entries. Either allocate the object larger and move the
   fields after the entries (every +0x80..+0xA8 reader changes: risky), or keep the object and
   move only the entries to a block of our own, changing every entry access (the class's
   methods above, and any of the 144 readers that index entries; each one checked by hand) and
   the five-count loops to N. A trace line at each patched site, so a test shows which ran.
3. Look for other per-player tables of five (or of the session's maximum): WorldChrMan's player
   slots, the network player list, P2P connections, the phantom colours, the HUD's party list
   (ours: `PartyListSize`).
4. Ours: `TeamSize`, `GuestSigns` (3, 2, 1 after 7, 6, 5, 4?), `BBCOOP_LOBBY_TEAM`, the screens.

## Risk

A table of five that is missed shows only with that many players, as a crash or a player who
never appears. Each step needs a test with that many games; two games already fill an 8 GB
laptop's graphics memory.
