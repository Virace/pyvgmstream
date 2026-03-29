class PyVGMStreamError(Exception):
    """Base exception for pyvgmstream."""


class OptionalDependencyError(PyVGMStreamError):
    """Raised when an optional dependency-backed feature is unavailable."""
