#ifndef BALAT_RISK_H
#define BALAT_RISK_H

#include "balat_types.h"

typedef struct {
    int32_t caution_enter_cm;
    int32_t caution_exit_cm;
    int32_t danger_enter_cm;
    int32_t danger_exit_cm;
    uint8_t confirm_samples;
} balat_risk_config_t;

typedef struct {
    balat_risk_state_t state;
    uint8_t confirm_cnt;
    bool cue_req;
    balat_fault_t fault;
} balat_risk_t;

void balat_risk_init(balat_risk_t *risk);

void balat_risk_step(balat_risk_t *risk,
                     bool sample_valid,
                     bool stale,
                     bool map_valid,
                     bool cooldown,
                     bool approaching,
                     int64_t dist2_cm2,
                     uint32_t margin_cm,
                     const balat_risk_config_t *config);

#endif
