// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: low latency's bookkeeping (vk_low_latency.cpp), apart so it can be tested without a GPU:
//  - the setting (bbport.ini low_latency): off, auto (with frame generation), on, on with boost;
//  - which of the game's frames a flip, a GPU submission and a presentation belong to. NVIDIA
//    Reflex (VK_NV_low_latency2) marks each step of a frame with the ID its presentation carries
//    (VkPresentIdKHR), AMD Anti-Lag 2 (VK_AMD_anti_lag) with a frame index. The game makes frame N
//    (sceGnmSubmitDone starts it), hands its flip over (sceVideoOutSubmitFlip or the flip of
//    sceGnmSubmitAndFlipCommandBuffers), the GPU command thread prepares the flip (in order), the
//    swap thread presents it, after the frames frame generation made before it;
//  - the presentation IDs: strictly increasing on a swapchain, so a game frame N has four, the
//    generated frames before it first (4N, 4N+1, 4N+2) and its own last (4N+3);
//  - the latency NVIDIA's driver reports back (vkGetLatencyTimingsNV), averaged.
#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>

namespace BbLatencyFrames {

/// bbport.ini low_latency (BbSettings::low_latency).
enum Setting : int { SettingOff = 0, SettingAuto = 1, SettingOn = 2, SettingBoost = 3, SettingCount };
inline constexpr const char* SettingNames[] = {"off", "auto", "on", "boost"};

/// What runs: nothing, low latency, low latency with the GPU's clocks kept up (Reflex only).
enum Active : int { ActiveOff = 0, ActiveOn = 1, ActiveBoost = 2 };

/// Auto turns it on with frame generation (which holds every game frame back to make the ones
/// between: NVIDIA ships its frame generation with Reflex on for that reason).
inline Active ActiveFor(int setting, bool frame_generation) {
    switch (setting) {
    case SettingOn:
        return ActiveOn;
    case SettingBoost:
        return ActiveBoost;
    case SettingAuto:
        return frame_generation ? ActiveOn : ActiveOff;
    default:
        return ActiveOff;
    }
}

/// The ini's word (or a number 0..3); auto for anything else.
inline int ParseSetting(const char* value) {
    if (!value) {
        return SettingAuto;
    }
    for (int i = 0; i < SettingCount; ++i) {
        const char* name = SettingNames[i];
        const char* v = value;
        while (*name && *v == *name) {
            ++name;
            ++v;
        }
        if (!*name && !*v) {
            return i;
        }
    }
    if (value[0] >= '0' && value[0] < char('0' + SettingCount) && value[1] == 0) {
        return value[0] - '0';
    }
    return SettingAuto;
}

/// The shortest time between two game frames the driver lets through (the FPS limit), 0 none.
inline std::uint32_t MinimumIntervalUs(int fps_limit) {
    return fps_limit > 0 ? std::uint32_t(1000000 / fps_limit) : 0u;
}

inline constexpr std::uint64_t PresentsPerFrame = 4; // up to three generated, then the game's own

/// The presentation ID of game frame `frame`: its own (game) or the generated one `index` before
/// it. 0 (no frame) stays 0: presented without an ID.
inline std::uint64_t PresentId(std::uint64_t frame, std::uint32_t index, bool game) {
    if (frame == 0) {
        return 0;
    }
    return frame * PresentsPerFrame +
           (game ? PresentsPerFrame - 1 : std::min<std::uint64_t>(index, PresentsPerFrame - 2));
}

/// Which game frame each step works on. Not thread safe: the caller locks.
class Frames {
public:
    /// The game's thread: its frame went to the flip queue. Returns that frame.
    std::uint64_t Submitted() {
        if (submitted) {
            ++current; // a second flip with no frame start between: a frame of its own
        }
        submitted = true;
        flips.push_back(current);
        if (flips.size() > MaxQueued) {
            flips.pop_front(); // flips the GPU thread never takes (none expected)
        }
        return current;
    }

    /// The game's thread: it starts a frame. True when the one before was flipped: the moment
    /// for low latency's wait (a frame without a flip, as on loading screens, never waits).
    bool Begin() {
        if (!submitted) {
            return false;
        }
        submitted = false;
        ++current;
        return true;
    }

    /// The frame the game makes now.
    std::uint64_t Current() const {
        return current;
    }

    /// The GPU command thread: the frame of the flip it prepares now, 0 with none handed over.
    std::uint64_t Take() {
        if (flips.empty()) {
            return 0;
        }
        taken = flips.front();
        flips.pop_front();
        return taken;
    }

    /// The GPU command thread: the frame its submissions belong to now (the next flip's).
    std::uint64_t Recording() const {
        return flips.empty() ? taken + 1 : flips.front();
    }

    std::size_t Queued() const {
        return flips.size();
    }

    static constexpr std::size_t MaxQueued = 16;

private:
    std::uint64_t current = 1;
    std::uint64_t taken = 0;
    bool submitted = false;
    std::deque<std::uint64_t> flips;
};

/// One frame's times from the driver (VkLatencyTimingsFrameReportNV, microseconds).
struct Report {
    std::uint64_t present_id;
    std::uint64_t sim_start;
    std::uint64_t present_end;
    std::uint64_t gpu_render_end;
};

/// The game frames' latency: from the start of the game's frame to the later of its presentation
/// and the end of its GPU work. Reports already counted (the driver repeats its last frames)
/// and generated frames are skipped.
class LatencyAverage {
public:
    void Add(const Report& r) {
        if (r.present_id == 0 || r.present_id % PresentsPerFrame != PresentsPerFrame - 1 ||
            r.present_id <= last_id || r.sim_start == 0 || r.present_end == 0) {
            return;
        }
        const std::uint64_t end = std::max(r.present_end, r.gpu_render_end);
        if (end <= r.sim_start || end - r.sim_start > 1000000) {
            return; // out of order or a second and more: not a frame's latency
        }
        last_id = r.present_id;
        total_us += double(end - r.sim_start);
        ++count;
    }

    /// The average in milliseconds since the last Take (0 with no frame), and starts again.
    double Take(std::uint32_t* frames = nullptr) {
        const double ms = count ? total_us / double(count) / 1000.0 : 0.0;
        if (frames) {
            *frames = count;
        }
        total_us = 0.0;
        count = 0;
        return ms;
    }

private:
    std::uint64_t last_id = 0;
    double total_us = 0.0;
    std::uint32_t count = 0;
};

} // namespace BbLatencyFrames
