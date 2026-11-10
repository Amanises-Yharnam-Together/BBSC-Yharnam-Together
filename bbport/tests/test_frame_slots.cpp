// The frame limiter's slot rule (gpu/shim/bbport_frame_slots.h): two flips are never closer than
// a period minus 1/16, and on time the slots stay on their grid. No game, Vulkan device or window.
//   ninja -C out/gpu frame-slots-test && out/gpu/frame-slots-test.exe
#include <cassert>
#include <chrono>
#include <cstdio>
#include "bbport_frame_slots.h"

using namespace std::chrono;
using Clock = steady_clock;

int main() {
    const nanoseconds period{1000000000 / 120}; // 8.33 ms
    const Clock::time_point start{};

    // On time: the next slot is one period after this one (no drift from the wake-up delay).
    Clock::time_point slot = start;
    for (int i = 0; i < 1000; ++i) {
        const auto flipped = slot + microseconds(200); // woken a little late
        slot = BbFrameSlots::NextSlot(slot, flipped, period);
    }
    assert(slot == start + period * 1000);

    // A late frame (5 ms past its slot): the next one may not follow it closely.
    const auto late = start + milliseconds(5);
    const auto next = BbFrameSlots::NextSlot(start, late, period);
    assert(next - late >= period - period / 16);
    // Nor later than a period after the flip.
    assert(next - late <= period);

    // Very late (more than a period): one period minus the slack after the flip, not at once.
    const auto very_late = start + milliseconds(30);
    assert(BbFrameSlots::NextSlot(start, very_late, period) == very_late + period - period / 16);

    // Simulated: 1200 frames at a cap of 120, every 16th late by 4-12 ms: no interval between
    // flips shorter than the period minus 1/16.
    slot = start;
    Clock::time_point previous{};
    nanoseconds shortest = hours(1);
    for (int i = 0; i < 1200; ++i) {
        const auto flipped = slot + (i % 16 == 5 ? milliseconds(4 + i % 9) : microseconds(50));
        if (i > 0) {
            shortest = std::min(shortest, duration_cast<nanoseconds>(flipped - previous));
        }
        previous = flipped;
        slot = BbFrameSlots::NextSlot(slot, flipped, period);
    }
    std::printf("shortest interval %.2f ms\n", shortest.count() / 1e6);
    assert(shortest >= period - period / 16);

    // The game's own 60 FPS mode (co-op's): vblank 60 Hz, no frame limit. A model where every
    // frame is drawn only once the last one is flipped: on vblank ticks only, frames of 18 ms wait
    // for every second tick (30 FPS); with late flips (the pace is the vblank's rate) about 55.
    // (The real game keeps more than one frame in flight: on the rig it falls gradually instead.)
    const auto frames_per_second = [](milliseconds work, bool late_flips) {
        const nanoseconds vblank{1000000000 / 60};
        const unsigned pace = BbFrameSlots::FlipPace(0, 60, false, late_flips);
        const Clock::time_point begin{};
        Clock::time_point slot = begin, flipped = begin, last{};
        nanoseconds closest = hours(1);
        int flips = 0;
        while (flipped < begin + seconds(10)) {
            const auto queued = flipped + work;
            flipped = BbFrameSlots::FlipTime(queued, slot, pace != 0, begin, vblank);
            if (pace != 0) {
                slot = BbFrameSlots::NextSlot(slot, flipped, nanoseconds{1000000000 / pace});
            }
            if (flips++ > 0) {
                closest = std::min(closest, duration_cast<nanoseconds>(flipped - last));
            }
            last = flipped;
        }
        assert(closest >= vblank - vblank / 16 && "never above the mode's rate");
        return flips / 10.0;
    };
    assert(BbFrameSlots::FlipPace(0, 60, false, false) == 0);
    assert(BbFrameSlots::FlipPace(0, 60, false, true) == 60);
    assert(BbFrameSlots::FlipPace(0, 90, false, true) == 90);
    assert(BbFrameSlots::FlipPace(0, 480, true, true) == 0 && "unlocked: as before");
    assert(BbFrameSlots::FlipPace(120, 480, true, true) == 120);
    const double on_ticks = frames_per_second(milliseconds(18), false);
    const double with_late = frames_per_second(milliseconds(18), true);
    std::printf("18 ms frames at 60 Hz: %.1f FPS on ticks, %.1f FPS with late flips\n", on_ticks,
                with_late);
    assert(on_ticks > 29.5 && on_ticks < 30.5);
    assert(with_late > 54.0 && with_late < 56.5);
    // A PC that keeps up stays at 60, late flips or not; one far behind is not held back more.
    assert(frames_per_second(milliseconds(10), true) > 59.5);
    assert(frames_per_second(milliseconds(10), true) < 60.5);
    assert(frames_per_second(milliseconds(10), false) > 59.5);
    assert(frames_per_second(milliseconds(40), true) > 24.5);
    assert(frames_per_second(milliseconds(40), false) < 20.5);
    std::printf("frame slots: ok\n");
    return 0;
}
