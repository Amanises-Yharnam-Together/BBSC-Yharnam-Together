// SPDX-License-Identifier: GPL-2.0-or-later
// bbport co-op: the launcher's settings as UTF-8, whatever the PC's code page (env_text.h).
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <string>
#include "gpu/shim/core/env_text.h"

int main() {
    using BbEnv::WideToUtf8;
    assert(WideToUtf8(L"") == "");
    assert(WideToUtf8(L"Hunter") == "Hunter");
    assert(WideToUtf8(L"ö") == "\xC3\xB6");                // two bytes
    assert(WideToUtf8(L"Охотник") ==
           "\xD0\x9E\xD1\x85\xD0\xBE\xD1\x82\xD0\xBD\xD0\xB8\xD0\xBA");
    assert(WideToUtf8(L"我") == "\xE6\x88\x91");            // three bytes
    assert(WideToUtf8(L"\U0001F319") == "\xF0\x9F\x8C\x99");    // four bytes (a surrogate pair)
#ifdef _WIN32
    assert(WideToUtf8(std::wstring{wchar_t(0xD83C)}.c_str()) == "\xEF\xBF\xBD"); // half a pair

    // The wide value is what counts, not the code page's guess.
    _wputenv(L"BB_ENV_TEXT_TEST=Ох");
    assert(BbEnv::Text("BB_ENV_TEXT_TEST", "fallback") == "\xD0\x9E\xD1\x85");
    _wputenv(L"BB_ENV_TEXT_TEST=");
#endif
    assert(BbEnv::Text("BB_ENV_TEXT_TEST", "fallback") == "fallback");
    assert(BbEnv::Text("BB_ENV_TEXT_NOT_SET", "fallback") == "fallback");
    std::puts("env text: ok");
    return 0;
}
