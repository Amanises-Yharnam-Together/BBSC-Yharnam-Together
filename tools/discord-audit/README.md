# Discord bug audit

A small read-only bot that downloads every message in the project's Discord
server (channels, threads, forum posts, attachment names) and turns them into
one combined bug audit: duplicates merged, how many people hit each bug,
versions, first/last seen, workarounds, status, and links back to the
original messages.

The bot never posts anything and only needs permission to read.

## Files

| File | What it does |
| --- | --- |
| `fetch.py` | Downloads messages into `data/`. Re-running fetches only new ones. Standard library only. |
| `audit.py` | Writes `out/discord-messages.md` (plain export) and, with an Anthropic API key, `out/bug-audit.md`. |
| `run-audit.bat` | Windows: runs both, double-click. |
| `.env.example` | Copy to `.env` and fill in. `.env`, `data/` and `out/` are git-ignored. |

## One-time setup (about 5 minutes)

### 1. Create the bot

1. Open <https://discord.com/developers/applications> and sign in.
2. **New Application**, name it e.g. `Yharnam Bug Audit`, accept, **Create**.
3. Left menu **Bot**:
   - Under **Privileged Gateway Intents** turn on **Message Content Intent**
     and press **Save Changes**. Without it Discord sends every message
     with empty text.
   - Turn **Public Bot** off, so only you can add it to servers.
   - Press **Reset Token**, confirm, then **Copy**. This is the password of
     the bot: don't paste it in Discord, a chat or a commit.

### 2. Invite it to the server

1. Left menu **General Information**: copy the **Application ID**.
2. Open this link with your id in place of `APP_ID`:

   `https://discord.com/oauth2/authorize?client_id=APP_ID&scope=bot&permissions=66560`

   (66560 = View Channels + Read Message History.)
3. Pick the server, **Authorize**.
4. If some channels are private (staff, testers), open each channel's
   settings, **Permissions**, add the bot's role and allow **View Channel**
   and **Read Message History**. `fetch.py` lists the channels it can't read.
   Archived *private* threads also need **Manage Threads**; skip it unless
   bugs are reported in private threads.

### 3. Give the token to the tool

In `tools\discord-audit\` copy `.env.example` to `.env` and paste the token
after `DISCORD_BOT_TOKEN=`. Optional: `ANTHROPIC_API_KEY=` for the automatic
audit (from <https://console.anthropic.com/settings/keys>).

Needs Python 3.9+ (`python --version`). For the automatic audit also run
`pip install -r requirements.txt` once.

## Running it

Double-click `run-audit.bat`, or:

```
python fetch.py                  # download / update messages
python audit.py --export-only    # out\discord-messages.md, no API key needed
python audit.py                  # out\bug-audit.md via the Claude API
python audit.py --since 2026-10-01 --channels bug,help
```

Without an API key, upload `out\discord-messages.md` to Claude in the
project and ask for the audit.

The first download of a big server takes a few minutes (Discord allows about
50 requests a second; the script waits when asked to). Later runs only fetch
new messages, so it can run on a schedule (Windows Task Scheduler or cron on
the server).

## Privacy

`data/` holds the server's messages in plain text. Keep it on your own
machine, don't commit it (it is git-ignored) and delete it when you no longer
need it. The automatic audit sends the message text to the Claude API.

## Tests

`python -m unittest -v` (offline: fake Discord, fake Claude).
