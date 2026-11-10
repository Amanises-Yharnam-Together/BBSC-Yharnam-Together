"""Download every message the bot can read in a Discord server.

Reads all text, announcement and voice-chat channels, every thread (active
and archived) and every forum post. Messages are saved under
data/<server id>/ as one JSON-lines file per channel or thread. Running it
again only downloads messages that are newer than the last run.

Settings (in tools/discord-audit/.env or the environment):
  DISCORD_BOT_TOKEN   the bot token from the Discord developer portal
  DISCORD_GUILD_ID    the server id (optional when the bot is in one server)

Only the Python standard library is needed:
  python fetch.py            download / update
  python fetch.py --list     show the servers the bot is in and stop
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from common import guild_dir, load_env, read_json, write_json

API = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together, 1.0)"

# Channel types, https://discord.com/developers/docs/resources/channel
TEXT, VOICE, CATEGORY, NEWS, STAGE, FORUM, MEDIA = 0, 2, 4, 5, 13, 15, 16
THREAD_TYPES = {10, 11, 12}
MESSAGE_CHANNELS = {TEXT, VOICE, NEWS, STAGE}
THREAD_PARENTS = {TEXT, NEWS, FORUM, MEDIA}


class Forbidden(Exception):
    pass


class Discord:
    def __init__(self, token):
        self.token = token
        self.calls = 0

    def get(self, path, **params):
        query = {k: v for k, v in params.items() if v is not None}
        url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
        for attempt in range(8):
            req = urllib.request.Request(url, headers={
                "Authorization": "Bot " + self.token,
                "User-Agent": USER_AGENT,
            })
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    self.calls += 1
                    body = json.loads(resp.read().decode("utf-8"))
                    # Be polite: wait out the bucket instead of hitting 429.
                    if resp.headers.get("X-RateLimit-Remaining") == "0":
                        time.sleep(float(resp.headers.get("X-RateLimit-Reset-After") or 1))
                    return body
            except urllib.error.HTTPError as err:
                if err.code == 429:
                    try:
                        wait = float(json.loads(err.read().decode("utf-8")).get("retry_after", 2))
                    except Exception:
                        wait = 2.0
                    time.sleep(wait + 0.25)
                    continue
                if err.code in (403, 404):
                    raise Forbidden(f"{err.code} on {path}")
                if err.code == 401:
                    sys.exit("Discord said 401 Unauthorized: the bot token is wrong or was reset. "
                             "Copy a fresh one from the developer portal into .env.")
                if err.code >= 500 and attempt < 7:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except urllib.error.URLError:
                if attempt < 7:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise RuntimeError(f"gave up on {path}")


def slim(msg):
    """Keep only what the audit needs from a Discord message object."""
    author = msg.get("author") or {}
    out = {
        "id": msg["id"],
        "t": msg.get("timestamp"),
        "author": author.get("global_name") or author.get("username") or "?",
        "author_id": author.get("id"),
        "bot": bool(author.get("bot")),
        "content": msg.get("content") or "",
    }
    if msg.get("edited_timestamp"):
        out["edited"] = msg["edited_timestamp"]
    files = [{"name": a.get("filename"), "url": a.get("url"), "size": a.get("size")}
             for a in msg.get("attachments") or []]
    if files:
        out["files"] = files
    embeds = []
    for e in msg.get("embeds") or []:
        text = " - ".join(x for x in (e.get("title"), e.get("description")) if x)
        if text:
            embeds.append(text[:1500])
    if embeds:
        out["embeds"] = embeds
    ref = msg.get("message_reference") or {}
    if ref.get("message_id"):
        out["reply_to"] = ref["message_id"]
    if msg.get("thread"):
        out["thread"] = msg["thread"]["id"]
    return out


def fetch_new_messages(api, channel_id, after):
    """All messages newer than `after`, oldest first."""
    found = []
    cursor = after or "0"
    while True:
        page = api.get(f"/channels/{channel_id}/messages", limit=100, after=cursor)
        if not page:
            break
        page.sort(key=lambda m: int(m["id"]))
        found.extend(page)
        cursor = page[-1]["id"]
        if len(page) < 100:
            break
    return found


def archived_threads(api, channel_id, kind):
    threads, before = [], None
    while True:
        page = api.get(f"/channels/{channel_id}/threads/archived/{kind}", limit=100, before=before)
        batch = page.get("threads") or []
        threads.extend(batch)
        if not page.get("has_more") or not batch:
            break
        before = batch[-1]["thread_metadata"]["archive_timestamp"]
    return threads


def pick_guild(api, wanted):
    guilds = api.get("/users/@me/guilds")
    if wanted:
        for g in guilds:
            if g["id"] == str(wanted):
                return g
        sys.exit(f"The bot is not in server {wanted}. It is in: "
                 + ", ".join(f"{g['name']} ({g['id']})" for g in guilds))
    if len(guilds) == 1:
        return guilds[0]
    if not guilds:
        sys.exit("The bot is not in any server yet. Use the invite link from the guide first.")
    sys.exit("The bot is in several servers. Put one id in .env as DISCORD_GUILD_ID:\n"
             + "\n".join(f"  {g['id']}  {g['name']}" for g in guilds))


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--guild", default=os.environ.get("DISCORD_GUILD_ID"), help="server id")
    ap.add_argument("--list", action="store_true", help="list the bot's servers and stop")
    args = ap.parse_args()

    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        sys.exit("No bot token. Put DISCORD_BOT_TOKEN=... in tools/discord-audit/.env (see README.md).")
    api = Discord(token)

    if args.list:
        for g in api.get("/users/@me/guilds"):
            print(g["id"], g["name"])
        return

    guild = pick_guild(api, args.guild)
    gid = guild["id"]
    gdir = guild_dir(gid)
    gdir.mkdir(parents=True, exist_ok=True)
    meta = read_json(gdir / "meta.json", {"channels": {}})
    meta["guild"] = {"id": gid, "name": guild["name"]}
    print(f"Server: {guild['name']} ({gid})")

    channels = api.get(f"/guilds/{gid}/channels")
    by_id = {c["id"]: c for c in channels}

    # Every thread: active ones for the whole server, archived ones per channel.
    threads = {}
    try:
        for t in api.get(f"/guilds/{gid}/threads/active").get("threads") or []:
            threads[t["id"]] = t
    except Forbidden:
        pass
    for c in channels:
        if c["type"] not in THREAD_PARENTS:
            continue
        for kind in ("public", "private"):
            try:
                for t in archived_threads(api, c["id"], kind):
                    threads[t["id"]] = t
            except Forbidden:
                pass  # no access, or no Manage Threads for private ones

    targets = [c for c in channels if c["type"] in MESSAGE_CHANNELS] + list(threads.values())
    skipped, new_total, empty_content = [], 0, 0

    for c in targets:
        cid = c["id"]
        parent = by_id.get(c.get("parent_id") or "")
        info = meta["channels"].get(cid, {})
        info.update({
            "name": c.get("name") or cid,
            "type": c["type"],
            "parent": parent.get("name") if parent else None,
            "parent_type": parent.get("type") if parent else None,
        })
        label = ("#" + info["parent"] + " > " if c["type"] in THREAD_TYPES and info["parent"] else "#") + info["name"]
        try:
            new = fetch_new_messages(api, cid, info.get("last_id"))
        except Forbidden:
            skipped.append(label)
            meta["channels"][cid] = info
            continue
        if new:
            with open(gdir / f"{cid}.jsonl", "a", encoding="utf-8") as f:
                for m in new:
                    s = slim(m)
                    if not s["bot"] and not s["content"] and not s.get("files") and not s.get("embeds"):
                        empty_content += 1
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
            info["last_id"] = new[-1]["id"]
            info["count"] = info.get("count", 0) + len(new)
            new_total += len(new)
            print(f"  {label}: +{len(new)}")
        meta["channels"][cid] = info
        write_json(gdir / "meta.json", meta)  # save progress as we go

    meta["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_json(gdir / "meta.json", meta)
    total = sum(ch.get("count", 0) for ch in meta["channels"].values())
    print(f"Done: {new_total} new messages, {total} saved in total, {api.calls} API calls.")
    if skipped:
        print(f"No access to {len(skipped)} channel(s): " + ", ".join(skipped[:15])
              + (" ..." if len(skipped) > 15 else ""))
        print("Give the bot's role View Channel + Read Message History there if they matter.")
    if new_total and empty_content > new_total * 0.5:
        print("WARNING: most messages came back with no text. Turn on 'Message Content Intent' "
              "on the Bot page of the developer portal, then delete the data folder and run again.")


if __name__ == "__main__":
    main()
