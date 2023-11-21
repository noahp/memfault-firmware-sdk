#pragma once

//! @file
//! Connectivity metrics implementation.

#ifdef __cplusplus
extern "C" {
#endif

//! Record a successful or failed sync event.
//!
//! This API can be used to count "sync" successes and failures. A "sync" has an
//! implementation-specific meaning. Some examples of sync events:
//!
//! - transferring data over BLE
//! - uploading data over MQTT
//! - sending data over a cellular modem
//!
//! Using this standard metric will enable some automatic "sync reliability"
//! analysis by the Memfault backend.
void memfault_metrics_connectivity_record_sync_success(void);
void memfault_metrics_connectivity_record_sync_failure(void);

//! Record a successful or failed Memfault sync event.
//!
//! This metric measures a specific sync type, "Memfault syncs", which are
//! uploads of data to Memfault itself.
void memfault_metrics_connectivity_record_memfault_sync_success(void);
void memfault_metrics_connectivity_record_memfault_sync_failure(void);

#ifdef __cplusplus
}
#endif
