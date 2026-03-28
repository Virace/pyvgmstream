from __future__ import annotations

import pytest

import pyvgmstream
from pyvgmstream import NativeBackendUnavailableError


def test_public_api_exports_expected_entrypoints() -> None:
    assert pyvgmstream.__version__ == "0.1.0"
    assert pyvgmstream.__all__ == [
        "PyVGMStreamError",
        "NativeBackendUnavailableError",
        "probe",
        "open_stream",
        "decode_to_wav_file",
        "decode_to_wav_bytes",
    ]


@pytest.mark.parametrize(
    ("func_name", "args", "kwargs"),
    [
        ("probe", ("dummy.wem",), {}),
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

    with pytest.raises(
        NativeBackendUnavailableError,
        match="native backend is not available yet",
    ):
        func(*args, **kwargs)
