#include "balat_types.h"

#include <stdio.h>
#include <string.h>

const char *balat_risk_name(balat_risk_state_t state)
{
    switch (state) {
    case BALAT_RISK_INVALID:
        return "INVALID";
    case BALAT_RISK_SAFE:
        return "SAFE";
    case BALAT_RISK_CAUTION:
        return "CAUTION";
    case BALAT_RISK_DANGER:
        return "DANGER";
    case BALAT_RISK_COOLDOWN:
        return "COOLDOWN";
    default:
        return "UNKNOWN";
    }
}

typedef struct {
    balat_fault_t bit;
    const char *name;
} fault_name_t;

static const fault_name_t FAULT_NAMES[] = {
    {BALAT_FAULT_NO_FIX, "NO_FIX"},
    {BALAT_FAULT_STALE, "STALE"},
    {BALAT_FAULT_MAP, "MAP"},
    {BALAT_FAULT_CHECKSUM, "CHECKSUM"},
    {BALAT_FAULT_MALFORMED, "MALFORMED"},
    {BALAT_FAULT_BACKWARD_TIME, "BACKWARD_TIME"},
    {BALAT_FAULT_JUMP, "JUMP"},
    {BALAT_FAULT_UNCERTAIN, "UNCERTAIN"},
    {BALAT_FAULT_OUT_OF_RANGE, "OUT_OF_RANGE"},
    {BALAT_FAULT_MANUAL_DISABLE, "MANUAL_DISABLE"},
    {BALAT_FAULT_CONFIG, "CONFIG"},
    {BALAT_FAULT_GAP, "GAP"},
    {BALAT_FAULT_SPEED, "SPEED"},
    {BALAT_FAULT_CUE_DISABLED, "CUE_DISABLED"},
};

void balat_fault_format(balat_fault_t fault, char *buf, size_t len)
{
    size_t used = 0;
    bool first = true;

    if (buf == NULL || len == 0u) {
        return;
    }

    if (fault == BALAT_FAULT_NONE) {
        (void)snprintf(buf, len, "NONE");
        return;
    }

    buf[0] = '\0';
    for (size_t i = 0; i < sizeof(FAULT_NAMES) / sizeof(FAULT_NAMES[0]); ++i) {
        if ((fault & FAULT_NAMES[i].bit) == 0u) {
            continue;
        }
        int written = snprintf(buf + used, len - used, "%s%s",
                               first ? "" : "|", FAULT_NAMES[i].name);
        if (written < 0) {
            break;
        }
        if ((size_t)written >= len - used) {
            used = len - 1u;
            break;
        }
        used += (size_t)written;
        first = false;
    }
}
