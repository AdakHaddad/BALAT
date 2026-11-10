#!/usr/bin/env python3
"""Generate ESP32 C fixtures for the Sumbawa Besar road map.

Writes:
  esp32/components/balat_core/generated/balat_map_fixture.c
  esp32/components/balat_core/generated/balat_replay_fixture.c

The map fixture must include a correct FNV-1a checksum over the segments and
manifest parameters, matching the balat_map_checksum() function in balat_map.c.

Road data: © OpenStreetMap contributors (ODbL)
  Manually digitised segments for Sumbawa Besar, West Nusa Tenggara, Indonesia.
  See data/road_manifest.json for provenance.
"""

from __future__ import annotations
import csv
import ctypes
import math
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ORIGIN_LAT_DEG7 = -84_900_000
ORIGIN_LON_DEG7 = 1_174_200_000
COS_LAT_Q14 = 16204
BALAT_MAP_VERSION = 1
BUFFER_CM = 0  # no buffer for v0.1 segments

ROAD_SEGMENTS_CSV = REPO / "data" / "road_segments.csv"
MAP_FIXTURE_OUT   = REPO / "esp32" / "components" / "balat_core" / "generated" / "balat_map_fixture.c"
REPLAY_FIXTURE_OUT = REPO / "esp32" / "components" / "balat_core" / "generated" / "balat_replay_fixture.c"

# ---------------------------------------------------------------------------
# FNV-1a checksum (matches balat_map_checksum in balat_map.c)
# ---------------------------------------------------------------------------

FNV_OFFSET_BASIS = 0x811C9DC5
FNV_PRIME        = 0x01000193
FNV_MASK         = 0xFFFF_FFFF


def fnv_u8(h: int, b: int) -> int:
    return ((h ^ (b & 0xFF)) * FNV_PRIME) & FNV_MASK


def fnv_u16(h: int, v: int) -> int:
    h = fnv_u8(h, v & 0xFF)
    h = fnv_u8(h, (v >> 8) & 0xFF)
    return h


def fnv_i16(h: int, v: int) -> int:
    return fnv_u16(h, v & 0xFFFF)


def fnv_u32(h: int, v: int) -> int:
    for i in range(4):
        h = fnv_u8(h, (v >> (8 * i)) & 0xFF)
    return h


def fnv_i32(h: int, v: int) -> int:
    return fnv_u32(h, v & 0xFFFF_FFFF)


def compute_checksum(segments: list[dict], origin_lat: int, origin_lon: int, cos_lat: int) -> int:
    h = FNV_OFFSET_BASIS
    h = fnv_u32(h, len(segments))
    h = fnv_i32(h, origin_lat)
    h = fnv_i32(h, origin_lon)
    h = fnv_i16(h, cos_lat)
    for s in segments:
        h = fnv_u16(h, s["seg_id"] & 0xFFFF)
        h = fnv_i32(h, s["ax"])
        h = fnv_i32(h, s["ay"])
        h = fnv_i32(h, s["bx"])
        h = fnv_i32(h, s["by"])
        h = fnv_i16(h, s["ux_q14"])
        h = fnv_i16(h, s["uy_q14"])
        h = fnv_u8(h,  s["road_class"] & 0xFF)
        h = fnv_u16(h, BUFFER_CM)
    return h


# ---------------------------------------------------------------------------
# Load segments from CSV
# ---------------------------------------------------------------------------

def load_segments(path: Path) -> list[dict]:
    segs = []
    with open(path) as f:
        for row in csv.DictReader(f):
            segs.append({
                "seg_id":     int(row["seg_id"]),
                "ax":         int(row["ax"]),
                "ay":         int(row["ay"]),
                "bx":         int(row["bx"]),
                "by":         int(row["by"]),
                "ux_q14":     int(row["ux_q14"]),
                "uy_q14":     int(row["uy_q14"]),
                "road_class": int(row["road_class"]),
            })
    return segs


