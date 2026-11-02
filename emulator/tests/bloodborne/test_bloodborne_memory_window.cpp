// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <gtest/gtest.h>

#include "core/bloodborne_memory_window.h"

using Core::Bloodborne::MemoryWindows;

namespace {
constexpr u32 Read = 1;
constexpr u32 Write = 2;
constexpr u32 ReadWrite = 3;
constexpr u64 Start = 0x2'0000'0000;
constexpr u64 End = 0x2'0010'0000;
} // namespace

TEST(MemoryWindows, ARegionSeenThisGenerationCoversItsInsideOnly) {
    MemoryWindows windows;
    EXPECT_FALSE(windows.Covers(2, Start, 8, Read));
    windows.Note(2, Start, End, ReadWrite);
    EXPECT_TRUE(windows.Covers(2, Start, 8, Read));
    EXPECT_TRUE(windows.Covers(2, End - 8, 8, Read));
    EXPECT_TRUE(windows.Covers(2, Start, End - Start, ReadWrite));
    EXPECT_FALSE(windows.Covers(2, Start - 8, 8, Read));
    EXPECT_FALSE(windows.Covers(2, End - 4, 8, Read)) << "past the end";
    EXPECT_FALSE(windows.Covers(2, End, 8, Read));
}

TEST(MemoryWindows, AChangedTableForgetsEveryRegion) {
    MemoryWindows windows;
    windows.Note(2, Start, End, Read);
    EXPECT_FALSE(windows.Covers(4, Start, 8, Read));
}

TEST(MemoryWindows, NothingIsTrustedWhileTheTableChanges) {
    MemoryWindows windows;
    windows.Note(3, Start, End, Read);
    EXPECT_FALSE(windows.Covers(3, Start, 8, Read));
    windows.Note(2, Start, End, Read);
    EXPECT_FALSE(windows.Covers(3, Start, 8, Read));
}

TEST(MemoryWindows, TheAskedProtectionMustBeThere) {
    MemoryWindows windows;
    windows.Note(2, Start, End, Read);
    EXPECT_TRUE(windows.Covers(2, Start, 8, Read));
    EXPECT_FALSE(windows.Covers(2, Start, 8, Write));
    EXPECT_FALSE(windows.Covers(2, Start, 8, ReadWrite));
}

TEST(MemoryWindows, ASizeOfNothingOrPastTheAddressSpaceIsNoAccess) {
    MemoryWindows windows;
    windows.Note(2, 0, ~u64{0}, Read);
    EXPECT_FALSE(windows.Covers(2, Start, 0, Read));
    EXPECT_FALSE(windows.Covers(2, ~u64{0} - 3, 8, Read));
}

TEST(MemoryWindows, TheOldestRegionMakesWayForANewOne) {
    MemoryWindows windows;
    for (u64 index = 0; index < 9; ++index) {
        windows.Note(2, Start + index * 0x1000, Start + (index + 1) * 0x1000, Read);
    }
    EXPECT_FALSE(windows.Covers(2, Start, 8, Read));
    EXPECT_TRUE(windows.Covers(2, Start + 0x1000, 8, Read));
    EXPECT_TRUE(windows.Covers(2, Start + 8 * 0x1000, 8, Read));
}
