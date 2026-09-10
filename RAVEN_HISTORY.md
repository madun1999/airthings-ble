# Raven history status

Corentium Home 2 exposes Raven history through ATOM path `30018/0/31001`.
Captured payloads contain a 12-byte chunk header followed by checksum-protected
records. `airthings_ble.atom.raven.RavenChunk` validates the chunk lengths,
record framing, and CRC-16/X-25 checksums.

## Safety boundary

Observed GET requests advance the history stream. No replay request or
acknowledgement has been identified. Treat every request as destructive. The
Home Assistant integration does not access this endpoint.

`tools/capture_raven_chunk.py` performs exactly one request, creates a new raw
response file with exclusive-create semantics, flushes it to durable storage,
and disconnects. It refuses to run without an explicit warning acknowledgement:

```bash
python tools/capture_raven_chunk.py 30:AF:7E:26:60:69 captures/chunk-001.atom \
  --confirm 'I UNDERSTAND THIS READ MAY CONSUME DEVICE HISTORY'
```

Stop Home Assistant polling and close the Airthings app before capture. Use a
new output filename for every run. The command saves the complete outer ATOM
response before attempting to decode it, so an unknown payload remains
available for later analysis.

## Confirmed structure

- Chunk header: little-endian start cursor, end cursor, record count, and record
  byte count.
- Record marker `0x09`, tag `0x24`, embedded length, device-relative counter,
  type, payload, and CRC-16/X-25.
- Type `0x03`: relative-counter to Unix-time anchor.
- Type `0x11`: five-minute temperature and humidity; extended records also
  contain battery voltage and an hourly sequence candidate.
- Type `0x21`: hourly radon record with confirmed 24-hour and seven-day rolling
  average fields.
- Type `0x22`: daily radon record with rolling-average candidates whose ordering
  is not yet confirmed.

## Unknowns blocking automatic synchronization

1. The unambiguous end-of-history response and whether requesting it advances
   state.
2. Cursor continuity rules across reconnects, device resets, and ring-buffer
   wraparound.
3. Whether any request can replay a prior cursor or acknowledge a chunk.
4. Exact timestamp semantics during clock changes and daylight-saving changes.
5. Ordering and units of all type `0x22` rolling and statistical fields.
6. Meaning of the remaining type `0x11`, `0x21`, and `0x22` payload bytes.
7. Whether firmware revisions change framing, checksums, or endpoint behavior.

Automatic import remains unsafe until at least items 1–3 are resolved and a
crash-resumable raw-chunk journal exists.
