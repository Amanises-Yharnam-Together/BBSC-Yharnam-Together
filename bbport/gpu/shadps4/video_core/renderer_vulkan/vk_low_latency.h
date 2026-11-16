// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: low latency for the game's frames: NVIDIA Reflex (VK_NV_low_latency2) or AMD Anti-Lag 2
// (VK_AMD_anti_lag), whichever the driver offers; the same on Windows and Linux.
//
// The latency the port adds is the time a game frame waits: for the GPU (the game runs up to a
// frame ahead of it), in the flip queue and, with frame generation, held back while the frames
// between are made. Both make the game start its next frame later, just in time for the GPU,
// instead of early and then waiting with input already read:
//   * the wait is at the start of a game frame (sceGnmSubmitDone, the game's thread), once the
//     frame before was flipped;
//   * Reflex: the driver's sleep (vkLatencySleepNV) and the steps of each frame marked with the
//     ID its presentation carries (vkSetLatencyMarkerNV: simulation, render submit, present;
//     VkLatencySubmissionPresentIdNV on the frame's GPU submissions). Boost keeps the GPU's clocks
//     up. The driver reports each frame's times back (vkGetLatencyTimingsNV): the menu shows the
//     game frames' latency, measured whether the setting is on or off;
//   * Anti-Lag 2: vkAntiLagUpdateAMD at the start of the frame (it waits there) and right before
//     the frame's presentation.
// bbport.ini low_latency: off, auto (default: on with frame generation), on, boost. Live.
// BbLatencyFrames (bbport_latency_frames.h) keeps which game frame each step belongs to.
#pragma once

#include <string>
#include <vector>
#include "common/types.h"
#include "video_core/renderer_vulkan/vk_common.h"

namespace Vulkan {

class Instance;

namespace LowLatency {

/// Device creation: the device extensions and features low latency needs, if the driver has them
/// (Instance::CreateDevice, which enables them).
struct DeviceSupport {
    bool reflex = false;   // VK_NV_low_latency2 and VK_KHR_present_id (presentId)
    bool anti_lag = false; // VK_AMD_anti_lag (antiLag)
};
DeviceSupport Probe(vk::PhysicalDevice physical, const std::vector<std::string>& extensions);

/// The presenter's device (Presenter's constructor) and its end (destructor).
void Attach(const Instance& instance);
void Detach();

/// Swapchain::Create: the latency create info to chain into VkSwapchainCreateInfoKHR (null without
/// Reflex), and the swapchain made and gone (Destroy, or retired through oldSwapchain).
const void* SwapchainCreateNext(const Instance& instance);
void SwapchainMade(const Instance& instance, vk::SwapchainKHR swapchain);
void SwapchainGone(vk::SwapchainKHR swapchain);

/// The game's thread: a flip of its frame was handed over (sceVideoOutSubmitFlip, or the EOP flip
/// of sceGnmSubmitAndFlipCommandBuffers).
void GameFrameSubmitted();
/// The game's thread: it starts its next frame (sceGnmSubmitDone): the wait.
void BeginGameFrame();

/// The GPU command thread: the game frame of the flip it prepares now (VideoOutDriver::
/// SubmitFlipInternal, in flip order), 0 when none; and that its commands are submitted.
u64 FlipTaken();
void FlipSubmitted(u64 frame);
/// The GPU command thread: the presentation ID its submissions belong to now (the next flip's
/// game frame), 0 without Reflex.
u64 SubmissionPresentId();

/// The presentation ID of game frame `frame`'s own image (game) or of the generated image `index`
/// before it; 0 without Reflex, or for no frame (presented without an ID).
u64 PresentId(u64 frame, u32 index, bool game);

/// The swap thread, around the presentation of game frame `frame`'s own image.
void BeforePresent(u64 frame);
void AfterPresent(u64 frame);

} // namespace LowLatency
} // namespace Vulkan