# ---------------------------------------------------------------------------
# Compute bounding box
# ---------------------------------------------------------------------------

def bbox(segs: list[dict]) -> tuple[int, int, int, int]:
    xs = [s["ax"] for s in segs] + [s["bx"] for s in segs]
    ys = [s["ay"] for s in segs] + [s["by"] for s in segs]
    return min(xs), max(xs), min(ys), max(ys)


# ---------------------------------------------------------------------------
# Generate replay trace (approach → pass → retreat)
#
# Pick a path that:
#   1. Starts ~600 cm (6 m) north of segment 29 (Jl. Hasanuddin, N–S secondary)
#      which passes close to x≈0 in local coords.
#   2. Moves south at ~10 cm/step (1 m/s at 10 Hz) until it reaches ~20 cm
#      (past the DANGER threshold of 200 cm).
#   3. Reverses and retreats back to start.
#
# Segment 29 is in the Hasanuddin road group; its midpoint is near x=0, y≈0.
# We approach from the east (positive x) so the nearest road is Jl. Hasanuddin
# (segments around x≈0). Start at x=+800 cm, y≈0 and move west.
# ---------------------------------------------------------------------------

def make_replay(segs: list[dict], n_total: int = 201) -> list[tuple[int, int]]:
    """Approach segment closest to (0,0) from x=+800 cm, then retreat."""
    # Find the segment with midpoint closest to origin
    def midpoint_dist2(s: dict) -> float:
        mx = (s["ax"] + s["bx"]) / 2
        my = (s["ay"] + s["by"]) / 2
        return mx * mx + my * my

    closest = min(segs, key=midpoint_dist2)
    # Foot of perpendicular from origin to this segment
    ax, ay = closest["ax"], closest["ay"]
    bx, by = closest["bx"], closest["by"]
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 > 0:
        t = max(0.0, min(1.0, (-ax * dx + (-ay) * dy) / length2))
        road_x = int(ax + t * dx)
        road_y = int(ay + t * dy)
    else:
        road_x, road_y = ax, ay

    # Approach from +800 cm in the x direction (east of road)
    start_x = road_x + 800
    start_y = road_y

    # Half the trace approaches, half retreats
    half = n_total // 2
    # Approach: from start to road_x (passes through danger zone then clamps)
    # We overshoot slightly to road_x + 50 so we clearly pass threshold
    end_x = road_x + 50  # stop 50 cm from road (inside DANGER zone)

    pts: list[tuple[int, int]] = []
    for i in range(half + 1):
        t = i / half
        x = int(start_x + t * (end_x - start_x))
        pts.append((x, start_y))

    # Retreat: mirror back to start
    for i in range(1, n_total - len(pts) + 1):
        t = i / (n_total - len(pts))
        x = int(end_x + t * (start_x - end_x))
        pts.append((x, start_y))

    # Trim / pad to exactly n_total
    pts = pts[:n_total]
    while len(pts) < n_total:
        pts.append(pts[-1])

    return pts


# ---------------------------------------------------------------------------
# Write fixture files
# ---------------------------------------------------------------------------

