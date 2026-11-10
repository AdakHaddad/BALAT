#include "balat_engine.h"

#include <string.h>

#define BALAT_INVALIDATING_MASK                                                \
    (BALAT_FAULT_NO_FIX | BALAT_FAULT_CHECKSUM | BALAT_FAULT_MALFORMED |      \
     BALAT_FAULT_BACKWARD_TIME | BALAT_FAULT_JUMP | BALAT_FAULT_UNCERTAIN |    \
     BALAT_FAULT_OUT_OF_RANGE | BALAT_FAULT_CONFIG | BALAT_FAULT_GAP |         \
     BALAT_FAULT_SPEED)

static bool engine_map_valid(const balat_engine_t *engine)
{
    return engine->map.valid &&
           (engine->injected_faults & BALAT_FAULT_MAP) == 0u;
}

static bool engine_stale(const balat_engine_t *engine, uint32_t now_ms)
{
    if (!engine_map_valid(engine)) {
        return true;
    }
    if (engine->manual_disable || engine->force_invalid) {
        return true;
    }
    if ((engine->injected_faults &
         (BALAT_INVALIDATING_MASK | BALAT_FAULT_STALE)) != 0u) {
        return true;
    }
    return balat_gate_is_stale(&engine->gate, now_ms,
                               engine->config.gate.stale_ms);
}

static balat_fault_t engine_faults(const balat_engine_t *engine, bool stale,
                                   bool map_valid)
{
    balat_fault_t fault = engine->risk.fault | engine->map.fault |
                          engine->last_reject_fault | engine->injected_faults;

    if (stale) {
        fault |= BALAT_FAULT_STALE;
    }
    if (!map_valid) {
        fault |= BALAT_FAULT_MAP;
    }
    if (engine->manual_disable) {
        fault |= BALAT_FAULT_MANUAL_DISABLE;
    }
    return fault;
}

static void set_event(balat_engine_t *engine, const char *name)
{
    size_t length = strlen(name);

    if (length >= sizeof(engine->event)) {
        length = sizeof(engine->event) - 1u;
    }
    memcpy(engine->event, name, length);
    engine->event[length] = '\0';
    engine->event_pending = true;
}

static void apply_gated(balat_engine_t *engine,
                        const balat_gated_fix_t *gated)
{
    const balat_map_segment_t *segment;
    uint32_t margin_cm;

    if (!gated->accepted) {
        engine->force_invalid = true;
        engine->last_reject_fault = gated->fault;
        balat_traj_reset(&engine->traj);
        balat_risk_step(&engine->risk, true, true, engine_map_valid(engine),
                        engine->cue.cooldown, false, 0, 0u,
                        &engine->config.risk);
        engine->decision_pending = true;
        return;
    }

    engine->last_fix = *gated;
    engine->have_fix = true;
    engine->last_reject_fault = gated->fault;
    engine->force_invalid = gated->gap;

    engine->last_geom =
        balat_nearest_segment(&engine->map, gated->x_cm, gated->y_cm);
    if (!engine->last_geom.valid) {
        engine->force_invalid = true;
        balat_traj_reset(&engine->traj);
        balat_risk_step(&engine->risk, true, true, engine_map_valid(engine),
                        engine->cue.cooldown, false, 0, 0u,
                        &engine->config.risk);
        engine->decision_pending = true;
        return;
    }

    engine->last_traj =
        balat_traj_update(&engine->traj, gated, &engine->last_geom,
                          &engine->config.traj);
    if (engine->last_traj.fault != BALAT_FAULT_NONE) {
        engine->force_invalid = true;
        engine->last_reject_fault |= engine->last_traj.fault;
    }

    margin_cm = gated->uncertainty_cm;
    segment = balat_map_find_segment(&engine->map,
                                     engine->last_geom.segment_id);
    if (segment != NULL) {
        margin_cm += segment->buffer_cm;
    }

    balat_risk_step(&engine->risk, true, engine->force_invalid,
                    engine_map_valid(engine), engine->cue.cooldown,
                    engine->last_traj.approaching, engine->last_geom.dist2_cm2,
                    margin_cm, &engine->config.risk);
    engine->decision_pending = true;
}

