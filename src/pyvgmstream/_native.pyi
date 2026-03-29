from __future__ import annotations

from typing import Callable, TypedDict


class ProbeResult(TypedDict):
    source_path: str
    subsong: int
    backend_name: str
    sample_rate: int
    sample_format: int
    sample_size: int
    channels: int
    input_channels: int
    channel_layout: int
    subsong_count: int
    stream_samples: int
    play_samples: int
    duration_seconds: float
    stream_bitrate: int
    loop_start: int
    loop_end: int
    loop_flag: bool
    play_forever: bool
    codec_name: str
    layout_name: str
    meta_name: str


def backend_name() -> str: ...
def vgmstream_version() -> int: ...
def set_log_callback(level: int, callback: Callable[[int, str], None] | None = None) -> None: ...
def disable_log_callback() -> None: ...
def _emit_test_log_for_tests(level: int, message: str) -> None: ...
def probe(
    source_path: str,
    subsong: int = 0,
    sample_format: int = 0,
    ignore_loop: int = -1,
) -> ProbeResult: ...


class NativeStreamHandle:
    def __init__(
        self,
        source_path: str,
        subsong: int = 0,
        sample_format: int = 0,
        ignore_loop: int = -1,
    ) -> None: ...

    @property
    def sample_rate(self) -> int: ...

    @property
    def sample_format(self) -> int: ...

    @property
    def sample_size(self) -> int: ...

    @property
    def channels(self) -> int: ...

    @property
    def input_channels(self) -> int: ...

    @property
    def channel_layout(self) -> int: ...

    @property
    def stream_samples(self) -> int: ...

    @property
    def play_samples(self) -> int: ...

    @property
    def stream_bitrate(self) -> int: ...

    @property
    def loop_start(self) -> int: ...

    @property
    def loop_end(self) -> int: ...

    @property
    def play_forever(self) -> bool: ...

    @property
    def done(self) -> bool: ...

    def read_frames(self, frame_count: int) -> bytes: ...
    def tell_samples(self) -> int: ...
    def seek_samples(self, position: int) -> None: ...
    def reset(self) -> None: ...
    def close(self) -> None: ...
