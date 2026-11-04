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
    // Kaniel 2026-11-01 (device lost on 1.3.2): the stream waits on memory for a moment, again and
    // again, as in every frame; busy all the while. That is no deadlock: it waits for idle.
    {
        std::atomic<bool> idle{false};
        std::atomic<bool> flicker{false};
        std::atomic<bool> done{false};
        const auto start = std::chrono::steady_clock::now();
        std::thread gpu{[&] {
            for (int i = 0; i < 40; ++i) { // 40 short waits of 5 ms, 200 ms in all
                flicker = (i % 2) == 0;
                std::this_thread::sleep_for(std::chrono::milliseconds{5});
            }
            flicker = false;
            std::this_thread::sleep_for(std::chrono::milliseconds{100});
            idle = true;
            done = true;
        }};
        std::unique_lock lock{mutex};
        BbIdleWait::IdleUnlessStuck(cv, lock, [&] { return idle.load(); },
                                    [&] { return flicker.load(); });
        lock.unlock();
        assert(done.load()); // it waited for idle, not for the first wait on memory
        assert(std::chrono::steady_clock::now() - start >= std::chrono::milliseconds{280});
        gpu.join();
    }
    // Stuck, but not for StuckMs yet: still waiting. Stuck that long: it goes on.
    {
        std::atomic<bool> idle{false};
        const auto start = std::chrono::steady_clock::now();
        std::unique_lock lock{mutex};
        BbIdleWait::IdleUnlessStuck(cv, lock, [&] { return idle.load(); }, [] { return true; },
                                    std::chrono::milliseconds{60});
        lock.unlock();
        assert(std::chrono::steady_clock::now() - start >= std::chrono::milliseconds{60});
    }
    std::puts("idle wait: ok");
    return 0;
}
