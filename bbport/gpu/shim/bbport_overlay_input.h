// SPDX-License-Identifier: GPL-2.0-or-later
// bbport co-op: which of our screens take the keys, pad and mouse from the game (bbport_overlay.cpp),
// apart from ImGui so a test can hold them together. Kaniel's players 2026-10-30 (day 4): "When in
// the travel together mode, the pop-up is not interactable": the team trip's question held the game's
// input, but its keys, buttons and clicks were never passed on to it, so nothing answered it.

#pragma once

namespace BbOverlayInput {

/// What is open over the game this frame.
struct Screens {
    bool menu = false;     // the Insert settings menu
    bool quit = false;     // the L3+R3 quit box
    bool prompt = false;   // the text entry (its typing comes as text input)
    bool team = false;     // the team screen
    bool joining = false;  // the team load's cover: nothing on it to press
    bool map = false;      // the map screen
    bool travel = false;   // the travel together question (TeamTravel::Asking)
};

/// The game gets no input (runtime_pad, the mouse camera).
inline bool HoldsGame(const Screens& s) {
    return s.menu || s.quit || s.prompt || s.team || s.joining || s.map || s.travel;
}

/// Key, pad button, mouse and stick events go to ImGui (the screens with something to choose).
inline bool TakesEvents(const Screens& s) {
    return s.menu || s.quit || s.team || s.map || s.travel;
}

/// The system's text input is on (SDL_StartTextInput): a text box has the focus (ImGui's
/// WantTextInput) on a screen that takes the events. Kaniel 2026-11-05: the team screen's search
/// boxes took no typing while this was the Insert menu's only.
inline bool WantsTextInput(const Screens& s, bool box_focused) {
    return box_focused && TakesEvents(s);
}

/// The system cursor shows over the game, fullscreen too: the screens chosen on with the mouse.
inline bool ShowsCursor(const Screens& s) {
    return s.menu || s.quit || s.team || s.travel;
}

} // namespace BbOverlayInput
