"""Decode Raven history payloads returned by the Airthings ATOM API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_RECORD_MARKER = 0x09
_RECORD_TAG = 0x24
_CRC_SIZE = 2


def _u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def _u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little")


def _crc16_x25(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc ^ 0xFFFF


@dataclass(frozen=True)
class RavenRecord:
    """Common Raven record fields."""

    counter: int
    record_type: int
    raw: bytes


@dataclass(frozen=True)
class RavenTimeAnchor(RavenRecord):
    """Mapping between the device-relative counter and Unix time."""

    unix_seconds: int

    @property
    def timestamp(self) -> datetime:
        """Return the anchor's UTC timestamp."""
        return datetime.fromtimestamp(self.unix_seconds, timezone.utc)


@dataclass(frozen=True)
class RavenEnvironmentalSample(RavenRecord):
    """Five-minute temperature and humidity sample."""

    temperature_centikelvin: int
    humidity_hundredths: int
    battery_mv: int | None = None
    hourly_sequence: int | None = None
    extension: bytes | None = None

    @property
    def temperature_celsius(self) -> float:
        """Return temperature in degrees Celsius."""
        return self.temperature_centikelvin / 100.0 - 273.15

    @property
    def humidity_percent(self) -> float:
        """Return relative humidity as a percentage."""
        return self.humidity_hundredths / 100.0


@dataclass(frozen=True)
class RavenHourlyRadonSample(RavenRecord):
    """Hourly radon record with confirmed rolling averages."""

    sequence: int
    hourly_radon_candidate: int
    radon_24h_bq_m3: int
    radon_24h_statistical: int
    radon_7d_bq_m3: int
    radon_7d_statistical: int
    payload: bytes


@dataclass(frozen=True)
class RavenDailyRadonSample(RavenRecord):
    """Daily record containing three not-yet-ordered rolling averages."""

    hourly_sequence: int
    rolling_average_candidates: tuple[int, int, int]
    statistical_candidates: tuple[int, int]
    payload: bytes


@dataclass(frozen=True)
class RavenUnknownRecord(RavenRecord):
    """Checksum-valid Raven record whose type is not decoded."""

    payload: bytes


@dataclass(frozen=True)
class RavenChunk:
    """One Raven history chunk returned by endpoint 30018/0/31001."""

    start_cursor: int
    end_cursor: int
    declared_record_count: int
    declared_record_bytes: int
    records: tuple[RavenRecord, ...]

    @classmethod
    def parse(cls, data: bytes) -> RavenChunk:
        """Parse and validate a complete inner Raven chunk."""
        if len(data) < 12:
            raise ValueError("Raven chunk is shorter than its 12-byte header")

        record_count = _u16(data, 8)
        record_bytes = _u16(data, 10)
        if len(data) - 12 != record_bytes:
            raise ValueError(
                f"Raven chunk declares {record_bytes} record bytes, "
                f"got {len(data) - 12}"
            )

        records: list[RavenRecord] = []
        offset = 12
        while offset < len(data):
            if offset + 2 > len(data):
                raise ValueError("Truncated Raven record header")
            length = data[offset + 1]
            if length < 10 or offset + length > len(data):
                raise ValueError(f"Invalid Raven record length {length}")
            records.append(parse_raven_record(data[offset : offset + length]))
            offset += length

        if len(records) != record_count:
            raise ValueError(
                f"Raven chunk declares {record_count} records, got {len(records)}"
            )

        return cls(
            start_cursor=_u32(data, 0),
            end_cursor=_u32(data, 4),
            declared_record_count=record_count,
            declared_record_bytes=record_bytes,
            records=tuple(records),
        )


def parse_raven_record(data: bytes) -> RavenRecord:
    """Parse and checksum one complete Raven record."""
    if len(data) < 10 or data[0] != _RECORD_MARKER:
        raise ValueError("Invalid Raven record marker or size")
    if data[1] != len(data):
        raise ValueError(f"Raven record declares length {data[1]}, got {len(data)}")
    if data[2] != _RECORD_TAG:
        raise ValueError(f"Unexpected Raven record tag 0x{data[2]:02x}")
    expected_crc = _u16(data, len(data) - _CRC_SIZE)
    actual_crc = _crc16_x25(data[:-_CRC_SIZE])
    if actual_crc != expected_crc:
        raise ValueError(
            f"Invalid Raven record CRC: expected 0x{expected_crc:04x}, "
            f"calculated 0x{actual_crc:04x}"
        )

    counter = _u32(data, 3)
    record_type = data[7]
    common = {"counter": counter, "record_type": record_type, "raw": data}

    if record_type == 0x03 and len(data) == 14:
        return RavenTimeAnchor(**common, unix_seconds=_u32(data, 8))

    if record_type == 0x11 and len(data) in (14, 27):
        extension = data[12:-2] if len(data) == 27 else None
        battery_mv = _u16(data, 13) if extension is not None else None
        hourly_sequence = _u16(data, 17) if extension is not None else None
        return RavenEnvironmentalSample(
            **common,
            temperature_centikelvin=_u16(data, 8),
            humidity_hundredths=_u16(data, 10),
            battery_mv=battery_mv,
            hourly_sequence=hourly_sequence,
            extension=extension,
        )

    if record_type == 0x21 and len(data) == 96:
        return RavenHourlyRadonSample(
            **common,
            sequence=_u16(data, 8),
            hourly_radon_candidate=_u16(data, 10),
            radon_24h_bq_m3=_u16(data, 12),
            radon_24h_statistical=_u16(data, 14),
            radon_7d_bq_m3=_u16(data, 16),
            radon_7d_statistical=_u16(data, 18),
            payload=data[8:-2],
        )

    if record_type == 0x22 and len(data) == 96:
        return RavenDailyRadonSample(
            **common,
            hourly_sequence=_u16(data, 24),
            rolling_average_candidates=(_u16(data, 26), _u16(data, 30), _u16(data, 34)),
            statistical_candidates=(_u16(data, 28), _u16(data, 32)),
            payload=data[8:-2],
        )

    return RavenUnknownRecord(**common, payload=data[8:-2])


def raven_timestamp(record: RavenRecord, anchor: RavenTimeAnchor) -> datetime:
    """Map a record's device-relative counter to UTC using a time anchor."""
    return anchor.timestamp + timedelta(seconds=record.counter - anchor.counter)
