#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "balat_coord.h"
#include "balat_cue.h"
#include "balat_engine.h"
#include "balat_fixture.h"
#include "balat_geometry.h"
#include "balat_log.h"
#include "balat_nmea.h"
#include "balat_risk.h"

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition); \
        return 1; \
    } \
} while (0)

static balat_map_t load_fixture(void)
{
    balat_map_t map;
    memset(&map, 0, sizeof(map));
    if (!balat_map_load(&map, &balat_fixture_manifest, balat_fixture_segments)) {
        fprintf(stderr, "fixture map did not validate\n");
        exit(1);
    }
    return map;
}

static int test_nmea_and_coords(void)
{
    balat_nmea_sentence_t sentence;
    balat_coord_t coord;
    int32_t x;
    int32_t y;

    CHECK(balat_nmea_parse("$GPRMC,123519.00,A,4807.0380,N,01131.0000,E,0.5,0.0,231003,,A*7B", &sentence) == BALAT_NMEA_OK);
    CHECK(sentence.kind == BALAT_NMEA_RMC && sentence.fix_valid);
    CHECK(sentence.lat_deg7 == 481173000 && sentence.lon_deg7 == 115166667);
    CHECK(sentence.utc_valid && sentence.speed_kn100 == 50u);
    CHECK(balat_nmea_parse("$GPRMC,123519.00,A,4807.0380,N,01131.0000,E,0.5,0.0,231003,,A*00", &sentence) == BALAT_NMEA_BAD_CHECKSUM);
    CHECK(balat_nmea_parse("$GPGGA,123519.00,4807.0380,N,01131.0000,E,0,00,99.9,0,M,0,M,,*6B", &sentence) == BALAT_NMEA_OK);
    CHECK(sentence.kind == BALAT_NMEA_GGA && !sentence.fix_valid && sentence.quality == 0u);

    balat_coord_init(&coord, -338250000, 186500000, 13611);
    CHECK(balat_coord_convert(&coord, -338250000, 186500000, &x, &y));
    CHECK(x == 0 && y == 0);
    CHECK(!balat_coord_convert(&coord, 900000000, 1800000000, &x, &y));
    return 0;
}

static int test_map_integrity(void)
{
    balat_map_t map = load_fixture();
    balat_map_manifest_t corrupt = balat_fixture_manifest;

    CHECK(map.valid && map.count == 7u);
    corrupt.checksum ^= 1u;
    CHECK(!balat_map_load(&map, &corrupt, balat_fixture_segments));
    return 0;
}

static int test_engine_requires_fresh_gga(void)
{
    balat_map_t map = load_fixture();
    balat_engine_t engine;
    balat_engine_config_t config = {
        .gate = {3000u, 5000u, 1500u, 30u, 50u, 500u, 100u, 2916u, false},
        .traj = {30u, 1500u, 5000u}, .risk = {500, 600, 200, 300, 2u},
        .cue = {500u, 30000u}, .use_gga = true, .reset_reason = "test"};
    balat_nmea_sentence_t rmc;
    balat_nmea_sentence_t gga;

    CHECK(balat_nmea_parse("$GPRMC,120000.00,A,3349.5000,S,01839.0000,E,0.0,0.0,010126,,A*63", &rmc) == BALAT_NMEA_OK);
    CHECK(balat_nmea_parse("$GPGGA,120000.00,3349.5000,S,01839.0000,E,1,08,1.0,0,M,0,M,,*40", &gga) == BALAT_NMEA_OK);
    balat_engine_init(&engine, &config, &map);
    balat_engine_on_nmea(&engine, &rmc, 1000u);
    CHECK(!engine.have_fix && engine.force_invalid);
    balat_engine_on_nmea(&engine, &gga, 1100u);
    balat_engine_on_nmea(&engine, &rmc, 1200u);
    CHECK(engine.have_fix && engine.last_fix.accepted);
    CHECK(engine.last_fix.uncertainty_cm == 150u);
    return 0;
}

