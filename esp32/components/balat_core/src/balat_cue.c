#include "balat_cue.h"

#include <string.h>

void balat_cue_init(balat_cue_state_t *state)
{
    if (state == NULL) {
        return;
    }
    memset(state, 0, sizeof(*state));
}

balat_cue_result_t balat_cue_step(balat_cue_state_t *state,
                                  uint32_t now_ms,
                                  bool enable,
                                  bool request,
                                  bool override_cooldown,
                                  const balat_cue_config_t *config)
{
    balat_cue_result_t result;

    memset(&result, 0, sizeof(result));

    if (state == NULL || config == NULL) {
        return result;
    }

    if (!enable) {
        if (state->cue_en) {
            result.stopped = true;
            result.duration_ms = (uint32_t)(now_ms - state->on_start_ms);
            state->last_duration_ms = result.duration_ms;
        }
        state->cue_en = false;
        state->cooldown = false;
        return result;
    }

    if (state->cooldown) {
        if (override_cooldown && request) {
            state->cooldown = false;
        } else {
            if ((uint32_t)(now_ms - state->cooldown_start_ms) >=
                config->cooldown_ms) {
                state->cooldown = false;
            } else {
                result.cooldown = true;
                result.duration_ms = state->last_duration_ms;
                return result;
            }
        }
    }

    if (state->cue_en) {
        uint32_t elapsed = (uint32_t)(now_ms - state->on_start_ms);
        if (!request || elapsed >= config->max_on_ms) {
            state->cue_en = false;
            state->cooldown = true;
            state->cooldown_start_ms = now_ms;
            state->last_duration_ms = elapsed;
            result.stopped = true;
            result.cooldown = true;
            result.duration_ms = elapsed;
            return result;
        }
        result.cue_active = true;
        result.duration_ms = elapsed;
        return result;
    }

    if (request) {
        state->cue_en = true;
        state->on_start_ms = now_ms;
        result.started = true;
        result.cue_active = true;
        result.duration_ms = 0u;
    } else {
        result.duration_ms = state->last_duration_ms;
    }
    return result;
}
