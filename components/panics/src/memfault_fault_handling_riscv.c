//! @file
//!
//! Copyright (c) Memfault, Inc.
//! See License.txt for details
//!
//! Copyright (c) Memfault, Inc.
//! See License.txt for details
//!
//! @brief
//! Fault handling for RISC-V based architectures

#if defined(__riscv)

  #include "memfault/core/compiler.h"
  #include "memfault/core/platform/core.h"
  #include "memfault/core/reboot_tracking.h"
  #include "memfault/panics/arch/riscv/riscv.h"
  #include "memfault/panics/coredump.h"
  #include "memfault/panics/coredump_impl.h"
  #include "memfault/panics/fault_handling.h"

const sMfltCoredumpRegion *memfault_coredump_get_arch_regions(size_t *num_regions) {
  *num_regions = 0;
  return NULL;
}

static eMemfaultRebootReason s_crash_reason = kMfltRebootReason_Unknown;

static void prv_fault_handling_assert(void *pc, void *lr, eMemfaultRebootReason reason) {
  sMfltRebootTrackingRegInfo info = {
    .pc = (uint32_t)pc,
    .lr = (uint32_t)lr,
  };
  s_crash_reason = reason;
  memfault_reboot_tracking_mark_reset_imminent(s_crash_reason, &info);
}

void memfault_arch_fault_handling_assert(void *pc, void *lr, eMemfaultRebootReason reason) {
  prv_fault_handling_assert(pc, lr, reason);
}

// For non-esp-idf riscv implementations, provide a full assert handler and
// other utilities.
  #if !defined(ESP_IDF_VERSION) && defined(__ZEPHYR__)

    #include "hal/cpu_hal.h"

void memfault_platform_halt_if_debugging(void) {
  if (cpu_ll_is_debugger_attached()) {
    MEMFAULT_BREAKPOINT();
  }
}

static inline uint32_t prv_read_mstatus(void) {
  uint32_t mstatus;
  __asm volatile("csrr %0, mstatus" : "=r"(mstatus));
  return mstatus;
}

bool memfault_arch_is_inside_isr(void) {
  // Read the value of mstatus CSR
  uint32_t mstatus = prv_read_mstatus();

  // Check the MPIE (Machine Previous Interrupt Enable) bit
  // If MPIE is set, then the processor is inside an ISR
  return (mstatus & (1U << 7)) != 0;
}

static void prv_fault_handling_assert_native(void *pc, void *lr, eMemfaultRebootReason reason) {
  prv_fault_handling_assert(pc, lr, reason);

  #if MEMFAULT_ASSERT_HALT_IF_DEBUGGING_ENABLED
  memfault_platform_halt_if_debugging();
  #endif

  // dereference a null pointer to trigger fault
  *(uint32_t *)0 = 0x90;

  // We just trap'd into the fault handler logic so it should never be possible to get here but if
  // we do the best thing that can be done is rebooting the system to recover it.
  memfault_platform_reboot();
}

MEMFAULT_NO_OPT
void memfault_fault_handling_assert_extra(void *pc, void *lr, sMemfaultAssertInfo *extra_info) {
  prv_fault_handling_assert_native(pc, lr, extra_info->assert_reason);

  MEMFAULT_UNREACHABLE;
}

MEMFAULT_NO_OPT
void memfault_fault_handling_assert(void *pc, void *lr) {
  prv_fault_handling_assert_native(pc, lr, kMfltRebootReason_Assert);

  MEMFAULT_UNREACHABLE;
}

  #else
    #error "Unsupported RISC-V platform, please contact support@memfault.com"
  #endif  // !defined(ESP_IDF_VERSION) && defined(__ZEPHYR__)

void memfault_fault_handler(const sMfltRegState *regs, eMemfaultRebootReason reason) {
  if (s_crash_reason == kMfltRebootReason_Unknown) {
    // TODO confirm this works correctly- we should have the correct
    // pre-exception reg set here
    prv_fault_handling_assert((void *)regs->mepc, (void *)regs->ra, reason);
  }

  sMemfaultCoredumpSaveInfo save_info = {
    .regs = regs,
    .regs_size = sizeof(*regs),
    .trace_reason = s_crash_reason,
  };

  sCoredumpCrashInfo info = {
    .stack_address = (void *)regs->sp,
    .trace_reason = save_info.trace_reason,
    .exception_reg_state = regs,
  };
  save_info.regions = memfault_platform_coredump_get_regions(&info, &save_info.num_regions);

  const bool coredump_saved = memfault_coredump_save(&save_info);
  if (coredump_saved) {
    memfault_reboot_tracking_mark_coredump_saved();
  }
}

size_t memfault_coredump_storage_compute_size_required(void) {
  // actual values don't matter since we are just computing the size
  sMfltRegState core_regs = {0};
  sMemfaultCoredumpSaveInfo save_info = {
    .regs = &core_regs,
    .regs_size = sizeof(core_regs),
    .trace_reason = kMfltRebootReason_UnknownError,
  };

  sCoredumpCrashInfo info = {
    // we'll just pass the current stack pointer, value shouldn't matter
    .stack_address = (void *)&core_regs,
    .trace_reason = save_info.trace_reason,
    .exception_reg_state = NULL,
  };
  save_info.regions = memfault_platform_coredump_get_regions(&info, &save_info.num_regions);

  return memfault_coredump_get_save_size(&save_info);
}

#endif  // __riscv
