// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// bbport: the screen tint check. Reports of 2026-11-11/12: after a lamp travel the whole picture
// turned purple (ivan, 1.5.0, DLSS: red ~254 and blue ~244 on every pixel while green still
// carried the scene) or red (1.4.0), until a restart; the log said nothing. The presenter copies
// a few rows of the presented frame some seconds after each area load (and every 30 s while it
// holds, and every 5 minutes otherwise), and this decides whether one or two channels sit at full
// while another follows the scene, for one warning line with the upscaler, HDR and the area.
// Pure logic here (tests/test_screen_tint.cpp); the readback is vk_temporal_upscaler.cpp's.

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

namespace BbScreenTint {

enum Channel : std::uint8_t { ChannelR = 1, ChannelG = 2, ChannelB = 4 };

/// A channel value counted as "at full" (of 255) and the share of samples that must be there.
constexpr int FullValue = 235;
constexpr double FullShare = 0.9;
/// The spread (standard deviation, of 255) of a channel that follows the scene.
constexpr double FollowSpread = 8.0;
/// Fewer samples than this give no verdict.
constexpr std::size_t MinSamples = 256;
/// Rows of the frame copied for a look, and every how many pixels of a row are counted.
constexpr std::size_t RowCount = 16;
constexpr std::size_t PixelStep = 4;

/// When to look (seconds): after a load, again while tinted, otherwise now and then.
constexpr double FirstDelaySeconds = 5.0;
constexpr double HoldSeconds = 30.0;
constexpr double IdleSeconds = 300.0;

struct Stats {
    std::array<double, 3> sum{}, sum_sq{};
    std::array<std::size_t, 3> full{};
    std::size_t count = 0;

    /// `pixels`: `n` RGBA8 (or BGRA8) pixels.
    void Add(const std::uint8_t* pixels, std::size_t n, bool bgra, std::size_t step = 1) {
        for (std::size_t i = 0; i < n; i += step) {
            const std::uint8_t* p = pixels + i * 4;
            const int rgb[3] = {bgra ? p[2] : p[0], p[1], bgra ? p[0] : p[2]};
            for (int c = 0; c < 3; ++c) {
                sum[c] += rgb[c];
                sum_sq[c] += double(rgb[c]) * rgb[c];
                full[c] += rgb[c] >= FullValue ? 1u : 0u;
            }
            ++count;
        }
    }
};

struct Verdict {
    bool tinted = false;
    std::uint8_t full_mask = 0;   ///< channels at full on (almost) every sample
    std::uint8_t follow_mask = 0; ///< channels that vary with the scene
    std::array<double, 3> means{}, spreads{};
};

inline Verdict Judge(const Stats& stats) {
    Verdict v;
    if (stats.count < MinSamples) {
        return v;
    }
    const double n = double(stats.count);
    for (int c = 0; c < 3; ++c) {
        v.means[c] = stats.sum[c] / n;
        v.spreads[c] = std::sqrt(std::max(0.0, stats.sum_sq[c] / n - v.means[c] * v.means[c]));
        if (double(stats.full[c]) >= FullShare * n) {
            v.full_mask |= std::uint8_t(1u << c);
        } else if (v.spreads[c] >= FollowSpread) {
            v.follow_mask |= std::uint8_t(1u << c);
        }
    }
    const int stuck = (v.full_mask & 1) + ((v.full_mask >> 1) & 1) + ((v.full_mask >> 2) & 1);
    v.tinted = stuck >= 1 && stuck <= 2 && v.follow_mask != 0;
    return v;
}

enum class Report { Quiet, Tinted, Cleared };

class Schedule {
public:
    /// Whether to copy this frame's rows now; `map` is the area (0: none yet). A changed area
    /// counts as a load. Once true, false again until Result (or HoldSeconds without one).
    bool Due(double now, std::uint32_t map) {
        if (map == 0) {
            return false;
        }
        if (map != last_map) {
            last_map = map;
            pending = false;
            next = now + FirstDelaySeconds;
            return false;
        }
        if (pending) {
            if (now - pending_since <= HoldSeconds) {
                return false;
            }
            pending = false; // the readback never came back
            next = now;
        }
        if (now < next) {
            return false;
        }
        pending = true;
        pending_since = now;
        return true;
    }

    /// The look's result: whether to log the tint (every look while it holds) or its end (once).
    Report Result(bool tinted, double now) {
        pending = false;
        next = now + (tinted ? HoldSeconds : IdleSeconds);
        const bool was = tinted_last;
        tinted_last = tinted;
        return tinted ? Report::Tinted : was ? Report::Cleared : Report::Quiet;
    }

private:
    std::uint32_t last_map = 0;
    double next = 0.0, pending_since = 0.0;
    bool pending = false, tinted_last = false;
};

inline std::string ChannelNames(std::uint8_t mask) {
    static const char* names[3] = {"red", "green", "blue"};
    std::string out;
    int seen = 0, total = (mask & 1) + ((mask >> 1) & 1) + ((mask >> 2) & 1);
    for (int c = 0; c < 3; ++c) {
        if (!(mask & (1u << c))) continue;
        if (seen) out += seen + 1 == total ? " and " : ", ";
        out += names[c];
        ++seen;
    }
    return out;
}

/// "Screen tint: red and blue at full, green follows the scene (means R 254 G 82 B 244) ...".
inline std::string Line(const Verdict& v, const char* upscaler, const char* scene_input, bool hdr_output,
                        const std::string& area) {
    const std::string follows = ChannelNames(v.follow_mask);
    char text[512];
    std::snprintf(text, sizeof(text),
                  "Screen tint: %s at full, %s %s the scene (means R %.0f G %.0f B %.0f, spread "
                  "%.0f %.0f %.0f); upscaler %s, %s, HDR output %s, area %s",
                  ChannelNames(v.full_mask).c_str(), follows.c_str(),
                  v.follow_mask == ChannelR || v.follow_mask == ChannelG || v.follow_mask == ChannelB
                      ? "follows" : "follow",
                  v.means[0], v.means[1], v.means[2], v.spreads[0], v.spreads[1], v.spreads[2],
                  upscaler, scene_input, hdr_output ? "on" : "off", area.c_str());
    return text;
}

inline std::string ClearedLine(const std::string& area) {
    return "Screen tint: gone (area " + area + ")";
}

/// The rows a look copies: RowCount of them, evenly spread (fewer on a tiny frame).
inline std::vector<std::uint32_t> SampleRows(std::uint32_t height) {
    std::vector<std::uint32_t> rows;
    const std::size_t n = std::min<std::size_t>(RowCount, height);
    for (std::size_t i = 0; i < n; ++i) {
        rows.push_back(std::uint32_t((2 * i + 1) * height / (2 * n)));
    }
    return rows;
}

} // namespace BbScreenTint
