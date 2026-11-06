#include "balat_risk.h"

#include <string.h>

static int64_t threshold_squared(int32_t threshold_cm, uint32_t margin_cm)
{
    int64_t effective = (int64_t)threshold_cm + (int64_t)margin_cm;
    return effective * effective;
}

static bool confirm_qualified(balat_risk_t *risk,
                              uint8_t confirm_samples,
                              balat_risk_state_t target)
{
    uint8_t required = confirm_samples == 0u ? 1u : confirm_samples;

    if ((uint8_t)(risk->confirm_cnt + 1u) >= required) {
        risk->state = target;
        risk->confirm_cnt = 0u;
        return true;
    }
    ++risk->confirm_cnt;
    return false;
}

void balat_risk_init(balat_risk_t *risk)
{
    if (risk == NULL) {
        return;
    }
    memset(risk, 0, sizeof(*risk));
    risk->state = BALAT_RISK_INVALID;
}

void balat_risk_step(balat_risk_t *risk,
                     bool sample_valid,
                     bool stale,
                     bool map_valid,
                     bool cooldown,
                     bool approaching,
                     int64_t dist2_cm2,
                     uint32_t margin_cm,
                     const balat_risk_config_t *config)
{
    int64_t caution_enter2;
    int64_t caution_exit2;
    int64_t danger_enter2;
    int64_t danger_exit2;

    if (risk == NULL || config == NULL) {
        return;
    }

    caution_enter2 = threshold_squared(config->caution_enter_cm, margin_cm);
    caution_exit2 = threshold_squared(config->caution_exit_cm, margin_cm);
    danger_enter2 = threshold_squared(config->danger_enter_cm, margin_cm);
    danger_exit2 = threshold_squared(config->danger_exit_cm, margin_cm);

    if (stale || !map_valid) {
        risk->state = BALAT_RISK_INVALID;
        risk->confirm_cnt = 0u;
    } else if (sample_valid) {
        if (cooldown) {
            risk->state = BALAT_RISK_COOLDOWN;
            risk->confirm_cnt = 0u;
        } else {
            switch (risk->state) {
            case BALAT_RISK_INVALID:
                risk->state = BALAT_RISK_SAFE;
                risk->confirm_cnt = 0u;
                break;

            case BALAT_RISK_SAFE:
                if (dist2_cm2 <= danger_enter2 && approaching) {
                    (void)confirm_qualified(risk, config->confirm_samples,
                                            BALAT_RISK_DANGER);
                } else if (dist2_cm2 <= caution_enter2 && approaching) {
                    (void)confirm_qualified(risk, config->confirm_samples,
                                            BALAT_RISK_CAUTION);
                } else {
                    risk->confirm_cnt = 0u;
                }
                break;

            case BALAT_RISK_CAUTION:
                if (dist2_cm2 <= danger_enter2 && approaching) {
                    (void)confirm_qualified(risk, config->confirm_samples,
                                            BALAT_RISK_DANGER);
                } else if (dist2_cm2 >= caution_exit2 || !approaching) {
                    risk->state = BALAT_RISK_SAFE;
                    risk->confirm_cnt = 0u;
                } else {
                    risk->confirm_cnt = 0u;
                }
                break;

            case BALAT_RISK_DANGER:
                if (dist2_cm2 >= caution_exit2) {
                    risk->state = BALAT_RISK_SAFE;
                    risk->confirm_cnt = 0u;
                } else if (dist2_cm2 >= danger_exit2) {
                    risk->state = BALAT_RISK_CAUTION;
                    risk->confirm_cnt = 0u;
                } else {
                    risk->confirm_cnt = 0u;
                }
                break;

            case BALAT_RISK_COOLDOWN:
                if (!cooldown) {
                    risk->state = BALAT_RISK_SAFE;
                    risk->confirm_cnt = 0u;
                }
                break;

            default:
                risk->state = BALAT_RISK_INVALID;
                risk->confirm_cnt = 0u;
                break;
            }
        }
    }

    risk->fault = 0u;
    if (stale) {
        risk->fault |= BALAT_FAULT_STALE;
    }
    if (!map_valid) {
        risk->fault |= BALAT_FAULT_MAP;
    }
    risk->cue_req = (risk->state == BALAT_RISK_DANGER) && !stale && map_valid &&
                    !cooldown;
}
