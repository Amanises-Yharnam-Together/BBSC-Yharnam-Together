// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: a shader table walker's roots (flatten_extended_userdata_pass.cpp), checked before the
// walk. A root is a pointer in the draw's user data (two dwords, the walker masks it to 48 bits);
// one that is null or points into the first 64 KiB (Info::UdPointerNull) has no tables behind it.
// Walking it anyway made every load under it a fault through the vectored handler
// (bbport_srt_fault.h): tens of thousands a second when the game draws with null tables.
// Pure: no Vulkan, no game; tests/test_srt_null_root.cpp.
#pragma once

#include <cstdint>
#include <cstring>

namespace BbSrtRoots {

constexpr uint32_t MaxRoots = 8;
constexpr uint32_t UserDataRegs = 16;

/// The user data registers the walker loads its roots from, in order (sgpr = byte offset / 4).
/// `known` false: the walker was not followed (the walk goes as before).
struct Roots {
    uint8_t sgpr[MaxRoots];
    uint8_t count;
    bool known;
};

enum class Walk {
    Tables,   ///< no root null: walk the draw's user data
    SomeNull, ///< walk `walk_ud`: each null root points at zeros there
    AllNull,  ///< no walk: the walker's words are zeros (ZeroWalkerWords)
};

/// Zeros the tables of a null root read: big enough for any table offset a walker reads at
/// (immediate offsets from the shader's loads), never written (zero-filled pages of the image's
/// uninitialized data: no file size, no memory until read).
constexpr uint64_t ZeroTablesSize = 1ull << 20;
inline const void* ZeroTables() {
    alignas(4096) static uint8_t zeros[ZeroTablesSize];
    return zeros;
}

inline bool PointerNull(uint64_t pointer) {
    return (pointer & 0xFFFFFFFFFFFFull) < 0x10000;
}

/// The walk for this draw. `ud` holds `size` user data dwords (at most UserDataRegs are read);
/// `null_roots` counts the null ones. SomeNull: `walk_ud` is `ud` with each null root pointing at
/// ZeroTables(), so its tables read zeros as the faulting walk did, without the faults (a pointer
/// in a zero table is null again: such nested loads still fault, one each).
inline Walk Prepare(const Roots& roots, const uint32_t* ud, uint32_t size,
                    uint32_t (&walk_ud)[UserDataRegs], uint32_t& null_roots) {
    null_roots = 0;
    if (!roots.known || roots.count == 0) {
        return Walk::Tables;
    }
    const uint32_t n = size < UserDataRegs ? size : UserDataRegs;
    bool copied = false;
    for (uint32_t i = 0; i < roots.count && i < MaxRoots; ++i) {
        const uint32_t sgpr = roots.sgpr[i];
        if (sgpr + 2 > n) {
            return Walk::Tables; // not this draw's user data: the walk reads it as before
        }
        uint64_t pointer;
        std::memcpy(&pointer, ud + sgpr, sizeof(pointer));
        if (!PointerNull(pointer)) {
            continue;
        }
        if (!copied) {
            std::memset(walk_ud, 0, sizeof(walk_ud));
            std::memcpy(walk_ud, ud, n * sizeof(uint32_t));
            copied = true;
        }
        const uint64_t zeros = reinterpret_cast<uint64_t>(ZeroTables());
        std::memcpy(walk_ud + sgpr, &zeros, sizeof(zeros));
        ++null_roots;
    }
    if (null_roots == 0) {
        return Walk::Tables;
    }
    return null_roots == roots.count ? Walk::AllNull : Walk::SomeNull;
}

/// The words a walker writes (from `first`, the user data registers, to `end`) as zeros: what a
/// walk with every root null reads.
inline void ZeroWalkerWords(uint32_t* flat, uint32_t first, uint32_t end) {
    if (end > first) {
        std::memset(flat + first, 0, (end - first) * sizeof(uint32_t));
    }
}

} // namespace BbSrtRoots
