#ifndef BALAT_TYPES_H
#define BALAT_TYPES_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define BALAT_FW_VERSION "esp32c3-0.1.0"
#define BALAT_MAP_VERSION 1u
#define BALAT_MAX_SEGMENTS 256u
#define BALAT_MAX_COORD_CM 1000000
#define BALAT_NMEA_MAX_LEN 128u

typedef enum {
    BALAT_RISK_INVALID = 0,
    BALAT_RISK_SAFE = 1,
    BALAT_RISK_CAUTION = 2,
    BALAT_RISK_DANGER = 3,
    BALAT_RISK_COOLDOWN = 4
} balat_risk_state_t;

typedef uint32_t balat_fault_t;

enum {
    BALAT_FAULT_NONE = 0u,
    BALAT_FAULT_NO_FIX = 1u << 0,
    BALAT_FAULT_STALE = 1u << 1,
    BALAT_FAULT_MAP = 1u << 2,
    BALAT_FAULT_CHECKSUM = 1u << 3,
    BALAT_FAULT_MALFORMED = 1u << 4,
    BALAT_FAULT_BACKWARD_TIME = 1u << 5,
    BALAT_FAULT_JUMP = 1u << 6,
    BALAT_FAULT_UNCERTAIN = 1u << 7,
    BALAT_FAULT_OUT_OF_RANGE = 1u << 8,
    BALAT_FAULT_MANUAL_DISABLE = 1u << 9,
    BALAT_FAULT_CONFIG = 1u << 10,
    BALAT_FAULT_GAP = 1u << 11,
    BALAT_FAULT_SPEED = 1u << 12,
    BALAT_FAULT_CUE_DISABLED = 1u << 13
};

const char *balat_risk_name(balat_risk_state_t state);

void balat_fault_format(balat_fault_t fault, char *buf, size_t len);

#endif
