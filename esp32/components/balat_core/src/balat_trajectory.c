#include "balat_trajectory.h"

#include <string.h>

static void store_previous(balat_traj_state_t *state,
                           const balat_gated_fix_t *fix)
{
    state->have_prev = true;
    state->prev_x_cm = fix->x_cm;
    state->prev_y_cm = fix->y_cm;
    state->prev_utc_ms = fix->utc_ms;
    state->prev_utc_valid = fix->utc_valid;
    state->prev_received_ms = fix->received_ms;
}

void balat_traj_init(balat_traj_state_t *state)
{
    if (state == NULL) {
        return;
    }
    memset(state, 0, sizeof(*state));
}

void balat_traj_reset(balat_traj_state_t *state)
{
    if (state == NULL) {
        return;
    }
    memset(state, 0, sizeof(*state));
}

balat_traj_result_t balat_traj_update(balat_traj_state_t *state,
                                      const balat_gated_fix_t *fix,
                                      const balat_geom_t *geom,
                                      const balat_traj_config_t *config)
{
    balat_traj_result_t result;
    uint64_t dt_ms;
    int64_t dx;
    int64_t dy;
    int64_t speed2;
    int64_t dot;
    int64_t rx;
    int64_t ry;

    memset(&result, 0, sizeof(result));

    if (state == NULL || fix == NULL || geom == NULL || config == NULL ||
        !geom->valid || !fix->accepted) {
        result.fault = BALAT_FAULT_CONFIG;
        return result;
    }

    if (fix->gap) {
        balat_traj_reset(state);
        store_previous(state, fix);
        result.fault = BALAT_FAULT_GAP;
        return result;
    }

    if (!state->have_prev) {
        store_previous(state, fix);
        return result;
    }

    if (fix->utc_valid && state->prev_utc_valid) {
        if (fix->utc_ms <= state->prev_utc_ms) {
            result.fault = BALAT_FAULT_BACKWARD_TIME;
            store_previous(state, fix);
            return result;
        }
        dt_ms = fix->utc_ms - state->prev_utc_ms;
    } else {
        uint32_t received_dt = fix->received_ms - state->prev_received_ms;
        if ((int32_t)received_dt <= 0) {
            result.fault = BALAT_FAULT_BACKWARD_TIME;
            store_previous(state, fix);
            return result;
        }
        dt_ms = received_dt;
    }

    if (dt_ms > config->max_gap_ms) {
        balat_traj_reset(state);
        store_previous(state, fix);
        result.fault = BALAT_FAULT_GAP;
        return result;
    }

    dx = (int64_t)fix->x_cm - state->prev_x_cm;
    dy = (int64_t)fix->y_cm - state->prev_y_cm;
    speed2 = (dx * dx + dy * dy) * 1000000LL / ((int64_t)dt_ms * (int64_t)dt_ms);

    rx = (int64_t)geom->closest_x_cm - fix->x_cm;
    ry = (int64_t)geom->closest_y_cm - fix->y_cm;
    dot = dx * rx + dy * ry;

    result.dt_ms = (uint32_t)dt_ms;
    result.speed2_cm2_s2 = speed2;

    if (speed2 < (int64_t)config->min_speed_cm_s * config->min_speed_cm_s) {
        result.valid = true;
        result.approaching = false;
        result.speed2_cm2_s2 = 0;
        result.vx_cm_s = 0;
        result.vy_cm_s = 0;
    } else if (speed2 > (int64_t)config->max_speed_cm_s * config->max_speed_cm_s) {
        balat_traj_reset(state);
        store_previous(state, fix);
        result.valid = false;
        result.approaching = false;
        result.fault = BALAT_FAULT_SPEED;
        return result;
    } else {
        result.valid = true;
        result.approaching = (dot > 0);
        result.vx_cm_s = (int32_t)(dx * 1000LL / (int64_t)dt_ms);
        result.vy_cm_s = (int32_t)(dy * 1000LL / (int64_t)dt_ms);
    }

    store_previous(state, fix);
    return result;
}
