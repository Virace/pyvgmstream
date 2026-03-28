class PyVGMStreamError(Exception):
    """Base exception for pyvgmstream."""


class NativeBackendUnavailableError(PyVGMStreamError):
    """Raised when the native vgmstream binding is not available yet."""
