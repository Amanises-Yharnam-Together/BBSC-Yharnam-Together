// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Players' reports (Discord, 1.0.0 to 1.3.x): with the co-op server out of reach the game said
// "not signed in to PlayStation Network". The reason the sign-in failed is kept for the screens
// (core/bloodborne_sign_in.h), which say it in place of that text.
#include <gtest/gtest.h>

#include "core/bloodborne_sign_in.h"

using namespace Core::Bloodborne;

TEST(SignIn, TheServerAddressAsThePlayerSetIt) {
    EXPECT_EQ(SignInServerText("26.1.2.3", 31313), "26.1.2.3:31313");
    EXPECT_EQ(SignInServerText("seamlesshunt.com", 0), "seamlesshunt.com");
    EXPECT_EQ(SignInServerText("", 31313), "");
}

TEST(SignIn, AFailedSignInIsKeptUntilOneWorks) {
    SignInNotes notes;
    EXPECT_EQ(notes.Last().problem, SignInProblem::None);
    EXPECT_EQ(notes.Last().server, "");

    notes.Failed(SignInProblem::NoAnswer, "26.1.2.3", 31313);
    EXPECT_EQ(notes.Last().problem, SignInProblem::NoAnswer);
    EXPECT_EQ(notes.Last().server, "26.1.2.3:31313");

    notes.Failed(SignInProblem::WrongLogin, "seamlesshunt.com", 31313);
    EXPECT_EQ(notes.Last().problem, SignInProblem::WrongLogin);
    EXPECT_EQ(notes.Last().server, "seamlesshunt.com:31313");

    notes.SignedIn();
    EXPECT_EQ(notes.Last().problem, SignInProblem::None);
    EXPECT_EQ(notes.Last().server, "");
}

TEST(SignIn, TheServersOwnRefusalComesBeforeTheFailureItCaused) {
    // A link the server refused (another release) never answers the sign-in.
    constexpr std::string_view another_build =
        "another build: everyone needs the same release (this game runs 1.3.2)";
    EXPECT_EQ(ShownSignInProblem(SignInProblem::NoAnswer, another_build), SignInProblem::Refused);
    EXPECT_EQ(ShownSignInProblem(SignInProblem::Other, another_build), SignInProblem::Refused);
    EXPECT_EQ(ShownSignInProblem(SignInProblem::NoAnswer, ""), SignInProblem::NoAnswer);
    EXPECT_EQ(ShownSignInProblem(SignInProblem::WrongLogin, ""), SignInProblem::WrongLogin);
    // Signed in (or offline by choice): nothing to say, whatever the link last heard.
    EXPECT_EQ(ShownSignInProblem(SignInProblem::None, ""), SignInProblem::None);
    EXPECT_EQ(ShownSignInProblem(SignInProblem::None, another_build), SignInProblem::None);
}

TEST(SignIn, TheServerRefusingTheAccountIsAWrongLogin) {
    // The rig, 2026-11-10: a wrong password on a local server is refused on the link ("another
    // player has this id"), and the screens told the player to update the game.
    EXPECT_EQ(ShownSignInProblem(SignInProblem::NoAnswer,
                                 "sign-in refused: another player has this id (rig_host)"),
              SignInProblem::WrongLogin);
    EXPECT_EQ(ShownSignInProblem(SignInProblem::NoAnswer, "account: sign in in the launcher first"),
              SignInProblem::WrongLogin);
    EXPECT_EQ(ShownSignInProblem(SignInProblem::NoAnswer,
                                 "the region's directory does not answer: try again in a minute"),
              SignInProblem::Refused);
}

TEST(SignIn, TheGamesPlayStationNetworkTextsAreTheOnesReplaced) {
    // The game's own "not signed in to PlayStation Network" texts (found in the 1.09 message
    // files): at least one is known, and no other text is touched.
    ASSERT_FALSE(PsnSignInTexts.empty());
    for (const auto& [category, id] : PsnSignInTexts) {
        EXPECT_TRUE(IsPsnSignInText(category, id));
        EXPECT_FALSE(IsPsnSignInText(category + 1, id));
    }
    EXPECT_FALSE(IsPsnSignInText(0, 0));
    // "Lost connection to the network. Returning to title menu." stays the game's.
    EXPECT_FALSE(IsPsnSignInText(204, 4701));
}
