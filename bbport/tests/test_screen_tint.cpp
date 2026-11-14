// SPDX-License-Identifier: GPL-2.0-or-later
// The screen tint check (shim/bbport_screen_tint.h). Reports of 2026-11-11/12: after a lamp
// travel the whole picture turned purple (ivan, 1.5.0: red ~254 and blue ~244 on every pixel,
// green still carrying the scene, 20..140) or red (1.4.0), until a restart. The check samples a
// few rows of the presented frame some seconds after each area load and logs one warning line.
//   ninja -C out/gpu screen-tint-test && out/gpu/screen-tint-test.exe
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
#include "bbport_screen_tint.h"

using namespace BbScreenTint;

namespace {

/// A frame of `count` RGBA8 pixels: channel c is `fixed[c]` when >= 0, else follows a scene
/// value going from `low` to `high` (a gradient with some texture).
std::vector<std::uint8_t> Frame(int count, int r, int g, int b, int low = 15, int high = 150) {
    std::vector<std::uint8_t> pixels(std::size_t(count) * 4);
    for (int i = 0; i < count; ++i) {
        const int scene = low + (i * 37 % count) * (high - low) / count;
        const int fixed[3] = {r, g, b};
        for (int c = 0; c < 3; ++c) {
            pixels[std::size_t(i) * 4 + c] = std::uint8_t(fixed[c] >= 0 ? fixed[c] : scene);
        }
        pixels[std::size_t(i) * 4 + 3] = 255;
    }
    return pixels;
}

Verdict JudgeFrame(const std::vector<std::uint8_t>& pixels, bool bgra = false) {
    Stats stats;
    stats.Add(pixels.data(), pixels.size() / 4, bgra);
    return Judge(stats);
}

} // namespace

