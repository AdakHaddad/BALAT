#ifndef BALAT_CUE_H
#define BALAT_CUE_H

#include "balat_types.h"

typedef struct {
    uint32_t max_on_ms;
    uint32_t cooldown_ms;
} balat_cue_config_t;

typedef struct {
    bool cue_en;
    bool cooldown;
    uint32_t on_start_ms;
    uint32_t cooldown_start_ms;
    uint32_t last_duration_ms;
} balat_cue_state_t;

typedef struct {
    bool cue_active;
    bool cooldown;
    bool started;
    bool stopped;
    uint32_t duration_ms;
} balat_cue_result_t;

void balat_cue_init(balat_cue_state_t *state);

balat_cue_result_t balat_cue_step(balat_cue_state_t *state,
                                  uint32_t now_ms,
                                  bool enable,
                                  bool request,
                                  const balat_cue_config_t *config);

#endif
