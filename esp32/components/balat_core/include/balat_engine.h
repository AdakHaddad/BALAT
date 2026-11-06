#ifndef BALAT_ENGINE_H
#define BALAT_ENGINE_H

#include "balat_cue.h"
#include "balat_gate.h"
#include "balat_geometry.h"
#include "balat_map.h"
#include "balat_nmea.h"
#include "balat_risk.h"
#include "balat_trajectory.h"

typedef struct {
    balat_gate_config_t gate;
    balat_traj_config_t traj;
    balat_risk_config_t risk;
    balat_cue_config_t cue;
    bool use_gga;
    const char *reset_reason;
} balat_engine_config_t;

typedef struct {
    bool fix_valid;
    bool stale;
    bool map_valid;
    bool approaching;
    bool cue_request;
    bool cue_active;
    bool cooldown;
    bool manual_disable;
    bool cue_enable;
    balat_risk_state_t risk_state;
    balat_fault_t fault;
    uint32_t fix_seq;
    uint32_t rx_seq;
    uint64_t timestamp_utc_ms;
    bool timestamp_utc_valid;
    uint32_t received_ms;
    uint32_t age_ms;
    int32_t x_cm;
    int32_t y_cm;
    int64_t dist2_cm2;
    uint16_t segment_id;
    int32_t closest_x_cm;
    int32_t closest_y_cm;
    int64_t speed2_cm2_s2;
    int32_t vx_cm_s;
    int32_t vy_cm_s;
    uint32_t uncertainty_cm;
    uint8_t quality;
    uint32_t cue_duration_ms;
    bool cue_started;
    bool cue_stopped;
} balat_engine_status_t;

typedef struct {
    balat_map_t map;
    balat_coord_t coord;
    balat_gate_state_t gate;
    balat_traj_state_t traj;
    balat_risk_t risk;
    balat_cue_state_t cue;
    balat_engine_config_t config;
    balat_engine_status_t status;

    balat_gated_fix_t last_fix;
    balat_geom_t last_geom;
    balat_traj_result_t last_traj;
    bool have_fix;
    bool force_invalid;
    balat_fault_t last_reject_fault;
    balat_fault_t injected_faults;

    bool gga_valid;
    uint8_t gga_quality;
    uint16_t gga_hdop_centi;
    uint32_t gga_received_ms;

    uint32_t rx_seq;
    bool decision_pending;
    bool event_pending;
    char event[32];

    bool cue_enable;
    bool manual_disable;
    bool prev_manual_disable;
    balat_risk_state_t prev_state;
    bool prev_cue_active;
    bool prev_stale;
} balat_engine_t;

void balat_engine_init(balat_engine_t *engine,
                       const balat_engine_config_t *config,
                       const balat_map_t *map);

void balat_engine_on_nmea(balat_engine_t *engine,
                          const balat_nmea_sentence_t *sentence,
                          uint32_t now_ms);

void balat_engine_on_bad_sentence(balat_engine_t *engine,
                                  balat_nmea_status_t status,
                                  uint32_t now_ms);

void balat_engine_on_synthetic_fix(balat_engine_t *engine,
                                   int32_t x_cm,
                                   int32_t y_cm,
                                   uint64_t utc_ms,
                                   uint32_t now_ms,
                                   uint32_t uncertainty_cm);

void balat_engine_tick(balat_engine_t *engine,
                       uint32_t now_ms,
                       bool cue_enable,
                       bool manual_disable);

void balat_engine_inject_fault(balat_engine_t *engine, balat_fault_t fault);

void balat_engine_clear_injected_faults(balat_engine_t *engine);

void balat_engine_clear_decision(balat_engine_t *engine);

#endif
