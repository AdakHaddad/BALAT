#!/usr/bin/env python3
"""Generate deterministic C fixtures from the checked-in BALAT demo data."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "esp32" / "components" / "balat_core" / "generated"

FNV_OFFSET = 2166136261
FNV_PRIME = 16777619


def fnv_byte(value: int, byte: int) -> int:
    return ((value ^ byte) * FNV_PRIME) & 0xFFFFFFFF


def fnv_u16(value: int, item: int) -> int:
    for shift in (0, 8):
        value = fnv_byte(value, (item >> shift) & 0xFF)
    return value


def fnv_u32(value: int, item: int) -> int:
    for shift in (0, 8, 16, 24):
        value = fnv_byte(value, (item >> shift) & 0xFF)
    return value


def checksum(segments: list[dict[str, str]], origin_lat: int, origin_lon: int,
             cos_q14: int) -> int:
    value = FNV_OFFSET
    value = fnv_u32(value, len(segments))
    value = fnv_u32(value, origin_lat & 0xFFFFFFFF)
    value = fnv_u32(value, origin_lon & 0xFFFFFFFF)
    value = fnv_u16(value, cos_q14 & 0xFFFF)
    for row in segments:
        for item, bits in ((int(row["seg_id"]), 16),
                           (int(row["ax"]), 32), (int(row["ay"]), 32),
                           (int(row["bx"]), 32), (int(row["by"]), 32),
                           (int(row["ux_q14"]), 16), (int(row["uy_q14"]), 16),
                           (int(row["road_class"]), 8), (0, 16)):
            if bits == 8:
                value = fnv_byte(value, item)
            elif bits == 16:
                value = fnv_u16(value, item & 0xFFFF)
            else:
                value = fnv_u32(value, item & 0xFFFFFFFF)
    return value


def main() -> None:
    manifest = json.loads((DATA / "road_manifest.json").read_text())
    with (DATA / "road_segments.csv").open(newline="") as source:
        segments = list(csv.DictReader(source))
    with (DATA / "demo_trace.csv").open(newline="") as source:
        trace = list(csv.DictReader(source))

    origin_lat = round(float(manifest["origin_lat"]) * 10_000_000)
    origin_lon = round(float(manifest["origin_lon"]) * 10_000_000)
    cos_q14 = 13611
    value = checksum(segments, origin_lat, origin_lon, cos_q14)
    OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "balat_fixture.h").write_text("""#ifndef BALAT_FIXTURE_H
#define BALAT_FIXTURE_H

#include <stddef.h>
#include <stdint.h>
#include \"balat_map.h\"

extern const balat_map_manifest_t balat_fixture_manifest;
extern const balat_map_segment_t balat_fixture_segments[];
extern const size_t balat_fixture_segment_count;
typedef struct { int32_t x_cm; int32_t y_cm; } balat_replay_point_t;
extern const balat_replay_point_t balat_fixture_replay[];
extern const size_t balat_fixture_replay_count;
#endif
""")
    map_lines = ["#include \"balat_fixture.h\"", "",
                 "const balat_map_segment_t balat_fixture_segments[] = {"]
    for row in segments:
        map_lines.append("    {%s, %s, %s, %s, %s, %s, %s, %s, 0}," % tuple(
            row[k] for k in ("seg_id", "ax", "ay", "bx", "by", "ux_q14",
                             "uy_q14", "road_class")))
    map_lines += ["};", "",
                  "const size_t balat_fixture_segment_count = "
                  "sizeof(balat_fixture_segments) / sizeof(balat_fixture_segments[0]);",
                  "const balat_map_manifest_t balat_fixture_manifest = {",
                  "    .map_version = BALAT_MAP_VERSION,",
                  f"    .checksum = 0x{value:08X}u,",
                  f"    .segment_count = {len(segments)}u,",
                  f"    .origin_lat_deg7 = {origin_lat},",
                  f"    .origin_lon_deg7 = {origin_lon},",
                  f"    .cos_lat_q14 = {cos_q14},",
                  "    .min_x_cm = -1000000, .max_x_cm = 1000000,",
                  "    .min_y_cm = -1000000, .max_y_cm = 1000000,",
                  f"    .source = \"{manifest['source']}\",",
                  f"    .license = \"{manifest['license']}\",",
                  f"    .extraction_utc = \"{manifest['extraction_utc']}\",",
                  f"    .crs = \"{manifest['crs']}\",",
                  f"    .coordinate_unit = \"{manifest['coordinate_unit']}\",",
                  "};", ""]
    (OUT / "balat_map_fixture.c").write_text("\n".join(map_lines))

    replay_lines = ["#include \"balat_fixture.h\"", "",
                    "const balat_replay_point_t balat_fixture_replay[] = {"]
    replay_lines += [f"    {{{row['x_cm']}, {row['y_cm']}}}," for row in trace]
    replay_lines += ["};", "",
                     "const size_t balat_fixture_replay_count = "
                     "sizeof(balat_fixture_replay) / sizeof(balat_fixture_replay[0]);", ""]
    (OUT / "balat_replay_fixture.c").write_text("\n".join(replay_lines))


if __name__ == "__main__":
    main()
