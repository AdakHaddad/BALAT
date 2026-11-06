#include "balat_fixture.h"

const balat_map_segment_t balat_fixture_segments[] = {
    {0, 0, -55660, 0, -18553, 0, 16384, 3, 0},
    {1, 0, -18553, 0, 18553, 0, 16384, 3, 0},
    {2, 0, 18553, 0, 55660, 0, 16384, 3, 0},
    {3, -55487, 0, -18496, 0, 16384, 0, 2, 0},
    {4, -18496, 0, 18496, 0, 16384, 0, 2, 0},
    {5, 18496, 0, 55487, 0, 16384, 0, 2, 0},
    {6, -9248, -11132, 9248, 11132, 10470, 12602, 1, 0},
};

const size_t balat_fixture_segment_count = sizeof(balat_fixture_segments) / sizeof(balat_fixture_segments[0]);
const balat_map_manifest_t balat_fixture_manifest = {
    .map_version = BALAT_MAP_VERSION,
    .checksum = 0xC140F1AEu,
    .segment_count = 7u,
    .origin_lat_deg7 = -338250000,
    .origin_lon_deg7 = 186500000,
    .cos_lat_q14 = 13611,
    .min_x_cm = -1000000, .max_x_cm = 1000000,
    .min_y_cm = -1000000, .max_y_cm = 1000000,
    .source = "OpenStreetMap via Overpass API",
    .license = "ODbL — https://opendatacommons.org/licenses/odbl/",
    .extraction_utc = "2026-10-31T04:26:24.414299+00:00",
    .crs = "equirectangular projection from origin",
    .coordinate_unit = "centimetres",
};
