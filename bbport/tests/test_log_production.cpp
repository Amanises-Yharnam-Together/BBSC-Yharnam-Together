// SPDX-License-Identifier: GPL-2.0-or-later
// The port's log in a production build (BB_PRODUCTION=1, make-release; Kaniel 2026-11-04: "remove
// or optimise hard all logging for prod"): LOG_TRACE and LOG_DEBUG are compiled out (their
// arguments are never evaluated), and the log file (BB_LOG_FILE) keeps only warnings and errors,
// whatever BB_LOG_LEVEL asks, unless the player turned on the bug-report switch (bbport.ini
// coop_trace=1, which run.py passes as BB_COOP_TRACE=1): then it keeps BB_LOG_LEVEL's lines from
// info on, as a dev build does. Each case runs in a process of its own: the log reads its
// settings once.
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>
#include <vector>
#include "common/logging/log.h"

#if !BB_PRODUCTION
#error "build this test with BB_PRODUCTION=1"
#endif

static int failures;
#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, #condition);     \
            ++failures;                                                                            \
        }                                                                                          \
    } while (false)

static void SetVariable(const char* name, const std::string& value) {
#ifdef _WIN32
    _putenv_s(name, value.c_str());
#else
    setenv(name, value.c_str(), 1);
#endif
}

static std::vector<std::string> ReadLines(const std::filesystem::path& path) {
    std::ifstream file{path};
    std::vector<std::string> lines;
    for (std::string line; std::getline(file, line);) {
        lines.push_back(line);
    }
    return lines;
}

static bool Has(const std::vector<std::string>& lines, const std::string& text) {
    for (const auto& line : lines) {
        if (line.find(text) != std::string::npos) return true;
    }
    return false;
}

static int evaluated = 0;
// Not static: its only calls are in compiled-out lines (clang: -Wunneeded-internal-declaration).
int Count();
int Count() {
    return ++evaluated;
}

// One game: logs a line of each level into `path`; exit code 3 when a compiled-out line's
// arguments were evaluated.
static int Game(const char* path, const char* coop_trace) {
    SetVariable("BB_LOG_FILE", path);
    SetVariable("BB_LOG_LEVEL", "trace"); // the most a launcher could ask for
    SetVariable("BB_GPU_LOG", "critical");
    if (*coop_trace) SetVariable("BB_COOP_TRACE", coop_trace);
    LOG_TRACE(Debug, "trace line {}", Count());
    LOG_DEBUG(Debug, "debug line {}", Count());
    LOG_INFO(Debug, "info line");
    LOG_WARNING(Debug, "warning line");
    LOG_ERROR(Debug, "error line");
    LOG_CRITICAL(Debug, "critical line");
    const bool info_on = Common::Log::ShouldLog(Common::Log::Level::info);
    const std::string trace{coop_trace};
    if (info_on != (trace == "1" || trace == "on")) return 4;
    return evaluated == 0 ? 0 : 3;
}

static std::vector<std::string> RunGame(const char* self, const std::filesystem::path& path,
                                        const char* coop_trace) {
    std::filesystem::create_directories(path.parent_path());
    const std::string command = "\"" + std::string{self} + "\" game \"" + path.string() + "\" " +
                                (*coop_trace ? coop_trace : "-");
#ifdef _WIN32
    const int code = std::system(("\"" + command + "\"").c_str());
#else
    const int code = std::system(command.c_str());
#endif
    CHECK(code == 0);
    return ReadLines(path);
}

int main(int argc, char** argv) {
    if (argc == 4 && std::string{argv[1]} == "game") {
        return Game(argv[2], std::string{argv[3]} == "-" ? "" : argv[3]);
    }
    const auto folder = std::filesystem::temp_directory_path() / "bbport-log-production-test";
    std::error_code ignored;
    std::filesystem::remove_all(folder, ignored);

    // A player's game: warnings and worse only.
    const auto plain = RunGame(argv[0], folder / "plain" / "shad_log.txt", "");
    CHECK(plain.size() == 3);
    CHECK(Has(plain, "Game: warning line"));
    CHECK(Has(plain, "error line"));
    CHECK(Has(plain, "critical line"));
    CHECK(!Has(plain, "info line"));
    CHECK(!Has(plain, "debug line"));
    CHECK(!Has(plain, "trace line"));

    // coop_trace=1 for a bug report: info lines come back; debug and trace stay out of the build.
    for (const char* on : {"1", "on"}) {
        const auto detailed =
            RunGame(argv[0], folder / (std::string{"detailed-"} + on) / "shad_log.txt", on);
        CHECK(detailed.size() == 4);
        CHECK(Has(detailed, "info line"));
        CHECK(Has(detailed, "warning line"));
        CHECK(!Has(detailed, "debug line"));
        CHECK(!Has(detailed, "trace line"));
    }

    // Anything else is off.
    const auto other = RunGame(argv[0], folder / "zero" / "shad_log.txt", "0");
    CHECK(other.size() == 3);
    CHECK(!Has(other, "info line"));

    std::filesystem::remove_all(folder, ignored);
    if (failures != 0) {
        std::fprintf(stderr, "log production: %d check(s) failed\n", failures);
        return 1;
    }
    std::puts("log production: ok");
    return 0;
}
