// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: waiting for the GPU to go idle before a compute submission, unless it cannot. A graphics
// stream waiting on a label only that compute packet writes never goes idle: the game sat in
// sceGnmDingDong and the command processor spun on WaitRegMem for ever, an endless loading screen
// (rig 2026-10-31, label 51 of 52). `stuck`: the graphics stream waits on memory.
//
// Kaniel 2026-11-01 (local 1.3.2, RTX 4070 Ti): the graphics stream waits on memory for a moment
// in almost every frame, so going on at the first sight of a wait let nearly every compute
// submission run beside the graphics work it was meant to follow: the GPU was lost ("device lost
// during submit", a write to address 0) on the first load into the Dream. Only a wait that lasts
// StuckMs is the deadlock; a short one is waited out as before.
#pragma once
#include <chrono>
#include <condition_variable>
#include <mutex>

namespace BbIdleWait {

inline constexpr std::chrono::milliseconds StuckMs{250};

template <typename Idle, typename Stuck>
void IdleUnlessStuck(std::condition_variable& cv, std::unique_lock<std::mutex>& lock, Idle idle,
                     Stuck stuck, std::chrono::milliseconds stuck_for = StuckMs) {
    using Clock = std::chrono::steady_clock;
    bool waiting = false;
    Clock::time_point since{};
    while (!idle()) {
        if (stuck()) {
            const auto now = Clock::now();
            if (!waiting) {
                waiting = true;
                since = now;
            } else if (now - since >= stuck_for) {
                return;
            }
        } else {
            waiting = false;
        }
        cv.wait_for(lock, std::chrono::milliseconds{1});
    }
}

} // namespace BbIdleWait
