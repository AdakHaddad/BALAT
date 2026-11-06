#ifndef BALAT_GATE_H
#define BALAT_GATE_H

#include "balat_coord.h"
#include "balat_nmea.h"

typedef struct {
    uint32_t stale_ms;
    uint32_t max_gap_ms;
    uint32_t max_speed_cm_s;
    uint32_t min_speed_cm_s;
    uint32_t base_uncertainty_cm;
    uint32_t max_uncertainty_cm;
    uint32_t hdop_scale_cm;
    uint16_t max_speed_kn100;
    bool require_utc;
} balat_gate_config_t;

typedef struct {
    bool have_fix;
    uint32_t fix_seq;
    int32_t x_cm;
    int32_t y_cm;
    int32_t lat_deg7;
    int32_t lon_deg7;
    uint64_t utc_ms;
    bool utc_valid;
    uint32_t received_ms;
    uint32_t uncertainty_cm;
    uint8_t quality;
} balat_gate_state_t;

typedef struct {
    bool accepted;
    bool gap;
    balat_fault_t fault;
    uint32_t fix_seq;
    int32_t x_cm;
    int32_t y_cm;
    int32_t lat_deg7;
    int32_t lon_deg7;
    uint64_t utc_ms;
    bool utc_valid;
    uint32_t received_ms;
    uint32_t uncertainty_cm;
    uint8_t quality;
    uint16_t speed_kn100;
} balat_gated_fix_t;

void balat_gate_init(balat_gate_state_t *state);

bool balat_gate_is_stale(const balat_gate_state_t *state,
                         uint32_t now_ms,
                         uint32_t stale_ms);

uint32_t balat_gate_age_ms(const balat_gate_state_t *state, uint32_t now_ms);

uint32_t balat_gate_uncertainty(const balat_gate_config_t *config,
                                uint16_t hdop_centi,
                                bool hdop_valid);

balat_gated_fix_t balat_gate_process_rmc(balat_gate_state_t *state,
                                         const balat_nmea_sentence_t *rmc,
                                         uint8_t gga_quality,
                                         uint16_t gga_hdop_centi,
                                         bool gga_fresh,
                                         const balat_coord_t *coord,
                                         uint32_t now_ms,
                                         const balat_gate_config_t *config);

balat_gated_fix_t balat_gate_process_local(balat_gate_state_t *state,
                                           int32_t x_cm,
                                           int32_t y_cm,
                                           uint64_t utc_ms,
                                           bool utc_valid,
                                           uint8_t quality,
                                           uint16_t speed_kn100,
                                           uint32_t uncertainty_cm,
                                           uint32_t now_ms,
                                           const balat_gate_config_t *config);

#endif
