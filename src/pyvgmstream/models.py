from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StreamInfo:
    source_path: str
    subsong: int
    backend_name: str
    sample_rate: int
    channels: int
    subsong_count: int
    loop_flag: bool
    codec_name: str
    layout_name: str
    meta_name: str


@dataclass(frozen=True, slots=True)
class DecodeResult:
    output_path: Path
    sample_rate: int
    channels: int
    frame_count: int
    byte_count: int
