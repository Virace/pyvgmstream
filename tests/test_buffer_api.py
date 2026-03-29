from __future__ import annotations

import sys
from types import ModuleType

import pyvgmstream
import pytest

from pyvgmstream import DecodeConfig, DecodeResult, SampleFormat, StreamHandle
from pyvgmstream import api as api_module
from tests.wav_header import inspect_wav_file, inspect_wav_header


class FakeNativeBufferStreamHandle:
    def __init__(
        self,
        buffer_data: bytes,
        filename_hint: str,
        subsong: int = 0,
        sample_format: int = 0,
        ignore_loop: int = -1,
    ) -> None:
        self.buffer_data = buffer_data
        self.filename_hint = filename_hint
        self.subsong = subsong
        self.sample_rate = 48000
        self.sample_format = sample_format or SampleFormat.PCM24.value
        self.sample_size = 3 if self.sample_format == SampleFormat.PCM24.value else 2
        self.channels = 2
        self.input_channels = 2
        self.channel_layout = 3
        self.stream_samples = 1024
        self.play_samples = 1024
        self.stream_bitrate = 192000
        self.loop_start = 0
        self.loop_end = 0
        self.play_forever = False
        self.done = False
        self._payload = b"\x01\x02\x03\x04\x05\x06" if self.sample_size == 3 else b"\x01\x02\x03\x04"

    def read_frames(self, frame_count: int) -> bytes:
        del frame_count
        if self.done:
            return b""
        self.done = True
        return self._payload

    def tell_samples(self) -> int:
        return 0

    def seek_samples(self, position: int) -> None:
        del position

    def reset(self) -> None:
        self.done = False

    def close(self) -> None:
        return


def test_probe_buffer_passes_bytes_and_filename_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_native = ModuleType("pyvgmstream._native")
    captured: dict[str, object] = {}

    def fake_probe_buffer(
        buffer_data: bytes,
        filename_hint: str,
        subsong: int = 0,
        sample_format: int = 0,
        ignore_loop: int = -1,
    ) -> dict[str, object]:
        captured["buffer_data"] = buffer_data
        captured["filename_hint"] = filename_hint
        captured["subsong"] = subsong
        captured["sample_format"] = sample_format
        captured["ignore_loop"] = ignore_loop
        return {
            "source_path": filename_hint,
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

    fake_native.probe_buffer = fake_probe_buffer
    monkeypatch.setitem(sys.modules, "pyvgmstream._native", fake_native)
    monkeypatch.setattr(pyvgmstream, "_native", fake_native, raising=False)

    info = api_module.probe_buffer(memoryview(b"demo"), filename_hint="sample.wem")

    assert captured == {
        "buffer_data": b"demo",
        "filename_hint": "sample.wem",
        "subsong": 0,
        "sample_format": 0,
        "ignore_loop": -1,
    }
    assert info.sample_format is SampleFormat.PCM24


def test_open_stream_from_buffer_passes_decode_config(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_native = ModuleType("pyvgmstream._native")
    captured: dict[str, object] = {}

    class FakeCtor(FakeNativeBufferStreamHandle):
        def __init__(
            self,
            buffer_data: bytes,
            filename_hint: str,
            subsong: int = 0,
            sample_format: int = 0,
            ignore_loop: int = -1,
        ) -> None:
            captured["buffer_data"] = buffer_data
            captured["filename_hint"] = filename_hint
            captured["subsong"] = subsong
            captured["sample_format"] = sample_format
            captured["ignore_loop"] = ignore_loop
            super().__init__(buffer_data, filename_hint, subsong, sample_format, ignore_loop)

    fake_native.NativeBufferStreamHandle = FakeCtor
    monkeypatch.setitem(sys.modules, "pyvgmstream._native", fake_native)
    monkeypatch.setattr(pyvgmstream, "_native", fake_native, raising=False)

    stream = api_module.open_stream_from_buffer(
        bytearray(b"demo"),
        filename_hint="sample.wem",
        config=DecodeConfig(sample_format=SampleFormat.PCM16, ignore_loop=False),
    )

    assert captured == {
        "buffer_data": b"demo",
        "filename_hint": "sample.wem",
        "subsong": 0,
        "sample_format": SampleFormat.PCM16.value,
        "ignore_loop": 0,
    }
    assert isinstance(stream, StreamHandle)
    assert stream.sample_format is SampleFormat.PCM16


def test_decode_buffer_to_wav_bytes_preserves_sample_width(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_stream = FakeNativeBufferStreamHandle(b"demo", "sample.wem", sample_format=SampleFormat.PCM24.value)
    monkeypatch.setattr(
        api_module,
        "open_stream_from_buffer",
        lambda data, *, filename_hint, subsong=0, config=None: StreamHandle(fake_stream),
    )

    wav_bytes = api_module.decode_buffer_to_wav_bytes(b"demo", filename_hint="sample.wem")
    header = inspect_wav_header(wav_bytes)

    assert header["format_code"] == 1
    assert header["sample_rate"] == 48000
    assert header["channels"] == 2
    assert header["bits_per_sample"] == 24


def test_decode_buffer_to_wav_file_writes_output(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake_stream = FakeNativeBufferStreamHandle(b"demo", "sample.wem", sample_format=SampleFormat.PCM24.value)
    monkeypatch.setattr(
        api_module,
        "open_stream_from_buffer",
        lambda data, *, filename_hint, subsong=0, config=None: StreamHandle(fake_stream),
    )

    output_path = tmp_path / "decoded.wav"
    result = api_module.decode_buffer_to_wav_file(b"demo", output_path, filename_hint="sample.wem")

    assert isinstance(result, DecodeResult)
    header = inspect_wav_file(output_path)
    assert header["format_code"] == 1
    assert header["bits_per_sample"] == 24
    assert result.output_path == output_path.resolve()


@pytest.mark.parametrize("bad_value", ["demo", 123, object()])
def test_buffer_api_rejects_non_buffer_inputs(bad_value: object) -> None:
    with pytest.raises(TypeError, match="bytes-like"):
        api_module.probe_buffer(bad_value, filename_hint="sample.wem")


def test_buffer_api_requires_filename_hint() -> None:
    with pytest.raises(ValueError, match="filename_hint"):
        api_module.probe_buffer(b"demo", filename_hint="")
