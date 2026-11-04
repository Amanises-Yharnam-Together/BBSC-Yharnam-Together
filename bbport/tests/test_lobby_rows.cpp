// SPDX-License-Identifier: GPL-2.0-or-later
// bbport co-op: Hunters online on the team screen (bbcoop/lobby_rows.h).
#include <cassert>
#include <cstdio>
#include "gpu/bbcoop/lobby_rows.h"

using namespace LobbyRows;

int main() {
    assert(!ListedOnline("t1", "t1")); // a teammate: on the cards
    assert(ListedOnline("t2", "t1"));  // another team's: listed, with its team
    assert(ListedOnline("", "t1"));    // in no team
    assert(ListedOnline("t2", ""));    // this player in no team sees everyone
    assert(ListedOnline("", ""));

    assert(MayInvite(true, false, ""));
    assert(!MayInvite(false, false, "")); // the team is full, or this player leads none
    assert(!MayInvite(true, true, ""));   // in this team, whatever its leader's name says
    assert(!MayInvite(true, false, "Lisara")); // in another team
    std::puts("lobby rows: ok");
    return 0;
}
