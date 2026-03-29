from __future__ import annotations

import io
import wave
from pathlib import Path

import pytest

from pyvgmstream import DecodeResult, decode_to_wav_bytes, decode_to_wav_file
from pyvgmstream import _native


def _sample_wem() -> Path:
    wem_dir = Path(".temp") / "wem"
    sample = next(iter(sorted(wem_dir.glob("*.wem"))), None)
    if sample is None:
        pytest.skip("no real .wem sample is available under .temp/wem")
    return sample


def test_decode_to_wav_bytes_returns_valid_wav() -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    payload = decode_to_wav_bytes(_sample_wem())

    assert payload.startswith(b"RIFF")
    assert b"WAVE" in payload[:16]

    with wave.open(io.BytesIO(payload), "rb") as wav_file:
        assert wav_file.getframerate() > 0
        assert wav_file.getnchannels() > 0
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() > 0


def test_decode_to_wav_file_writes_output_and_returns_summary(tmp_path: Path) -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    output_path = tmp_path / "decoded.wav"
    result = decode_to_wav_file(_sample_wem(), output_path)

    assert isinstance(result, DecodeResult)
    assert result.output_path == output_path.resolve()
    assert result.sample_rate > 0
    assert result.channels > 0
    assert result.frame_count > 0
    assert result.byte_count == output_path.stat().st_size

    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getframerate() == result.sample_rate
        assert wav_file.getnchannels() == result.channels
        assert wav_file.getnframes() == result.frame_count
