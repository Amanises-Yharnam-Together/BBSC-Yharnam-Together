# Friendly fire

Kaniel 2026-11-11: "we have duels, but also could have friendly fire. Which is basically you hit
your teammates always, but it's not an intention, just for harder play."

## How it plays

- It is a team rule, **off by default**. The team's leader turns it on in the game: the co-op team
  screen, the settings page (the cog, Triangle on a pad), the row **Friendly fire**. The other
  members see the row and cannot change it. It applies to the whole team at once, mid-hunt too.
- With it on, every teammate's attack hurts the teammates it reaches, at all times, on any map.
- It is not a duel: no question, no countdown, no banner, no colour change, nothing given back.
- A teammate's killing blow is a death as any other: the team's death mode decides (down for a
  revive, or spectate), with the same wipe, Rot and boss-fight rules as a death by an enemy.
- A downed teammate is still struck back up, as without the rule.
- Duels still work: a duel's lethal hit puts a duelist out as before.

## How it works

- `TeamRules.friendly_fire` (server/coop/coop.proto) is kept by the server with the team's other
  rules and reaches every member's game in the team's state. A server's default for new teams:
  `TeamDefaultRules=...; friendlyfire` (shadnet.cfg).
- The team screen sends the rules as one text (`ScreenRulesText`); the rule is its ninth value,
  written only when on, so the texts from before the rule read as they did.
- Each game puts the other members' bodies in its world on the invaders' team (the way a downed
  body is made strikable, `DownedTeams`), so the game's own hits land, as in a duel. Invaders'
  bodies are left alone. With the rule off each body takes its own team back.
- For such a body no enemy-bar damage is counted, and it is not taken for a downed one
  (`OnDownedTeam`).

## Checked

- Unit tests: the rule's text and words (`test_bloodborne_host_rules.cpp`), the bodies' teams
  (`test_bloodborne_party_death.cpp`), the server's rule (`server/tests/test_team_lobby.cpp`).
- Rig scenario `friendly-fire` (tools/rig/scenarios.py): off, strikes pass through; on, they land;
  a lethal one downs the guest and the host strikes it up; off again.

## Seen on the rig (2026-11-11, 2 games, headless)

- Off: a teammate's strikes pass through. On: the struck teammate loses HP on its own game, a
  lethal strike downs it as an ordinary party death (no duel, no wipe), strikes revive it. Off
  again: each body takes its own team back and strikes pass through.
- No banner, echoes, insight or invader lines in either game's log with the rule on.
- The `duel` and party-death down-revive scenarios pass unchanged.

## Known limit

With the rule on, an enemy targets only the player whose game runs it: a teammate's body on the
invaders' team drops out of that enemy's target list (probe `friendly-fire-enemy`: both players
listed with the rule off, only the runner's own with it on, both again once it is off). The enemy
keeps fighting, and an ordinary enemy is run by the nearest player's game, so it mostly goes for
whoever is nearest anyway; but a second teammate cannot draw an enemy another game runs, and a
boss (one game runs it for the fight) is expected to go for one player only. Not tested on a boss.
A fix needs the bodies strikable without leaving the enemies' targets (another team, or the
target search told to keep them).

## Not yet seen in play

- Lock-on, the enemy bar, damage numbers and colour over a teammate with the rule on (the rig is
  headless), and the settings row on a real screen.
