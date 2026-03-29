class PyVGMStreamError(Exception):
    """`pyvgmstream` 的基础异常类型。"""


class OptionalDependencyError(PyVGMStreamError):
    """当可选依赖后端不可用时抛出。"""
