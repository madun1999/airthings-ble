#!/usr/bin/env python3
"""Capture exactly one consuming Raven history response and persist it safely."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import cbor2
from airthings_ble.atom.raven import RavenChunk
from airthings_ble.atom.request import AtomRequest
from airthings_ble.atom.request_path import AtomRequestPath
from airthings_ble.const import COMMAND_UUID_ATOM, COMMAND_UUID_ATOM_NOTIFY
from bleak import BleakScanner
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

_LOGGER = logging.getLogger("raven-capture")
_CONFIRMATION = "I UNDERSTAND THIS READ MAY CONSUME DEVICE HISTORY"


class _NotificationCollector:
    """Collect notification fragments until the connection becomes quiet."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.changed = asyncio.Event()

    def __call__(self, _sender: Any, data: bytearray) -> None:
        self.data.extend(data)
        self.changed.set()

    async def wait(self, first_timeout: float = 10, quiet_time: float = 0.5) -> bytes:
        await asyncio.wait_for(self.changed.wait(), first_timeout)
        while True:
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), quiet_time)
            except TimeoutError:
                return bytes(self.data)


def _extract_chunk(response: bytes, request: AtomRequest) -> bytes:
    if response[:5] != bytes.fromhex("1001000345"):
        raise ValueError("invalid ATOM response header")
    if response[5:7] != request.random_bytes:
        raise ValueError("ATOM response request token does not match")
    decoded = cbor2.loads(response[7:])
    if not isinstance(decoded, list) or not decoded or not isinstance(decoded[0], dict):
        raise ValueError("invalid ATOM response body")
    envelope = decoded[0]
    if envelope.get(0) != AtomRequestPath.RAVEN_HISTORY.value:
        raise ValueError("ATOM response path does not match Raven history")
    chunk = envelope.get(2)
    if not isinstance(chunk, bytes):
        raise ValueError("Raven history response does not contain bytes")
    return chunk


def _persist_once(path: Path, data: bytes) -> None:
    """Create and fsync a new file; never overwrite a previous capture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


async def _capture(address: str, output: Path) -> None:
    device = await BleakScanner.find_device_by_address(address, timeout=20)
    if device is None:
        raise RuntimeError(f"Bluetooth device {address} was not discovered")

    request = AtomRequest(AtomRequestPath.RAVEN_HISTORY)
    collector = _NotificationCollector()
    client = await establish_connection(
        BleakClientWithServiceCache,
        device,
        device.name or address,
        max_attempts=3,
    )
    try:
        await client.start_notify(COMMAND_UUID_ATOM_NOTIFY, collector)
        await client.write_gatt_char(COMMAND_UUID_ATOM, request.as_bytes())
        response = await collector.wait()
        _persist_once(output, response)
    finally:
        if client.is_connected:
            await client.disconnect()

    chunk = RavenChunk.parse(_extract_chunk(response, request))
    print(
        f"saved {len(response)} bytes to {output}; "
        f"records={len(chunk.records)} cursors={chunk.start_cursor}..{chunk.end_cursor}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture one potentially consuming Corentium Raven history response"
    )
    parser.add_argument("address", help="Bluetooth address")
    parser.add_argument("output", type=Path, help="new file for the raw ATOM response")
    parser.add_argument(
        "--confirm",
        metavar="TEXT",
        help=f"required literal confirmation: {_CONFIRMATION!r}",
    )
    args = parser.parse_args()
    if args.confirm != _CONFIRMATION:
        parser.error(f"--confirm must equal {_CONFIRMATION!r}")
    asyncio.run(_capture(args.address, args.output))


if __name__ == "__main__":
    main()