static int test_geometry_vectors(void)
{
    FILE *vectors = fopen("../../tb/road_geom_vectors.txt", "r");
    char line[256];
    unsigned count = 0u;

    CHECK(vectors != NULL);
    while (fgets(line, sizeof(line), vectors) != NULL) {
        balat_map_segment_t segment;
        balat_map_manifest_t manifest = balat_fixture_manifest;
        balat_map_t map;
        balat_geom_t result;
        int32_t px, py;
        unsigned long long expected;
        unsigned inside;
        int read;
        int ux, uy;
        read = sscanf(line, "%d %d %d %d %d %d %d %d %llx %u", &px, &py,
                      &segment.ax_cm, &segment.ay_cm, &segment.bx_cm,
                      &segment.by_cm, &ux, &uy, &expected, &inside);
        CHECK(read == 10);
        segment.seg_id = 0u;
        segment.ux_q14 = (int16_t)ux;
        segment.uy_q14 = (int16_t)uy;
        segment.road_class = 1u;
        segment.buffer_cm = 0u;
        manifest.segment_count = 1u;
        manifest.checksum = balat_map_checksum(&segment, 1u,
                                               manifest.origin_lat_deg7,
                                               manifest.origin_lon_deg7,
                                               manifest.cos_lat_q14);
        CHECK(balat_map_load(&map, &manifest, &segment));
        result = balat_nearest_segment(&map, px, py);
        CHECK(result.valid);
        CHECK(result.dist2_cm2 == (int64_t)expected);
        CHECK(result.inside_span == (inside != 0u));
        ++count;
    }
    fclose(vectors);
    CHECK(count == 18u);
    return 0;
}

static int test_risk_and_cue(void)
{
    balat_risk_t risk;
    balat_cue_state_t cue;
    balat_risk_config_t risk_config = {500, 600, 200, 300, 2u};
    balat_cue_config_t cue_config = {500u, 30000u};
    balat_cue_result_t event;

    balat_risk_init(&risk);
    balat_risk_step(&risk, true, false, true, false, false, 1000000, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_SAFE);
    balat_risk_step(&risk, true, false, true, false, true, 40000, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_SAFE);
    balat_risk_step(&risk, true, false, true, false, true, 40000, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_DANGER && risk.cue_req);
    balat_risk_step(&risk, true, true, true, false, true, 0, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_INVALID && !risk.cue_req);

    balat_cue_init(&cue);
    event = balat_cue_step(&cue, 100u, true, true, false, &cue_config);
    CHECK(event.started && event.cue_active);
    event = balat_cue_step(&cue, 600u, true, true, false, &cue_config);
    CHECK(event.stopped && event.cooldown && !event.cue_active && event.duration_ms == 500u);
    event = balat_cue_step(&cue, 30599u, true, true, false, &cue_config);
    CHECK(!event.cue_active && event.cooldown);
    event = balat_cue_step(&cue, 30600u, true, true, false, &cue_config);
    CHECK(event.started && event.cue_active);
    event = balat_cue_step(&cue, 30601u, false, true, false, &cue_config);
    CHECK(event.stopped && !cue.cue_en && !cue.cooldown);

    balat_cue_init(&cue);
    event = balat_cue_step(&cue, 100u, true, true, false, &cue_config);
    CHECK(event.started && event.cue_active);
    event = balat_cue_step(&cue, 600u, true, true, false, &cue_config);
    CHECK(event.stopped && event.cooldown);
    event = balat_cue_step(&cue, 1000u, true, true, false, &cue_config);
    CHECK(!event.cue_active && event.cooldown);
    event = balat_cue_step(&cue, 1100u, true, true, true, &cue_config);
    CHECK(event.started && event.cue_active && !cue.cooldown);

    /* Zero cooldown must permit the next bounded pulse without reporting an
     * inhibited state. */
    cue_config.cooldown_ms = 0u;
    balat_cue_init(&cue);
    event = balat_cue_step(&cue, 100u, true, true, false, &cue_config);
    CHECK(event.started && event.cue_active);
    event = balat_cue_step(&cue, 600u, true, true, false, &cue_config);
    CHECK(event.stopped && !event.cooldown && !cue.cooldown &&
          event.duration_ms == 500u);
    event = balat_cue_step(&cue, 601u, true, true, false, &cue_config);
    CHECK(event.started && event.cue_active && !cue.cooldown);

    balat_risk_init(&risk);
    balat_risk_step(&risk, true, false, true, false, false, 1000000, 0u, &risk_config);
    balat_risk_step(&risk, true, false, true, false, true, 250000, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_SAFE && !risk.cue_req);
    balat_risk_step(&risk, true, false, true, false, true, 250000, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_CAUTION && risk.cue_req);
    balat_risk_step(&risk, true, false, true, true, true, 40000, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_CAUTION);
    balat_risk_step(&risk, true, false, true, true, true, 40000, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_DANGER && risk.cue_req);
    balat_risk_step(&risk, true, true, true, false, true, 0, 0u, &risk_config);
    CHECK(risk.state == BALAT_RISK_INVALID && !risk.cue_req);
    return 0;
}

