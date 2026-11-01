// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: waiting for the GPU to go idle before a compute submission, unless it cannot. A graphics
// stream waiting on a label only that compute packet writes never goes idle: the game sat in
// sceGnmDingDong and the command processor spun on WaitRegMem for ever, an endless loading screen
// (rig 2026-10-31, label 51 of 52). `stuck`: the graphics stream waits on memory.
#pragma once
#include <chrono>
#include <condition_variable>
#include <mutex>

namespace BbIdleWait {

template <typename Idle, typename Stuck>
void IdleUnlessStuck(std::condition_variable& cv, std::unique_lock<std::mutex>& lock, Idle idle,
                     Stuck stuck) {
    while (!idle()) {
        if (stuck()) {
            return;
        }
        cv.wait_for(lock, std::chrono::milliseconds{1});
    }
}

} // namespace BbIdleWait
