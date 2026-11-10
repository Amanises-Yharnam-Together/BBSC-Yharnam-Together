// SPDX-License-Identifier: GPL-2.0-or-later
// A shader table walker whose root pointer is null (gpu/shim/bbport_srt_roots.h): the roots are
// checked before the walk, so a null root costs no fault at all. Before, every load under a null
// root went through the vectored fault handler (bbport_srt_fault.h): krolebord's 1.3.1 log
// (2026-10-28, an RTX 4050) counted 8,388,608 of them in about two minutes, about 70,000 a
// second, and the game fell from 50 to 6.7 FPS. A null root's tables read zeros as before; the
// other roots of the shader still read theirs.
// No game, Vulkan device or window.
//   ninja -C out/gpu srt-null-root-test && out/gpu/srt-null-root-test.exe
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "bbport_srt_fault.h"
#include "bbport_srt_roots.h"

#ifdef _WIN32
#include <windows.h>
#else
#include <csignal>
#include <sys/mman.h>
#include <ucontext.h>
#endif

namespace {

// Two roots, as the walker generator writes them (flatten_extended_userdata_pass.cpp): user data
// dwords 0-1 point at a table whose dword 2 goes to flat dword 16, dwords 2-3 at one whose
// dword 3 goes to flat dword 17.
const uint8_t kWalker[] = {
    0x57,                                                       // push rdi
    0x48, 0x8b, 0x3f,                                           // mov rdi, [rdi]
    0x49, 0xba, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, // mov r10, 0xffffffffffff
    0x4c, 0x21, 0xd7,                                           // and rdi, r10
    0x44, 0x8b, 0x57, 0x08,                                     // mov r10d, [rdi+8]
    0x44, 0x89, 0x56, 0x40,                                     // mov [rsi+0x40], r10d
    0x5f,                                                       // pop rdi
    0x57,                                                       // push rdi
    0x48, 0x8b, 0x7f, 0x08,                                     // mov rdi, [rdi+8]
    0x49, 0xba, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, // mov r10, 0xffffffffffff
    0x4c, 0x21, 0xd7,                                           // and rdi, r10
    0x44, 0x8b, 0x57, 0x0c,                                     // mov r10d, [rdi+12]
    0x44, 0x89, 0x56, 0x44,                                     // mov [rsi+0x44], r10d
    0x5f,                                                       // pop rdi
    0xc3,                                                       // ret
};

uint8_t* g_code = nullptr;
int g_faults = 0;

bool InWalker(uint64_t rip) {
    const auto start = reinterpret_cast<uint64_t>(g_code);
    return rip >= start && rip < start + sizeof(kWalker);
}

#ifdef _WIN32
LONG CALLBACK OnFault(EXCEPTION_POINTERS* info) {
    auto* c = info->ContextRecord;
    if (info->ExceptionRecord->ExceptionCode != EXCEPTION_ACCESS_VIOLATION || !InWalker(c->Rip)) {
        return EXCEPTION_CONTINUE_SEARCH;
    }
    uint64_t rip = c->Rip, rdi = c->Rdi, r10 = c->R10;
    if (!BbSrtFault::Resume(rip, rdi, r10)) {
        return EXCEPTION_CONTINUE_SEARCH;
    }
    c->Rip = rip, c->Rdi = rdi, c->R10 = r10;
    ++g_faults;
    return EXCEPTION_CONTINUE_EXECUTION;
}
#else
void OnFault(int, siginfo_t*, void* raw) {
    auto& g = static_cast<ucontext_t*>(raw)->uc_mcontext.gregs;
    uint64_t rip = g[REG_RIP], rdi = g[REG_RDI], r10 = g[REG_R10];
    if (!InWalker(rip) || !BbSrtFault::Resume(rip, rdi, r10)) {
        std::_Exit(3);
    }
    g[REG_RIP] = rip, g[REG_RDI] = rdi, g[REG_R10] = r10;
    ++g_faults;
}
#endif

typedef void(__attribute__((sysv_abi)) * Walker)(const uint32_t*, uint32_t*);

struct Result {
    uint32_t first, second;
    BbSrtRoots::Walk walk;
    uint32_t null_roots;
    int faults;
};

/// One draw as RefreshFlatBuf does it: user data copied in front, then the walk BbSrtRoots chose.
Result Draw(Walker walker, const BbSrtRoots::Roots& roots, const void* first, const void* second,
            uint64_t tag = 0) {
    uint32_t user_data[16] = {};
    const uint64_t a = reinterpret_cast<uint64_t>(first) | tag;
    const uint64_t b = reinterpret_cast<uint64_t>(second) | tag;
    std::memcpy(&user_data[0], &a, 8);
    std::memcpy(&user_data[2], &b, 8);
    uint32_t flat[32];
    std::memset(flat, 0xcd, sizeof(flat)); // the last draw's words
    std::memcpy(flat, user_data, sizeof(user_data));
    const int faults_before = g_faults;
    uint32_t walk_ud[16];
    uint32_t null_roots = 0;
    const auto walk = BbSrtRoots::Prepare(roots, user_data, 16, walk_ud, null_roots);
    switch (walk) {
    case BbSrtRoots::Walk::Tables:
        walker(user_data, flat);
        break;
    case BbSrtRoots::Walk::SomeNull:
        walker(walk_ud, flat);
        break;
    case BbSrtRoots::Walk::AllNull:
        BbSrtRoots::ZeroWalkerWords(flat, 16, 32);
        break;
    }
    return {flat[16], flat[17], walk, null_roots, g_faults - faults_before};
}

int Fail(const char* what, const Result& r) {
    std::printf("srt-null-root-test: %s (read %#x %#x, walk %d, %u null roots, %d faults)\n", what,
                r.first, r.second, int(r.walk), r.null_roots, r.faults);
    return 1;
}

} // namespace

