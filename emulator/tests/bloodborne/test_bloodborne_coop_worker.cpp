// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <atomic>
#include <chrono>
#include <future>
#include <thread>
#include <vector>
#include <gtest/gtest.h>

#include "core/bloodborne_coop_worker.h"

using Core::Bloodborne::CoopWorker;
using Core::Bloodborne::OffMainPart;
using Core::Bloodborne::OffMainSwitches;

TEST(CoopWorker, AJobRunsOffTheGameThread) {
    CoopWorker worker;
    std::promise<std::thread::id> ran;
    ASSERT_TRUE(worker.Post([&] { ran.set_value(std::this_thread::get_id()); }));
    EXPECT_NE(ran.get_future().get(), std::this_thread::get_id());
}

TEST(CoopWorker, StepsWaitForTheGameThreadAndKeepTheirOrder) {
    CoopWorker worker;
    std::vector<int> order;
    std::thread::id applied_on;
    std::promise<void> posted;
    ASSERT_TRUE(worker.Post([&] {
        worker.OnGameThread([&] {
            order.push_back(1);
            applied_on = std::this_thread::get_id();
        });
        worker.OnGameThread([&] { order.push_back(2); });
        posted.set_value();
    }));
    posted.get_future().wait();
    EXPECT_TRUE(order.empty());
    EXPECT_EQ(worker.ApplyPending(), 2u);
    EXPECT_EQ(order, (std::vector<int>{1, 2}));
    EXPECT_EQ(applied_on, std::this_thread::get_id());
    EXPECT_EQ(worker.ApplyPending(), 0u);
}

TEST(CoopWorker, AFullQueueRefusesInsteadOfMakingTheGameWait) {
    CoopWorker worker;
    std::promise<void> release;
    auto released = release.get_future().share();
    std::promise<void> started;
    ASSERT_TRUE(worker.Post([&, released] {
        started.set_value();
        released.wait();
    }));
    started.get_future().wait();
    for (std::size_t job = 0; job < CoopWorker::MaxWaitingJobs; ++job) {
        EXPECT_TRUE(worker.Post([] {}));
    }
    EXPECT_FALSE(worker.Post([] {}));
    release.set_value();
}

TEST(CoopWorker, StartsItsThreadOnlyWhenFirstNeeded) {
    std::atomic<int> started{0};
    {
        CoopWorker worker{[&] { ++started; }};
        EXPECT_EQ(started.load(), 0);
    }
    EXPECT_EQ(started.load(), 0);
}

TEST(CoopWorker, GoesIdleEveryPeriodAndStopsAtItsEnd) {
    std::atomic<int> idle{0};
    {
        CoopWorker worker{{}, [&] { ++idle; }, std::chrono::milliseconds{5}};
        std::promise<void> ran;
        ASSERT_TRUE(worker.Post([&] { ran.set_value(); }));
        ran.get_future().wait();
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds{5};
        while (idle.load() < 2 && std::chrono::steady_clock::now() < deadline) {
            std::this_thread::yield();
        }
    }
    EXPECT_GE(idle.load(), 2);
}

TEST(OffMainSwitches, OnUnlessStartedOff) {
    EXPECT_TRUE(OffMainSwitches{}.On(OffMainPart::Flags));
    EXPECT_FALSE(OffMainSwitches{false}.On(OffMainPart::Flags));
}

TEST(OffMainSwitches, TheFileChangesAPartWhileTheGameRuns) {
    OffMainSwitches switches;
    switches.Apply("flags=0\r\n");
    EXPECT_FALSE(switches.On(OffMainPart::Flags));
    switches.Apply("flags=1");
    EXPECT_TRUE(switches.On(OffMainPart::Flags));
    switches.Apply("worldfile=0\n");
    EXPECT_TRUE(switches.On(OffMainPart::Flags));
    EXPECT_FALSE(switches.On(OffMainPart::WorldFile));
    switches.Apply("all=0\n");
    EXPECT_FALSE(switches.On(OffMainPart::Flags));
    switches.Apply("all=1\n");
    EXPECT_TRUE(switches.On(OffMainPart::WorldFile));
}

TEST(OffMainSwitches, OtherLinesChangeNothing) {
    OffMainSwitches switches;
    switches.Apply("\n# flags=0\nflags=2\nflags\n=0\nother=0\n");
    EXPECT_TRUE(switches.On(OffMainPart::Flags));
}
