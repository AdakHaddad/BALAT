#ifndef BALAT_TRAJECTORY_H
#define BALAT_TRAJECTORY_H

#include "balat_gate.h"
#include "balat_geometry.h"

typedef struct {
    uint32_t min_speed_cm_s;
    uint32_t max_speed_cm_s;
    uint32_t max_gap_ms;
} balat_traj_config_t;

typedef struct {
    bool have_prev;
    int32_t prev_x_cm;
    int32_t prev_y_cm;
    uint64_t prev_utc_ms;
    bool prev_utc_valid;
    uint32_t prev_received_ms;
} balat_traj_state_t;

typedef struct {
    bool valid;
    bool approaching;
    balat_fault_t fault;
    int32_t vx_cm_s;
    int32_t vy_cm_s;
    int64_t speed2_cm2_s2;
    uint32_t dt_ms;
} balat_traj_result_t;

void balat_traj_init(balat_traj_state_t *state);

void balat_traj_reset(balat_traj_state_t *state);

balat_traj_result_t balat_traj_update(balat_traj_state_t *state,
                                      const balat_gated_fix_t *fix,
                                      const balat_geom_t *geom,
                                      const balat_traj_config_t *config);

#endif
