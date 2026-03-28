"""Public Python package shell for pyvgmstream."""

from .api import decode_to_wav_bytes, decode_to_wav_file, open_stream, probe
from .errors import NativeBackendUnavailableError, PyVGMStreamError

__all__ = [
    "PyVGMStreamError",
    "NativeBackendUnavailableError",
    "probe",
    "open_stream",
    "decode_to_wav_file",
    "decode_to_wav_bytes",
]

__version__ = "0.1.0"