def write_map_fixture(segs: list[dict], checksum: int, path: Path) -> None:
    min_x, max_x, min_y, max_y = bbox(segs)
    n = len(segs)
    utc = "2026-11-10T13:38:02.000000+00:00"
    with open(path, "w") as f:
        f.write('#include "balat_fixture.h"\n\n')
        f.write("/* Sumbawa Besar road network, West Nusa Tenggara, Indonesia.\n")
        f.write(" * Source: OpenStreetMap contributors (ODbL) — manually digitised segments.\n")
        f.write(" * Attribution: © OpenStreetMap contributors — https://www.openstreetmap.org/copyright\n")
        f.write(" * Generated by scripts/gen_sumbawa_esp32_fixture.py — do not edit.\n")
        f.write(" * Origin: lat -8.490 deg, lon 117.420 deg\n")
        f.write(f" * {n} segments. See data/road_manifest.json for full provenance.\n")
        f.write(" */\n\n")
        f.write("const balat_map_segment_t balat_fixture_segments[] = {\n")
        f.write("    /* {seg_id, ax_cm, ay_cm, bx_cm, by_cm, ux_q14, uy_q14, road_class, buffer_cm} */\n")
        for s in segs:
            f.write(f"    {{{s['seg_id']}, "
                    f"{s['ax']}, {s['ay']}, "
                    f"{s['bx']}, {s['by']}, "
                    f"{s['ux_q14']}, {s['uy_q14']}, "
                    f"{s['road_class']}, 0}},\n")
        f.write("};\n\n")
        f.write("const size_t balat_fixture_segment_count = "
                "sizeof(balat_fixture_segments) / sizeof(balat_fixture_segments[0]);\n\n")
        f.write("const balat_map_manifest_t balat_fixture_manifest = {\n")
        f.write(f"    .map_version     = BALAT_MAP_VERSION,\n")
        f.write(f"    .checksum        = 0x{checksum:08X}u,\n")
        f.write(f"    .segment_count   = {n}u,\n")
        f.write(f"    .origin_lat_deg7 = {ORIGIN_LAT_DEG7},\n")
        f.write(f"    .origin_lon_deg7 = {ORIGIN_LON_DEG7},\n")
        f.write(f"    .cos_lat_q14     = {COS_LAT_Q14},\n")
        f.write(f"    .min_x_cm        = {min_x}, .max_x_cm = {max_x},\n")
        f.write(f"    .min_y_cm        = {min_y}, .max_y_cm = {max_y},\n")
        f.write(f'    .source          = "OpenStreetMap contributors (ODbL) — Sumbawa Besar",\n')
        f.write(f'    .license         = "ODbL — https://opendatacommons.org/licenses/odbl/",\n')
        f.write(f'    .extraction_utc  = "{utc}",\n')
        f.write(f'    .crs             = "equirectangular projection from origin",\n')
        f.write(f'    .coordinate_unit = "centimetres",\n')
        f.write("};\n")


def write_replay_fixture(pts: list[tuple[int, int]], path: Path) -> None:
    with open(path, "w") as f:
        f.write('#include "balat_fixture.h"\n\n')
        f.write("/* Sumbawa Besar demo replay — approach and retreat from nearest road.\n")
        f.write(" * Generated by scripts/gen_sumbawa_esp32_fixture.py — do not edit.\n")
        f.write(" * Local coords (cm) relative to origin lat -8.490°, lon 117.420°.\n")
        f.write(" */\n\n")
        f.write("const balat_replay_point_t balat_fixture_replay[] = {\n")
        for x, y in pts:
            f.write(f"    {{{x}, {y}}},\n")
        f.write("};\n\n")
        f.write("const size_t balat_fixture_replay_count = "
                "sizeof(balat_fixture_replay) / sizeof(balat_fixture_replay[0]);\n")


if __name__ == "__main__":
    segs = load_segments(ROAD_SEGMENTS_CSV)
    print(f"Loaded {len(segs)} segments from {ROAD_SEGMENTS_CSV}")

    checksum = compute_checksum(segs, ORIGIN_LAT_DEG7, ORIGIN_LON_DEG7, COS_LAT_Q14)
    print(f"Map checksum: 0x{checksum:08X}")

    replay = make_replay(segs, n_total=201)
    start = replay[0]
    end   = replay[len(replay)//2]
    print(f"Replay: {len(replay)} points, start=({start[0]},{start[1]}), "
          f"closest approach=({end[0]},{end[1]})")

    write_map_fixture(segs, checksum, MAP_FIXTURE_OUT)
    write_replay_fixture(replay, REPLAY_FIXTURE_OUT)

    print(f"Wrote {MAP_FIXTURE_OUT}")
    print(f"Wrote {REPLAY_FIXTURE_OUT}")
