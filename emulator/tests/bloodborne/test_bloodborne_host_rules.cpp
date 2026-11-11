// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <cstring>
#include <string>
#include <vector>

#include <gtest/gtest.h>

#include "core/bloodborne_host_rules.h"

using namespace Core::Bloodborne;

namespace {

TEST(BloodborneHostRules, AreOffUnlessTheLauncherSaysSo) {
    EXPECT_EQ(ParseHostRules(""), HostRules{});
    EXPECT_EQ(ParseHostRules("off"), HostRules{});
    EXPECT_EQ(ParseHostRules("nonsense"), HostRules{});
    const HostRules all = ParseHostRules("rot, travel,vote ,scale");
    EXPECT_TRUE(all.rot && all.travel_together && all.travel_vote && all.enemy_scaling);
    // The vote is a part of travelling together.
    EXPECT_EQ(ParseHostRules("vote"), HostRules{});
    EXPECT_EQ(ParseHostRules("scale"), (HostRules{.enemy_scaling = true}));
    EXPECT_EQ(HostRulesText({}), "off");
    EXPECT_EQ(HostRulesText(all), "rot,travel,vote,scale");
    EXPECT_EQ(ParseHostRules(HostRulesText(all)), all);
}

TEST(BloodborneRot, EachDeathAddsOnePenaltyUpToFive) {
    Rot rot;
    EXPECT_EQ(rot.Effect(), RotEffect{});
    EXPECT_EQ(rot.Die(0), RotKind::MaxHp);
    EXPECT_EQ(rot.Die(1), RotKind::MaxStamina);
    EXPECT_EQ(rot.Die(2), RotKind::StaminaUse);
    EXPECT_EQ(rot.Die(3), RotKind::Rally);
    EXPECT_EQ(rot.Die(9), RotKind::Discovery); // any roll picks one
    EXPECT_EQ(rot.Kinds().size(), MaxRot);
    EXPECT_EQ(rot.Die(0), RotKind::None); // full
    EXPECT_EQ(rot.Kinds().size(), MaxRot);
    EXPECT_EQ(rot.Numbers(), (std::vector<u32>{1, 2, 3, 4, 5}));
}

TEST(BloodborneRot, PenaltiesStack) {
    Rot rot;
    rot.Die(0);
    rot.Die(5);
    rot.Die(3);
    const RotEffect effect = rot.Effect();
    EXPECT_FLOAT_EQ(effect.max_hp_rate, 0.8f);
    EXPECT_FLOAT_EQ(effect.rally_rate, 0.85f);
    EXPECT_FLOAT_EQ(effect.max_stamina_rate, 1.0f);
    EXPECT_FLOAT_EQ(effect.stamina_use_rate, 1.0f);
    EXPECT_EQ(effect.discovery, 0);
    Rot other;
    for (int i = 0; i < 5; ++i) {
        other.Die(1 + 5 * i); // max stamina each time
    }
    EXPECT_FLOAT_EQ(other.Effect().max_stamina_rate, 0.5f);
    Rot more;
    more.Die(2);
    more.Die(4);
    more.Die(4);
    EXPECT_FLOAT_EQ(more.Effect().stamina_use_rate, 1.1f);
    EXPECT_EQ(more.Effect().discovery, -20);
    EXPECT_EQ(more.HudText(), "Stam use+10% Disc-20");
}

TEST(BloodborneRot, EveryCureTakesItAllAway) {
    for (const RotCure cure : {RotCure::LampRest, RotCure::LevelUp, RotCure::BossKill,
                               RotCure::Revenge, RotCure::OwnBloodstain}) {
        Rot rot;
        EXPECT_FALSE(rot.Cure(cure)); // nothing to take
        rot.Die(0, 0x1234);
        rot.Die(1);
        EXPECT_TRUE(rot.Cure(cure));
        EXPECT_TRUE(rot.Kinds().empty());
        EXPECT_EQ(rot.Effect(), RotEffect{});
        EXPECT_EQ(rot.HudText(), "");
    }
}

TEST(BloodborneRot, KillingYourKillerCuresIt) {
    Rot rot;
    rot.Die(0, 0x10001);
    EXPECT_EQ(rot.Killer(), 0x10001u);
    EXPECT_FALSE(rot.Killed(0x10002)); // another enemy
    EXPECT_FALSE(rot.Killed(0));
    EXPECT_EQ(rot.Kinds().size(), 1u);
    // The last death's killer counts.
    rot.Die(1, 0x10003);
    EXPECT_FALSE(rot.Killed(0x10001));
    EXPECT_TRUE(rot.Killed(0x10003));
    EXPECT_TRUE(rot.Kinds().empty());
    EXPECT_EQ(rot.Killer(), 0u);
}

TEST(BloodborneRot, TheServersRotComesBack) {
    Rot rot;
    const std::vector<u32> kept{4, 1, 0, 9, 4};
    rot.Set(kept);
    EXPECT_EQ(rot.Numbers(), (std::vector<u32>{4, 1, 4}));
    const std::vector<u32> too_many{1, 1, 1, 1, 1, 1, 1};
    rot.Set(too_many);
    EXPECT_EQ(rot.Kinds().size(), MaxRot);
}

// A loaded PARAM file as the game keeps it (see test_bloodborne_harder_enemies.cpp).
std::vector<u8> MakeEffects(const std::vector<s32>& ids, bool share_last = false) {
    const std::size_t data = 0x40 + ids.size() * 24;
    std::vector<u8> param(data + ids.size() * SpEffectRowSize);
    const u16 rows = static_cast<u16>(ids.size());
    std::memcpy(param.data() + 0x0A, &rows, sizeof(rows));
    std::memcpy(param.data() + 0x0C, "SP_EFFECT_PARAM_ST", 18);
    for (std::size_t row = 0; row < ids.size(); ++row) {
        const std::size_t own = share_last && row + 1 == ids.size() ? row - 1 : row;
        const u64 offset = data + own * SpEffectRowSize;
        std::memcpy(param.data() + 0x40 + row * 24, &ids[row], sizeof(s32));
        std::memcpy(param.data() + 0x40 + row * 24 + 8, &offset, sizeof(offset));
    }
    return param;
}

float FieldOf(const std::vector<u8>& param, std::size_t row, u64 field) {
    float value = 0.0f;
    std::memcpy(&value, param.data() + 0x40 + 2 * 24 + row * SpEffectRowSize + field,
                sizeof(value));
    return value;
}

TEST(BloodborneRot, EachPenaltyIsALastingEffectRow) {
    std::vector<u8> param = MakeEffects({RotTemplateRow, 5509});
    const float half = 0.5f, ten = 10.0f, lasting = -1.0f;
    u8* source = param.data() + 0x40 + 2 * 24;
    std::memcpy(source + 0x10, &half, 4);
    std::memcpy(source + 0x1FC, &ten, 4);
    std::memcpy(source + SpEffectDurationOffset, &lasting, 4);
    source[0x15F] = 0x6F; // who it is for
    ASSERT_TRUE(WriteRotRow(param, RotRows[0], 0.8f));
    EXPECT_FLOAT_EQ(FieldOf(param, 1, 0x10), 0.8f);
    EXPECT_FLOAT_EQ(FieldOf(param, 1, 0x1FC), 0.0f);
    EXPECT_FLOAT_EQ(FieldOf(param, 1, SpEffectDurationOffset), -1.0f);
    EXPECT_EQ(param[0x40 + 2 * 24 + SpEffectRowSize + 0x15F], 0x6F);
    EXPECT_FLOAT_EQ(FieldOf(param, 0, 0x10), 0.5f); // the template stays
    // A missing row, or one whose data another id shares: nothing written.
    EXPECT_FALSE(WriteRotRow(param, RotRows[1], 0.9f));
    std::vector<u8> shared = MakeEffects({RotTemplateRow, 5509, 5510}, true);
    EXPECT_FALSE(WriteRotRow(shared, RotRows[0], 0.8f));
    // Each kind's value.
    Rot rot;
    rot.Die(0);
    rot.Die(4);
    rot.Die(9);
    EXPECT_FLOAT_EQ(RotRowValue(rot.Effect(), RotKind::MaxHp), 0.9f);
    EXPECT_FLOAT_EQ(RotRowValue(rot.Effect(), RotKind::Discovery), -20.0f);
    EXPECT_FLOAT_EQ(RotRowValue(rot.Effect(), RotKind::Rally), 1.0f);
    for (std::size_t i = 0; i < RotRows.size(); ++i) {
        EXPECT_EQ(static_cast<std::size_t>(RotRows[i].kind), i + 1);
    }
}

TEST(BloodborneTravelTogether, AsksOnlyWithTheRuleAndATeamOutOfBossFights) {
    const HostRules on{.travel_together = true};
    EXPECT_TRUE(OffersTeamTravel(on, true, 1, false));
    EXPECT_FALSE(OffersTeamTravel(HostRules{}, true, 1, false)); // free travel stays
    EXPECT_FALSE(OffersTeamTravel(on, false, 1, false));         // alone, out of a session
    EXPECT_FALSE(OffersTeamTravel(on, true, 0, false));          // nobody else in it
    EXPECT_FALSE(OffersTeamTravel(on, true, 2, true));           // a boss fight
}

TEST(BloodborneTravelVote, OneNoStopsTheTrip) {
    TravelVote vote;
    EXPECT_EQ(vote.At(0), TravelVote::Result::None);
    const std::vector<std::string> others{"b", "c"};
    vote.Start(7, others, 1000);
    EXPECT_EQ(vote.At(1000), TravelVote::Result::Waiting);
    vote.Answer(7, "b", true);
    EXPECT_EQ(vote.At(2000), TravelVote::Result::Waiting);
    vote.Answer(7, "c", false);
    EXPECT_EQ(vote.At(2000), TravelVote::Result::Stopped);
    // A later Yes does not undo it.
    vote.Answer(7, "c", true);
    EXPECT_EQ(vote.At(30'000), TravelVote::Result::Stopped);
}

TEST(BloodborneTravelVote, EveryYesOrTheTimeGoes) {
    TravelVote vote;
    const std::vector<std::string> others{"b", "c"};
    vote.Start(1, others, 0);
    vote.Answer(1, "b", true);
    vote.Answer(2, "c", false); // another trip's answer
    vote.Answer(1, "x", false); // not asked
    EXPECT_EQ(vote.At(1), TravelVote::Result::Waiting);
    vote.Answer(1, "c", true);
    EXPECT_EQ(vote.At(1), TravelVote::Result::Go);
    // Silence for TravelVoteMs is a Yes.
    vote.Start(2, others, 0);
    EXPECT_EQ(vote.LeftMs(5'000), TravelVoteMs - 5'000);
    EXPECT_EQ(vote.At(TravelVoteMs - 1), TravelVote::Result::Waiting);
    EXPECT_EQ(vote.At(TravelVoteMs), TravelVote::Result::Go);
    // A member gone says nothing more.
    vote.Start(3, others, 0);
    vote.Answer(3, "b", true);
    vote.Drop("c");
    EXPECT_EQ(vote.At(1), TravelVote::Result::Go);
    vote.Clear();
    EXPECT_EQ(vote.At(1), TravelVote::Result::None);
    // Nobody else: at once.
    vote.Start(4, {}, 0);
    EXPECT_EQ(vote.At(0), TravelVote::Result::Go);
}

TEST(BloodborneEnemyScaling, FromVanillaAloneToTheHarderDefaultsForAFullTeam) {
    EXPECT_FALSE(TeamScaledEnemies(0).has_value());
    EXPECT_FALSE(TeamScaledEnemies(1).has_value());
    const auto two = TeamScaledEnemies(2);
    const auto three = TeamScaledEnemies(3);
    const auto four = TeamScaledEnemies(4);
    const auto five = TeamScaledEnemies(5);
    ASSERT_TRUE(two && three && four && five);
    EXPECT_FLOAT_EQ(two->hp, 1.0f + 2.0f / 4.0f);
    EXPECT_FLOAT_EQ(two->damage, 1.0f + 0.5f / 4.0f);
    EXPECT_FLOAT_EQ(two->poise, 1.0f + 2.0f / 4.0f);
    EXPECT_FLOAT_EQ(three->hp, 1.0f + 4.0f / 4.0f);
    EXPECT_FLOAT_EQ(four->hp, 1.0f + 6.0f / 4.0f);
    EXPECT_FLOAT_EQ(five->hp, HarderDefaultHp);
    EXPECT_FLOAT_EQ(five->damage, HarderDefaultDamage);
    EXPECT_FLOAT_EQ(five->poise, HarderDefaultPoise);
    // Never past a full team.
    EXPECT_FLOAT_EQ(TeamScaledEnemies(7)->hp, HarderDefaultHp);
    // Each step is one the game takes (ParseHarderEnemies' range).
    for (std::size_t n = 2; n <= TeamSlots; ++n) {
        const auto scaled = TeamScaledEnemies(n);
        EXPECT_TRUE(ParseHarderEnemies(std::to_string(scaled->hp) + "," +
                                       std::to_string(scaled->damage) + "," +
                                       std::to_string(scaled->poise))
                        .has_value());
    }
}

// Kaniel 2026-11-05: the enemies' strength is the team's (its leader sets it on the team screen):
// Auto grows from vanilla alone to the team's strength for a full team, Fixed is the team's
// strength at all times; neither takes a player's own launcher value while in a team.
TEST(BloodborneEnemyScaling, TheTeamsStrengthOverEachPlayersOwn) {
    const HarderEnemies own{9.0f, 9.0f, 9.0f};
    const HarderEnemies team{2.0f, 1.25f, 2.0f};
    HostRules rules;
    rules.enemy_scaling = true;
    rules.enemies = team;
    EXPECT_FALSE(EnemiesWanted(rules, true, 1, own).has_value()) << "Auto alone: vanilla";
    const auto full = EnemiesWanted(rules, true, TeamSlots, own);
    ASSERT_TRUE(full.has_value());
    EXPECT_FLOAT_EQ(full->hp, 2.0f);
    EXPECT_FLOAT_EQ(full->damage, 1.25f);
    EXPECT_FLOAT_EQ(full->poise, 2.0f);
    const auto three = EnemiesWanted(rules, true, 3, own);
    ASSERT_TRUE(three.has_value());
    EXPECT_FLOAT_EQ(three->hp, 1.5f) << "half way for 3 of 5";
    // Auto without a strength: the standard (TeamScaledEnemies).
    rules.enemies.reset();
    EXPECT_FLOAT_EQ(EnemiesWanted(rules, true, TeamSlots, own)->hp, HarderDefaultHp);
    // Fixed: the team's at all times, the standard when it has none.
    rules.enemy_scaling = false;
    rules.enemies = team;
    ASSERT_TRUE(EnemiesWanted(rules, true, 1, own).has_value());
    EXPECT_FLOAT_EQ(EnemiesWanted(rules, true, 1, own)->damage, 1.25f);
    rules.enemies.reset();
    EXPECT_FLOAT_EQ(EnemiesWanted(rules, true, 4, own)->poise, HarderDefaultPoise);
    // Out of a team: the player's own launcher setting, as before.
    EXPECT_FLOAT_EQ(EnemiesWanted(rules, false, 1, own)->hp, 9.0f);
    EXPECT_FALSE(EnemiesWanted(rules, false, 1, std::nullopt).has_value());
}

TEST(BloodborneEnemyScaling, TheTeamsStrengthFromItsRules) {
    EXPECT_FALSE(TeamStrength(0.0f, 0.0f, 0.0f).has_value()) << "none: the standard";
    const auto set = TeamStrength(2.0f, 0.0f, 4.0f);
    ASSERT_TRUE(set.has_value());
    EXPECT_FLOAT_EQ(set->hp, 2.0f);
    EXPECT_FLOAT_EQ(set->damage, HarderDefaultDamage);
    EXPECT_FLOAT_EQ(set->poise, 4.0f);
}

// Kaniel 2026-11-05: what the team screen's leader sets goes to the game as one text.
TEST(BloodborneHostRules, TheTeamScreensRulesAsOneText) {
    HostRules rules;
    rules.travel_together = true;
    rules.travel_vote = true;
    rules.enemy_scaling = true;
    rules.boss_tempo = BossTempo::Relentless;
    rules.enemies = HarderEnemies{2.5f, 1.25f, 3.0f};
    const std::string text = ScreenRulesText(rules);
    EXPECT_EQ(text, "0,1,1,1,2,2.5,1.25,3");
    EXPECT_EQ(ParseScreenRules(text), rules);
    HostRules standard;
    EXPECT_EQ(ScreenRulesText(standard), "0,0,0,0,0,0,0,0");
    EXPECT_EQ(ParseScreenRules("0,0,0,0,0,0,0,0"), standard);
    EXPECT_FALSE(ParseScreenRules("0,0,0,0,3,0,0,0").has_value()) << "no such tempo";
    EXPECT_FALSE(ParseScreenRules("0,0,0,0,0,0.5,0,0").has_value()) << "weaker than vanilla";
    EXPECT_FALSE(ParseScreenRules("0,0,0,0,0,11,0,0").has_value());
    EXPECT_FALSE(ParseScreenRules("0,0,0").has_value());
    EXPECT_FALSE(ParseScreenRules("").has_value());
}

// Kaniel 2026-11-11: the launcher has no party settings any more: the rules a player set on the
// team screen are kept in its user folder and are its own at the next start.
TEST(BloodborneHostRules, TheTeamScreensRulesAreThePlayersOwnAtTheNextStart) {
    // Nothing set anywhere: none of its own (the team it makes takes the server's default).
    EXPECT_FALSE(OwnRulesAtStart(nullptr, nullptr, "").has_value());
    EXPECT_FALSE(OwnRulesAtStart(nullptr, nullptr, "not rules\n").has_value());
    // The saved line, as the team screen sent it (ScreenRulesText), a line end or not.
    HostRules saved;
    saved.rot = true;
    saved.boss_tempo = BossTempo::Relentless;
    saved.enemies = HarderEnemies{4.0f, 2.0f, 4.0f};
    EXPECT_EQ(OwnRulesAtStart(nullptr, nullptr, ScreenRulesText(saved)), saved);
    EXPECT_EQ(OwnRulesAtStart(nullptr, nullptr, ScreenRulesText(saved) + "\r\n"), saved);
    // An enemy strength alone is no rule: only the rules' setting or the saved ones count.
    EXPECT_FALSE(OwnRulesAtStart(nullptr, "3,1.5,3", "").has_value());
    // The dev settings (the rig's) go over the saved ones, with their own strength.
    HostRules dev = ParseHostRules("travel,vote");
    EXPECT_EQ(OwnRulesAtStart("travel,vote", nullptr, ScreenRulesText(saved)), dev);
    dev.enemies = HarderEnemies{5.0f, 2.0f, 5.0f};
    EXPECT_EQ(OwnRulesAtStart("travel,vote", "5,2,5", ScreenRulesText(saved)), dev);
    EXPECT_EQ(OwnRulesAtStart("off", nullptr, ScreenRulesText(saved)), HostRules{});
}

TEST(BloodborneEnemyScaling, CountsTheHuntersOnThisMap) {
    const std::vector<MemberMap> board{{"me", 0x15000000}, {"b", 0x15000000}, {"c", 0x18000000}};
    EXPECT_EQ(HuntersOnMap(board, "me", 0x15000000), 2u);
    EXPECT_EQ(HuntersOnMap(board, "me", 0x18000000), 2u); // a board from before this trip
    EXPECT_EQ(HuntersOnMap(board, "me", 0x21000000), 1u);
    EXPECT_EQ(HuntersOnMap({}, "me", 0x15000000), 1u);
    EXPECT_EQ(HuntersOnMap(board, "me", 0), 1u); // loading
}

// Kaniel 2026-10-28: the boss tempo rule, Vanilla (off) unless the leader picks Aggressive or
// Relentless.
TEST(BloodborneBossTempo, IsALevelWordOfTheRules) {
    EXPECT_EQ(ParseHostRules("").boss_tempo, BossTempo::Vanilla);
    EXPECT_EQ(ParseHostRules("aggressive").boss_tempo, BossTempo::Aggressive);
    EXPECT_EQ(ParseHostRules("rot, relentless").boss_tempo, BossTempo::Relentless);
    EXPECT_EQ(ParseHostRules("aggressive,relentless").boss_tempo, BossTempo::Relentless)
        << "the last word";
    EXPECT_EQ(HostRulesText({.boss_tempo = BossTempo::Aggressive}), "aggressive");
    const HostRules all = ParseHostRules("rot,travel,vote,scale,relentless");
    EXPECT_EQ(HostRulesText(all), "rot,travel,vote,scale,relentless");
    EXPECT_EQ(ParseHostRules(HostRulesText(all)), all);
}

TEST(BloodborneBossTempo, EachLevelsTuning) {
    EXPECT_EQ(BossTempoTuningFor(BossTempo::Vanilla), BossTempoTuning{});
    const BossTempoTuning aggressive = BossTempoTuningFor(BossTempo::Aggressive);
    EXPECT_FLOAT_EQ(aggressive.gap, 0.5f);
    EXPECT_FLOAT_EQ(aggressive.odds, 0.5f);
    EXPECT_FLOAT_EQ(aggressive.turn, 1.3f);
    EXPECT_FLOAT_EQ(aggressive.anim, 1.0f) << "animation speed is not in this round";
    const BossTempoTuning relentless = BossTempoTuningFor(BossTempo::Relentless);
    EXPECT_FLOAT_EQ(relentless.gap, 0.25f);
    EXPECT_FLOAT_EQ(relentless.odds, 0.25f);
    EXPECT_FLOAT_EQ(relentless.turn, 1.6f);
    EXPECT_FALSE(BossTempoTuning{}.Changes());
    EXPECT_TRUE(aggressive.Changes());
}

// SHADPS4_BLOODBORNE_BOSS_TEMPO=gap,odds,turn,anim tunes a level that is on; Vanilla stays the
// game's.
TEST(BloodborneBossTempo, TheDevSettingTunesALevelThatIsOn) {
    const auto tuned = ParseBossTempoTuning(" 0.4, 0.3 ,1.5,1");
    ASSERT_TRUE(tuned);
    EXPECT_FLOAT_EQ(tuned->gap, 0.4f);
    EXPECT_FLOAT_EQ(tuned->odds, 0.3f);
    EXPECT_FLOAT_EQ(tuned->turn, 1.5f);
    EXPECT_FLOAT_EQ(tuned->anim, 1.0f);
    EXPECT_FALSE(ParseBossTempoTuning(""));
    EXPECT_FALSE(ParseBossTempoTuning("0.5,0.5,1.3"));
    EXPECT_FALSE(ParseBossTempoTuning("0.5,x,1.3,1"));
    EXPECT_FALSE(ParseBossTempoTuning("0,0.5,1.3,1")) << "no breather at all is a typo";
    EXPECT_FALSE(ParseBossTempoTuning("0.5,1.5,1.3,1")) << "a chance is at most 1";
    EXPECT_FALSE(ParseBossTempoTuning("0.5,0.5,9,1")) << "a typo, not a turn speed";
    EXPECT_EQ(BossTempoTuningFor(BossTempo::Vanilla, tuned), BossTempoTuning{});
    EXPECT_EQ(BossTempoTuningFor(BossTempo::Aggressive, tuned), *tuned);
    EXPECT_EQ(BossTempoTuningFor(BossTempo::Relentless, std::nullopt),
              BossTempoTuningFor(BossTempo::Relentless));
}

// A boss's breathers (AddSubGoal of GOAL_COMMON_Wait 2000, Turn 2001, LeaveTarget 2016 and
// SidewayMove 2017) last `gap` of their time; a Wait, LeaveTarget or SidewayMove is cut to
// almost nothing unless the roll (0-99) is under `odds`. A turn is never cut: the boss would
// swing facing away.
TEST(BloodborneBossTempo, BreathersShortenAndMostlyGo) {
    const BossTempoTuning aggressive = BossTempoTuningFor(BossTempo::Aggressive);
    EXPECT_FLOAT_EQ(BossGoalLife(GoalCommonWait, 2.0f, aggressive, 0), 1.0f);
    EXPECT_FLOAT_EQ(BossGoalLife(GoalCommonWait, 2.0f, aggressive, 49), 1.0f);
    EXPECT_FLOAT_EQ(BossGoalLife(GoalCommonWait, 2.0f, aggressive, 50), CutGoalLife);
    EXPECT_FLOAT_EQ(BossGoalLife(GoalCommonLeaveTarget, 3.0f, aggressive, 10), 1.5f);
    EXPECT_FLOAT_EQ(BossGoalLife(GoalCommonSidewayMove, 3.0f, aggressive, 99), CutGoalLife);
    EXPECT_FLOAT_EQ(BossGoalLife(GoalCommonTurn, 2.0f, aggressive, 99), 1.0f);
    EXPECT_FLOAT_EQ(BossGoalLife(2002, 2.0f, aggressive, 99), 2.0f) << "not a breather";
    EXPECT_FLOAT_EQ(BossGoalLife(GoalCommonWait, -1.0f, aggressive, 99), -1.0f)
        << "no time limit stays";
    EXPECT_FLOAT_EQ(BossGoalLife(GoalCommonWait, 0.02f, aggressive, 99), 0.02f)
        << "never longer than the game's";
    for (const s32 goal : {GoalCommonWait, GoalCommonTurn, 2002}) {
        EXPECT_FLOAT_EQ(BossGoalLife(goal, 2.0f, BossTempoTuning{}, 99), 2.0f);
    }
    EXPECT_TRUE(IsBossTempoGoal(GoalCommonSidewayMove));
    EXPECT_FALSE(IsBossTempoGoal(2015)) << "ApproachTarget is no breather";
}

} // namespace
