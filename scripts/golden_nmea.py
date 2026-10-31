#!/usr/bin/env python3
"""Golden NMEA parser model and test-vector generator for tb_nmea_parser.

Mirrors the RTL nmea_parser.v coordinate conversion exactly:
  - Parse ddmm.mmmm (lat) or dddmm.mmmm (lon) from NMEA RMC sentence.
  - Convert to 1e-7 degrees using: deg7 = deg*10_000_000 + div3(min_combined*50)
    where min_combined = min_int*10000 + min_frac (padded to 4 digits).
  - div3 rounds: if remainder >= 2, round up.

Generates:
  tb/nmea_test_vectors.txt  — test vectors for Verilog $readmemh.

No third-party packages required.
"""

from __future__ import annotations

import struct
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def div3_round(x: int) -> int:
    """Divide by 3 with rounding (match RTL)."""
    q, r = divmod(x, 3)
    return q + 1 if r >= 2 else q


def nmea_coord_to_deg7(field: str, deg_digits: int) -> int:
    """Convert NMEA coordinate field to 1e-7 degrees (unsigned).

    field: e.g. "4807.0380" for latitude (deg_digits=2)
           or "01131.0000" for longitude (deg_digits=3)
    """
    if "." in field:
        int_part, frac_part = field.split(".")
    else:
        int_part = field
        frac_part = ""

    deg = int(int_part[:deg_digits])
    min_int = int(int_part[deg_digits:]) if len(int_part) > deg_digits else 0

    # Pad fractional part to exactly 4 digits
    frac_part = frac_part[:4]  # truncate beyond 4
    frac_part = frac_part.ljust(4, "0")  # pad to 4
    min_frac = int(frac_part)

    min_combined = min_int * 10000 + min_frac
    min_x50 = min_combined * 50
    min_deg7 = div3_round(min_x50)
    return deg * 10_000_000 + min_deg7


def nmea_checksum(sentence_body: str) -> str:
    """XOR checksum of chars between $ and *."""
    xor = 0
    for ch in sentence_body:
        xor ^= ord(ch)
    return f"{xor:02X}"


def make_rmc(
    utc: str = "123519.00",
    status: str = "A",
    lat: str = "4807.0380",
    ns: str = "N",
    lon: str = "01131.0000",
    ew: str = "E",
    speed: str = "0.0",
    course: str = "0.0",
    date: str = "231003",
    mag: str = "",
    mode: str = "A",
    talker: str = "GP",
) -> str:
    """Build a complete $xxRMC sentence with checksum."""
    body = f"{talker}RMC,{utc},{status},{lat},{ns},{lon},{ew},{speed},{course},{date},{mag},{mode}"
    ck = nmea_checksum(body)
    return f"${body}*{ck}\r\n"


def parse_rmc_golden(sentence: str) -> dict | None:
    """Parse RMC sentence and return expected outputs, or None if invalid."""
    if not sentence.startswith("$"):
        return None
    # Verify checksum
    star = sentence.index("*")
    body = sentence[1:star]
    expected_ck = sentence[star + 1 : star + 3]
    actual_ck = nmea_checksum(body)
    if expected_ck.upper() != actual_ck.upper():
        return None

    fields = body.split(",")
    # fields[0] = talker+RMC
    if not fields[0].endswith("RMC"):
        return None
    talker = fields[0][:-3]
    if talker not in ("GP", "GN"):
        return None

    utc_str = fields[1]
    status = fields[2]
    lat_str = fields[3]
    ns = fields[4]
    lon_str = fields[5]
    ew = fields[6]
    speed_str = fields[7]

    # UTC: hhmmss -> packed BCD
    utc_digits = utc_str.split(".")[0]
    utc_digits = utc_digits.ljust(6, "0")[:6]
    utc_bcd = 0
    for i, d in enumerate(utc_digits):
        utc_bcd |= int(d) << (4 * (5 - i))

    fix_valid = 1 if status == "A" else 0

    lat_deg7 = nmea_coord_to_deg7(lat_str, 2)
    if ns in ("S", "s"):
        lat_deg7 = -lat_deg7

    lon_deg7 = nmea_coord_to_deg7(lon_str, 3)
    if ew in ("W", "w"):
        lon_deg7 = -lon_deg7

    # Speed: convert to 1/100 knot
    if "." in speed_str:
        s_int, s_frac = speed_str.split(".")
    else:
        s_int = speed_str
        s_frac = ""
    s_int_val = int(s_int) if s_int else 0
    s_frac = s_frac[:2]
    frac_d = len(s_frac)
    s_frac_val = int(s_frac) if s_frac else 0
    if frac_d == 0:
        speed_100 = s_int_val * 100
    elif frac_d == 1:
        speed_100 = s_int_val * 100 + s_frac_val * 10
    else:
        speed_100 = s_int_val * 100 + s_frac_val

    return {
        "lat_deg7": lat_deg7,
        "lon_deg7": lon_deg7,
        "speed_kn": speed_100,
        "utc_time": utc_bcd,
        "fix_valid": fix_valid,
    }


