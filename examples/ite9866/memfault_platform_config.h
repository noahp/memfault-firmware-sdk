#pragma once

// Minimal config for ITE9866 ARM9 (ARMv5TE) metrics-only build.
// No coredump, no logs, no battery/connectivity.

#define MEMFAULT_METRICS_BATTERY_ENABLE 0
#define MEMFAULT_METRICS_CONNECTIVITY_CONNECTED_TIME 0
#define MEMFAULT_PLATFORM_METRICS_CONNECTIVITY_BOOT 0

// Disable log saving and log metrics to avoid pulling in the log ring buffer
#define MEMFAULT_SDK_LOG_SAVE_DISABLE 1
#define MEMFAULT_METRICS_LOGS_ENABLE 0

// Don't embed a build ID in events; simplifies the build
#define MEMFAULT_EVENT_INCLUDE_BUILD_ID 0
#define MEMFAULT_USE_GNU_BUILD_ID 0
