// Low latency's bookkeeping (gpu/shim/bbport_latency_frames.h): the setting, which game frame a
// flip, a submission and a presentation belong to, the presentation IDs and the latency average.
// No game, Vulkan device or window.
//   ninja -C out/gpu latency-frames-test && out/gpu/latency-frames-test
#include <cassert>
#include <cmath>
#include <cstdio>
#include "bbport_latency_frames.h"

using namespace BbLatencyFrames;

int main() {
    // The setting: auto follows frame generation; boost only when asked for.
    assert(ActiveFor(SettingOff, true) == ActiveOff);
    assert(ActiveFor(SettingAuto, false) == ActiveOff);
    assert(ActiveFor(SettingAuto, true) == ActiveOn);
    assert(ActiveFor(SettingOn, false) == ActiveOn);
    assert(ActiveFor(SettingBoost, false) == ActiveBoost);
    assert(ActiveFor(42, true) == ActiveOff);
    assert(ParseSetting("off") == SettingOff);
    assert(ParseSetting("auto") == SettingAuto);
    assert(ParseSetting("on") == SettingOn);
    assert(ParseSetting("boost") == SettingBoost);
    assert(ParseSetting("3") == SettingBoost);
    assert(ParseSetting("0") == SettingOff);
    assert(ParseSetting("onn") == SettingAuto);
    assert(ParseSetting("") == SettingAuto);
    assert(ParseSetting(nullptr) == SettingAuto);
    assert(ParseSetting("9") == SettingAuto);
    assert(MinimumIntervalUs(0) == 0);
    assert(MinimumIntervalUs(60) == 16666);
    assert(MinimumIntervalUs(120) == 8333);

    // Presentation IDs: the generated frames first, the game's own last, strictly increasing.
    assert(PresentId(0, 0, true) == 0);
    assert(PresentId(1, 0, false) == 4);
    assert(PresentId(1, 2, false) == 6);
    assert(PresentId(1, 7, false) == 6); // never the game frame's
    assert(PresentId(1, 0, true) == 7);
    assert(PresentId(2, 0, false) == 8);
    {
        std::uint64_t last = 0;
        for (std::uint64_t frame = 1; frame < 50; ++frame) {
            for (std::uint32_t i = 0; i < 3; ++i) {
                assert(PresentId(frame, i, false) > last);
                last = PresentId(frame, i, false);
            }
            assert(PresentId(frame, 0, true) > last);
            last = PresentId(frame, 0, true);
        }
    }

    // A game frame: started, flipped, taken by the GPU thread in order.
    {
        Frames f;
        assert(f.Current() == 1);
        assert(!f.Begin()); // nothing flipped yet: no wait
        assert(f.Recording() == 1);
        assert(f.Submitted() == 1);
        assert(f.Recording() == 1);
        assert(f.Begin()); // frame 1 flipped: frame 2 starts, after the wait
        assert(f.Current() == 2);
        assert(f.Submitted() == 2);
        assert(f.Queued() == 2);
        assert(f.Take() == 1);
        assert(f.Recording() == 2);
        assert(f.Take() == 2);
        assert(f.Take() == 0); // none left
        assert(f.Recording() == 3);
        // A frame without a flip (a loading screen) does not wait and keeps its number.
        assert(f.Begin());
        assert(f.Current() == 3);
        assert(!f.Begin());
        assert(f.Current() == 3);
        // Two flips with no frame start between: the second is a frame of its own.
        assert(f.Submitted() == 3);
        assert(f.Submitted() == 4);
        assert(f.Take() == 3);
        assert(f.Take() == 4);
        assert(f.Begin());
        assert(f.Current() == 5);
    }
    // Flips nobody takes do not pile up.
    {
        Frames f;
        for (int i = 0; i < 100; ++i) {
            f.Submitted();
            f.Begin();
        }
        assert(f.Queued() == Frames::MaxQueued);
        assert(f.Take() == 100 - Frames::MaxQueued + 1);
    }

    // The latency average: game frames only, each once, from the start of the frame to the later
    // of its presentation and its GPU work.
    {
        LatencyAverage a;
        std::uint32_t frames = 99;
        assert(a.Take(&frames) == 0.0 && frames == 0);
        a.Add({PresentId(1, 0, true), 1000, 21000, 0});     // 20 ms
        a.Add({PresentId(1, 0, true), 1000, 21000, 0});     // repeated: skipped
        a.Add({PresentId(2, 0, false), 1000, 90000, 0});    // generated: skipped
        a.Add({PresentId(2, 0, true), 30000, 50000, 60000}); // GPU done later: 30 ms
        a.Add({PresentId(3, 0, true), 0, 50000, 0});        // no start: skipped
        a.Add({PresentId(4, 0, true), 90000, 80000, 0});    // ends before it starts: skipped
        a.Add({PresentId(5, 0, true), 1, 3000000, 0});      // seconds: skipped
        a.Add({PresentId(1, 0, true), 1000, 2000, 0});      // older than the last: skipped
        const double ms = a.Take(&frames);
        assert(frames == 2);
        assert(std::fabs(ms - 25.0) < 1e-9);
        assert(a.Take(&frames) == 0.0 && frames == 0);
        a.Add({PresentId(6, 0, true), 1000, 11000, 0});
        assert(std::fabs(a.Take() - 10.0) < 1e-9);
    }

    std::printf("latency frames: all tests passed\n");
    return 0;
}
