idf_component_register(
    SRCS
        "src/balat_common.c"
        "src/balat_coord.c"
        "src/balat_cue.c"
        "src/balat_engine.c"
        "src/balat_gate.c"
        "src/balat_geometry.c"
        "src/balat_log.c"
        "src/balat_map.c"
        "src/balat_nmea.c"
        "src/balat_risk.c"
        "src/balat_trajectory.c"
        "generated/balat_map_fixture.c"
        "generated/balat_replay_fixture.c"
    INCLUDE_DIRS "include" "generated"
)
