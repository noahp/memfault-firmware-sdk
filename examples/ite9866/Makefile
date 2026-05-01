## Makefile for ITE9866 (ARM9, ARMv5TE) metrics serialization test ELF
##
## Usage:
##   make          — build ite9866_metrics_test.elf
##   make clean    — remove build artifacts

CC      := arm-none-eabi-gcc
SIZE    := arm-none-eabi-size

SDK_ROOT := ../..

# ARMv5TE, ARM mode, software floating-point (ARM9 has no VFP)
ARCH_FLAGS := -march=armv5te -marm -msoft-float

CFLAGS := \
  $(ARCH_FLAGS) \
  -std=c99 \
  -Os \
  -g \
  -ffunction-sections \
  -fdata-sections \
  -Wall \
  -Wextra \
  -Werror \
  -I$(SDK_ROOT)/components/include \
  -I. \
  -Isrc

LDFLAGS := \
  $(ARCH_FLAGS) \
  -T ite9866.ld \
  -nostartfiles \
  -Wl,--gc-sections \
  -specs=nosys.specs \
  -lc \
  -lgcc

BUILD_DIR := build

# Source files — SDK paths relative to this Makefile
SDK_SRCS := \
  $(SDK_ROOT)/components/metrics/src/memfault_metrics.c \
  $(SDK_ROOT)/components/metrics/src/memfault_metrics_serializer.c \
  $(SDK_ROOT)/components/metrics/src/memfault_metrics_reliability.c \
  $(SDK_ROOT)/components/core/src/memfault_event_storage.c \
  $(SDK_ROOT)/components/core/src/memfault_serializer_helper.c \
  $(SDK_ROOT)/components/core/src/memfault_batched_events.c \
  $(SDK_ROOT)/components/core/src/memfault_build_id.c \
  $(SDK_ROOT)/components/core/src/memfault_sdk_assert.c \
  $(SDK_ROOT)/components/core/src/memfault_ram_reboot_info_tracking.c \
  $(SDK_ROOT)/components/util/src/memfault_minimal_cbor.c \
  $(SDK_ROOT)/components/util/src/memfault_circular_buffer.c

APP_SRCS := src/main.c

# Map each source to an object path inside BUILD_DIR, stripping any leading
# "../../" so SDK files also land inside build/ rather than escaping it.
obj_of = $(BUILD_DIR)/$(patsubst ../../%,%,$(1:.c=.o))

SDK_OBJS := $(foreach s,$(SDK_SRCS),$(call obj_of,$(s)))
APP_OBJS := $(foreach s,$(APP_SRCS),$(call obj_of,$(s)))
OBJS     := $(SDK_OBJS) $(APP_OBJS)

TARGET := $(BUILD_DIR)/ite9866_metrics_test.elf

.PHONY: all clean

all: $(TARGET)
	$(SIZE) $<

$(TARGET): $(OBJS) ite9866.ld
	$(CC) $(LDFLAGS) $(OBJS) -o $@

# SDK sources: the real source is two levels up relative to build/<path>
$(BUILD_DIR)/components/%.o: $(SDK_ROOT)/components/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

# App sources
$(BUILD_DIR)/src/%.o: src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(BUILD_DIR)
