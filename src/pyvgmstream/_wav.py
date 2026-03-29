"""WAV 封装辅助工具。"""

from __future__ import annotations

from os import PathLike
from pathlib import Path
import struct

from .models import SampleFormat


PathInput = str | PathLike[str]


def build_wav_payload(
    *,
    sample_format: SampleFormat,
    sample_rate: int,
    channels: int,
    sample_size: int,
    frame_count: int,
    pcm_payload: bytes,
) -> bytes:
    """为给定帧数据构造完整 WAV 负载。"""

    header = build_wav_header(
        sample_format=sample_format,
        sample_rate=sample_rate,
        channels=channels,
        sample_size=sample_size,
        frame_count=frame_count,
        data_size=len(pcm_payload),
    )
    return header + pcm_payload


def write_wav_file(
    path: PathInput,
    *,
    sample_format: SampleFormat,
    sample_rate: int,
    channels: int,
    sample_size: int,
    frame_count: int,
    pcm_payload: bytes,
) -> None:
    """把给定帧数据写成 WAV 文件。"""

    output_path = Path(path).expanduser().resolve()
    output_path.write_bytes(
        build_wav_payload(
            sample_format=sample_format,
            sample_rate=sample_rate,
            channels=channels,
            sample_size=sample_size,
            frame_count=frame_count,
            pcm_payload=pcm_payload,
        )
    )


def build_wav_header(
    *,
    sample_format: SampleFormat,
    sample_rate: int,
    channels: int,
    sample_size: int,
    frame_count: int,
    data_size: int,
) -> bytes:
    """构造最小 WAV 头。"""

    format_code = _resolve_wav_format_code(sample_format)
    bits_per_sample = sample_size * 8
    block_align = channels * sample_size
    byte_rate = sample_rate * block_align

    fmt_chunk = (
        b"fmt "
        + struct.pack(
            "<IHHIIHH",
            16,
            format_code,
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
        )
    )
    fact_chunk = (
        b"fact" + struct.pack("<II", 4, frame_count)
        if sample_format is SampleFormat.FLOAT
        else b""
    )
    data_chunk_header = b"data" + struct.pack("<I", data_size)
    riff_size = 4 + len(fmt_chunk) + len(fact_chunk) + len(data_chunk_header) + data_size
    return b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + fmt_chunk + fact_chunk + data_chunk_header


def _resolve_wav_format_code(sample_format: SampleFormat) -> int:
    """把采样格式映射到 WAV format code。"""

    if sample_format is SampleFormat.FLOAT:
        return 3
    return 1
