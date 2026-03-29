from __future__ import annotations

import pytest

import pyvgmstream
from pyvgmstream import _native


def test_public_api_exports_expected_entrypoints() -> None:
    assert pyvgmstream.__version__ == "0.1.0"
    assert pyvgmstream.__all__ == [
        "PyVGMStreamError",
        "StreamInfo",
        "DecodeResult",
        "StreamHandle",
        "probe",
        "open_stream",
        "decode_to_wav_file",
        "decode_to_wav_bytes",
    ]


@pytest.mark.parametrize(
    ("func_name", "args", "kwargs"),
    [
        ("open_stream", ("dummy.wem",), {}),
        ("decode_to_wav_file", ("dummy.wem", "dummy.wav"), {}),
        ("decode_to_wav_bytes", ("dummy.wem",), {}),
    ],
)
def test_placeholder_entrypoints_raise_clear_backend_error(
    func_name: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> None:
    func = getattr(pyvgmstream, func_name)

    assert _native.backend_name() == "pyvgmstream-libvgmstream"
    with pytest.raises(ValueError, match="could not open input file"):
        func(*args, **kwargs)


def test_wav_export_entrypoints_are_documented_as_wav_only() -> None:
    assert pyvgmstream.decode_to_wav_file.__doc__ is not None
    assert pyvgmstream.decode_to_wav_bytes.__doc__ is not None
    assert "WAV" in pyvgmstream.decode_to_wav_file.__doc__
    assert "WAV" in pyvgmstream.decode_to_wav_bytes.__doc__
