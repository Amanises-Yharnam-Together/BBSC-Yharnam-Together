// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: low latency for the game's frames (vk_low_latency.h).

#include "video_core/renderer_vulkan/vk_low_latency.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include "bbport_latency_frames.h"
#include "bbport_settings.h"
#include "common/logging/log.h"
#include "core/emulator_settings.h"
#include "video_core/renderer_vulkan/vk_instance.h"

namespace Vulkan::LowLatency {

namespace {

using namespace BbLatencyFrames;
using Clock = std::chrono::steady_clock;

// Read without the lock (PresentId, SubmissionPresentId's early out).
std::atomic<bool> reflex{false};

// Everything below: under `mutex`.
std::mutex mutex;
bool attached = false;
bool anti_lag = false;
VkDevice device = VK_NULL_HANDLE;
VkSwapchainKHR swapchain = VK_NULL_HANDLE; // the current one (Reflex's calls name it)
VkSemaphore sleep_semaphore = VK_NULL_HANDLE; // timeline, signalled when the driver's sleep ends
u64 sleep_value = 0;
u32 sleep_timeouts = 0;
bool sleep_broken = false; // the driver's sleep never ended: no more sleeping this session
Frames frames;
// What the driver was told: Reflex per swapchain (-1: not yet), Anti-Lag once.
int reflex_told = -1;
u32 reflex_interval_told = 0;
int anti_lag_told = -1;
LatencyAverage average;
Clock::time_point next_report{};
Clock::time_point next_log{};
double log_total_ms = 0.0;
u32 log_frames = 0;

constexpr auto SleepTimeout = std::chrono::milliseconds(200);
constexpr u32 SleepTimeoutsAllowed = 3;

Active Wanted() {
    const auto& s = BbSettings::Get();
    const bool frame_generation = s.frame_generation.load(std::memory_order_relaxed) &&
                                  s.upscaler.load(std::memory_order_relaxed) != BbSettings::UpscalerOff;
    return ActiveFor(s.low_latency.load(std::memory_order_relaxed), frame_generation);
}

/// The frame limit (the swap thread's pacing), 0 none: the driver paces the game to it instead.
u32 WantedFps() {
    return EmulatorSettings.GetFrameLimit();
}

void AttachLocked(const Instance& instance) {
    if (attached) {
        return;
    }
    attached = true;
    device = static_cast<VkDevice>(instance.GetDevice());
    bool has_reflex = instance.IsLowLatencyReflexSupported();
    anti_lag = instance.IsAntiLagSupported();
    if (has_reflex) {
        VkSemaphoreTypeCreateInfo type{};
        type.sType = VK_STRUCTURE_TYPE_SEMAPHORE_TYPE_CREATE_INFO;
        type.semaphoreType = VK_SEMAPHORE_TYPE_TIMELINE;
        type.initialValue = 0;
        VkSemaphoreCreateInfo info{};
        info.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;
        info.pNext = &type;
        if (VULKAN_HPP_DEFAULT_DISPATCHER.vkCreateSemaphore(device, &info, nullptr,
                                                            &sleep_semaphore) != VK_SUCCESS) {
            sleep_semaphore = VK_NULL_HANDLE;
            has_reflex = false;
        }
    }
    reflex.store(has_reflex, std::memory_order_relaxed);
    auto& s = BbSettings::Get();
    s.low_latency_kind.store(has_reflex ? BbSettings::LowLatencyReflex
                             : anti_lag ? BbSettings::LowLatencyAntiLag
                                        : BbSettings::LowLatencyNone,
                             std::memory_order_relaxed);
    std::printf("Low latency: %s\n", has_reflex ? "NVIDIA Reflex available (VK_NV_low_latency2)"
                                     : anti_lag ? "AMD Anti-Lag 2 available (VK_AMD_anti_lag)"
                                                : "not offered by this GPU's driver");
}

#ifdef VK_NV_low_latency2
void Mark(u64 frame, VkLatencyMarkerNV marker) {
    if (!reflex.load(std::memory_order_relaxed) || swapchain == VK_NULL_HANDLE || frame == 0) {
        return;
    }
    VkSetLatencyMarkerInfoNV info{};
    info.sType = VK_STRUCTURE_TYPE_SET_LATENCY_MARKER_INFO_NV;
    info.presentID = BbLatencyFrames::PresentId(frame, 0, true);
    info.marker = marker;
    VULKAN_HPP_DEFAULT_DISPATCHER.vkSetLatencyMarkerNV(device, swapchain, &info);
}
#endif

#ifdef VK_AMD_anti_lag
void AntiLagUpdate(VkAntiLagModeAMD mode, VkAntiLagStageAMD stage, u64 frame) {
    VkAntiLagPresentationInfoAMD presentation{};
    presentation.sType = VK_STRUCTURE_TYPE_ANTI_LAG_PRESENTATION_INFO_AMD;
    presentation.stage = stage;
    presentation.frameIndex = frame;
    VkAntiLagDataAMD data{};
    data.sType = VK_STRUCTURE_TYPE_ANTI_LAG_DATA_AMD;
    data.mode = mode;
    data.maxFPS = mode == VK_ANTI_LAG_MODE_ON_AMD ? WantedFps() : 0;
    data.pPresentationInfo = mode == VK_ANTI_LAG_MODE_ON_AMD ? &presentation : nullptr;
    VULKAN_HPP_DEFAULT_DISPATCHER.vkAntiLagUpdateAMD(device, &data);
}
#endif

/// Under the lock: the driver told what the setting asks for now (it changes live).
void ApplyModes(Active active) {
    auto& s = BbSettings::Get();
    const bool any = reflex.load(std::memory_order_relaxed) || anti_lag;
    s.low_latency_running.store(any ? int(active) : int(ActiveOff), std::memory_order_relaxed);
#ifdef VK_NV_low_latency2
    if (reflex.load(std::memory_order_relaxed) && swapchain != VK_NULL_HANDLE) {
        const u32 interval = active != ActiveOff ? MinimumIntervalUs(int(WantedFps())) : 0u;
        if (reflex_told != int(active) || reflex_interval_told != interval) {
            VkLatencySleepModeInfoNV mode{};
            mode.sType = VK_STRUCTURE_TYPE_LATENCY_SLEEP_MODE_INFO_NV;
            mode.lowLatencyMode = active != ActiveOff;
            mode.lowLatencyBoost = active == ActiveBoost;
            mode.minimumIntervalUs = interval;
            const VkResult result =
                VULKAN_HPP_DEFAULT_DISPATCHER.vkSetLatencySleepModeNV(device, swapchain, &mode);
            if (reflex_told != int(active)) {
                std::printf("Low latency: NVIDIA Reflex %s%s (%d)\n",
                            active == ActiveOff ? "off" : "on",
                            active == ActiveBoost ? " with boost" : "", int(result));
            }
            reflex_told = int(active);
            reflex_interval_told = interval;
        }
    }
#endif
#ifdef VK_AMD_anti_lag
    if (anti_lag && anti_lag_told != (active != ActiveOff ? 1 : 0)) {
        if (active == ActiveOff && anti_lag_told == 1) {
            AntiLagUpdate(VK_ANTI_LAG_MODE_OFF_AMD, VK_ANTI_LAG_STAGE_INPUT_AMD, 0);
        }
        anti_lag_told = active != ActiveOff ? 1 : 0;
        std::printf("Low latency: AMD Anti-Lag 2 %s\n", anti_lag_told ? "on" : "off");
    }
#endif
}

/// Without the lock: until the driver's sleep ends (it signals `value`).
bool WaitForSleep(VkDevice waiting_device, VkSemaphore semaphore, u64 value) {
    VkSemaphoreWaitInfo wait{};
    wait.sType = VK_STRUCTURE_TYPE_SEMAPHORE_WAIT_INFO;
    wait.semaphoreCount = 1;
    wait.pSemaphores = &semaphore;
    wait.pValues = &value;
    const u64 timeout = u64(std::chrono::nanoseconds(SleepTimeout).count());
    return VULKAN_HPP_DEFAULT_DISPATCHER.vkWaitSemaphores(waiting_device, &wait, timeout) ==
           VK_SUCCESS;
}

/// Under the lock, once a second: the frames' times the driver measured, for the menu and the log.
void ReadTimings() {
#if defined(VK_NV_low_latency2) && VK_HEADER_VERSION >= 280
    if (!reflex.load(std::memory_order_relaxed) || swapchain == VK_NULL_HANDLE) {
        return;
    }
    const auto now = Clock::now();
    if (now < next_report) {
        return;
    }
    next_report = now + std::chrono::seconds(1);
    std::array<VkLatencyTimingsFrameReportNV, 64> reports{};
    for (auto& report : reports) {
        report.sType = VK_STRUCTURE_TYPE_LATENCY_TIMINGS_FRAME_REPORT_NV;
    }
    VkGetLatencyMarkerInfoNV info{};
    info.sType = VK_STRUCTURE_TYPE_GET_LATENCY_MARKER_INFO_NV;
    info.timingCount = u32(reports.size());
    info.pTimings = reports.data();
    VULKAN_HPP_DEFAULT_DISPATCHER.vkGetLatencyTimingsNV(device, swapchain, &info);
    const u32 count = std::min<u32>(info.timingCount, u32(reports.size()));
    // Oldest first: the average skips IDs it has counted.
    std::sort(reports.begin(), reports.begin() + count,
              [](const auto& a, const auto& b) { return a.presentID < b.presentID; });
    for (u32 i = 0; i < count; ++i) {
        const auto& r = reports[i];
        average.Add({r.presentID, r.simStartTimeUs, r.presentEndTimeUs, r.gpuRenderEndTimeUs});
    }
    u32 frames_measured = 0;
    const double ms = average.Take(&frames_measured);
    if (frames_measured) {
        BbSettings::Get().low_latency_ms.store(float(ms), std::memory_order_relaxed);
        log_total_ms += ms * frames_measured;
        log_frames += frames_measured;
    }
    if (now >= next_log) {
        next_log = now + std::chrono::seconds(10);
        if (log_frames) {
            std::printf("Low latency: NVIDIA Reflex %s, game frames %.1f ms from their start to "
                        "the display (%u frames)\n",
                        reflex_told == ActiveOff ? "off" : reflex_told == ActiveBoost ? "on, boost" : "on",
                        log_total_ms / log_frames, log_frames);
        }
        log_total_ms = 0.0;
        log_frames = 0;
    }
#endif
}

} // namespace

DeviceSupport Probe(vk::PhysicalDevice physical, const std::vector<std::string>& extensions) {
    DeviceSupport support;
    // BB_LOW_LATENCY_DEVICE=0: neither extension enabled (a driver that misbehaves with them).
    if (const char* env = std::getenv("BB_LOW_LATENCY_DEVICE"); env && env[0] == '0') {
        return support;
    }
    const auto has = [&](const char* name) {
        return std::find(extensions.begin(), extensions.end(), name) != extensions.end();
    };
    const VkPhysicalDevice handle = static_cast<VkPhysicalDevice>(physical);
#ifdef VK_NV_low_latency2
    if (has(VK_NV_LOW_LATENCY_2_EXTENSION_NAME) && has(VK_KHR_PRESENT_ID_EXTENSION_NAME)) {
        VkPhysicalDevicePresentIdFeaturesKHR present_id{};
        present_id.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_ID_FEATURES_KHR;
        VkPhysicalDeviceFeatures2 features{};
        features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2;
        features.pNext = &present_id;
        VULKAN_HPP_DEFAULT_DISPATCHER.vkGetPhysicalDeviceFeatures2(handle, &features);
        support.reflex = present_id.presentId == VK_TRUE;
    }
#endif
#ifdef VK_AMD_anti_lag
    if (has(VK_AMD_ANTI_LAG_EXTENSION_NAME)) {
        VkPhysicalDeviceAntiLagFeaturesAMD anti_lag_features{};
        anti_lag_features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ANTI_LAG_FEATURES_AMD;
        VkPhysicalDeviceFeatures2 features{};
        features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2;
        features.pNext = &anti_lag_features;
        VULKAN_HPP_DEFAULT_DISPATCHER.vkGetPhysicalDeviceFeatures2(handle, &features);
        support.anti_lag = anti_lag_features.antiLag == VK_TRUE;
    }
#endif
    (void)has;
    (void)handle;
    return support;
}

void Attach(const Instance& instance) {
    std::scoped_lock lock{mutex};
    AttachLocked(instance);
}

void Detach() {
    std::scoped_lock lock{mutex};
    if (sleep_semaphore != VK_NULL_HANDLE && device != VK_NULL_HANDLE) {
        VULKAN_HPP_DEFAULT_DISPATCHER.vkDestroySemaphore(device, sleep_semaphore, nullptr);
    }
    sleep_semaphore = VK_NULL_HANDLE;
    swapchain = VK_NULL_HANDLE;
    device = VK_NULL_HANDLE;
    anti_lag = false;
    reflex.store(false, std::memory_order_relaxed);
}

const void* SwapchainCreateNext(const Instance& instance) {
#ifdef VK_NV_low_latency2
    static VkSwapchainLatencyCreateInfoNV latency{};
    std::scoped_lock lock{mutex};
    AttachLocked(instance);
    if (!reflex.load(std::memory_order_relaxed)) {
        return nullptr;
    }
    latency.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_LATENCY_CREATE_INFO_NV;
    latency.pNext = nullptr;
    latency.latencyModeEnable = VK_TRUE;
    return &latency;
#else
    Attach(instance);
    return nullptr;
#endif
}

void SwapchainMade(const Instance& instance, vk::SwapchainKHR made) {
    std::scoped_lock lock{mutex};
    AttachLocked(instance);
    if (!reflex.load(std::memory_order_relaxed)) {
        return;
    }
    swapchain = static_cast<VkSwapchainKHR>(made);
    reflex_told = -1; // a new swapchain starts with low latency off
    ApplyModes(Wanted());
}

void SwapchainGone(vk::SwapchainKHR gone) {
    std::scoped_lock lock{mutex};
    if (swapchain == static_cast<VkSwapchainKHR>(gone)) {
        swapchain = VK_NULL_HANDLE;
    }
}

void GameFrameSubmitted() {
    std::scoped_lock lock{mutex};
    if (device == VK_NULL_HANDLE) {
        return;
    }
    const u64 frame = frames.Submitted();
#ifdef VK_NV_low_latency2
    Mark(frame, VK_LATENCY_MARKER_SIMULATION_END_NV);
    Mark(frame, VK_LATENCY_MARKER_RENDERSUBMIT_START_NV);
#else
    (void)frame;
#endif
}

void BeginGameFrame() {
    std::unique_lock lock{mutex};
    if (device == VK_NULL_HANDLE) {
        return;
    }
    const bool flipped = frames.Begin();
    const Active active = Wanted();
    ApplyModes(active);
    if (!flipped) {
        return;
    }
    const u64 frame = frames.Current();
#ifdef VK_NV_low_latency2
    if (reflex.load(std::memory_order_relaxed) && swapchain != VK_NULL_HANDLE) {
        if (active != ActiveOff && !sleep_broken) {
            VkLatencySleepInfoNV info{};
            info.sType = VK_STRUCTURE_TYPE_LATENCY_SLEEP_INFO_NV;
            info.signalSemaphore = sleep_semaphore;
            info.value = ++sleep_value;
            const VkResult result =
                VULKAN_HPP_DEFAULT_DISPATCHER.vkLatencySleepNV(device, swapchain, &info);
            if (result == VK_SUCCESS) {
                const VkDevice waiting_device = device;
                const VkSemaphore semaphore = sleep_semaphore;
                lock.unlock();
                const bool woke = WaitForSleep(waiting_device, semaphore, info.value);
                lock.lock();
                if (device == VK_NULL_HANDLE) {
                    return;
                }
                if (woke) {
                    sleep_timeouts = 0;
                } else if (++sleep_timeouts >= SleepTimeoutsAllowed) {
                    sleep_broken = true;
                    std::printf("Low latency: NVIDIA Reflex's sleep did not end %u times in a row: "
                                "no more sleeping this session\n",
                                sleep_timeouts);
                }
            }
        }
        Mark(frame, VK_LATENCY_MARKER_SIMULATION_START_NV);
        Mark(frame, VK_LATENCY_MARKER_INPUT_SAMPLE_NV);
    }
#endif
#ifdef VK_AMD_anti_lag
    if (anti_lag && active != ActiveOff) {
        // It waits here: without the lock, so the GPU and swap threads go on.
        lock.unlock();
        AntiLagUpdate(VK_ANTI_LAG_MODE_ON_AMD, VK_ANTI_LAG_STAGE_INPUT_AMD, frame);
    }
#endif
}

u64 FlipTaken() {
    std::scoped_lock lock{mutex};
    if (device == VK_NULL_HANDLE) {
        return 0;
    }
    return frames.Take();
}

void FlipSubmitted(u64 frame) {
#ifdef VK_NV_low_latency2
    if (frame == 0 || !reflex.load(std::memory_order_relaxed)) {
        return;
    }
    std::scoped_lock lock{mutex};
    Mark(frame, VK_LATENCY_MARKER_RENDERSUBMIT_END_NV);
#else
    (void)frame;
#endif
}

u64 SubmissionPresentId() {
    if (!reflex.load(std::memory_order_relaxed)) {
        return 0;
    }
    std::scoped_lock lock{mutex};
    return BbLatencyFrames::PresentId(frames.Recording(), 0, true);
}

u64 PresentId(u64 frame, u32 index, bool game) {
    if (!reflex.load(std::memory_order_relaxed)) {
        return 0;
    }
    return BbLatencyFrames::PresentId(frame, index, game);
}

void BeforePresent(u64 frame) {
    if (frame == 0) {
        return;
    }
    std::scoped_lock lock{mutex};
    if (device == VK_NULL_HANDLE) {
        return;
    }
#ifdef VK_NV_low_latency2
    Mark(frame, VK_LATENCY_MARKER_PRESENT_START_NV);
#endif
#ifdef VK_AMD_anti_lag
    if (anti_lag && anti_lag_told == 1) {
        AntiLagUpdate(VK_ANTI_LAG_MODE_ON_AMD, VK_ANTI_LAG_STAGE_PRESENT_AMD, frame);
    }
#endif
}

void AfterPresent(u64 frame) {
    if (frame == 0) {
        return;
    }
    std::scoped_lock lock{mutex};
    if (device == VK_NULL_HANDLE) {
        return;
    }
#ifdef VK_NV_low_latency2
    Mark(frame, VK_LATENCY_MARKER_PRESENT_END_NV);
#endif
    ReadTimings();
}

} // namespace Vulkan::LowLatency
