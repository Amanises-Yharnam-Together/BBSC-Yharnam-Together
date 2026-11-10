// SPDX-License-Identifier: GPL-2.0-or-later
// The console line for draws with null resource tables (gpu/shim/bbport_null_tables.h): at the
// first one, then at most once per 30 s while they go on, with the counts of that window, the
// map and the game's side, so a player's log tells where and how often (krolebord's 1.3.1 log,
// 2026-10-28: only "SRT walker ... read through a bad pointer" at powers of two).
//   ninja -C out/gpu null-tables-test && out/gpu/null-tables-test.exe
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "bbport_null_tables.h"

namespace {
int failures = 0;
void Check(bool ok, const char* what) {
    if (!ok) {
        std::printf("null-tables-test: %s\n", what);
        ++failures;
    }
}
} // namespace

int main() {
    using BbNullTables::Counts;
    BbNullTables::Window window;
    Counts since;
    // Nothing wrong yet: no line.
    Check(!window.Take(1000, Counts{}, since), "a line with nothing to tell");
    // The first null-root walk: a line at once.
    Counts total{1, 0, 0, 0};
    Check(window.Take(2000, total, since) && since.null_root_walks == 1, "no line at the first");
    // More within 30 s: held.
    total = {5000, 3, 0, 0};
    Check(!window.Take(20000, total, since), "a second line within 30 s");
    Check(!window.Take(31999, total, since), "a line before 30 s passed");
    // 30 s on: the window's counts.
    Check(window.Take(32000, total, since), "no line after 30 s");
    Check(since.null_root_walks == 4999 && since.vertex_skips == 3, "the window's counts");
    // A quiet window: nothing; the next one after it is told at once.
    Check(!window.Take(70000, total, since), "a line for a quiet window");
    total.vertex_skips = 4;
    Check(window.Take(90000, total, since) && since.vertex_skips == 1 && since.null_root_walks == 0,
          "no line after a quiet window");

    // The line: map, counts and the game's side.
    char line[512];
    BbNullTables::GameSide game;
    game.map = 0x22000000;
    game.pointer_probe = game.heap_probe = true;
    game.last_caller = 0x1098571;
    game.last_sgpr = 2;
    game.last_refused = 1 << 20;
    game.game_pointers_all = 7;
    game.heap_refusals_all = 2;
    BbNullTables::Format(line, sizeof(line), Counts{120, 4, 7, 2}, game);
    Check(std::strstr(line, "map 0x22000000") != nullptr, "no map");
    Check(std::strstr(line, "120 table walks with a null root") != nullptr, "no walk count");
    Check(std::strstr(line, "4 draws skipped") != nullptr, "no skip count");
    Check(std::strstr(line, "7 null table pointers (7 in all, last from eboot+0x1098571 into s2)") !=
              nullptr,
          "no game pointers");
    Check(std::strstr(line, "refused 2 chunks (2 in all, the last 1024 KiB)") != nullptr,
          "no heap refusals");
    BbNullTables::Format(line, sizeof(line), Counts{1, 0, 0, 0}, BbNullTables::GameSide{});
    Check(std::strstr(line, "table pointers not watched") != nullptr &&
              std::strstr(line, "GX heap not watched") != nullptr,
          "unwatched game side");
    game.game_pointers_all = 0;
    BbNullTables::Format(line, sizeof(line), Counts{1, 0, 0, 0}, game);
    Check(std::strstr(line, "no null table pointers (0 in all)") != nullptr, "no pointers told");
    if (failures == 0) {
        std::printf("null-tables-test: ok\n");
    }
    return failures == 0 ? 0 : 1;
}
