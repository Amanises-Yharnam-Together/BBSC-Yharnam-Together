// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: the port's settings as pages of the game's own System menu ("Display", "Game effects",
// "Game patches" after "Screen/Sound"), built and drawn by the game's menu code: rows are the
// game's list, toggle and slider rows, texts come from a hook on its message lookup, the values live
// in the port and are applied as the player changes them. BB_GAME_MENU=0 leaves the menu as it is.
#pragma once

#include <cstdint>
#include <string>

namespace BbGameMenu {
/// Installs the hooks (the loader calls it once, before any game code runs, while the image is
/// still writable). Each hooked function is checked byte for byte against the 1.09 eboot.
void PatchImage(unsigned char* image, std::uint64_t size);

/// Applies what the player changed on the port's pages (each presented frame).
void Poll();

// For the port's other game menus (bbport_trade_menu.cpp), on the game's thread.
std::uint64_t ImageBase();
/// A text the game looks up like its own messages (any category), both languages; before the game
/// runs (PatchImage).
std::uint32_t AddGameText(const char* english, const char* russian);
/// Slot `slot` (0-7) now says `utf8`: its message id.
std::uint32_t SetDynamicText(int slot, const char* utf8);
/// Players' reports (Discord, 1.0.0 to 1.3.x): with the co-op server out of reach the game said
/// "not signed in to PlayStation Network". Why the sign-in to the co-op server failed, in words
/// (bbcoop_sign_in_problem), in the menus' language or the game's own: what happened, with the
/// server's address, and what to check. False while there is nothing to say.
struct SignInWords {
    std::string what;  ///< "Can't reach the co-op server at 26.1.2.3:31313"
    std::string check; ///< "The server may not be started, ..."
};
bool SignInNotice(SignInWords& words, bool game_language);
/// Frees a text entry (0x40 bytes, MakeText's) and a std::function (0x28 bytes) as the game does.
void DestroyGameText(unsigned char* text);
void DestroyGameFunction(unsigned char* function);
} // namespace BbGameMenu
