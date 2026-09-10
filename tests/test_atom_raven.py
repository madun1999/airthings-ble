from datetime import datetime, timezone

import pytest
from airthings_ble.atom.raven import (
    RavenChunk,
    RavenDailyRadonSample,
    RavenEnvironmentalSample,
    RavenHourlyRadonSample,
    RavenTimeAnchor,
    parse_raven_record,
    raven_timestamp,
)


def test_parse_raven_chunk_and_anchor_timestamps() -> None:
    chunk = RavenChunk.parse(
        bytes.fromhex(
            "1a5400004454000003002a00"
            "090e24210a00000372eb8f6a24bb"
            "090e24530a000003a4eb8f6af27d"
            "090e245a0a000003abeb8f6a3cfd"
        )
    )

    assert chunk.start_cursor == 21530
    assert chunk.end_cursor == 21572
    assert chunk.declared_record_count == 3
    assert chunk.declared_record_bytes == 42
    assert all(isinstance(record, RavenTimeAnchor) for record in chunk.records)
    assert raven_timestamp(chunk.records[0], chunk.records[-1]) == datetime(
        2026, 8, 27, 7, 46, 58, tzinfo=timezone.utc
    )


def test_parse_extended_environmental_sample() -> None:
    sample = parse_raven_record(
        bytes.fromhex("091b241b0e0000112e745e161c450c18160100230000400000172a")
    )

    assert isinstance(sample, RavenEnvironmentalSample)
    assert sample.temperature_centikelvin == 29742
    assert sample.temperature_celsius == pytest.approx(24.27)
    assert sample.humidity_hundredths == 5726
    assert sample.humidity_percent == 57.26
    assert sample.battery_mv == 3141
    assert sample.hourly_sequence == 1
    assert sample.extension == bytes.fromhex("1c450c18160100230000400000")


def test_parse_hourly_radon_sample() -> None:
    sample = parse_raven_record(
        bytes.fromhex(
            "096024160e0000214c000000120024000e0018002900000039000000e8035704"
            "0000080b00000000000000000000000000000000463c999c777732585c1902a3"
            "75a91f744a0a0b022900000039000000e80357040000080b1b04000000009b55"
        )
    )

    assert isinstance(sample, RavenHourlyRadonSample)
    assert sample.sequence == 76
    assert sample.hourly_radon_candidate == 0
    assert sample.radon_24h_bq_m3 == 18
    assert sample.radon_24h_statistical == 36
    assert sample.radon_7d_bq_m3 == 14
    assert sample.radon_7d_statistical == 24


def test_parse_daily_radon_sample() -> None:
    sample = parse_raven_record(
        bytes.fromhex(
            "0960245b27010022ec040a005e008001a55a15001a59020060000b0013000b0013"
            "000b00001820400a0000000d0000000200000010000000140000000000000049"
            "0000005000000040007d0566568900400007004f46480040009c00ba8712ae"
        )
    )

    assert isinstance(sample, RavenDailyRadonSample)
    assert sample.hourly_sequence == 96
    assert sample.rolling_average_candidates == (11, 11, 11)
    assert sample.statistical_candidates == (19, 19)


def test_reject_bad_raven_crc() -> None:
    corrupted = bytearray.fromhex("090e24210a00000372eb8f6a24bb")
    corrupted[8] ^= 1

    with pytest.raises(ValueError, match="Invalid Raven record CRC"):
        parse_raven_record(bytes(corrupted))
