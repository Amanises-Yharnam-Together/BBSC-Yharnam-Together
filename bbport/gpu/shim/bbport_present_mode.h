// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: which present mode the swapchain takes (Swapchain::FindPresentMode), apart so it can be
// tested without a GPU. AMD's Windows driver has no Mailbox: every AMD player fell back to FIFO
// (V-Sync), where a frame that misses the display's refresh waits for the next one. On a 60 Hz
// monitor that is 30 FPS as soon as a frame takes over 16.7 ms: "60 FPS alone, 30 the moment
// someone joins" (Discord 2026-10-26..11-06; the AMD player's log of 2026-10-27 has "Requested
// present mode Mailbox is not supported, falling back to Fifo" in all nine sessions). Mailbox
// asks for frames that never wait for the display, so its stand-ins are the modes that do not
// make a late frame wait: FIFO Relaxed (V-Sync while on time, a late frame at once), then
// Immediate. FIFO only when the player chose it or nothing else is there.
#pragma once

#include <algorithm>
#include <array>
#include <span>
#include <string_view>

namespace BbPresentMode {

/// VkPresentModeKHR's values.
enum Mode : int { Immediate = 0, Mailbox = 1, Fifo = 2, FifoRelaxed = 3 };

constexpr const char* Name(int mode) {
    switch (mode) {
    case Immediate:
        return "Immediate";
    case Mailbox:
        return "Mailbox";
    case Fifo:
        return "Fifo";
    case FifoRelaxed:
        return "FifoRelaxed";
    default:
        return "?";
    }
}

/// The mode a setting (BB_PRESENT_MODE, the launcher's Presentation row) names; -1 unknown.
constexpr int Requested(std::string_view setting) {
    for (const int mode : {Immediate, Mailbox, Fifo, FifoRelaxed}) {
        if (setting == Name(mode)) {
            return mode;
        }
    }
    return -1;
}

/// The mode to use for `requested` among those the surface has (`supported`, VkPresentModeKHR
/// values; FIFO is always there by the Vulkan spec): itself when there, else its stand-ins in
/// order.
inline int Choose(int requested, std::span<const int> supported) {
    const auto has = [&](int mode) {
        return std::ranges::find(supported, mode) != supported.end();
    };
    std::array<int, 4> order{};
    switch (requested) {
    case Fifo:
        order = {Fifo, FifoRelaxed, Mailbox, Immediate};
        break;
    case FifoRelaxed:
        order = {FifoRelaxed, Fifo, Mailbox, Immediate};
        break;
    case Immediate:
        order = {Immediate, FifoRelaxed, Mailbox, Fifo};
        break;
    default: // Mailbox
        order = {Mailbox, FifoRelaxed, Immediate, Fifo};
        break;
    }
    for (const int mode : order) {
        if (has(mode)) {
            return mode;
        }
    }
    return Fifo;
}

} // namespace BbPresentMode
