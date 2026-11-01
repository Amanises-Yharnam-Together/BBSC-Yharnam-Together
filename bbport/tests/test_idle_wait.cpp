// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: a compute submission waits for idle, but never on a stream that waits for it.
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <thread>
#include "gpu/shim/bbport_idle_wait.h"

int main() {
    std::mutex mutex;
    std::condition_variable cv;
    // Idle already: at once.
    {
        std::unique_lock lock{mutex};
        BbIdleWait::IdleUnlessStuck(cv, lock, [] { return true; }, [] { return false; });
    }
    // Never idle, the stream waits on memory: it goes on (a plain wait hangs here for ever).
    {
        std::atomic<bool> stuck{false};
        std::thread gpu{[&] {
            std::this_thread::sleep_for(std::chrono::milliseconds{20});
            stuck = true;
        }};
        std::unique_lock lock{mutex};
        BbIdleWait::IdleUnlessStuck(cv, lock, [] { return false; }, [&] { return stuck.load(); });
        lock.unlock();
        gpu.join();
    }
    // Busy, not stuck: it still waits for idle (the frame pacing stays).
    {
        std::atomic<bool> idle{false};
        const auto start = std::chrono::steady_clock::now();
        std::thread gpu{[&] {
            std::this_thread::sleep_for(std::chrono::milliseconds{30});
            idle = true;
        }};
        std::unique_lock lock{mutex};
        BbIdleWait::IdleUnlessStuck(cv, lock, [&] { return idle.load(); }, [] { return false; });
        lock.unlock();
        gpu.join();
        assert(std::chrono::steady_clock::now() - start >= std::chrono::milliseconds{25});
    }
    std::puts("idle wait: ok");
    return 0;
}
