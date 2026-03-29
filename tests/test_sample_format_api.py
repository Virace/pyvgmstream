from __future__ import annotations

import sys
from types import ModuleType

import pyvgmstream
import pytest

from pyvgmstream import DecodeConfig, SampleFormat, StreamHandle
from pyvgmstream import api as api_module
from tests.wav_header import inspect_wav_header


class FakeNativeStreamHandle:
    def __init__(
        self,
        *,
        sample_format: SampleFormat = SampleFormat.PCM32,
        sample_size: int = 4,
        payload: bytes = b"",
    ) -> None:
        self.sample_rate = 48000
        self.channels = 2
        self.input_channels = 2
        self.channel_layout = 3
        self.stream_samples = 2048
        self.play_samples = 2048
        self.stream_bitrate = 128000
        self.loop_start = 0
        self.loop_end = 0
        self.play_forever = False
        self.done = False
        self.sample_format = sample_format.value
        self.sample_size = sample_size
        self._payload = payload or b"\x01\x02\x03\x04" * 4
        self.read_pcm16_called = False

    def read_frames(self, frame_count: int) -> bytes:
        del frame_count
        self.done = True
        return self._payload

    def read_pcm16(self, frame_count: int) -> bytes:
        del frame_count
        self.read_pcm16_called = True
        return b"unexpected"

    def tell_samples(self) -> int:
        return 0

    def seek_samples(self, position: int) -> None:
        del position

    def reset(self) -> None:
        self.done = False

    def close(self) -> None:
        return


class FakeContextStream:
    def __init__(
        self,
        *,
        sample_format: SampleFormat,
        sample_size: int,
        payload: bytes,
    ) -> None:
        self.sample_rate = 44100
        self.channels = 2
        self.sample_format = sample_format
        self.sample_size = sample_size
        self.done = False
        self._payload = payload
        self.read_pcm16_called = False

    def read_frames(self, frame_count: int) -> bytes:
        del frame_count
        if self.done:
            return b""
        self.done = True
        return self._payload

    def read_pcm16(self, frame_count: int) -> bytes:
        del frame_count
        self.read_pcm16_called = True
        return b"unexpected"

    def __enter__(self) -> FakeContextStream:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_stream_handle_exposes_dynamic_sample_format_and_generic_reads() -> None:
    native_handle = FakeNativeStreamHandle(sample_format=SampleFormat.PCM32, sample_size=4)
    stream = StreamHandle(native_handle)

    assert stream.sample_format is SampleFormat.PCM32
    assert stream.sample_size == 4
    assert stream.read_frames(16) == native_handle._payload

    with pytest.raises(ValueError, match="PCM16"):
        stream.read_pcm16(16)

    assert native_handle.read_pcm16_called is False


def test_probe_exposes_sample_format_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_native = ModuleType("pyvgmstream._native")
    captured: dict[str, object] = {}

    def fake_probe(
        source_path: str,
        subsong: int = 0,
        sample_format: int = 0,
        ignore_loop: int = -1,
    ) -> dict[str, object]:
        captured["source_path"] = source_path
        captured["subsong"] = subsong
        captured["sample_format"] = sample_format
        captured["ignore_loop"] = ignore_loop
        return {
            "source_path": source_path,
            "subsong": subsong,
            "backend_name": "pyvgmstream-libvgmstream",
            "sample_rate": 48000,
            "channels": 2,
            "input_channels": 2,
            "channel_layout": 3,
            "subsong_count": 1,
            "stream_samples": 1024,
            "play_samples": 1024,
            "duration_seconds": 1024 / 48000,
            "stream_bitrate": 192000,
            "loop_start": 0,
            "loop_end": 0,
            "loop_flag": False,
            "play_forever": False,
            "codec_name": "codec",
            "layout_name": "layout",
            "meta_name": "meta",
            "sample_format": SampleFormat.PCM24.value,
            "sample_size": 3,
        }

    fake_native.probe = fake_probe
    monkeypatch.setitem(sys.modules, "pyvgmstream._native", fake_native)
    monkeypatch.setattr(pyvgmstream, "_native", fake_native, raising=False)

    info = api_module.probe("demo.wem")

    assert captured == {
        "source_path": "demo.wem",
        "subsong": 0,
        "sample_format": 0,
        "ignore_loop": -1,
    }
    assert info.sample_format is SampleFormat.PCM24
    assert info.sample_size == 3


