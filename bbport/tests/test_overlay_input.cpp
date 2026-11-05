// SPDX-License-Identifier: GPL-2.0-or-later
// bbport co-op: our screens that hold the game's input take it themselves (bbport_overlay_input.h).
// Kaniel's players 2026-10-30: the travel together question could not be answered.
#include <cassert>
#include <cstdio>
#include <initializer_list>
#include "gpu/shim/bbport_overlay_input.h"

using namespace BbOverlayInput;

namespace {

void TravelQuestionTakesItsAnswer() {
    const Screens travel{.travel = true};
    assert(HoldsGame(travel));
    assert(TakesEvents(travel)); // Cross / Enter / the d-pad / a click reach its buttons
    assert(ShowsCursor(travel)); // its buttons take the mouse, fullscreen too
}

void ScreensWithButtonsTakeEvents() {
    // Every screen with something to choose that holds the game's input gets the events too, or
    // the player is stuck on it.
    for (const Screens s : {Screens{.menu = true}, Screens{.quit = true}, Screens{.team = true},
                            Screens{.map = true}, Screens{.travel = true}}) {
        assert(HoldsGame(s));
        assert(TakesEvents(s));
    }
}

void LoadCoverHoldsTheGameOnly() {
    const Screens joining{.joining = true};
    assert(HoldsGame(joining));
    assert(!TakesEvents(joining));
    assert(!ShowsCursor(joining));
}

void NothingOpenLeavesTheGame() {
    assert(!HoldsGame({}));
    assert(!TakesEvents({}));
    assert(!ShowsCursor({}));
}

// Kaniel 2026-11-05: the team screen's search boxes ("Search hunters online", the friends page's)
// took no typing: the system's text input came on for the Insert menu only, so no characters
// reached them. It comes on whenever a screen that takes the events has a text box focused.
void TextBoxesTakeTypingOnEveryScreenThatTakesEvents() {
    for (const Screens s : {Screens{.menu = true}, Screens{.quit = true}, Screens{.team = true},
                            Screens{.map = true}, Screens{.travel = true}}) {
        assert(WantsTextInput(s, true));
        assert(!WantsTextInput(s, false)); // no box focused: no text input (no IME over the game)
    }
    assert(!WantsTextInput(Screens{.joining = true}, true));
    assert(!WantsTextInput({}, true)); // the game's own (the prompt types through its own path)
}

} // namespace

int main() {
    TravelQuestionTakesItsAnswer();
    ScreensWithButtonsTakeEvents();
    LoadCoverHoldsTheGameOnly();
    NothingOpenLeavesTheGame();
    TextBoxesTakeTypingOnEveryScreenThatTakesEvents();
    std::printf("overlay-input-test: ok\n");
    return 0;
}