int main() {
    // ivan's purple frame: red and blue at full, green follows the scene.
    {
        const auto v = JudgeFrame(Frame(4000, 254, -1, 244));
        assert(v.tinted);
        assert(v.full_mask == (ChannelR | ChannelB));
        assert(v.follow_mask == ChannelG);
        assert(v.means[0] > 250 && v.means[2] > 240 && v.means[1] < 100);
    }
    // The 1.4.0 red screen: red alone at full.
    {
        const auto v = JudgeFrame(Frame(4000, 255, -1, -1));
        assert(v.tinted && v.full_mask == ChannelR);
        assert(v.follow_mask == (ChannelG | ChannelB));
    }
    // The same frame as BGRA (the swapchain's usual format): the channels are named right.
    {
        auto pixels = Frame(4000, 254, -1, 244);
        for (std::size_t i = 0; i < pixels.size(); i += 4) std::swap(pixels[i], pixels[i + 2]);
        const auto v = JudgeFrame(pixels, true);
        assert(v.tinted && v.full_mask == (ChannelR | ChannelB));
    }
    // Not a tint: an ordinary scene, a white-out (all three at full), black (loading), a grey
    // flat fill (nothing follows a scene), a scene that is merely reddish.
    assert(!JudgeFrame(Frame(4000, -1, -1, -1)).tinted);
    assert(!JudgeFrame(Frame(4000, 255, 255, 255)).tinted);
    assert(!JudgeFrame(Frame(4000, 0, 0, 0)).tinted);
    assert(!JudgeFrame(Frame(4000, 255, 30, 255)).tinted);
    assert(!JudgeFrame(Frame(4000, -1, -1, -1, 60, 200)).tinted);
    {
        // A red sky over a third of the picture is the game's, not a stuck channel.
        auto pixels = Frame(3000, -1, -1, -1);
        const auto sky = Frame(1500, 250, -1, -1, 10, 60);
        pixels.insert(pixels.end(), sky.begin(), sky.end());
        assert(!JudgeFrame(pixels).tinted);
    }
    // Too few samples: no verdict.
    assert(!JudgeFrame(Frame(10, 254, -1, 244)).tinted);

    // When to look: a few seconds after each area load, then every 30 s while the tint holds;
    // also once every 5 minutes (a lamp travel within the same area).
    {
        Schedule s;
        assert(!s.Due(0.0, 0));        // no area yet
        assert(!s.Due(1.0, 0x18010000)); // an area appears: a load
        assert(!s.Due(1.0 + FirstDelaySeconds - 0.1, 0x18010000));
        assert(s.Due(1.0 + FirstDelaySeconds, 0x18010000));
        assert(!s.Due(1.0 + FirstDelaySeconds + 0.1, 0x18010000)); // asked once, until the result
        assert(s.Result(false, 7.0) == Report::Quiet);
        assert(!s.Due(30.0, 0x18010000));
        assert(!s.Due(200.0, 0x18010000));
        assert(s.Due(7.0 + IdleSeconds, 0x18010000)); // the slow look
        assert(s.Result(true, 7.0 + IdleSeconds) == Report::Tinted);
        assert(!s.Due(7.0 + IdleSeconds + HoldSeconds - 1.0, 0x18010000));
        assert(s.Due(7.0 + IdleSeconds + HoldSeconds, 0x18010000)); // it holds: again in 30 s
        assert(s.Result(true, 7.0 + IdleSeconds + HoldSeconds) == Report::Tinted);
        assert(s.Due(400.0, 0x18010000));
        assert(s.Result(false, 400.0) == Report::Cleared); // once, when it goes
        // Another area: a load again.
        assert(!s.Due(401.0, 0x15000000));
        assert(s.Due(401.0 + FirstDelaySeconds, 0x15000000));
        assert(s.Result(false, 401.0 + FirstDelaySeconds) == Report::Quiet);
        // A load while a look is pending restarts its wait.
        assert(!s.Due(420.0, 0x18010000));
        assert(s.Due(420.0 + FirstDelaySeconds, 0x18010000));
        assert(!s.Due(421.0, 0x15000000));
        assert(!s.Due(421.0 + FirstDelaySeconds - 0.5, 0x15000000));
        assert(s.Due(421.0 + FirstDelaySeconds, 0x15000000));
        // A readback that never reports (a lost frame) does not stop the checks.
        assert(!s.Due(421.0 + FirstDelaySeconds + 1.0, 0x15000000));
        assert(s.Due(421.0 + FirstDelaySeconds + HoldSeconds + 1.0, 0x15000000));
    }

    // The log line: what is stuck, the means, the upscaler, HDR and the area; "cleared" once gone.
    {
        Stats stats;
        const auto purple = Frame(4000, 254, -1, 244);
        stats.Add(purple.data(), purple.size() / 4, false);
        const Verdict v = Judge(stats);
        const std::string line = Line(v, "DLSS", "HDR scene input", false, "m24_01_00_00");
        std::printf("%s\n", line.c_str());
        assert(line.rfind("Screen tint: ", 0) == 0);
        assert(line.find("red and blue at full") != std::string::npos);
        assert(line.find("green follows the scene") != std::string::npos);
        assert(line.find("DLSS") != std::string::npos);
        assert(line.find("HDR scene input") != std::string::npos);
        assert(line.find("HDR output off") != std::string::npos);
        assert(line.find("m24_01_00_00") != std::string::npos);
        const std::string gone = ClearedLine("m24_01_00_00");
        assert(gone.rfind("Screen tint: gone", 0) == 0);
    }
    // Rows to sample: spread over the picture, inside it, none twice.
    {
        const auto rows = SampleRows(1080);
        assert(rows.size() == RowCount);
        for (std::size_t i = 0; i < rows.size(); ++i) {
            assert(rows[i] < 1080);
            if (i) assert(rows[i] > rows[i - 1]);
        }
        assert(rows.front() < 100 && rows.back() > 980);
        assert(SampleRows(4).size() == 4);
    }
    std::printf("screen-tint-test: ok\n");
    return 0;
}
