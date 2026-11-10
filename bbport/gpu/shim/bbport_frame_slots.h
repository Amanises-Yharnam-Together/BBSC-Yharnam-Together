// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: the frame limiter's slots (VideoOutDriver::PresentThread). The flip times are the frame
// times the game sees (flip status), and its movement slows down above ~120 FPS. Slots used to
// stay on a fixed grid that "never lags behind by more than a period": the frame after a late one
// was flipped early, so single intervals of 6 ms (165 FPS) passed at a cap of 120. The next slot
// is a period after the slot, but no earlier than a period minus 1/16 after the flip made:
// counting only from the flip added the wake-up delay to every frame (116 FPS at a cap of 120).
// From Supermedo's bbport (dd1686d2, d646b1dc).
#pragma once

#include <algorithm>
#include <chrono>

namespace BbFrameSlots {

/// The next flip slot after a flip at `flipped` in the slot `slot`.
template <typename TimePoint, typename Duration>
constexpr TimePoint NextSlot(TimePoint slot, TimePoint flipped, Duration period) {
    return std::max(slot + period, flipped + period - period / 16);
}

/// The rate the present thread paces its flips at, 0 none: the frame limit, else with the game's
/// own 30/60/90 modes (`uncapped_vblank` false) the vblank's rate, when `late_flips`. A frame
/// that is ready after its vblank tick is then shown at once, not on the next tick: an
/// overloaded PC in co-op's 60 FPS mode keeps a higher, steadier rate (rig slow-frames-60).
/// Flips still keep a period between them (NextSlot), so the game never runs above its mode's
/// rate.
constexpr unsigned FlipPace(unsigned frame_limit, unsigned vblank_hz, bool uncapped_vblank,
                            bool late_flips) {
    if (frame_limit != 0) {
        return frame_limit;
    }
    return !uncapped_vblank && late_flips ? vblank_hz : 0;
}

/// When a frame queued at `queued` is flipped: with a pace (`between_ticks`) at its slot or
/// when it comes, whichever is later; else on the first vblank tick (`first_tick` + n periods)
/// that is not before it.
template <typename TimePoint, typename Duration>
constexpr TimePoint FlipTime(TimePoint queued, TimePoint slot, bool between_ticks,
                             TimePoint first_tick, Duration vblank) {
    if (between_ticks) {
        return std::max(queued, slot);
    }
    if (queued <= first_tick) {
        return first_tick;
    }
    const auto ticks = (queued - first_tick + vblank - Duration{1}) / vblank;
    return first_tick + vblank * ticks;
}

} // namespace BbFrameSlots
