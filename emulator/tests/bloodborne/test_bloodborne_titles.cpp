// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Which game gets seamless co-op. It was the EU Game of the Year edition's id alone (CUSA03173),
// and every other release of the same 1.09 executable started without co-op's code while the
// launcher still gave it the party HUD: nothing stopped the HUD's new sprites, so they played
// through their frames ("test" names, three placeholder players, 99 vials flashing), Create a team
// stayed grey and the co-op menu could not be closed (about 13 players on Discord, 2026-10-25 to
// 2026-11-07, most on the US CUSA00900).
#include <string_view>
#include <gtest/gtest.h>

#include "core/bloodborne_titles.h"

using namespace Core::Bloodborne;

TEST(Titles, EveryRetailReleaseIsBloodborne) {
    // The 01.09 eboot's own content-id table (Japan, US, EU, Asia, each with its Game of the Year
    // edition): bbport/scripts/game_check.py SUPPORTED_TITLES, the launcher's TITLE_IDS.
    for (const std::string_view title :
         {"CUSA03173", "CUSA00207", "CUSA00208", "CUSA00900", "CUSA03179", "CUSA01363", "CUSA03023",
          "CUSA00299", "CUSA03014"}) {
        EXPECT_TRUE(IsBloodborneTitle(title)) << title;
    }
}

TEST(Titles, AnotherGameIsNot) {
    for (const std::string_view title :
         {"", "UNKNOWN", "CUSA00001", "CUSA0317", "CUSA031730", "cusa03173", "CUSA03173 "}) {
        EXPECT_FALSE(IsBloodborneTitle(title)) << '"' << title << '"';
    }
}

TEST(Titles, TheUsReleaseGetsSeamlessCoop) {
    // noodlenoodle3029, 2026-10-27: "Bloodborne CUSA00900, version 1.09 ... In-game HUD rapidly
    // flashes "test" and shows three placeholder players with 99 items."
    EXPECT_EQ(SeamlessCoopGameFor("CUSA00900", "01.09"), CoopGame::Yes);
    EXPECT_EQ(SeamlessCoopGameFor("CUSA03173", "01.09"), CoopGame::Yes);
}

TEST(Titles, AnOldParamSfoBesideThe109ExecutableStillGetsCoop) {
    // The launcher's game check goes by the executable (game_check.py SUPPORTED_IMAGE), so a game
    // folder with the 1.09 eboot.bin and the base game's sce_sys/param.sfo starts; co-op's own
    // site check (bloodborne_patch_sites.h) then decides by the code itself. (A few players had
    // the flashing HUD on CUSA03173 until a fresh dump; their logs never came, this is one way.)
    EXPECT_EQ(SeamlessCoopGameFor("CUSA03173", "01.00"), CoopGame::OtherVersion);
    EXPECT_EQ(SeamlessCoopGameFor("CUSA00900", "Unknown"), CoopGame::OtherVersion);
    EXPECT_TRUE(GetsSeamlessCoop(CoopGame::OtherVersion));
    EXPECT_TRUE(GetsSeamlessCoop(CoopGame::Yes));
}

TEST(Titles, AnotherGameGetsNone) {
    EXPECT_EQ(SeamlessCoopGameFor("CUSA00001", "01.09"), CoopGame::OtherGame);
    EXPECT_EQ(SeamlessCoopGameFor("", "01.09"), CoopGame::OtherGame);
    EXPECT_FALSE(GetsSeamlessCoop(CoopGame::OtherGame));
}
