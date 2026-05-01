//! ITE9866 (ARM9, ARMv5TE) minimal metrics serialization test.
//!
//! This file implements all required Memfault platform dependencies for the
//! metrics + event-storage subsystems only. No coredump, no panics, no logs.
//! The resulting ELF is intended for backend analysis of metrics serialization
//! support, not for execution.

#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "memfault/core/event_storage.h"
#include "memfault/core/platform/core.h"
#include "memfault/core/platform/debug_log.h"
#include "memfault/core/platform/device_info.h"
#include "memfault/core/reboot_tracking.h"
#include "memfault/metrics/metrics.h"
#include "memfault/metrics/platform/timer.h"

// ---------------------------------------------------------------------------
// Platform: device info
// ---------------------------------------------------------------------------

void memfault_platform_get_device_info(sMemfaultDeviceInfo *info) {
  *info = (sMemfaultDeviceInfo){
    .device_serial = "ITE9866-TEST-001",
    .software_type = "ec-firmware",
    .software_version = "1.0.0",
    .hardware_version = "ite9866-evt",
  };
}

// ---------------------------------------------------------------------------
// Platform: time
// ---------------------------------------------------------------------------

uint64_t memfault_platform_get_time_since_boot_ms(void) {
  return 0;
}

// ---------------------------------------------------------------------------
// Platform: logging (no-op stubs; SDK_LOG_SAVE_DISABLE=1 so no ring buffer)
// ---------------------------------------------------------------------------

void memfault_platform_log(eMemfaultPlatformLogLevel level, const char *fmt, ...) {
  (void)level;
  (void)fmt;
}

void memfault_platform_log_raw(const char *fmt, ...) {
  (void)fmt;
}

void memfault_platform_hexdump(eMemfaultPlatformLogLevel level, const void *data,
                               size_t data_len) {
  (void)level;
  (void)data;
  (void)data_len;
}

// ---------------------------------------------------------------------------
// Platform: halt (called by SDK assert; no Cortex-M debug registers on ARM9)
// ---------------------------------------------------------------------------

void memfault_platform_halt_if_debugging(void) {
  // No DHCSR on ARM9 — nothing to do
}

// ---------------------------------------------------------------------------
// Platform: reboot
// ---------------------------------------------------------------------------

MEMFAULT_NORETURN void memfault_platform_reboot(void) {
  while (1) {
  }
}

// ---------------------------------------------------------------------------
// Platform: metrics timer (fires the heartbeat callback periodically)
// ---------------------------------------------------------------------------

bool memfault_platform_metrics_timer_boot(uint32_t period_sec,
                                          MemfaultPlatformTimerCallback *callback) {
  (void)period_sec;
  (void)callback;
  // No real timer on this test build — heartbeat will be triggered manually.
  return true;
}

// ---------------------------------------------------------------------------
// Platform: boot
// ---------------------------------------------------------------------------

// Event storage backing buffer — sized to hold at least one worst-case heartbeat.
static uint8_t s_event_storage[512];

// Noinit region used by reboot tracking to survive warm resets.
static uint8_t s_reboot_tracking[MEMFAULT_REBOOT_TRACKING_REGION_SIZE];

int memfault_platform_boot(void) {
  const sResetBootupInfo bootup_info = {
    .reset_reason_reg = 0,
  };
  memfault_reboot_tracking_boot(s_reboot_tracking, &bootup_info);

  const sMemfaultEventStorageImpl *storage =
    memfault_events_storage_boot(s_event_storage, sizeof(s_event_storage));

  const sMemfaultMetricBootInfo metrics_boot = {
    .unexpected_reboot_count = 0,
  };
  memfault_metrics_boot(storage, &metrics_boot);

  return 0;
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

int main(void) {
  memfault_platform_boot();

  // Set some representative EC metrics
  MEMFAULT_METRIC_SET_UNSIGNED(uptime_ms, 300000);
  MEMFAULT_METRIC_SET_SIGNED(cpu_temp_c, 42);
  MEMFAULT_METRIC_SET_UNSIGNED(fan_speed_rpm, 3200);

  MEMFAULT_METRIC_TIMER_START(ec_sleep_ms);
  MEMFAULT_METRIC_TIMER_STOP(ec_sleep_ms);

  // Serialize the heartbeat into event storage
  memfault_metrics_heartbeat_debug_trigger();

  return 0;
}
