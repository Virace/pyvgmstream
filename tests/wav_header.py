from __future__ import annotations

import struct
from pathlib import Path


def inspect_wav_header(payload: bytes) -> dict[str, int]:
    if payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        raise AssertionError("payload is not a RIFF/WAVE file")

    fmt_offset = payload.find(b"fmt ")
    data_offset = payload.find(b"data")
    if fmt_offset < 0 or data_offset < 0:
        raise AssertionError("payload is missing fmt/data chunks")

    fmt_chunk_size = struct.unpack_from("<I", payload, fmt_offset + 4)[0]
    if fmt_chunk_size < 16:
        raise AssertionError("fmt chunk is too small")

    (
        format_code,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    ) = struct.unpack_from("<HHIIHH", payload, fmt_offset + 8)
    data_size = struct.unpack_from("<I", payload, data_offset + 4)[0]

    return {
        "format_code": format_code,
        "channels": channels,
        "sample_rate": sample_rate,
        "byte_rate": byte_rate,
        "block_align": block_align,
        "bits_per_sample": bits_per_sample,
        "data_size": data_size,
        "data_offset": data_offset + 8,
    }


def inspect_wav_file(path: Path) -> dict[str, int]:
    return inspect_wav_header(path.read_bytes())
