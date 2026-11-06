#include "balat_gate.h"

#include <string.h>

static balat_gated_fix_t reject(balat_fault_t fault)
{
    balat_gated_fix_t result;

    memset(&result, 0, sizeof(result));
    result.accepted = false;
    result.fault = fault;
    return result;
}

static balat_gated_fix_t accept(const balat_gate_state_t *state,
                                bool gap,
                                balat_fault_t fault)
{
    balat_gated_fix_t result;

    memset(&result, 0, sizeof(result));
    result.accepted = true;
    result.gap = gap;
    result.fault = fault;
    result.fix_seq = state->fix_seq;
    result.x_cm = state->x_cm;
    result.y_cm = state->y_cm;
    result.lat_deg7 = state->lat_deg7;
    result.lon_deg7 = state->lon_deg7;
    result.utc_ms = state->utc_ms;
    result.utc_valid = state->utc_valid;
    result.received_ms = state->received_ms;
    result.uncertainty_cm = state->uncertainty_cm;
    result.quality = state->quality;
    return result;
}

void balat_gate_init(balat_gate_state_t *state)
{
    if (state == NULL) {
        return;
    }
    memset(state, 0, sizeof(*state));
}

bool balat_gate_is_stale(const balat_gate_state_t *state,
                         uint32_t now_ms,
                         uint32_t stale_ms)
{
    if (state == NULL || !state->have_fix) {
        return true;
    }
    return (uint32_t)(now_ms - state->received_ms) > stale_ms;
}

uint32_t balat_gate_age_ms(const balat_gate_state_t *state, uint32_t now_ms)
{
    if (state == NULL || !state->have_fix) {
        return UINT32_MAX;
    }
    return (uint32_t)(now_ms - state->received_ms);
}

uint32_t balat_gate_uncertainty(const balat_gate_config_t *config,
                                uint16_t hdop_centi,
                                bool hdop_valid)
{
    uint32_t uncertainty;

    if (config == NULL) {
        return UINT32_MAX;
    }

    uncertainty = config->base_uncertainty_cm;
    if (hdop_valid) {
        uncertainty += ((uint32_t)hdop_centi * config->hdop_scale_cm) / 100u;
    }
    return uncertainty;
}

balat_gated_fix_t balat_gate_process_rmc(balat_gate_state_t *state,
                                         const balat_nmea_sentence_t *rmc,
                                         uint8_t gga_quality,
                                         uint16_t gga_hdop_centi,
                                         bool gga_fresh,
                                         const balat_coord_t *coord,
                                         uint32_t now_ms,
                                         const balat_gate_config_t *config)
{
    uint32_t uncertainty;
    uint8_t quality;
    int32_t x_cm;
    int32_t y_cm;
    balat_gated_fix_t result;

    if (state == NULL || rmc == NULL || coord == NULL || config == NULL ||
        rmc->kind != BALAT_NMEA_RMC) {
        return reject(BALAT_FAULT_MALFORMED);
    }

    if (!rmc->fix_valid) {
        return reject(BALAT_FAULT_NO_FIX);
    }
    if (config->require_utc && !rmc->utc_valid) {
        return reject(BALAT_FAULT_MALFORMED);
    }

    if (gga_fresh && gga_quality == 0u) {
        return reject(BALAT_FAULT_NO_FIX);
    }

    quality = gga_fresh ? gga_quality : rmc->quality;
    if (quality == 0u) {
        return reject(BALAT_FAULT_NO_FIX);
    }

    if (rmc->speed_kn100 > config->max_speed_kn100) {
        return reject(BALAT_FAULT_SPEED);
    }

    uncertainty = balat_gate_uncertainty(config, gga_hdop_centi, gga_fresh);
    if (uncertainty > config->max_uncertainty_cm) {
        return reject(BALAT_FAULT_UNCERTAIN);
    }

    if (!balat_coord_convert(coord, rmc->lat_deg7, rmc->lon_deg7, &x_cm,
                             &y_cm)) {
        return reject(BALAT_FAULT_OUT_OF_RANGE);
    }

    result = balat_gate_process_local(state, x_cm, y_cm, rmc->utc_ms,
                                      rmc->utc_valid, quality,
                                      rmc->speed_kn100, uncertainty, now_ms,
                                      config);
    if (result.accepted) {
        state->lat_deg7 = rmc->lat_deg7;
        state->lon_deg7 = rmc->lon_deg7;
        result.lat_deg7 = rmc->lat_deg7;
        result.lon_deg7 = rmc->lon_deg7;
        result.speed_kn100 = rmc->speed_kn100;
    }
    return result;
}

balat_gated_fix_t balat_gate_process_local(balat_gate_state_t *state,
                                           int32_t x_cm,
                                           int32_t y_cm,
                                           uint64_t utc_ms,
                                           bool utc_valid,
                                           uint8_t quality,
                                           uint16_t speed_kn100,
                                           uint32_t uncertainty_cm,
                                           uint32_t now_ms,
                                           const balat_gate_config_t *config)
{
    uint64_t dt_ms;
    bool gap;
    uint32_t max_distance_cm;
    int64_t dx;
    int64_t dy;
    int64_t dist2;

    if (state == NULL || config == NULL) {
        return reject(BALAT_FAULT_CONFIG);
    }
    if (quality == 0u) {
        return reject(BALAT_FAULT_NO_FIX);
    }
    if (speed_kn100 > config->max_speed_kn100) {
        return reject(BALAT_FAULT_SPEED);
    }
    if (uncertainty_cm > config->max_uncertainty_cm) {
        return reject(BALAT_FAULT_UNCERTAIN);
    }
    if (x_cm < -BALAT_MAX_COORD_CM || x_cm > BALAT_MAX_COORD_CM ||
        y_cm < -BALAT_MAX_COORD_CM || y_cm > BALAT_MAX_COORD_CM) {
        return reject(BALAT_FAULT_OUT_OF_RANGE);
    }
    if (config->require_utc && !utc_valid) {
        return reject(BALAT_FAULT_MALFORMED);
    }

    gap = false;
    if (state->have_fix) {
        if (utc_valid && state->utc_valid) {
            if (utc_ms <= state->utc_ms) {
                return reject(BALAT_FAULT_BACKWARD_TIME);
            }
            dt_ms = utc_ms - state->utc_ms;
        } else {
            if ((int32_t)(now_ms - state->received_ms) <= 0) {
                return reject(BALAT_FAULT_BACKWARD_TIME);
            }
            dt_ms = (uint64_t)(now_ms - state->received_ms);
        }

        gap = dt_ms > config->max_gap_ms;
        if (!gap) {
            dx = (int64_t)x_cm - state->x_cm;
            dy = (int64_t)y_cm - state->y_cm;
            dist2 = dx * dx + dy * dy;

            max_distance_cm = (uint32_t)(((uint64_t)config->max_speed_cm_s *
                                          dt_ms) /
                                         1000u) +
                              uncertainty_cm + state->uncertainty_cm + 100u;
            if (dist2 > (int64_t)max_distance_cm * max_distance_cm) {
                return reject(BALAT_FAULT_JUMP);
            }
        }
    }

    ++state->fix_seq;
    state->have_fix = true;
    state->x_cm = x_cm;
    state->y_cm = y_cm;
    state->utc_ms = utc_ms;
    state->utc_valid = utc_valid;
    state->received_ms = now_ms;
    state->uncertainty_cm = uncertainty_cm;
    state->quality = quality;
    state->lat_deg7 = 0;
    state->lon_deg7 = 0;

    return accept(state, gap, gap ? BALAT_FAULT_GAP : BALAT_FAULT_NONE);
}