void balat_engine_init(balat_engine_t *engine,
                       const balat_engine_config_t *config,
                       const balat_map_t *map)
{
    if (engine == NULL || config == NULL || map == NULL) {
        return;
    }

    memset(engine, 0, sizeof(*engine));
    engine->config = *config;
    engine->map = *map;

    if (map->valid) {
        balat_coord_init(&engine->coord, map->manifest.origin_lat_deg7,
                         map->manifest.origin_lon_deg7,
                         map->manifest.cos_lat_q14);
    } else {
        balat_coord_init(&engine->coord, 0, 0, 16384);
    }

    balat_gate_init(&engine->gate);
    balat_traj_init(&engine->traj);
    balat_risk_init(&engine->risk);
    balat_cue_init(&engine->cue);

    engine->force_invalid = true;
    engine->prev_state = BALAT_RISK_INVALID;
    engine->prev_stale = true;
    engine->status.map_valid = map->valid;
    engine->status.risk_state = BALAT_RISK_INVALID;
    engine->status.stale = true;
    engine->status.fault = map->fault | BALAT_FAULT_STALE;
}

void balat_engine_on_nmea(balat_engine_t *engine,
                          const balat_nmea_sentence_t *sentence,
                          uint32_t now_ms)
{
    balat_gated_fix_t gated;
    bool gga_fresh = false;

    if (engine == NULL || sentence == NULL) {
        return;
    }

    if (sentence->kind == BALAT_NMEA_GGA) {
        if (engine->config.use_gga) {
            engine->gga_valid = true;
            engine->gga_quality = sentence->quality;
            engine->gga_hdop_centi = sentence->hdop_centi;
            engine->gga_received_ms = now_ms;
        }
        return;
    }

    if (sentence->kind != BALAT_NMEA_RMC) {
        return;
    }

    ++engine->rx_seq;

    if (engine->config.use_gga && engine->gga_valid &&
        (uint32_t)(now_ms - engine->gga_received_ms) <=
            engine->config.gate.stale_ms) {
        gga_fresh = true;
    }

    if (engine->config.use_gga && !gga_fresh) {
        memset(&gated, 0, sizeof(gated));
        gated.fault = BALAT_FAULT_UNCERTAIN;
        apply_gated(engine, &gated);
        return;
    }

    gated = balat_gate_process_rmc(&engine->gate, sentence,
                                   gga_fresh ? engine->gga_quality : sentence->quality,
                                   gga_fresh ? engine->gga_hdop_centi : 0u,
                                   gga_fresh, &engine->coord, now_ms,
                                   &engine->config.gate);
    apply_gated(engine, &gated);
}

void balat_engine_on_bad_sentence(balat_engine_t *engine,
                                  balat_nmea_status_t status,
                                  uint32_t now_ms)
{
    balat_fault_t fault;

    if (engine == NULL || status == BALAT_NMEA_OK ||
        status == BALAT_NMEA_IGNORED) {
        return;
    }

    switch (status) {
    case BALAT_NMEA_BAD_CHECKSUM:
        fault = BALAT_FAULT_CHECKSUM;
        break;
    case BALAT_NMEA_OUT_OF_RANGE:
        fault = BALAT_FAULT_OUT_OF_RANGE;
        break;
    case BALAT_NMEA_MALFORMED:
    default:
        fault = BALAT_FAULT_MALFORMED;
        break;
    }

    ++engine->rx_seq;
    engine->force_invalid = true;
    engine->last_reject_fault = fault;
    balat_traj_reset(&engine->traj);
    balat_risk_step(&engine->risk, true, true, engine_map_valid(engine),
                    engine->cue.cooldown, false, 0, 0u, &engine->config.risk);
    engine->decision_pending = true;
    (void)now_ms;
}

void balat_engine_on_synthetic_fix(balat_engine_t *engine,
                                   int32_t x_cm,
                                   int32_t y_cm,
                                   uint64_t utc_ms,
                                   uint32_t now_ms,
                                   uint32_t uncertainty_cm)
{
    balat_gated_fix_t gated;

    if (engine == NULL) {
        return;
    }

    ++engine->rx_seq;
    gated = balat_gate_process_local(&engine->gate, x_cm, y_cm, utc_ms, true,
                                     1u, 0u, uncertainty_cm, now_ms,
                                     &engine->config.gate);
    apply_gated(engine, &gated);
}

