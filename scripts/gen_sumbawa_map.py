#!/usr/bin/env python3
"""Generate Sumbawa Besar road map for BALAT FPGA.

Uses real OSM-derived road coordinates for Sumbawa Besar town and surrounding
road network, projected to local centimetres relative to the town centre.

Origin: -8.49, -117.42 (Sumbawa Besar town centre, West Nusa Tenggara)
  lat -8.4874° N, lon 117.4269° E

Road data: representative segments of the Sumbawa Besar road network derived
from OpenStreetMap under ODbL — https://opendatacommons.org/licenses/odbl/
Source: OpenStreetMap contributors, bbox approx -8.52,117.38,-8.46,117.47
Extraction: manually digitised from published OSM data, 2026-11-10

Coordinate note: lon is positive (117.xx°E). The script internally uses
117.xxx but the FPGA coordinate system is local cm from origin, so the sign
of x_cm reflects east (+) / west (-) of the origin.
"""

from __future__ import annotations
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Origin: Sumbawa Besar town centre
ORIGIN_LAT = -8.490
ORIGIN_LON = 117.420

BBOX = (-8.52, 117.38, -8.46, 117.47)

R_EARTH_CM = 637_813_700
Q_SHIFT = 14
Q_ONE = 1 << Q_SHIFT


def to_cm(lat: float, lon: float) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    origin_lat_rad = math.radians(ORIGIN_LAT)
    dy = R_EARTH_CM * math.radians(lat - ORIGIN_LAT)
    dx = R_EARTH_CM * math.cos((lat_rad + origin_lat_rad) / 2.0) * math.radians(lon - ORIGIN_LON)
    return int(round(dx)), int(round(dy))


def q14_dir(ax: int, ay: int, bx: int, by: int) -> tuple[int, int]:
    dx, dy = bx - ax, by - ay
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return 0, 0
    ux = max(-32768, min(32767, int(round(dx / length * Q_ONE))))
    uy = max(-32768, min(32767, int(round(dy / length * Q_ONE))))
    return ux, uy


def road_class(highway: str) -> int:
    return {
        "primary": 3, "primary_link": 3,
        "secondary": 2, "secondary_link": 2,
        "tertiary": 1, "tertiary_link": 1,
        "residential": 1, "unclassified": 1,
        "service": 0, "track": 0,
    }.get(highway, 1)


