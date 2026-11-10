// The swapchain's present mode (gpu/shim/bbport_present_mode.h). No game, Vulkan device or window.
//   ninja -C out/gpu present-mode-test && out/gpu/present-mode-test.exe
#include <cassert>
#include <cstdio>
#include <string_view>
#include <vector>
#include "bbport_present_mode.h"

using namespace BbPresentMode;

int main() {
    // The launcher's Presentation choices, all four (FIFO Relaxed used to be "unknown").
    assert(Requested("Mailbox") == Mailbox);
    assert(Requested("Fifo") == Fifo);
    assert(Requested("FifoRelaxed") == FifoRelaxed);
    assert(Requested("Immediate") == Immediate);
    assert(Requested("") == -1);
    assert(Requested("mailbox") == -1);

    // NVIDIA on Windows has them all: what was asked for.
    const std::vector<int> all{Immediate, Mailbox, Fifo, FifoRelaxed};
    for (const int mode : all) {
        assert(Choose(mode, all) == mode);
    }

    // AMD's Windows driver has no Mailbox (the player's log of 2026-10-27, AMD Radeon Graphics:
    // "Requested present mode Mailbox is not supported, falling back to Fifo", nine sessions of
    // nine). FIFO is V-Sync: a late frame waits a whole refresh, 30 FPS on a 60 Hz monitor. The
    // default must not end up there while a mode that lets a late frame through is offered.
    const std::vector<int> amd{Immediate, Fifo, FifoRelaxed};
    assert(Choose(Mailbox, amd) == FifoRelaxed);
    assert(Choose(Mailbox, std::vector<int>{Immediate, Fifo}) == Immediate);
    assert(Choose(Mailbox, std::vector<int>{Fifo}) == Fifo);
    // A player who chose V-Sync keeps it.
    assert(Choose(Fifo, amd) == Fifo);
    assert(Choose(FifoRelaxed, amd) == FifoRelaxed);
    assert(Choose(FifoRelaxed, std::vector<int>{Immediate, Mailbox, Fifo}) == Fifo);
    assert(Choose(Immediate, std::vector<int>{Fifo, FifoRelaxed}) == FifoRelaxed);
    // An unknown setting is the default's.
    assert(Choose(-1, amd) == FifoRelaxed);
    assert(Choose(-1, all) == Mailbox);
    // Nothing reported: FIFO, which the Vulkan spec guarantees.
    assert(Choose(Mailbox, std::vector<int>{}) == Fifo);
    assert(std::string_view{Name(FifoRelaxed)} == "FifoRelaxed");
    std::printf("present mode: ok\n");
    return 0;
}
