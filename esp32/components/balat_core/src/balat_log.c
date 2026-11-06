#include "balat_log.h"

#include <stdio.h>

size_t balat_log_format_csv(const balat_engine_status_t *status,
                            const char *event,
                            char *buffer,
                            size_t buffer_len)
{
    int written;
    char faults[160];

    if (buffer == NULL || buffer_len == 0u) {
        return 0u;
    }
    if (status == NULL) {
        written = snprintf(buffer, buffer_len, "event=INVALID_LOG");
    } else {
        balat_fault_format(status->fault, faults, sizeof(faults));
        written = snprintf(
            buffer, buffer_len,
            "event=%s,rx_seq=%lu,fix_seq=%lu,risk=%s,fault=%s,fix_valid=%u,"
            "stale=%u,map_valid=%u,x_cm=%ld,y_cm=%ld,dist2_cm2=%lld,seg=%u,"
            "closest_x_cm=%ld,closest_y_cm=%ld,approaching=%u,vx_cm_s=%ld,"
            "vy_cm_s=%ld,speed2_cm2_s2=%lld,uncertainty_cm=%lu,cue_request=%u,"
            "cue_active=%u,cooldown=%u,cue_duration_ms=%lu,age_ms=%lu\n",
            event == NULL ? "DECISION" : event,
            (unsigned long)status->rx_seq, (unsigned long)status->fix_seq,
            balat_risk_name(status->risk_state), faults,
            status->fix_valid ? 1u : 0u, status->stale ? 1u : 0u,
            status->map_valid ? 1u : 0u, (long)status->x_cm,
            (long)status->y_cm, (long long)status->dist2_cm2,
            (unsigned)status->segment_id, (long)status->closest_x_cm,
            (long)status->closest_y_cm, status->approaching ? 1u : 0u,
            (long)status->vx_cm_s, (long)status->vy_cm_s,
            (long long)status->speed2_cm2_s2,
            (unsigned long)status->uncertainty_cm,
            status->cue_request ? 1u : 0u, status->cue_active ? 1u : 0u,
            status->cooldown ? 1u : 0u,
            (unsigned long)status->cue_duration_ms,
            (unsigned long)status->age_ms);
    }
    if (written < 0) {
        buffer[0] = '\0';
        return 0u;
    }
    if ((size_t)written >= buffer_len) {
        return buffer_len - 1u;
    }
    return (size_t)written;
}
