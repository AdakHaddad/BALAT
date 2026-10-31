#!/usr/bin/env python3
"""OSM road extraction and FPGA segment ROM generator for BALAT v0.1.

Downloads road geometries from the Overpass API for a given bounding box,
projects to a local metric coordinate system (UTM), simplifies and segments
polylines, computes Q14 unit directions, and emits:

    rtl/road_seg_rom.v   — Verilog ROM with packed segment records
    data/road_segments.csv — human-readable segment list
    data/road_manifest.json — provenance manifest

Requires no third-party packages beyond the Python standard library.
Overpass API is used directly via urllib (no osmnx/geopandas dependency).

Usage:
    python3 scripts/osm_to_segments.py --bbox <south,west,north,east>
    python3 scripts/osm_to_segments.py --bbox -33.83,18.64,-33.82,18.66

If no --bbox is provided, a small demo area near Cape Town is used.
A --csv option allows loading segments from a local CSV instead of OSM.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------
# Coordinate projection: lat/lon -> local metric (simplified UTM)
# ---------------------------------------------------------------

def lat_lon_to_local_cm(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[int, int]:
    """Convert lat/lon to local centimetres relative to origin.

    Uses a simple equirectangular projection (valid for areas < ~50 km).
    x = east, y = north.
    """
    R_EARTH_CM = 637_813_700  # mean Earth radius in cm
    lat_rad = math.radians(lat)
    origin_lat_rad = math.radians(origin_lat)

    dy = R_EARTH_CM * math.radians(lat - origin_lat)
    dx = R_EARTH_CM * math.cos((lat_rad + origin_lat_rad) / 2.0) * math.radians(lon - origin_lon)
    return int(round(dx)), int(round(dy))


# ---------------------------------------------------------------
# Q14 unit direction (matches rtl/road_geom.v)
# ---------------------------------------------------------------

Q_SHIFT = 14
Q_ONE = 1 << Q_SHIFT

def q14_direction(ax: int, ay: int, bx: int, by: int) -> tuple[int, int]:
    """Compute Q14 unit direction from A to B, matching RTL convention."""
    dx = bx - ax
    dy = by - ay
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return 0, 0
    ux = int(round(dx / length * Q_ONE))
    uy = int(round(dy / length * Q_ONE))
    # Clamp to signed 16-bit
    ux = max(-32768, min(32767, ux))
    uy = max(-32768, min(32767, uy))
    return ux, uy


# ---------------------------------------------------------------
# Road class mapping
# ---------------------------------------------------------------

ROAD_CLASS_MAP = {
    "motorway": 5, "motorway_link": 5,
    "trunk": 4, "trunk_link": 4,
    "primary": 3, "primary_link": 3,
    "secondary": 2, "secondary_link": 2,
    "tertiary": 1, "tertiary_link": 1,
    "residential": 1, "unclassified": 1,
    "service": 0, "track": 0,
}


# ---------------------------------------------------------------
# Overpass API query
# ---------------------------------------------------------------

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

ROAD_HIGHWAY_TYPES = [
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "residential", "unclassified",
    "service",
]


def fetch_osm_roads(south: float, west: float, north: float, east: float) -> list[dict]:
    """Fetch road ways from Overpass API."""
    highway_filter = "|".join(ROAD_HIGHWAY_TYPES)
    query = f"""
    [out:json][timeout:30];
    way["highway"~"^({highway_filter})$"]({south},{west},{north},{east});
    out body;>;out skel qt;
    """
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(OVERPASS_URL, data=data, method="POST")
    req.add_header("User-Agent", "BALAT-OSM-Extract/0.1")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["elements"]


def parse_osm_elements(elements: list[dict]) -> list[dict]:
    """Parse Overpass response into road segments with coordinates."""
    nodes = {}
    ways = []
    for el in elements:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way":
            ways.append(el)

    roads = []
    for way in ways:
        tags = way.get("tags", {})
        highway = tags.get("highway", "unclassified")
        name = tags.get("name", "")
        coords = []
        for nid in way.get("nodes", []):
            if nid in nodes:
                coords.append(nodes[nid])
        if len(coords) >= 2:
            roads.append({
                "osm_id": way["id"],
                "highway": highway,
                "name": name,
                "coords": coords,
            })
    return roads


# ---------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------

def segment_roads(
    roads: list[dict],
    origin_lat: float,
    origin_lon: float,
    max_seg_len_cm: int = 50000,  # 500 m max segment
    simplify_tol_cm: int = 200,    # 2 m simplification tolerance
) -> list[dict]:
    """Convert road polylines to local-coordinate line segments."""
    segments = []
    seg_id = 0

    for road in roads:
        highway = road["highway"]
        road_class = ROAD_CLASS_MAP.get(highway, 0)

        # Convert to local cm
        points = [lat_lon_to_local_cm(lat, lon, origin_lat, origin_lon)
                  for lat, lon in road["coords"]]

        # Douglas-Peucker simplification
        points = _simplify(points, simplify_tol_cm)

        # Split into segments
        for i in range(len(points) - 1):
            ax, ay = points[i]
            bx, by = points[i + 1]
            dx = bx - ax
            dy = by - ay
            seg_len = math.sqrt(dx * dx + dy * dy)

            if seg_len > max_seg_len_cm:
                # Sub-divide
                n_sub = int(math.ceil(seg_len / max_seg_len_cm))
                for j in range(n_sub):
                    t0 = j / n_sub
                    t1 = (j + 1) / n_sub
                    sx = int(round(ax + t0 * dx))
                    sy = int(round(ay + t0 * dy))
                    ex = int(round(ax + t1 * dx))
                    ey = int(round(ay + t1 * dy))
                    ux, uy = q14_direction(sx, sy, ex, ey)
                    segments.append({
                        "seg_id": seg_id,
                        "ax": sx, "ay": sy, "bx": ex, "by": ey,
                        "ux_q14": ux, "uy_q14": uy,
                        "road_class": road_class,
                        "osm_id": road.get("osm_id", 0),
                    })
                    seg_id += 1
            else:
                ux, uy = q14_direction(ax, ay, bx, by)
                segments.append({
                    "seg_id": seg_id,
                    "ax": ax, "ay": ay, "bx": bx, "by": by,
                    "ux_q14": ux, "uy_q14": uy,
                    "road_class": road_class,
                    "osm_id": road.get("osm_id", 0),
                })
                seg_id += 1

    return segments


def _simplify(points: list[tuple[int, int]], tol: int) -> list[tuple[int, int]]:
    """Douglas-Peucker simplification."""
    if len(points) <= 2:
        return points

    # Find point with max distance from line (first, last)
    ax, ay = points[0]
    bx, by = points[-1]
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy

    max_dist = 0.0
    max_idx = 0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        if len_sq == 0:
            d = math.sqrt((px - ax) ** 2 + (py - ay) ** 2)
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
            qx = ax + t * dx
            qy = ay + t * dy
            d = math.sqrt((px - qx) ** 2 + (py - qy) ** 2)
        if d > max_dist:
            max_dist = d
            max_idx = i

    if max_dist > tol:
        left = _simplify(points[:max_idx + 1], tol)
        right = _simplify(points[max_idx:], tol)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


# ---------------------------------------------------------------
# Verilog ROM generation
# ---------------------------------------------------------------

MAX_SEGMENTS = 256  # fits in 8-bit address

def generate_rom_verilog(segments: list[dict], path: Path) -> None:
    """Generate a Verilog ROM module for road segments.

    Each record: ax[31:0] ay[31:0] bx[31:0] by[31:0] ux_q14[15:0] uy_q14[15:0] road_class[7:0]
    Total: 4*32 + 2*16 + 8 = 168 bits per record.
    We pack into multiple 32-bit words addressed as (seg_addr * 6 + word_offset).
    Word 0: ax, Word 1: ay, Word 2: bx, Word 3: by, Word 4: {ux_q14, uy_q14}, Word 5: {24'd0, road_class}
    """
    n = min(len(segments), MAX_SEGMENTS)
    with open(path, "w") as f:
        f.write(f"// Generated by scripts/osm_to_segments.py — {n} segments.\n")
        f.write("// Do not edit. Re-run the script to regenerate.\n")
        f.write(f"// Each segment is 6 words (addr = seg_id * 6 + word_offset).\n")
        f.write(f"// Word 0: ax, 1: ay, 2: bx, 3: by, 4: {{ux_q14, uy_q14}}, 5: road_class\n")
        f.write(f"module road_seg_rom #(\n")
        f.write(f"    parameter SEG_COUNT = {n}\n")
        f.write(f") (\n")
        f.write(f"    input  wire [15:0] addr,\n")
        f.write(f"    output reg  [31:0] data\n")
        f.write(f");\n\n")
        f.write(f"    always @* begin\n")
        f.write(f"        case (addr)\n")

        for i in range(n):
            s = segments[i]
            base = i * 6
            ax = s["ax"] & 0xFFFFFFFF
            ay = s["ay"] & 0xFFFFFFFF
            bx = s["bx"] & 0xFFFFFFFF
            by = s["by"] & 0xFFFFFFFF
            ux = s["ux_q14"] & 0xFFFF
            uy = s["uy_q14"] & 0xFFFF
            rc = s["road_class"] & 0xFF

            f.write(f"            16'd{base}:   data = 32'h{ax:08X};  // seg {i} ax\n")
            f.write(f"            16'd{base+1}: data = 32'h{ay:08X};  // seg {i} ay\n")
            f.write(f"            16'd{base+2}: data = 32'h{bx:08X};  // seg {i} bx\n")
            f.write(f"            16'd{base+3}: data = 32'h{by:08X};  // seg {i} by\n")
            f.write(f"            16'd{base+4}: data = 32'h{(ux << 16) | uy:08X};  // seg {i} dir\n")
            f.write(f"            16'd{base+5}: data = 32'h{rc:08X};  // seg {i} class\n")

        f.write(f"            default: data = 32'h00000000;\n")
        f.write(f"        endcase\n")
        f.write(f"    end\n\n")
        f.write(f"endmodule\n")


def generate_csv(segments: list[dict], path: Path) -> None:
    """Write segments to CSV."""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "seg_id", "ax", "ay", "bx", "by", "ux_q14", "uy_q14", "road_class", "osm_id"
        ])
        w.writeheader()
        for s in segments:
            w.writerow(s)


def generate_manifest(
    segments: list[dict],
    bbox: tuple[float, float, float, float],
    origin: tuple[float, float],
    simplify_tol: int,
    path: Path,
) -> None:
    """Write a JSON manifest for provenance."""
    manifest = {
        "source": "OpenStreetMap via Overpass API",
        "license": "ODbL — https://opendatacommons.org/licenses/odbl/",
        "extraction_utc": datetime.now(timezone.utc).isoformat(),
        "bounding_box": {"south": bbox[0], "west": bbox[1], "north": bbox[2], "east": bbox[3]},
        "origin_lat": origin[0],
        "origin_lon": origin[1],
        "crs": "equirectangular projection from origin",
        "coordinate_unit": "centimetres",
        "coordinate_width": "signed 32-bit",
        "simplification_tolerance_cm": simplify_tol,
        "segment_count": len(segments),
        "max_segment_count": MAX_SEGMENTS,
        "direction_format": "Q14 signed 16-bit",
        "road_class_encoding": ROAD_CLASS_MAP,
    }
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------
# Manual correction: load extra segments from CSV
# ---------------------------------------------------------------

def load_corrections(csv_path: Path, origin_lat: float, origin_lon: float) -> list[dict]:
    """Load manual road corrections from CSV.

    CSV columns: lat1, lon1, lat2, lon2, road_class
    Converts to local cm and creates segments.
    """
    if not csv_path.exists():
        return []
    segments = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            ax, ay = lat_lon_to_local_cm(float(row["lat1"]), float(row["lon1"]), origin_lat, origin_lon)
            bx, by = lat_lon_to_local_cm(float(row["lat2"]), float(row["lon2"]), origin_lat, origin_lon)
            ux, uy = q14_direction(ax, ay, bx, by)
            segments.append({
                "seg_id": -1,  # renumbered later
                "ax": ax, "ay": ay, "bx": bx, "by": by,
                "ux_q14": ux, "uy_q14": uy,
                "road_class": int(row.get("road_class", 1)),
                "osm_id": 0,
            })
    return segments


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def make_sample_roads(origin_lat: float, origin_lon: float) -> list[dict]:
    """Generate deterministic synthetic roads for offline testing."""
    # Two intersecting roads: one north-south, one east-west
    dlat = 0.005  # ~550 m
    dlon = 0.006  # ~550 m
    return [
        {
            "osm_id": 1001,
            "highway": "primary",
            "name": "Route 1",
            "coords": [
                (origin_lat - dlat, origin_lon),
                (origin_lat, origin_lon),
                (origin_lat + dlat, origin_lon),
            ],
        },
        {
            "osm_id": 1002,
            "highway": "secondary",
            "name": "Cross Road",
            "coords": [
                (origin_lat, origin_lon - dlon),
                (origin_lat, origin_lon),
                (origin_lat, origin_lon + dlon),
            ],
        },
    ]


def main():
    parser = argparse.ArgumentParser(description="Extract OSM roads for BALAT FPGA.")
    parser.add_argument("--bbox", type=str, default="-33.83,18.64,-33.82,18.66",
                        help="south,west,north,east bounding box")
    parser.add_argument("--corrections", type=str, default="data/road_corrections.csv",
                        help="CSV of manual corrections (lat1,lon1,lat2,lon2,road_class)")
    parser.add_argument("--simplify", type=int, default=200,
                        help="Simplification tolerance in cm (default 200 = 2 m)")
    parser.add_argument("--max-seg-len", type=int, default=50000,
                        help="Max segment length in cm (default 50000 = 500 m)")
    parser.add_argument("--csv", type=str, default=None,
                        help="Load segments from a local CSV instead of OSM")
    parser.add_argument("--offline", action="store_true",
                        help="Use offline synthetic road network instead of Overpass")
    args = parser.parse_args()

    bbox = tuple(float(x) for x in args.bbox.split(","))
    assert len(bbox) == 4, "bbox must be south,west,north,east"
    origin_lat = (bbox[0] + bbox[2]) / 2.0
    origin_lon = (bbox[1] + bbox[3]) / 2.0

    if args.csv:
        print(f"Loading segments from {args.csv}...")
        segments = []
        with open(args.csv) as f:
            for row in csv.DictReader(f):
                segments.append({
                    "seg_id": int(row["seg_id"]),
                    "ax": int(row["ax"]), "ay": int(row["ay"]),
                    "bx": int(row["bx"]), "by": int(row["by"]),
                    "ux_q14": int(row["ux_q14"]), "uy_q14": int(row["uy_q14"]),
                    "road_class": int(row["road_class"]),
                    "osm_id": int(row.get("osm_id", 0)),
                })
    elif args.offline:
        print("Using synthetic road layout (offline mode)...")
        roads = make_sample_roads(origin_lat, origin_lon)
        segments = segment_roads(roads, origin_lat, origin_lon,
                                 max_seg_len_cm=args.max_seg_len,
                                 simplify_tol_cm=args.simplify)
    else:
        print(f"Fetching OSM roads for bbox {bbox}...")
        try:
            elements = fetch_osm_roads(*bbox)
            roads = parse_osm_elements(elements)
            print(f"  Found {len(roads)} road ways.")
            segments = segment_roads(roads, origin_lat, origin_lon,
                                     max_seg_len_cm=args.max_seg_len,
                                     simplify_tol_cm=args.simplify)
        except Exception as exc:
            print(f"  Overpass fetch failed ({exc}); falling back to offline synthetic roads.")
            roads = make_sample_roads(origin_lat, origin_lon)
            segments = segment_roads(roads, origin_lat, origin_lon,
                                     max_seg_len_cm=args.max_seg_len,
                                     simplify_tol_cm=args.simplify)

    # Load manual corrections
    corrections_path = REPO / args.corrections
    corrections = load_corrections(corrections_path, origin_lat, origin_lon)
    if corrections:
        print(f"  Added {len(corrections)} manual correction segments.")
        segments.extend(corrections)

    # Renumber
    for i, s in enumerate(segments):
        s["seg_id"] = i

    if len(segments) > MAX_SEGMENTS:
        print(f"  WARNING: {len(segments)} segments exceeds MAX_SEGMENTS={MAX_SEGMENTS}; truncating.")
        segments = segments[:MAX_SEGMENTS]

    print(f"  Total: {len(segments)} segments.")

    # Generate outputs
    rom_path = REPO / "rtl" / "road_seg_rom.v"
    csv_path = REPO / "data" / "road_segments.csv"
    manifest_path = REPO / "data" / "road_manifest.json"

    generate_rom_verilog(segments, rom_path)
    generate_csv(segments, csv_path)
    generate_manifest(segments, bbox, (origin_lat, origin_lon), args.simplify, manifest_path)

    print(f"  Wrote {rom_path}")
    print(f"  Wrote {csv_path}")
    print(f"  Wrote {manifest_path}")


if __name__ == "__main__":
    main()
