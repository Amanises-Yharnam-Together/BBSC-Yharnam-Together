"""Offline tests: a fake Discord API and a fake Claude. Run: python -m unittest -v"""

import io
import json
import shutil
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

import audit
import common
import fetch

G = "900"
CHANNELS = [
    {"id": "1", "type": 4, "name": "Community"},
    {"id": "10", "type": 0, "name": "bug-reports", "parent_id": "1"},
    {"id": "11", "type": 15, "name": "help-forum", "parent_id": "1"},
    {"id": "12", "type": 0, "name": "secret"},
    {"id": "13", "type": 2, "name": "Voice"},
]
THREADS = {
    "active": [{"id": "20", "type": 11, "name": "crash on join", "parent_id": "11"}],
    "archived_public_11": [{"id": "21", "type": 11, "name": "old post", "parent_id": "11",
                            "thread_metadata": {"archive_timestamp": "2026-10-01T00:00:00Z"}}],
}


def msg(i, text, author="lisara", files=()):
    return {"id": str(i), "timestamp": f"2026-11-0{1 + i % 8}T10:00:00+00:00",
            "author": {"id": "u-" + author, "username": author},
            "content": text,
            "attachments": [{"filename": f, "url": "https://cdn/" + f, "size": 5} for f in files]}


class FakeDiscord:
    def __init__(self):
        # 250 messages in #bug-reports to exercise paging (100 per page).
        self.messages = {
            "10": [msg(1000 + i, f"report {i}") for i in range(250)],
            "20": [msg(2000, "game crashes when I join on 1.3.2", "krolebord", ["log.zip"])],
            "21": [msg(2100, "black screen in Ebrietas fight")],
            "13": [],
        }

    def handle(self, path, params):
        if path == "/users/@me/guilds":
            return [{"id": G, "name": "Yharnam Together"}]
        if path == f"/guilds/{G}/channels":
            return CHANNELS
        if path == f"/guilds/{G}/threads/active":
            return {"threads": THREADS["active"]}
        if path.endswith("/threads/archived/public"):
            cid = path.split("/")[2]
            return {"threads": THREADS.get("archived_public_" + cid, []), "has_more": False}
        if path.endswith("/threads/archived/private"):
            raise fetch.Forbidden("403")
        if path.endswith("/messages"):
            cid = path.split("/")[2]
            if cid == "12":
                raise fetch.Forbidden("403")
            after = int(params.get("after", 0))
            newer = [m for m in self.messages[cid] if int(m["id"]) > after]
            page = newer[:int(params["limit"])]
            return list(reversed(page))  # Discord returns newest first
        raise AssertionError("unexpected call " + path)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for mod in (common, fetch, audit):
            for name, sub in (("DATA", "data"), ("OUT", "out"), ("HERE", ".")):
                if hasattr(mod, name):
                    p = mock.patch.object(mod, name, self.tmp / sub)
                    p.start()
                    self.addCleanup(p.stop)
        self.fake = FakeDiscord()

        def get(_self, path, **params):
            return self.fake.handle(path, {k: v for k, v in params.items() if v is not None})

        p = mock.patch.object(fetch.Discord, "get", get)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_fetch(self):
        env = {"DISCORD_BOT_TOKEN": "x", "DISCORD_GUILD_ID": ""}
        with mock.patch.dict("os.environ", env), mock.patch("sys.argv", ["fetch.py"]), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            fetch.main()
        return out.getvalue()


class FetchTests(Base):
    def test_downloads_channels_threads_and_forum_posts(self):
        out = self.run_fetch()
        gdir = self.tmp / "data" / G
        rows = lambda cid: [json.loads(x) for x in (gdir / f"{cid}.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows("10")), 250)
        self.assertEqual([r["id"] for r in rows("10")][:2], ["1000", "1001"])  # oldest first
        self.assertEqual(rows("20")[0]["files"][0]["name"], "log.zip")
        self.assertEqual(rows("21")[0]["content"], "black screen in Ebrietas fight")
        self.assertIn("#secret", out)  # reported as no access, not a crash
        meta = json.loads((gdir / "meta.json").read_text())
        self.assertEqual(meta["channels"]["20"]["parent"], "help-forum")

    def test_second_run_only_adds_new_messages(self):
        self.run_fetch()
        self.fake.messages["10"].append(msg(5000, "new bug: duel timer stuck"))
        out = self.run_fetch()
        self.assertIn("+1", out)
        lines = (self.tmp / "data" / G / "10.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 251)

    def test_warns_when_message_content_intent_is_off(self):
        for cid in self.fake.messages:
            for m in self.fake.messages[cid]:
                m["content"] = ""
                m["attachments"] = []
        self.assertIn("Message Content Intent", self.run_fetch())


class AuditTests(Base):
    def test_export_and_audit_with_links(self):
        self.run_fetch()
        calls = []

        def fake_ask(api, system, user, effort, schema=None):
            calls.append((system, user))
            if schema:
                num = int(user.split("crashes when I join")[0].rsplit("[#", 1)[1].split("]")[0])
                return json.dumps({"bugs": [{"title": "Crash on join", "refs": [num]}]})
            return f"# Bug audit\n\n### 1. Crash on join\nSources: [#{num_holder[0]}]"

        num_holder = []
        orig = fake_ask

        def wrapper(*a, **k):
            r = orig(*a, **k)
            if k.get("schema"):
                num_holder.append(json.loads(r)["bugs"][0]["refs"][0])
            return r

        with mock.patch.object(audit, "ask", wrapper), \
                mock.patch.object(audit, "client", lambda: None), \
                mock.patch("sys.argv", ["audit.py"]), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            audit.main()

        export = (self.tmp / "out" / "discord-messages.md").read_text()
        self.assertIn("## #help-forum > crash on join (forum post)", export)
        self.assertIn("(files: log.zip)", export)
        report = (self.tmp / "out" / "bug-audit.md").read_text()
        self.assertIn(f"https://discord.com/channels/{G}/20/2000", report)
        self.assertEqual(len(calls), 2)  # one extraction part, one merge

    def test_link_refs_handles_groups(self):
        refs = {1: "https://a", 2: "https://b"}
        self.assertEqual(audit.link_refs("see [#1, #2] and [#9]", refs),
                         "see [#1](https://a), [#2](https://b) and #9")

    def test_chunk_splits_big_channel(self):
        block = "## #big\n" + "\n".join("[#%d] x" % i + "y" * 50 for i in range(100))
        parts = audit.chunk([block, "## #small\n[#999] z"], limit=1000)
        self.assertGreater(len(parts), 3)
        self.assertTrue(all(len(p) <= 1200 for p in parts))
        self.assertIn("(continued)", parts[1])


if __name__ == "__main__":
    unittest.main()
