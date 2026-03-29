from __future__ import annotations

from pathlib import Path

import pytest

from pyvgmstream import decode_buffer_to_wav_bytes, open_stream, open_stream_from_buffer, probe, probe_buffer
from pyvgmstream import _native
from tests.wav_header import inspect_wav_header


def _sample_wem() -> Path:
    wem_dir = Path(".temp") / "wem"
    sample = next(iter(sorted(wem_dir.glob("*.wem"))), None)
    if sample is None:
        pytest.skip("no real .wem sample is available under .temp/wem")
    return sample


def test_probe_buffer_matches_path_probe_for_real_wem() -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    sample = _sample_wem()
    path_info = probe(sample)
    buffer_info = probe_buffer(sample.read_bytes(), filename_hint=sample.name)

    assert buffer_info.sample_rate == path_info.sample_rate
    assert buffer_info.sample_format == path_info.sample_format
    assert buffer_info.sample_size == path_info.sample_size
    assert buffer_info.channels == path_info.channels
    assert buffer_info.play_samples == path_info.play_samples
    assert buffer_info.codec_name == path_info.codec_name


def test_open_stream_from_buffer_matches_path_stream_for_real_wem() -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    sample = _sample_wem()
    with open_stream(sample) as path_stream, open_stream_from_buffer(
        sample.read_bytes(),
        filename_hint=sample.name,
    ) as buffer_stream:
        assert buffer_stream.sample_rate == path_stream.sample_rate
        assert buffer_stream.sample_format == path_stream.sample_format
        assert buffer_stream.sample_size == path_stream.sample_size
        assert buffer_stream.channels == path_stream.channels
        assert buffer_stream.read_frames(1024)


def test_decode_buffer_to_wav_bytes_returns_valid_wav_for_real_wem() -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    sample = _sample_wem()
    payload = decode_buffer_to_wav_bytes(sample.read_bytes(), filename_hint=sample.name)
    header = inspect_wav_header(payload)

    assert payload.startswith(b"RIFF")
    assert b"WAVE" in payload[:16]
    assert header["sample_rate"] > 0
    assert header["channels"] > 0
    assert header["data_size"] > 0