static int test_engine_danger_overrides_caution_cooldown(void)
{
    balat_map_t map;
    balat_map_segment_t segment = {0u, -2000, 0, 2000, 0, 16384, 0, 1u, 0u};
    balat_map_manifest_t manifest = balat_fixture_manifest;
    balat_engine_t engine;
    balat_engine_config_t config = {
        .gate = {3000u, 5000u, 1500u, 30u, 0u, 500u, 100u, 2916u, false},
        .traj = {30u, 1500u, 5000u}, .risk = {500, 600, 200, 300, 2u},
        .cue = {500u, 30000u}, .use_gga = false, .reset_reason = "test"};

    manifest.segment_count = 1u;
    manifest.checksum = balat_map_checksum(&segment, 1u,
                                           manifest.origin_lat_deg7,
                                           manifest.origin_lon_deg7,
                                           manifest.cos_lat_q14);
    CHECK(balat_map_load(&map, &manifest, &segment));
    balat_engine_init(&engine, &config, &map);

    engine.gate.have_fix = true;
    engine.gate.received_ms = 1000u;
    engine.force_invalid = false;
    engine.risk.state = BALAT_RISK_DANGER;
    engine.risk.cue_req = true;
    engine.cue.cooldown = true;
    engine.cue.cooldown_start_ms = 900u;
    engine.prev_state = BALAT_RISK_CAUTION;

    balat_engine_tick(&engine, 1000u, true, false);
    CHECK(engine.status.cue_active && engine.status.cue_started);
    CHECK(!engine.status.cooldown);

    balat_engine_tick(&engine, 1500u, true, false);
    CHECK(!engine.status.cue_active && engine.status.cooldown);
    balat_engine_tick(&engine, 1600u, true, false);
    CHECK(!engine.status.cue_active && engine.status.cooldown);
    return 0;
}

static int test_engine_replay_and_faults(void)
{
    balat_map_t map;
    balat_map_segment_t demo_segment = {0u, -2000, 0, 2000, 0, 16384, 0, 1u, 0u};
    balat_map_manifest_t demo_manifest = balat_fixture_manifest;
    balat_engine_t engine;
    balat_engine_config_t config = {
        .gate = {3000u, 5000u, 1500u, 30u, 0u, 500u, 100u, 2916u, false},
        .traj = {30u, 1500u, 5000u}, .risk = {500, 600, 200, 300, 2u},
        .cue = {500u, 30000u}, .use_gga = false, .reset_reason = "test"};
    char log_line[512];
    uint32_t time = 0u;

    demo_manifest.segment_count = 1u;
    demo_manifest.checksum = balat_map_checksum(&demo_segment, 1u,
                                                demo_manifest.origin_lat_deg7,
                                                demo_manifest.origin_lon_deg7,
                                                demo_manifest.cos_lat_q14);
    CHECK(balat_map_load(&map, &demo_manifest, &demo_segment));
    balat_engine_init(&engine, &config, &map);
    for (size_t i = 0; i < balat_fixture_replay_count; ++i) {
        balat_replay_point_t point = balat_fixture_replay[i];
        balat_engine_on_synthetic_fix(&engine, point.x_cm, point.y_cm, time, time, 0u);
        balat_engine_tick(&engine, time, true, false);
        CHECK(engine.status.map_valid && !engine.status.stale);
        CHECK(engine.status.dist2_cm2 == (int64_t)point.y_cm * point.y_cm);
        time += 100u;
    }
    CHECK(engine.status.risk_state == BALAT_RISK_COOLDOWN && !engine.status.cue_active);
    balat_engine_inject_fault(&engine, BALAT_FAULT_STALE);
    balat_engine_tick(&engine, time, true, false);
    CHECK(engine.status.risk_state == BALAT_RISK_INVALID && !engine.status.cue_active);
    balat_engine_clear_injected_faults(&engine);
    balat_engine_tick(&engine, time, false, true);
    CHECK((engine.status.fault & BALAT_FAULT_MANUAL_DISABLE) != 0u && !engine.status.cue_active);
    CHECK(balat_log_format_csv(&engine.status, "TEST", log_line, sizeof(log_line)) > 0u);
    CHECK(strstr(log_line, "event=TEST") != NULL && strstr(log_line, "risk=INVALID") != NULL);
    return 0;
}

int main(void)
{
    CHECK(test_nmea_and_coords() == 0);
    CHECK(test_map_integrity() == 0);
    CHECK(test_engine_requires_fresh_gga() == 0);
    CHECK(test_geometry_vectors() == 0);
    CHECK(test_risk_and_cue() == 0);
    CHECK(test_engine_danger_overrides_caution_cooldown() == 0);
    CHECK(test_engine_replay_and_faults() == 0);
    puts("PASS balat_core host regression");
    return 0;
}
