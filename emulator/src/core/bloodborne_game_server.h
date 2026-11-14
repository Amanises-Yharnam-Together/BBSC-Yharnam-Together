// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <mutex>
#include <string>
#include <string_view>
#include <utility>

#include "common/types.h"

namespace Core::Bloodborne {

// Discord audit A1 (bugs 3 and 22, 1.0.0-1.4.0): a teammate one side never sees, whose hits do
// not kill and whom the enemies leave be. In Ozi's logs of 2026-11-01 that player's game never
// signed in to the game's own server (ss4.scej-network.jp:20443, the host override's backend):
// no ss.info, no /basic_utils/login, its save loaded at once, while its server link (shadNet,
// 31314) worked and it joined the host's session. Every healthy game signs in first (the rig's,
// and all six of Ozi's host logs). The other games made its character but never got its state
// (hp 1/1), and it kept leaving the session. Nothing told the player. This is what the game did
// with its server, so the team screen can say so.
enum class GameServerSignIn : u8 {
    NotTried, // no request to the game server yet
    Trying,   // asked (ss.info), not signed in yet
    SignedIn, // /basic_utils/login answered
    Failed,   // a request failed before the sign-in (no answer, refused, an error status)
};

constexpr std::string_view GameServerSignInName(GameServerSignIn state) {
    switch (state) {
    case GameServerSignIn::NotTried:
        return "not tried";
    case GameServerSignIn::Trying:
        return "under way";
    case GameServerSignIn::SignedIn:
        return "done";
    case GameServerSignIn::Failed:
        return "failed";
    }
    return "?";
}

constexpr std::string_view GameServerHost = "ss4.scej-network.jp:20443";
constexpr std::string_view GameServerLoginPath = "/basic_utils/login";

// Whether a URL the game asked for is its own server's (before the host override).
constexpr bool IsGameServerUrl(std::string_view url) {
    return url.find(GameServerHost) != std::string_view::npos;
}

// Whether a request belongs to the game's sign-in: its own server's, or the sign-in itself
// (/basic_utils/login), which goes to the address ss.info hands back (the team's server, any
// host and port), not to ss4.scej-network.jp:20443.
constexpr bool IsGameServerRequest(std::string_view url) {
    return IsGameServerUrl(url) || url.find(GameServerLoginPath) != std::string_view::npos;
}

class GameServerSignInLog {
public:
    // A request the game sent to its server.
    void Asked() {
        std::scoped_lock lock{mutex};
        if (state == GameServerSignIn::NotTried) {
            state = GameServerSignIn::Trying;
        }
    }
    // Its answer: `ok` for a 2xx status, false for no answer or an error status.
    void Answered(std::string_view url, bool ok) {
        std::scoped_lock lock{mutex};
        if (ok && url.find(GameServerLoginPath) != std::string_view::npos) {
            state = GameServerSignIn::SignedIn;
            return;
        }
        if (!ok && state != GameServerSignIn::SignedIn) {
            state = GameServerSignIn::Failed;
            ++failures;
        }
    }
    GameServerSignIn State() const {
        std::scoped_lock lock{mutex};
        return state;
    }
    u32 Failures() const {
        std::scoped_lock lock{mutex};
        return failures;
    }
    // A character's save opened: the title, where the game signs in, is behind. Whether this is
    // the first one.
    bool SaveOpened() {
        std::scoped_lock lock{mutex};
        return !std::exchange(save_opened, true);
    }
    bool WasSaveOpened() const {
        std::scoped_lock lock{mutex};
        return save_opened;
    }
    // The team screen's line about it (GameServerNotice).
    std::string Notice() const;

private:
    mutable std::mutex mutex;
    GameServerSignIn state = GameServerSignIn::NotTried;
    u32 failures = 0;
    bool save_opened = false;
};

// This game's (one for the process: its http layer notes, the co-op code reads).
inline GameServerSignInLog& TheGameServerSignIn() {
    static GameServerSignInLog log;
    return log;
}

// What the team screen says about it once a save is open (`save_opened`: the title is behind,
// so a sign-in not tried by then never comes), one line of at most 95 characters; empty while
// all is well or still going.
inline std::string GameServerNotice(GameServerSignIn state, bool save_opened) {
    switch (state) {
    case GameServerSignIn::SignedIn:
        return {};
    case GameServerSignIn::Failed:
        return "This game cannot reach the game server (port 20443): teammates will not see you";
    case GameServerSignIn::NotTried:
        if (save_opened) {
            return "This game plays offline (no game server sign-in): teammates will not see you";
        }
        return {};
    case GameServerSignIn::Trying:
        if (save_opened) {
            return "This game is not signed in to the game server: teammates may not see you";
        }
        return {};
    }
    return {};
}

inline std::string GameServerSignInLog::Notice() const {
    std::scoped_lock lock{mutex};
    return GameServerNotice(state, save_opened);
}

} // namespace Core::Bloodborne