def test_probe_passes_requested_decode_config(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_native = ModuleType("pyvgmstream._native")
    captured: dict[str, object] = {}

    def fake_probe(
        source_path: str,
        subsong: int = 0,
        sample_format: int = 0,
        ignore_loop: int = -1,
    ) -> dict[str, object]:
        captured["source_path"] = source_path
        captured["subsong"] = subsong
        captured["sample_format"] = sample_format
        captured["ignore_loop"] = ignore_loop
        return {
            "source_path": source_path,
            "subsong": subsong,
            "backend_name": "pyvgmstream-libvgmstream",
            "sample_rate": 48000,
            "channels": 2,
            "input_channels": 2,
            "channel_layout": 3,
            "subsong_count": 1,
            "stream_samples": 1024,
            "play_samples": 1024,
            "duration_seconds": 1024 / 48000,
            "stream_bitrate": 192000,
            "loop_start": 0,
            "loop_end": 0,
            "loop_flag": False,
            "play_forever": False,
            "codec_name": "codec",
            "layout_name": "layout",
            "meta_name": "meta",
            "sample_format": sample_format or SampleFormat.PCM24.value,
            "sample_size": 3,
        }

    fake_native.probe = fake_probe
    monkeypatch.setitem(sys.modules, "pyvgmstream._native", fake_native)
    monkeypatch.setattr(pyvgmstream, "_native", fake_native, raising=False)

    api_module.probe(
        "demo.wem",
        config=DecodeConfig(sample_format=SampleFormat.PCM16, ignore_loop=True),
    )

    assert captured == {
        "source_path": "demo.wem",
        "subsong": 0,
        "sample_format": SampleFormat.PCM16.value,
        "ignore_loop": 1,
    }


def test_open_stream_passes_requested_decode_config(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_native = ModuleType("pyvgmstream._native")
    captured: dict[str, object] = {}

    class FakeCtor(FakeNativeStreamHandle):
        def __init__(
            self,
            source_path: str,
            subsong: int = 0,
            sample_format: int = 0,
            ignore_loop: int = -1,
        ) -> None:
            captured["source_path"] = source_path
            captured["subsong"] = subsong
            captured["sample_format"] = sample_format
            captured["ignore_loop"] = ignore_loop
            super().__init__(
                sample_format=SampleFormat(sample_format or SampleFormat.PCM24.value),
                sample_size=3 if sample_format == SampleFormat.PCM24.value else 2,
            )

    fake_native.NativeStreamHandle = FakeCtor
    monkeypatch.setitem(sys.modules, "pyvgmstream._native", fake_native)
    monkeypatch.setattr(pyvgmstream, "_native", fake_native, raising=False)

    stream = api_module.open_stream(
        "demo.wem",
        config=DecodeConfig(sample_format=SampleFormat.PCM16, ignore_loop=False),
    )

    assert captured == {
        "source_path": "demo.wem",
        "subsong": 0,
        "sample_format": SampleFormat.PCM16.value,
        "ignore_loop": 0,
    }
    assert stream.sample_format is SampleFormat.PCM16


def test_decode_to_wav_bytes_preserves_integer_sample_width(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"\x01\x02\x03\x04\x05\x06"
    fake_stream = FakeContextStream(
        sample_format=SampleFormat.PCM24,
        sample_size=3,
        payload=payload,
    )
    monkeypatch.setattr(api_module, "open_stream", lambda path, **kwargs: fake_stream)

    wav_bytes = api_module.decode_to_wav_bytes("demo.wem")
    header = inspect_wav_header(wav_bytes)

    assert header["format_code"] == 1
    assert header["sample_rate"] == 44100
    assert header["channels"] == 2
    assert header["bits_per_sample"] == 24
    assert header["block_align"] == 6
    assert wav_bytes[header["data_offset"] :] == payload

    assert fake_stream.read_pcm16_called is False


def test_decode_to_wav_bytes_preserves_float_output_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_stream = FakeContextStream(
        sample_format=SampleFormat.FLOAT,
        sample_size=4,
        payload=b"\x00\x00\x00\x00\x00\x00\x00?",
    )
    monkeypatch.setattr(api_module, "open_stream", lambda path, **kwargs: fake_stream)

    wav_bytes = api_module.decode_to_wav_bytes("demo.wem")
    header = inspect_wav_header(wav_bytes)

    assert header["format_code"] == 3
    assert header["sample_rate"] == 44100
    assert header["channels"] == 2
    assert header["bits_per_sample"] == 32
    assert header["block_align"] == 8
    assert wav_bytes[header["data_offset"] :] == fake_stream._payload