int main() {
#ifdef _WIN32
    g_code = static_cast<uint8_t*>(
        VirtualAlloc(nullptr, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    AddVectoredExceptionHandler(1, OnFault);
#else
    g_code = static_cast<uint8_t*>(mmap(nullptr, 4096, PROT_READ | PROT_WRITE | PROT_EXEC,
                                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
    struct sigaction sa {};
    sa.sa_sigaction = OnFault;
    sa.sa_flags = SA_SIGINFO;
    sigaction(SIGSEGV, &sa, nullptr);
#endif
    std::memcpy(g_code, kWalker, sizeof(kWalker));
    const auto walker = reinterpret_cast<Walker>(g_code);

    BbSrtRoots::Roots roots{};
    roots.sgpr[0] = 0;
    roots.sgpr[1] = 2;
    roots.count = 2;
    roots.known = true;
    const uint32_t a[4] = {0, 0, 0xaaaa, 0};
    const uint32_t b[4] = {0, 0, 0, 0xbbbb};

    // Good tables: walked as before.
    auto r = Draw(walker, roots, a, b);
    if (r.walk != BbSrtRoots::Walk::Tables || r.first != 0xaaaa || r.second != 0xbbbb || r.faults) {
        return Fail("good tables are not read", r);
    }
    // The walker alone on a null root: the faults the check saves (one per load under it).
    {
        uint32_t user_data[16] = {}; // both roots null
        uint32_t flat[32] = {};
        const int before = g_faults;
        walker(user_data, flat);
        if (g_faults - before != 2) {
            std::printf("srt-null-root-test: the bare walker took %d faults, not 2\n",
                        g_faults - before);
            return 1;
        }
    }
    // One null root: its table reads zeros, the other root's is read, no fault.
    r = Draw(walker, roots, nullptr, b);
    if (r.walk != BbSrtRoots::Walk::SomeNull || r.null_roots != 1 || r.first != 0 ||
        r.second != 0xbbbb || r.faults != 0) {
        return Fail("one null root", r);
    }
    // A pointer into the first 64 KiB is null too (Info::UdPointerNull), also with tag bits
    // above the 48 address bits the walker masks off.
    r = Draw(walker, roots, a, reinterpret_cast<const void*>(0x53c), 0xffff000000000000ull);
    if (r.walk != BbSrtRoots::Walk::SomeNull || r.null_roots != 1 || r.first != 0xaaaa ||
        r.second != 0 || r.faults != 0) {
        return Fail("a near-null tagged root", r);
    }
    // Every root null: no walk, the walker's words are zeros (not the last draw's), no fault.
    r = Draw(walker, roots, nullptr, nullptr);
    if (r.walk != BbSrtRoots::Walk::AllNull || r.null_roots != 2 || r.first != 0 ||
        r.second != 0 || r.faults != 0) {
        return Fail("every root null", r);
    }
    // After null roots, good tables are read again.
    r = Draw(walker, roots, a, b);
    if (r.walk != BbSrtRoots::Walk::Tables || r.first != 0xaaaa || r.second != 0xbbbb) {
        return Fail("good tables after null roots", r);
    }
    // Roots not known (a walker the decoder did not follow): walked as before, faults and all.
    BbSrtRoots::Roots unknown{};
    r = Draw(walker, unknown, nullptr, b);
    if (r.walk != BbSrtRoots::Walk::Tables || r.first != 0 || r.second != 0xbbbb ||
        r.faults != 1) {
        return Fail("unknown roots", r);
    }
    // A root past the user data the draw has: left to the walk.
    BbSrtRoots::Roots past{};
    past.sgpr[0] = 15;
    past.count = 1;
    past.known = true;
    uint32_t short_ud[16] = {}, walk_ud[16];
    uint32_t null_roots = 0;
    if (BbSrtRoots::Prepare(past, short_ud, 16, walk_ud, null_roots) != BbSrtRoots::Walk::Tables) {
        std::printf("srt-null-root-test: a root past the user data was judged\n");
        return 1;
    }
    std::printf("srt-null-root-test: ok\n");
    return 0;
}
