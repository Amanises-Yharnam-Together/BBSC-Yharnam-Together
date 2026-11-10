// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: the console line for draws with null resource tables (bbport_null_tables.h). Always on:
// it costs nothing while the tables are there, and one line per 30 s at most while they are not.
#include "bbport_null_tables.h"

#include <atomic>
#include <chrono>
#include <mutex>
#include "../bbcoop.h"
#include "bbport_guest_hooks.h"

namespace BbNullTables {
namespace {
std::atomic<uint64_t> null_root_walks{0}, vertex_skips{0};
std::mutex report_mutex;
Window window;
std::atomic<uint64_t> quiet_until{0}; ///< no report before (ms): the check without the lock

uint64_t NowMs() {
    return uint64_t(std::chrono::duration_cast<std::chrono::milliseconds>(
                        std::chrono::steady_clock::now().time_since_epoch())
                        .count());
}

void MaybeReport() {
    const uint64_t now = NowMs();
    if (now < quiet_until.load(std::memory_order_relaxed)) {
        return;
    }
    std::unique_lock lock{report_mutex, std::try_to_lock};
    if (!lock.owns_lock()) {
        return; // another thread is telling it
    }
    const auto game = BbGuestHooks::NullTables();
    Counts total;
    total.null_root_walks = null_root_walks.load(std::memory_order_relaxed);
    total.vertex_skips = vertex_skips.load(std::memory_order_relaxed);
    total.game_pointers = game.pointers;
    total.heap_refusals = game.heap_refusals;
    Counts since;
    if (!window.Take(now, total, since)) {
        return;
    }
    quiet_until.store(now + WindowMs, std::memory_order_relaxed);
    GameSide side;
    side.map = bbcoop_current_map();
    side.pointer_probe = game.pointer_probe;
    side.last_caller = game.last_caller;
    side.last_sgpr = game.last_sgpr;
    side.heap_probe = game.heap_probe;
    side.last_refused = game.last_refused;
    side.game_pointers_all = game.pointers;
    side.heap_refusals_all = game.heap_refusals;
    char line[640];
    Format(line, sizeof(line), since, side);
    std::fputs(line, stdout);
    std::fflush(stdout);
}
} // namespace

void NoteNullRootWalk() {
    null_root_walks.fetch_add(1, std::memory_order_relaxed);
    MaybeReport();
}

void NoteVertexSkip() {
    vertex_skips.fetch_add(1, std::memory_order_relaxed);
    MaybeReport();
}

} // namespace BbNullTables
