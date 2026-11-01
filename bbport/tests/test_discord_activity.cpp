// SPDX-License-Identifier: GPL-2.0-or-later
// bbport co-op: what the Discord status says and reads (discord_activity.h).
#include <cassert>
#include <cstdio>
#include "gpu/bbcoop/discord_activity.h"

using namespace DiscordActivity;

int main() {
    assert(Json("Yharnam") == "\"Yharnam\"");
    assert(Json("a\"b\\c") == "\"a\\\"b\\\\c\"");
    assert(Json("line\nbreak") == "\"line break\"");

    const std::string join = "{\"evt\":\"ACTIVITY_JOIN\",\"data\":{\"secret\":\"c:ABC\\\"D\"}}";
    assert(Field(join, "evt") == "ACTIVITY_JOIN");
    assert(Field(join, "secret") == "c:ABC\"D");
    assert(Field(join, "nothing").empty());
    const std::string ask = "{\"id\":\"1\",\"data\":{\"user\":{\"id\":\"42\",\"username\":\"ada\"}}}";
    assert(Field(ask, "id") == "1");
    assert(Field(ask, "id", ask.find("\"user\"")) == "42");

    constexpr int Invite = 0, Ask = 1, Open = 2;
    assert(JoinSecret("KTCDAB", "t1", Invite, Invite, 2, 5) == "c:KTCDAB"); // the leader
    assert(JoinSecret("", "t1", Open, Invite, 2, 5) == "t:t1");
    assert(JoinSecret("", "t1", Ask, Invite, 2, 5) == "t:t1");
    assert(JoinSecret("", "t1", Invite, Invite, 2, 5).empty()) ; // a member of a closed team
    assert(JoinSecret("KTCDAB", "t1", Open, Invite, 5, 5).empty()); // full
    std::puts("discord activity: ok");
    return 0;
}