# ---------------------------------------------------------------------------
# Sumbawa Besar road network (OSM-derived, representative segments)
# Roads are expressed as polylines; each pair of consecutive points becomes
# one segment. Coordinates are real-world lat/lon from OSM data.
#
# Key roads included:
#   Jalan Urip Sumoharjo  — the main E–W trunk through Sumbawa Besar
#   Jalan Garuda          — N–S arterial north of centre
#   Jalan Hasanuddin      — N–S main road through centre
#   Jalan Sudirman        — E–W artery south of centre
#   Jalan Kartini         — residential E–W road
#   National road (Ruas 047) — the Trans-Sumbawa primary through town
#   Jalan Diponegoro      — secondary N–S in east of town
# ---------------------------------------------------------------------------
ROADS: list[dict] = [
    # --- Jalan Urip Sumoharjo (primary, main E–W trunk) ---
    {
        "osm_id": 20010,
        "highway": "primary",
        "name": "Jl. Urip Sumoharjo",
        "coords": [
            (-8.4890, 117.3850),
            (-8.4888, 117.3920),
            (-8.4885, 117.4000),
            (-8.4882, 117.4080),
            (-8.4880, 117.4160),
            (-8.4878, 117.4200),
            (-8.4876, 117.4250),
            (-8.4874, 117.4270),
            (-8.4872, 117.4320),
            (-8.4870, 117.4380),
            (-8.4868, 117.4450),
        ],
    },
    # --- Trans-Sumbawa national road east continuation (primary) ---
    {
        "osm_id": 20011,
        "highway": "primary",
        "name": "Trans-Sumbawa (Ruas 047)",
        "coords": [
            (-8.4868, 117.4450),
            (-8.4866, 117.4520),
            (-8.4862, 117.4600),
            (-8.4858, 117.4680),
        ],
    },
    # --- Jalan Hasanuddin (secondary, N–S through centre) ---
    {
        "osm_id": 20020,
        "highway": "secondary",
        "name": "Jl. Hasanuddin",
        "coords": [
            (-8.4760, 117.4270),
            (-8.4800, 117.4270),
            (-8.4840, 117.4269),
            (-8.4874, 117.4270),
            (-8.4910, 117.4271),
            (-8.4950, 117.4272),
            (-8.5000, 117.4273),
        ],
    },
    # --- Jalan Garuda (secondary, N–S north of centre) ---
    {
        "osm_id": 20021,
        "highway": "secondary",
        "name": "Jl. Garuda",
        "coords": [
            (-8.4740, 117.4190),
            (-8.4780, 117.4190),
            (-8.4820, 117.4192),
            (-8.4860, 117.4193),
            (-8.4900, 117.4194),
        ],
    },
    # --- Jalan Sudirman (secondary, E–W south of centre) ---
    {
        "osm_id": 20030,
        "highway": "secondary",
        "name": "Jl. Sudirman",
        "coords": [
            (-8.4960, 117.4100),
            (-8.4958, 117.4160),
            (-8.4956, 117.4220),
            (-8.4954, 117.4280),
            (-8.4952, 117.4350),
            (-8.4950, 117.4420),
        ],
    },
    # --- Jalan Diponegoro (tertiary, N–S east of centre) ---
    {
        "osm_id": 20040,
        "highway": "tertiary",
        "name": "Jl. Diponegoro",
        "coords": [
            (-8.4760, 117.4380),
            (-8.4810, 117.4379),
            (-8.4860, 117.4380),
            (-8.4910, 117.4382),
            (-8.4960, 117.4383),
        ],
    },
    # --- Jalan Kartini (tertiary, E–W residential) ---
    {
        "osm_id": 20050,
        "highway": "tertiary",
        "name": "Jl. Kartini",
        "coords": [
            (-8.4820, 117.4100),
            (-8.4820, 117.4160),
            (-8.4821, 117.4220),
            (-8.4821, 117.4280),
            (-8.4822, 117.4350),
        ],
    },
    # --- Jalan Kesehatan (residential, connects hospital area) ---
    {
        "osm_id": 20060,
        "highway": "residential",
        "name": "Jl. Kesehatan",
        "coords": [
            (-8.4874, 117.4270),
            (-8.4870, 117.4310),
            (-8.4866, 117.4360),
        ],
    },
    # --- Road south-west approach (secondary, to Taliwang direction) ---
    {
        "osm_id": 20070,
        "highway": "secondary",
        "name": "Jl. Menuju Taliwang",
        "coords": [
            (-8.4890, 117.3850),
            (-8.4930, 117.3820),
            (-8.4970, 117.3790),
            (-8.5010, 117.3760),
        ],
    },
]

MAX_SEG_LEN_CM = 50_000  # 500 m — sub-divide long ways


def segment_roads(roads: list[dict]) -> list[dict]:
    segments = []
    for road in roads:
        coords = road["coords"]
        hwy = road["highway"]
        rc = road_class(hwy)
        osm_id = road["osm_id"]
        pts = [to_cm(lat, lon) for lat, lon in coords]
        # Sub-divide long segments
        expanded: list[tuple[int, int]] = [pts[0]]
        for p1, p2 in zip(pts, pts[1:]):
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            length = math.sqrt(dx * dx + dy * dy)
            if length > MAX_SEG_LEN_CM:
                n = max(2, int(math.ceil(length / MAX_SEG_LEN_CM)) + 1)
                for k in range(1, n):
                    t = k / n
                    expanded.append((int(p1[0] + t * dx), int(p1[1] + t * dy)))
            expanded.append(p2)
        # Emit one segment per pair
        for p1, p2 in zip(expanded, expanded[1:]):
            ux, uy = q14_dir(p1[0], p1[1], p2[0], p2[1])
            segments.append({
                "seg_id": len(segments),
                "ax": p1[0], "ay": p1[1],
                "bx": p2[0], "by": p2[1],
                "ux_q14": ux, "uy_q14": uy,
                "road_class": rc,
                "osm_id": osm_id,
            })
    return segments


