

#include "CppUTest/MemoryLeakDetectorMallocMacros.h"
#include "CppUTest/MemoryLeakDetectorNewMacros.h"
#include "CppUTest/TestHarness.h"
#include "CppUTestExt/MockSupport.h"
#include "comparators/comparator_memfault_metric_ids.hpp"
#include "memfault/metrics/connectivity.h"
#include "memfault/metrics/metrics.h"

static MemfaultMetricIdsComparator s_metric_id_comparator;

// These have to have global scope, so the test teardown can access them
static MemfaultMetricId sync_successful_key = MEMFAULT_METRICS_KEY(sync_successful);
static MemfaultMetricId sync_failure_key = MEMFAULT_METRICS_KEY(sync_failure);
static MemfaultMetricId memfault_sync_successful_key =
  MEMFAULT_METRICS_KEY(sync_memfault_successful);
static MemfaultMetricId memfault_sync_failure_key = MEMFAULT_METRICS_KEY(memfault_sync_failure);

// clang-format off
TEST_GROUP(MemfaultMetricsConnectivity){
  void setup() {
    mock().strictOrder();
    mock().installComparator("MemfaultMetricId", s_metric_id_comparator);
  }
  void teardown() {
    mock().checkExpectations();
    mock().removeAllComparatorsAndCopiers();
    mock().clear();
  }
};
// clang-format on

TEST(MemfaultMetricsConnectivity, Test_SyncMetrics) {
  // call the basic functions
  mock()
    .expectOneCall("memfault_metrics_heartbeat_add")
    .withParameterOfType("MemfaultMetricId", "key", &sync_successful_key)
    .withParameter("amount", 1)
    .andReturnValue(0);
  memfault_metrics_connectivity_record_sync_success();

  mock()
    .expectOneCall("memfault_metrics_heartbeat_add")
    .withParameterOfType("MemfaultMetricId", "key", &sync_failure_key)
    .withParameter("amount", 1)
    .andReturnValue(0);
  memfault_metrics_connectivity_record_sync_failure();

  mock()
    .expectOneCall("memfault_metrics_heartbeat_add")
    .withParameterOfType("MemfaultMetricId", "key", &memfault_sync_successful_key)
    .withParameter("amount", 1)
    .andReturnValue(0);
  memfault_metrics_connectivity_record_memfault_sync_success();

  mock()
    .expectOneCall("memfault_metrics_heartbeat_add")
    .withParameterOfType("MemfaultMetricId", "key", &memfault_sync_failure_key)
    .withParameter("amount", 1)
    .andReturnValue(0);
  memfault_metrics_connectivity_record_memfault_sync_failure();
}
