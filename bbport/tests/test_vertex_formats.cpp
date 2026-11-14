// SPDX-License-Identifier: GPL-2.0-or-later
// Vertex stream formats the renderer must take without stopping the game
// (video_core/renderer_vulkan/liverpool_to_vk.h). A player's RX 580 (AMD's Windows driver, no
// VK_EXT_vertex_input_dynamic_state, 2026-10-23) stopped at "Begin the hunt" on
// "Unknown data_format=15 and num_format=7": without dynamic vertex input the pipeline key takes
// the formats of the V#s as they are in guest memory, and 15 is a value the hardware reserves.
#include <cstdio>
// The recompiler's headers (info.h, regs_shader.h) are not -Wall -Wextra clean; this test is.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused-variable"
#pragma clang diagnostic ignored "-Wunused-parameter"
#pragma clang diagnostic ignored "-Wreorder-ctor"
#include "shader_recompiler/frontend/fetch_shader.h"
#pragma clang diagnostic pop
#include "video_core/renderer_vulkan/liverpool_to_vk.h"

static int failures;
#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, #condition);     \
            ++failures;                                                                            \
        }                                                                                          \
    } while (false)

int main() {
    using namespace AmdGpu;
    using namespace Vulkan::LiverpoolToVK;
    const auto reserved = static_cast<DataFormat>(15);

    // The pair from the player's log names no format: the draw is skipped, not the game stopped.
    CHECK(!IsKnownSurfaceFormat(reserved, NumberFormat::Float));
    CHECK(!IsKnownSurfaceFormat(static_cast<DataFormat>(63), NumberFormat::Uint));

    // Known stream formats are unchanged.
    CHECK(IsKnownSurfaceFormat(DataFormat::Format32_32_32, NumberFormat::Float));
    CHECK(IsKnownSurfaceFormat(DataFormat::Format8_8_8_8, NumberFormat::Unorm));
    // An invalid (unused) V# keeps meaning "no format", as SurfaceFormat always allowed.
    CHECK(IsKnownSurfaceFormat(DataFormat::FormatInvalid, NumberFormat::Float));

    // A stream the pipeline is built with must have a format the driver takes: an unknown one
    // falls back to a format every driver supports for vertex buffers.
    CHECK(VertexInputFormat(reserved, NumberFormat::Float) == vk::Format::eR32G32B32A32Sfloat);
    CHECK(VertexInputFormat(DataFormat::Format32_32_32, NumberFormat::Float) ==
          vk::Format::eR32G32B32Sfloat);
    CHECK(VertexInputFormat(DataFormat::Format16_16, NumberFormat::Float) ==
          vk::Format::eR16G16Sfloat);
    CHECK(VertexInputFormat(DataFormat::FormatInvalid, NumberFormat::Float) ==
          vk::Format::eUndefined);

    // A V# without records (a zeroed one: data format 0, number format 0) is a float4 that reads
    // zero from no buffer, never a VK_FORMAT_UNDEFINED attribute: an NVIDIA driver lost the
    // device ("WriteInvalid 0") on the first submit after a draw with one (PR #543).
    {
        using namespace Shader::Gcn;
        const Buffer zeroed{};
        CHECK(IsNullVertexInput(zeroed, true));
        const auto input = GetVertexInputFormat(zeroed, true);
        CHECK(input.data_format == DataFormat::Format32_32_32_32);
        CHECK(input.num_format == NumberFormat::Float);
        CHECK(input.stride == 0);
        CHECK(Vulkan::LiverpoolToVK::VertexInputFormat(input.data_format, input.num_format) ==
              vk::Format::eR32G32B32A32Sfloat);
        CHECK(TrySurfaceFormat(input.data_format, input.num_format) ==
              vk::Format::eR32G32B32A32Sfloat);

        // A V# with no records but leftover fields still reads zero (every fetch is out of range).
        Buffer leftover{};
        leftover.base_address = 0x1000;
        leftover.stride = 12;
        leftover.data_format = static_cast<u32>(DataFormat::Format32_32_32);
        leftover.num_format = static_cast<u32>(NumberFormat::Float);
        CHECK(IsNullVertexInput(leftover, true));
        CHECK(GetVertexInputFormat(leftover, true).stride == 0);

        // A V# with records keeps its own format and stride.
        Buffer stream = leftover;
        stream.num_records = 64;
        CHECK(!IsNullVertexInput(stream, true));
        const auto own = GetVertexInputFormat(stream, IsNullVertexInput(stream, true));
        CHECK(own.data_format == DataFormat::Format32_32_32);
        CHECK(own.num_format == NumberFormat::Float);
        CHECK(own.stride == 12);

        // BB_NULL_VERTEX_INPUT=0 describes a zeroed V# from its own fields, as before.
        CHECK(!IsNullVertexInput(zeroed, false));
        CHECK(GetVertexInputFormat(zeroed, false).data_format == DataFormat::FormatInvalid);
    }

    if (failures != 0) {
        std::fprintf(stderr, "vertex formats: %d check(s) failed\n", failures);
        return 1;
    }
    std::puts("vertex formats: ok");
    return 0;
}
