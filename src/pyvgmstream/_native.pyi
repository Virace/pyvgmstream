from __future__ import annotations

from typing import TypedDict


class ProbeResult(TypedDict):
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


def backend_name() -> str: ...
def vgmstream_version() -> int: ...
def probe(source_path: str, subsong: int = 0) -> ProbeResult: ...


class NativeStreamHandle:
    def __init__(self, source_path: str, subsong: int = 0) -> None: ...

    @property
    def sample_rate(self) -> int: ...

    @property
    def channels(self) -> int: ...

    @property
    def done(self) -> bool: ...

    def read_pcm16(self, frame_count: int) -> bytes: ...
    def tell_samples(self) -> int: ...
    def seek_samples(self, position: int) -> None: ...
    def reset(self) -> None: ...
    def close(self) -> None: ...
