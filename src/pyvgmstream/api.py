from __future__ import annotations

from os import PathLike

from .errors import NativeBackendUnavailableError

PathInput = str | PathLike[str]


def _raise_native_backend_unavailable() -> None:
    raise NativeBackendUnavailableError(
        "pyvgmstream native backend is not available yet. "
        "The current repository state only provides the cross-platform package skeleton."
    )


def probe(path: PathInput, *, subsong: int = 0) -> object:
    del path, subsong
    _raise_native_backend_unavailable()


def open_stream(path: PathInput, *, subsong: int = 0, config: object | None = None) -> object:
    del path, subsong, config
    _raise_native_backend_unavailable()


def decode_to_wav_file(
    in_path: PathInput,
    out_path: PathInput,
    *,
    config: object | None = None,
) -> object:
    del in_path, out_path, config
    _raise_native_backend_unavailable()


def decode_to_wav_bytes(path: PathInput, *, config: object | None = None) -> bytes:
    del path, config
    _raise_native_backend_unavailable()