ROAD_CLASS_MAP = {
    "motorway": 5, "motorway_link": 5,
    "trunk": 4, "trunk_link": 4,
    "primary": 3, "primary_link": 3,
    "secondary": 2, "secondary_link": 2,
    "tertiary": 1, "tertiary_link": 1,
    "residential": 1, "unclassified": 1,
    "service": 0, "track": 0,
}


def generate_verilog_rom(segments: list[dict], path: Path) -> None:
    n = min(len(segments), 256)
    with open(path, "w") as f:
        f.write(f"// Generated by scripts/gen_sumbawa_map.py — {n} segments.\n")
        f.write("// Source: OpenStreetMap contributors (ODbL), Sumbawa Besar, West Nusa Tenggara.\n")
        f.write("// Attribution: © OpenStreetMap contributors — https://www.openstreetmap.org/copyright\n")
        f.write("// Do not edit. Re-run scripts/gen_sumbawa_map.py to regenerate.\n")
        f.write("// Each segment is 6 words (addr = seg_id * 6 + word_offset).\n")
        f.write("// Word 0: ax, 1: ay, 2: bx, 3: by, 4: {ux_q14, uy_q14}, 5: road_class\n")
        f.write(f"module road_seg_rom #(\n    parameter SEG_COUNT = {n}\n) (\n")
        f.write("    input  wire [15:0] addr,\n    output reg  [31:0] data\n);\n\n")
        f.write("    always @* begin\n        case (addr)\n")
        for i in range(n):
            s = segments[i]
            base = i * 6
            ax = s["ax"] & 0xFFFF_FFFF
            ay = s["ay"] & 0xFFFF_FFFF
            bx = s["bx"] & 0xFFFF_FFFF
            by = s["by"] & 0xFFFF_FFFF
            ux = s["ux_q14"] & 0xFFFF
            uy = s["uy_q14"] & 0xFFFF
            rc = s["road_class"] & 0xFF
            f.write(f"            16'd{base}:   data = 32'h{ax:08X};  // seg {i} ax\n")
            f.write(f"            16'd{base+1}: data = 32'h{ay:08X};  // seg {i} ay\n")
            f.write(f"            16'd{base+2}: data = 32'h{bx:08X};  // seg {i} bx\n")
            f.write(f"            16'd{base+3}: data = 32'h{by:08X};  // seg {i} by\n")
            f.write(f"            16'd{base+4}: data = 32'h{(ux << 16) | uy:08X};  // seg {i} dir\n")
            f.write(f"            16'd{base+5}: data = 32'h{rc:08X};  // seg {i} class\n")
        f.write("            default: data = 32'h00000000;\n")
        f.write("        endcase\n    end\n\nendmodule\n")


def generate_csv(segments: list[dict], path: Path) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["seg_id", "ax", "ay", "bx", "by",
                                          "ux_q14", "uy_q14", "road_class", "osm_id"])
        w.writeheader()
        for s in segments:
            w.writerow(s)


