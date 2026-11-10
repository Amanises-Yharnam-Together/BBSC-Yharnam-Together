"""Turn the downloaded Discord messages into one combined bug audit.

Two ways to use it:

  python audit.py --export-only
      Writes out/discord-messages.md: every message, channel by channel, with
      a short [#123] reference per message. No API key needed. Upload that
      file to Claude and ask for the audit.

  python audit.py
      Does the audit itself with the Claude API (needs ANTHROPIC_API_KEY in
      .env). Writes out/bug-audit.md with every bug merged across channels:
      how many people hit it, versions, first/last seen, workaround, status
      and links back to the original Discord messages.

Options: --since 2026-10-01  only messages from that day on
         --channels bugs,help  only channels/threads whose name contains one of these
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

from common import DATA, OUT, load_env, message_link, read_json

MODEL = "claude-opus-5-5"
CHUNK_CHARS = 400_000  # about 100k tokens of Discord text per extraction call

PRODUCT = ("Yharnam Together: a seamless co-op mod for Bloodborne (PC port and "
           "shadPS4-based emulator builds), with a launcher, a co-op server "
           "(Local or Global/public), teams of up to 5, duels and invasions.")


# ----------------------------------------------------------------------------
# Loading and formatting the messages


def load_guild(guild_id=None):
    guilds = [p for p in DATA.iterdir() if p.is_dir()] if DATA.exists() else []
    if guild_id:
        guilds = [p for p in guilds if p.name == str(guild_id)]
    if not guilds:
        sys.exit("No downloaded messages found. Run fetch.py first.")
    if len(guilds) > 1:
        sys.exit("Several servers downloaded; pass --guild <id> or set DISCORD_GUILD_ID.")
    gdir = guilds[0]
    meta = read_json(gdir / "meta.json", {})
    return gdir, meta


def channel_label(info):
    name = info.get("name", "?")
    if info.get("type") in (10, 11, 12) and info.get("parent"):
        kind = "forum post" if info.get("parent_type") in (15, 16) else "thread"
        return f"#{info['parent']} > {name} ({kind})"
    return f"#{name}"


def build_transcript(gdir, meta, since=None, only=None):
    """Return (blocks, refs). Each block is one channel's text; refs maps the
    short number used in the text to the Discord link of that message."""
    gid = meta["guild"]["id"]
    refs, blocks = {}, []
    n = 0
    channels = meta.get("channels", {})
    # Plain channels first, then their threads right after them.
    order = sorted(channels.items(), key=lambda kv: (
        (kv[1].get("parent") or kv[1].get("name") or "").lower(),
        kv[1].get("type") in (10, 11, 12),
        kv[0]))
    for cid, info in order:
        path = gdir / f"{cid}.jsonl"
        if not path.exists():
            continue
        label = channel_label(info)
        if only and not any(w in label.lower() for w in only):
            continue
        lines = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            m = json.loads(raw)
            if m.get("bot") and not m.get("content") and not m.get("embeds"):
                continue
            if since and (m.get("t") or "") < since:
                continue
            text = m.get("content", "").strip()
            extra = []
            if m.get("files"):
                extra.append("files: " + ", ".join(f["name"] or "?" for f in m["files"]))
            for e in m.get("embeds", []):
                extra.append("embed: " + e)
            if not text and not extra:
                continue
            n += 1
            refs[n] = message_link(gid, cid, m["id"])
            when = (m.get("t") or "")[:16].replace("T", " ")
            who = m.get("author", "?") + (" [bot]" if m.get("bot") else "")
            body = text.replace("\r", "")
            if extra:
                body += (" " if body else "") + "(" + "; ".join(extra) + ")"
            lines.append(f"[#{n}] {when} {who}: {body}")
        if lines:
            blocks.append(f"## {label}\n" + "\n".join(lines))
    return blocks, refs


def chunk(blocks, limit=CHUNK_CHARS):
    chunks, cur, size = [], [], 0
    for b in blocks:
        parts = [b]
        if len(b) > limit:  # one huge channel: split it on line breaks
            head, *rows = b.split("\n")
            parts, piece = [], head
            for r in rows:
                if len(piece) + len(r) > limit:
                    parts.append(piece)
                    piece = head + " (continued)"
                piece += "\n" + r
            parts.append(piece)
        for p in parts:
            if cur and size + len(p) > limit:
                chunks.append("\n\n".join(cur))
                cur, size = [], 0
            cur.append(p)
            size += len(p)
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


# ----------------------------------------------------------------------------
# Claude calls

BUG_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["bugs"],
    "properties": {"bugs": {"type": "array", "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "area", "what_happens", "how_to_trigger", "versions",
                     "platform", "reporters", "refs", "first_seen", "last_seen",
                     "workaround", "status", "status_evidence"],
        "properties": {
            "title": {"type": "string"},
            "area": {"type": "string"},
            "what_happens": {"type": "string"},
            "how_to_trigger": {"type": "string"},
            "versions": {"type": "array", "items": {"type": "string"}},
            "platform": {"type": "string"},
            "reporters": {"type": "array", "items": {"type": "string"}},
            "refs": {"type": "array", "items": {"type": "integer"}},
            "first_seen": {"type": "string"},
            "last_seen": {"type": "string"},
            "workaround": {"type": "string"},
            "status": {"type": "string", "enum": ["open", "said fixed", "unclear"]},
            "status_evidence": {"type": "string"},
        }}}},
}

EXTRACT_PROMPT = f"""You are auditing a Discord server for the game mod {PRODUCT}

