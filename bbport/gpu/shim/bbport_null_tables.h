// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: draws whose resource tables are null, told in the console. Players with textures that
// break after a trip (invisible floors and stairs, textures in the wrong place) sent logs with
// "SRT walker ... read through a bad pointer" counted at powers of two and nothing else: no map,
// no rate, nothing from the game's side. This line comes at the first such draw and then at most
// once per 30 s while they go on: the counts in that window, the map, and what the game's own
// hooks saw (null table pointers it handed to the GPU, its GX heap refusing a chunk).
// Pure: no Vulkan, no game; tests/test_null_tables.cpp.
#pragma once

#include <cstdint>
#include <cstdio>

namespace BbNullTables {

constexpr uint64_t WindowMs = 30000;

struct Counts {
    uint64_t null_root_walks = 0; ///< shader table walks with a null root (zeros, no fault)
    uint64_t vertex_skips = 0;    ///< draws skipped: a null vertex buffer table
    uint64_t game_pointers = 0;   ///< null table pointers the game handed to the GPU (guest hook)
    uint64_t heap_refusals = 0;   ///< the game's GX heap refused a chunk (guest hook)
};

inline Counts Minus(const Counts& a, const Counts& b) {
    return {a.null_root_walks - b.null_root_walks, a.vertex_skips - b.vertex_skips,
            a.game_pointers - b.game_pointers, a.heap_refusals - b.heap_refusals};
}

/// When to report: the first time, then once a window has passed since the last report.
/// `since` gets the counts since the last report. Not thread-safe: the caller holds a lock.
class Window {
public:
    bool Take(uint64_t now_ms, const Counts& total, Counts& since) {
        if (reported_ && now_ms - last_ms_ < WindowMs) {
            return false;
        }
        since = Minus(total, last_);
        if (since.null_root_walks == 0 && since.vertex_skips == 0) {
            return false; // nothing drawn wrong since the last report
        }
        reported_ = true;
        last_ms_ = now_ms;
        last_ = total;
        return true;
    }

private:
    bool reported_ = false;
    uint64_t last_ms_ = 0;
    Counts last_{};
};

/// What the game's side looked like when the line was made.
struct GameSide {
    uint32_t map = 0;               ///< packed map id (0: not in a map)
    bool pointer_probe = false;     ///< the null table pointer hook is in
    uint64_t last_caller = 0;       ///< eboot offset of the last caller that handed one
    uint32_t last_sgpr = 0;         ///< its user data register
    bool heap_probe = false;        ///< the GX heap refusal hook is in
    uint64_t last_refused = 0;      ///< bytes of the last refused chunk
    uint64_t game_pointers_all = 0; ///< since the start
    uint64_t heap_refusals_all = 0;
};

inline int Format(char* out, size_t size, const Counts& since, const GameSide& game) {
    char pointers[160], heap[128];
    if (game.pointer_probe) {
        if (since.game_pointers != 0) {
            std::snprintf(pointers, sizeof(pointers),
                          "%llu null table pointers (%llu in all, last from eboot+%#llx into "
                          "s%u)",
                          (unsigned long long)since.game_pointers,
                          (unsigned long long)game.game_pointers_all,
                          (unsigned long long)game.last_caller, game.last_sgpr);
        } else {
            std::snprintf(pointers, sizeof(pointers), "no null table pointers (%llu in all)",
                          (unsigned long long)game.game_pointers_all);
        }
    } else {
        std::snprintf(pointers, sizeof(pointers), "table pointers not watched");
    }
    if (game.heap_probe) {
        if (since.heap_refusals != 0) {
            std::snprintf(heap, sizeof(heap),
                          "its GX heap refused %llu chunks (%llu in all, the last %llu KiB)",
                          (unsigned long long)since.heap_refusals,
                          (unsigned long long)game.heap_refusals_all,
                          (unsigned long long)(game.last_refused >> 10));
        } else {
            std::snprintf(heap, sizeof(heap), "its GX heap refused no chunk (%llu in all)",
                          (unsigned long long)game.heap_refusals_all);
        }
    } else {
        std::snprintf(heap, sizeof(heap), "GX heap not watched");
    }
    return std::snprintf(out, size,
                         "GPU: draws with null resource tables on map %#010x, in the last 30 s at "
                         "most: %llu table walks with a null root (zeros), %llu draws skipped for "
                         "a null vertex table; the game handed the GPU %s, %s\n",
                         game.map, (unsigned long long)since.null_root_walks,
                         (unsigned long long)since.vertex_skips, pointers, heap);
}

/// The port's counts (bbport_null_tables.cpp), each a possible report: a table walk with a null
/// root (not from a speculative walk), a draw skipped for its null vertex buffer table.
void NoteNullRootWalk();
void NoteVertexSkip();

} // namespace BbNullTables