# ---------------------------------------------------------------
# Test vectors
# ---------------------------------------------------------------
TEST_CASES = [
    # (description, sentence_builder_kwargs, expect_valid_output)
    (
        "Basic GPRMC, north-east",
        dict(talker="GP", lat="4807.0380", ns="N", lon="01131.0000", ew="E",
             speed="0.5", utc="123519.00", status="A"),
        True,
    ),
    (
        "GNRMC, south-west",
        dict(talker="GN", lat="3349.8000", ns="S", lon="07051.0000", ew="W",
             speed="12.3", utc="091500.00", status="A"),
        True,
    ),
    (
        "Void fix (status V)",
        dict(talker="GP", lat="0000.0000", ns="N", lon="00000.0000", ew="E",
             speed="0.0", utc="000000.00", status="V"),
        True,  # sentence is valid, but fix_valid=0
    ),
    (
        "High speed, high latitude",
        dict(talker="GN", lat="8959.9999", ns="N", lon="17959.9999", ew="E",
             speed="99.9", utc="235959.00", status="A"),
        True,
    ),
    (
        "Zero coordinates",
        dict(talker="GP", lat="0000.0000", ns="N", lon="00000.0000", ew="E",
             speed="0.0", utc="120000.00", status="A"),
        True,
    ),
]


def generate_test_vectors():
    """Generate test vector file for Verilog testbench."""
    vectors = []
    print("NMEA Parser Golden Model — Test Vectors")
    print("=" * 60)

    for desc, kwargs, expect_valid in TEST_CASES:
        sentence = make_rmc(**kwargs)
        result = parse_rmc_golden(sentence)
        sentence_clean = sentence.strip()

        print(f"\n{desc}")
        print(f"  Sentence: {sentence_clean}")
        if result:
            print(f"  lat_deg7:  {result['lat_deg7']:>12d}  ({result['lat_deg7']/1e7:.7f}°)")
            print(f"  lon_deg7:  {result['lon_deg7']:>12d}  ({result['lon_deg7']/1e7:.7f}°)")
            print(f"  speed_kn:  {result['speed_kn']:>12d}  ({result['speed_kn']/100:.2f} kn)")
            print(f"  utc_time:  0x{result['utc_time']:06X}")
            print(f"  fix_valid: {result['fix_valid']}")

        # Vector format: sentence bytes (hex), then expected outputs
        # Each line: <sentence_hex> <lat_deg7_hex> <lon_deg7_hex> <speed_hex> <utc_hex> <fix_valid>
        sentence_bytes = sentence_clean.encode("ascii")
        vectors.append({
            "desc": desc,
            "sentence": sentence_clean,
            "bytes_hex": sentence_bytes.hex(),
            "lat_deg7": result["lat_deg7"] if result else 0,
            "lon_deg7": result["lon_deg7"] if result else 0,
            "speed_kn": result["speed_kn"] if result else 0,
            "utc_time": result["utc_time"] if result else 0,
            "fix_valid": result["fix_valid"] if result else 0,
            "expect_output": expect_valid and result is not None,
        })

    # Write vector file for Verilog
    vec_path = REPO / "tb" / "nmea_test_vectors.txt"
    with open(vec_path, "w") as f:
        f.write("// Auto-generated by scripts/golden_nmea.py\n")
        f.write("// Format: one sentence per block.\n")
        f.write("// Line 1: expected lat_deg7 (signed hex 32-bit)\n")
        f.write("// Line 2: expected lon_deg7 (signed hex 32-bit)\n")
        f.write("// Line 3: expected speed_kn (hex 16-bit)\n")
        f.write("// Line 4: expected utc_time (hex 24-bit)\n")
        f.write("// Line 5: fix_valid (0 or 1)\n")
        f.write("// Line 6: expect_fix_ready (0 or 1)\n")
        f.write("// Line 7: sentence byte count (hex)\n")
        f.write("// Lines 8+: sentence bytes (hex, one per line)\n")
        f.write("//\n")
        for v in vectors:
            f.write(f"// {v['desc']}\n")
            lat = v["lat_deg7"] & 0xFFFFFFFF
            lon = v["lon_deg7"] & 0xFFFFFFFF
            f.write(f"{lat:08X}\n")
            f.write(f"{lon:08X}\n")
            f.write(f"{v['speed_kn']:04X}\n")
            f.write(f"{v['utc_time']:06X}\n")
            f.write(f"{v['fix_valid']:01X}\n")
            f.write(f"{1 if v['expect_output'] else 0:01X}\n")
            bdata = v["sentence"].encode("ascii")
            f.write(f"{len(bdata):02X}\n")
            for b in bdata:
                f.write(f"{b:02X}\n")
            f.write("//\n")

    print(f"\nWrote {len(vectors)} vectors to {vec_path}")

    # Also add bad-checksum test (should NOT produce fix_ready)
    bad_sentence = "$GPRMC,120000.00,A,4807.0380,N,01131.0000,E,0.0,0.0,231003,,A*00\r\n"
    f2_path = REPO / "tb" / "nmea_bad_vectors.txt"
    with open(f2_path, "w") as f:
        f.write("// Bad checksum sentence — should NOT produce fix_ready\n")
        bdata = bad_sentence.strip().encode("ascii")
        f.write(f"{len(bdata):02X}\n")
        for b in bdata:
            f.write(f"{b:02X}\n")
    print(f"Wrote bad-checksum vector to {f2_path}")


if __name__ == "__main__":
    generate_test_vectors()
