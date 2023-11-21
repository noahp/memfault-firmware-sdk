//! @file
//! Connectivity metrics implementation.

#include "memfault/metrics/connectivity.h"

// non-module includes below

#include "memfault/metrics/metrics.h"

// Sync success/failure metrics. The metrics add return code is ignored, this
// should not fail, but there's no action to take if it does.

#if MEMFAULT_METRICS_SYNC_SUCCESS
void memfault_metrics_connectivity_record_sync_success(void) {
  (void)MEMFAULT_HEARTBEAT_ADD(sync_successful, 1);
}

void memfault_metrics_connectivity_record_sync_failure(void) {
  (void)MEMFAULT_HEARTBEAT_ADD(sync_failure, 1);
}
#endif  // MEMFAULT_METRICS_SYNC_SUCCESS

#if MEMFAULT_METRICS_MEMFAULT_SYNC_SUCCESS
void memfault_metrics_connectivity_record_memfault_sync_success(void) {
  (void)MEMFAULT_HEARTBEAT_ADD(sync_memfault_successful, 1);
}

void memfault_metrics_connectivity_record_memfault_sync_failure(void) {
  (void)MEMFAULT_HEARTBEAT_ADD(memfault_sync_failure, 1);
}
#endif