Below is part of the server's message history. Every message starts with a
reference like [#123], then the date (UTC), the author and the text.

List every bug, crash, glitch, desync, install/launch/connection problem or
other thing that did not work as it should, that players or developers
report in these messages. Rules:
- One entry per distinct problem. If several people describe the same
  problem, make it one entry with all of them in reporters and all the
  message numbers in refs.
- Include problems mentioned only once. Leave out feature requests, balance
  opinions and plain questions that turned out to be user error, unless the
  answer shows a real problem.
- versions: every game/mod version that is mentioned with the problem
  (e.g. "1.3.2"); empty if none is said.
- platform: PC port, emulator, launcher, server, macOS, or unknown.
- status: "said fixed" only when a message says it was fixed or no longer
  happens (put that message number in status_evidence); otherwise "open" or
  "unclear".
- Dates as YYYY-MM-DD. Write in English, even when the messages are not.
- refs must be numbers that appear in the text below. Never invent any."""

MERGE_PROMPT = f"""You are writing the combined bug audit for the game mod {PRODUCT}

Below is a JSON list of bug entries that were extracted from different parts
of the project's Discord server. The same bug can appear several times under
different titles. Write the final audit in Markdown:

1. A title line "# Bug audit", then one sentence with the period covered
   and how many distinct bugs there are.
2. "## Summary": a table with columns  # | Bug | Area | People | Versions |
   Last seen | Status, sorted with the most-reported open bugs first.
3. "## Bugs": one "### N. Title" section per bug with: what happens; how to
   trigger it (if known); versions and platform; people who reported it and
   how many; first and last seen; workaround (if any); status and why; and
   "Sources:" followed by the message references written exactly as [#123].
4. "## Said to be fixed": the same short form for bugs whose status is said
   fixed, so they can be checked.

Merge duplicates (same symptom in the same place), and add up their
reporters (count distinct people) and refs. Keep every reference number you
were given; do not invent any. Be concise and concrete."""


def client():
    try:
        import anthropic
    except ImportError:
        sys.exit("The automatic audit needs the Anthropic SDK: pip install -r requirements.txt\n"
                 "Or run with --export-only and upload out/discord-messages.md to Claude.")
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        sys.exit("No ANTHROPIC_API_KEY in .env. Either add one, or run with --export-only "
                 "and upload out/discord-messages.md to Claude.")
    return anthropic.Anthropic()


def ask(api, system, user, effort, schema=None):
    output_config = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    with api.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config=output_config,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError("Claude declined this part of the history.")
    if msg.stop_reason == "max_tokens":
        print("  warning: the answer hit the length limit and may be cut short")
    return "".join(b.text for b in msg.content if b.type == "text")


def link_refs(text, refs):
    """Turn [#123] (and [#1, #2]) into clickable Discord links."""
    def one(num):
        url = refs.get(int(num))
        return f"[#{num}]({url})" if url else f"#{num}"

    def group(m):
        return ", ".join(one(x) for x in re.findall(r"\d+", m.group(1)))

    return re.sub(r"\[(#\d+(?:\s*,\s*#?\d+)*)\](?!\()", group, text)


# ----------------------------------------------------------------------------


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--guild", default=os.environ.get("DISCORD_GUILD_ID"))
    ap.add_argument("--export-only", action="store_true", help="only write out/discord-messages.md")
    ap.add_argument("--since", help="YYYY-MM-DD, skip older messages")
    ap.add_argument("--channels", help="comma list; keep channels whose name contains one of these")
    args = ap.parse_args()

    gdir, meta = load_guild(args.guild)
    only = [w.strip().lower() for w in args.channels.split(",")] if args.channels else None
    blocks, refs = build_transcript(gdir, meta, args.since, only)
    if not refs:
        sys.exit("No messages matched.")
    OUT.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    gname = meta["guild"]["name"]

    # The plain export is always written: it is also the audit's source.
    with open(OUT / "discord-messages.md", "w", encoding="utf-8") as f:
        f.write(f"# Discord history of {gname} (downloaded {meta.get('fetched_at', '?')})\n\n")
        f.write(f"{len(refs)} messages. Each [#N] reference maps to a Discord link in refs.json.\n\n")
        f.write("\n\n".join(blocks) + "\n")
    with open(OUT / "refs.json", "w", encoding="utf-8") as f:
        json.dump(refs, f)
    print(f"Wrote out/discord-messages.md ({len(refs)} messages) and out/refs.json")
    if args.export_only:
        return

    api = client()
    parts = chunk(blocks)
    print(f"Finding bugs in {len(parts)} part(s) with {MODEL} ...")
    found = []
    for i, part in enumerate(parts, 1):
        t0 = time.time()
        raw = ask(api, EXTRACT_PROMPT, part, effort="medium", schema=BUG_SCHEMA)
        bugs = json.loads(raw)["bugs"]
        found.extend(bugs)
        print(f"  part {i}/{len(parts)}: {len(bugs)} bug reports ({time.time() - t0:.0f}s)")
    with open(OUT / "bugs-raw.json", "w", encoding="utf-8") as f:
        json.dump(found, f, ensure_ascii=False, indent=1)

    print(f"Merging {len(found)} entries into one audit ...")
    report = ask(api, MERGE_PROMPT, json.dumps(found, ensure_ascii=False), effort="high")
    report = link_refs(report, refs)
    path = OUT / f"bug-audit-{stamp}.md"
    path.write_text(report + "\n", encoding="utf-8")
    (OUT / "bug-audit.md").write_text(report + "\n", encoding="utf-8")
    print(f"Wrote {path} (and out/bug-audit.md)")


if __name__ == "__main__":
    main()