void balat_engine_tick(balat_engine_t *engine,
                       uint32_t now_ms,
                       bool cue_enable,
                       bool manual_disable)
{
    balat_cue_result_t cue_result;
    bool map_valid;
    bool stale;
    bool request;
    bool danger_escalation;

    if (engine == NULL) {
        return;
    }

    engine->cue_enable = cue_enable;
    engine->manual_disable = manual_disable;

    map_valid = engine_map_valid(engine);
    stale = engine_stale(engine, now_ms);

    if (stale) {
        balat_risk_step(&engine->risk, true, true, map_valid,
                        engine->cue.cooldown, false, 0, 0u,
                        &engine->config.risk);
    }

    request = engine->risk.cue_req && !stale && map_valid;
    danger_escalation = request &&
                        engine->risk.state == BALAT_RISK_DANGER &&
                        engine->prev_state != BALAT_RISK_DANGER &&
                        engine->cue.cooldown;

    cue_result = balat_cue_step(&engine->cue, now_ms,
                                cue_enable && !manual_disable, request,
                                danger_escalation,
                                &engine->config.cue);

    if (cue_result.started) {
        set_event(engine, "CUE_START");
        engine->decision_pending = true;
    }
    if (cue_result.stopped) {
        set_event(engine, "CUE_STOP");
        engine->decision_pending = true;
    }
    if (engine->risk.state != engine->prev_state) {
        set_event(engine, "RISK_CHANGE");
        engine->decision_pending = true;
    }
    if (stale && !engine->prev_stale) {
        set_event(engine, "GNSS_STALE");
        engine->decision_pending = true;
    }
    if (manual_disable != engine->prev_manual_disable) {
        set_event(engine, manual_disable ? "MANUAL_DISABLE" : "MANUAL_ENABLE");
        engine->decision_pending = true;
    }

    engine->status.fix_valid =
        engine->have_fix && !stale && engine->last_fix.accepted;
    engine->status.stale = stale;
    engine->status.map_valid = map_valid;
    engine->status.approaching =
        engine->last_traj.valid && engine->last_traj.approaching && !stale;
    engine->status.cue_request = engine->risk.cue_req;
    engine->status.cue_active = engine->cue.cue_en;
    engine->status.cooldown = engine->cue.cooldown;
    engine->status.manual_disable = manual_disable;
    engine->status.cue_enable = cue_enable;
    engine->status.risk_state = engine->risk.state;
    engine->status.fault = engine_faults(engine, stale, map_valid);
    engine->status.fix_seq = engine->gate.fix_seq;
    engine->status.rx_seq = engine->rx_seq;
    engine->status.timestamp_utc_ms = engine->last_fix.utc_ms;
    engine->status.timestamp_utc_valid = engine->last_fix.utc_valid;
    engine->status.received_ms = now_ms;
    engine->status.age_ms =
        engine->have_fix
            ? balat_gate_age_ms(&engine->gate, now_ms)
            : 0u;
    engine->status.x_cm = engine->last_fix.x_cm;
    engine->status.y_cm = engine->last_fix.y_cm;
    engine->status.dist2_cm2 =
        engine->last_geom.valid ? engine->last_geom.dist2_cm2 : 0;
    engine->status.segment_id =
        engine->last_geom.valid ? engine->last_geom.segment_id : 0u;
    engine->status.closest_x_cm =
        engine->last_geom.valid ? engine->last_geom.closest_x_cm : 0;
    engine->status.closest_y_cm =
        engine->last_geom.valid ? engine->last_geom.closest_y_cm : 0;
    engine->status.speed2_cm2_s2 = engine->last_traj.speed2_cm2_s2;
    engine->status.vx_cm_s = engine->last_traj.vx_cm_s;
    engine->status.vy_cm_s = engine->last_traj.vy_cm_s;
    engine->status.uncertainty_cm = engine->last_fix.uncertainty_cm;
    engine->status.quality = engine->last_fix.quality;
    engine->status.cue_duration_ms = cue_result.duration_ms;
    engine->status.cue_started = cue_result.started;
    engine->status.cue_stopped = cue_result.stopped;

    engine->prev_state = engine->risk.state;
    engine->prev_stale = stale;
    engine->prev_manual_disable = manual_disable;
    engine->prev_cue_active = engine->cue.cue_en;
}

void balat_engine_inject_fault(balat_engine_t *engine, balat_fault_t fault)
{
    if (engine == NULL) {
        return;
    }
    engine->injected_faults |= fault;
    engine->decision_pending = true;
}

void balat_engine_clear_injected_faults(balat_engine_t *engine)
{
    if (engine == NULL) {
        return;
    }
    engine->injected_faults = BALAT_FAULT_NONE;
    engine->decision_pending = true;
}

void balat_engine_clear_decision(balat_engine_t *engine)
{
    if (engine == NULL) {
        return;
    }
    engine->decision_pending = false;
    engine->event_pending = false;
    engine->event[0] = '\0';
    engine->status.cue_started = false;
    engine->status.cue_stopped = false;
}
