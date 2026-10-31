from __future__ import annotations

import unittest

from poc.herdsync_dtn.ble_codec import (
    SUMMARY_BYTES,
    format_status,
    pack_summary,
    parse_peer_command,
)
from poc.herdsync_dtn.uart_frame import (
    TYPE_PEER,
    TYPE_RECORD,
    FrameParser,
    crc16_ccitt,
    decode_peer_summary,
    decode_record_payload,
    encode_frame,
    encode_peer_summary,
    encode_record_payload,
    summarize_frame,
)


class CrcTests(unittest.TestCase):
    def test_ccitt_false_known_vector(self) -> None:
        self.assertEqual(crc16_ccitt(b"123456789"), 0x29B1)


class FrameTests(unittest.TestCase):
    def test_record_frame_round_trip(self) -> None:
        payload = encode_record_payload(
            origin_id=1,
            epoch=1,
            seq=7,
            fix_time_s=12,
            x_cm=-1234,
            y_cm=5678,
            quality=87,
            battery_mv=3620,
            risk=4,
        )
        frame = encode_frame(TYPE_RECORD, payload)
        self.assertEqual(frame[:5], bytes((0xAA, 0x55, 1, TYPE_RECORD, 36)))
        parser = FrameParser()
        decoded = parser.feed(frame)
        self.assertEqual(len(decoded), 1)
        self.assertEqual(decoded[0].payload, payload)
        record = decode_record_payload(decoded[0].payload)
        self.assertEqual(record["origin_id"], 1)
        self.assertEqual(record["seq"], 7)
        self.assertEqual(record["x_cm"], -1234)
        self.assertEqual(record["risk"], 4)
        self.assertEqual(record["auth_tag"], "0000000000000000")

    def test_frame_split_across_feeds(self) -> None:
        payload = encode_peer_summary(3, 99, 44, 1)
        frame = encode_frame(TYPE_PEER, payload)
        parser = FrameParser()
        self.assertEqual(parser.feed(frame[:3]), [])
        self.assertEqual(parser.feed(frame[3:]), parser.frames)
        self.assertEqual(decode_peer_summary(parser.frames[0].payload)["peer_id"], 3)

    def test_noise_and_bad_crc_are_rejected(self) -> None:
        payload = encode_peer_summary(1, 2, 3, 0)
        frame = bytearray(encode_frame(TYPE_PEER, payload))
        frame[-1] ^= 0xFF
        parser = FrameParser()
        self.assertEqual(parser.feed(b"\x00\x11" + bytes(frame)), [])
        self.assertEqual(parser.crc_errors, 1)

    def test_oversized_length_is_rejected(self) -> None:
        parser = FrameParser()
        self.assertEqual(parser.feed(bytes((0xAA, 0x55, 1, 1, 65))), [])
        self.assertEqual(parser.length_errors, 1)

    def test_summary_for_unknown_type(self) -> None:
        frame = encode_frame(9, b"")
        parser = FrameParser()
        parser.feed(frame)
        summary = summarize_frame(parser.frames[0])
        self.assertEqual(summary["error"], "unknown frame type")


class BleCodecTests(unittest.TestCase):
    def _payload(self, **overrides) -> bytes:
        values = dict(
            origin_id=3,
            epoch=1,
            seq=44,
            fix_time_s=30,
            x_cm=-1500,
            y_cm=660,
            quality=99,
            battery_mv=3600,
            risk=3,
        )
        values.update(overrides)
        return encode_record_payload(**values)

    def test_summary_is_twenty_bytes_and_ordered(self) -> None:
        summary = pack_summary(self._payload())
        self.assertEqual(len(summary), SUMMARY_BYTES)
        self.assertEqual(summary[:4], (3).to_bytes(4, "big"))
        self.assertEqual(summary[4:8], (44).to_bytes(4, "big"))
        self.assertEqual(int.from_bytes(summary[12:14], "big", signed=True), -1500)
        self.assertEqual(int.from_bytes(summary[14:16], "big", signed=True), 660)
        self.assertEqual(summary[16], 3)
        self.assertEqual(summary[17], 99)
        self.assertEqual(int.from_bytes(summary[18:20], "big"), 3600)

    def test_summary_clamps_wide_coordinates(self) -> None:
        summary = pack_summary(self._payload(x_cm=100000, y_cm=-100000))
        self.assertEqual(int.from_bytes(summary[12:14], "big", signed=True), 32767)
        self.assertEqual(int.from_bytes(summary[14:16], "big", signed=True), -32768)

    def test_status_text_contains_record_fields(self) -> None:
        status = format_status(self._payload())
        self.assertIn("origin=3", status)
        self.assertIn("seq=44", status)
        self.assertIn("x=-15.00m", status)
        self.assertIn("y=6.60m", status)
        self.assertIn("risk=3", status)

    def test_peer_command_round_trip(self) -> None:
        self.assertEqual(parse_peer_command("2, 7, 30, 1"), (2, 7, 30, 1))

    def test_peer_command_rejects_bad_input(self) -> None:
        for text in ("2,7,30", "2,7,30,9", "x,7,30,1", "2,-1,30,1"):
            with self.assertRaises(ValueError):
                parse_peer_command(text)


if __name__ == "__main__":
    unittest.main()