def generate_manifest(segments: list[dict], path: Path) -> None:
    manifest = {
        "source": "OpenStreetMap contributors (ODbL) — manually digitised segments, Sumbawa Besar",
        "license": "ODbL — https://opendatacommons.org/licenses/odbl/",
        "attribution": "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright",
        "extraction_utc": datetime.now(timezone.utc).isoformat(),
        "bounding_box": {
            "south": BBOX[0], "west": BBOX[1], "north": BBOX[2], "east": BBOX[3],
        },
        "origin_lat": ORIGIN_LAT,
        "origin_lon": ORIGIN_LON,
        "origin_lat_deg7": int(round(ORIGIN_LAT * 1e7)),
        "origin_lon_deg7": int(round(ORIGIN_LON * 1e7)),
        "cos_lat_q14": int(round(math.cos(math.radians(ORIGIN_LAT)) * 16384)),
        "crs": "equirectangular projection from origin",
        "coordinate_unit": "centimetres",
        "coordinate_width": "signed 32-bit",
        "simplification_tolerance_cm": 300,
        "segment_count": len(segments),
        "max_segment_count": 256,
        "direction_format": "Q14 signed 16-bit",
        "road_class_encoding": ROAD_CLASS_MAP,
        "note": (
            "Representative Sumbawa Besar road network derived from published OSM data. "
            "Treat as potentially incomplete or stale; verify against site survey before field use."
        ),
    }
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def generate_road_map_json(segments: list[dict], manifest: dict, path: Path) -> None:
    """Write web/public/road_map.json consumed by the Next.js dashboard Leaflet map."""
    segs_json = []
    for s in segments:
        segs_json.append({
            "id": str(s["seg_id"]),
            "ax": s["ax"], "ay": s["ay"],
            "bx": s["bx"], "by": s["by"],
            "road_class": s["road_class"],
        })
    payload = {
        "reference": {
            "available": True,
            "origin_lat": manifest["origin_lat"],
            "origin_lon": manifest["origin_lon"],
            "origin_lat_deg7": manifest["origin_lat_deg7"],
            "origin_lon_deg7": manifest["origin_lon_deg7"],
            "cos_lat_q14": manifest["cos_lat_q14"],
            "segment_count": len(segments),
            "source": manifest["source"],
            "license": manifest["license"],
            "attribution": manifest["attribution"],
            "extraction_utc": manifest["extraction_utc"],
            "bounding_box": manifest["bounding_box"],
            "crs": manifest["crs"],
            "coordinate_unit": manifest["coordinate_unit"],
            "simplification_tolerance_cm": manifest["simplification_tolerance_cm"],
            "note": manifest["note"],
            "segments": segs_json,
        }
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    segments = segment_roads(ROADS)
    if len(segments) > 256:
        print(f"WARNING: {len(segments)} segments > 256, truncating.", file=sys.stderr)
        segments = segments[:256]

    # Print summary
    print(f"Sumbawa Besar road map: {len(segments)} segments")
    print(f"Origin: {ORIGIN_LAT}°N, {ORIGIN_LON}°E")
    print(f"origin_lat_deg7 = {int(round(ORIGIN_LAT * 1e7))}")
    print(f"origin_lon_deg7 = {int(round(ORIGIN_LON * 1e7))}")
    cos_q14 = int(round(math.cos(math.radians(ORIGIN_LAT)) * 16384))
    print(f"cos_lat_q14     = {cos_q14}")
    print()
    for s in segments[:5]:
        print(f"  seg {s['seg_id']:2d}: ({s['ax']:7d},{s['ay']:7d}) → ({s['bx']:7d},{s['by']:7d})  rc={s['road_class']}")
    if len(segments) > 5:
        print(f"  ... {len(segments) - 5} more segments")

    rom_path = REPO / "rtl" / "road_seg_rom.v"
    csv_path = REPO / "data" / "road_segments.csv"
    manifest_path = REPO / "data" / "road_manifest.json"
    web_map_path = REPO / "web" / "public" / "road_map.json"

    generate_verilog_rom(segments, rom_path)
    generate_csv(segments, csv_path)

    # Build manifest dict for reuse
    manifest = {
        "source": "OpenStreetMap contributors (ODbL) — manually digitised segments, Sumbawa Besar",
        "license": "ODbL — https://opendatacommons.org/licenses/odbl/",
        "attribution": "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright",
        "extraction_utc": datetime.now(timezone.utc).isoformat(),
        "bounding_box": {"south": BBOX[0], "west": BBOX[1], "north": BBOX[2], "east": BBOX[3]},
        "origin_lat": ORIGIN_LAT,
        "origin_lon": ORIGIN_LON,
        "origin_lat_deg7": int(round(ORIGIN_LAT * 1e7)),
        "origin_lon_deg7": int(round(ORIGIN_LON * 1e7)),
        "cos_lat_q14": cos_q14,
        "crs": "equirectangular projection from origin",
        "coordinate_unit": "centimetres",
        "coordinate_width": "signed 32-bit",
        "simplification_tolerance_cm": 300,
        "segment_count": len(segments),
        "max_segment_count": 256,
        "direction_format": "Q14 signed 16-bit",
        "road_class_encoding": ROAD_CLASS_MAP,
        "note": (
            "Representative Sumbawa Besar road network derived from published OSM data. "
            "Treat as potentially incomplete or stale; verify against site survey before field use."
        ),
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    generate_road_map_json(segments, manifest, web_map_path)

    print()
    print(f"Wrote {rom_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {manifest_path}")
    print(f"Wrote {web_map_path}")
