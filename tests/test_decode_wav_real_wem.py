from __future__ import annotations

from pathlib import Path

import pytest

from pyvgmstream import DecodeResult, SampleFormat, decode_to_wav_bytes, decode_to_wav_file, open_stream
from pyvgmstream import _native
from tests.wav_header import inspect_wav_file, inspect_wav_header


def _sample_wem() -> Path:
    wem_dir = Path(".temp") / "wem"
    sample = next(iter(sorted(wem_dir.glob("*.wem"))), None)
    if sample is None:
        pytest.skip("no real .wem sample is available under .temp/wem")
    return sample


def test_decode_to_wav_bytes_returns_valid_wav() -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    with open_stream(_sample_wem()) as stream:
        expected_sample_rate = stream.sample_rate
        expected_channels = stream.channels
        expected_sample_format = stream.sample_format
        expected_sample_size = stream.sample_size

    payload = decode_to_wav_bytes(_sample_wem())

    assert payload.startswith(b"RIFF")
    assert b"WAVE" in payload[:16]
    header = inspect_wav_header(payload)

    expected_format_code = 3 if expected_sample_format is SampleFormat.FLOAT else 1
    assert header["format_code"] == expected_format_code
    assert header["sample_rate"] == expected_sample_rate
    assert header["channels"] == expected_channels
    assert header["bits_per_sample"] == expected_sample_size * 8
    assert header["data_size"] > 0


def test_decode_to_wav_file_writes_output_and_returns_summary(tmp_path: Path) -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    with open_stream(_sample_wem()) as stream:
        expected_sample_rate = stream.sample_rate
        expected_channels = stream.channels
        expected_sample_format = stream.sample_format
        expected_sample_size = stream.sample_size

    output_path = tmp_path / "decoded.wav"
    result = decode_to_wav_file(_sample_wem(), output_path)

    assert isinstance(result, DecodeResult)
    assert result.output_path == output_path.resolve()
    assert result.sample_rate == expected_sample_rate
    assert result.channels == expected_channels
    assert result.frame_count > 0
    assert result.byte_count == output_path.stat().st_size

    header = inspect_wav_file(output_path)
    expected_format_code = 3 if expected_sample_format is SampleFormat.FLOAT else 1
    assert header["format_code"] == expected_format_code
    assert header["sample_rate"] == result.sample_rate
    assert header["channels"] == result.channels
    assert header["bits_per_sample"] == expected_sample_size * 8
    assert header["data_size"] // header["block_align"] == result.frame_count
