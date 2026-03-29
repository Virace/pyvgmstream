"""上游全局日志桥接。"""

from __future__ import annotations

from enum import IntEnum
from typing import Callable


class LogLevel(IntEnum):
    """上游 `libvgmstream_set_log()` 日志等级。

    Attributes:
        ALL: 捕获所有日志。
        DEBUG: 捕获调试级及以上日志。
        INFO: 捕获信息级及以上日志。
        NONE: 禁用当前日志回调。
    """

    ALL = 0
    DEBUG = 20
    INFO = 30
    NONE = 100


LogCallback = Callable[[LogLevel | int, str], None]


def set_log_callback(
    callback: LogCallback | None = None,
    *,
    level: LogLevel = LogLevel.INFO,
) -> None:
    """配置上游全局日志回调。

    Args:
        callback: Python 侧日志回调。若为 `None`，则回退到上游默认 stdout 回调。
        level: 要启用的最小日志等级。
    """

    from . import _native

    if callback is None:
        _native.set_log_callback(int(level), None)
        return

    def _bridge(raw_level: int, message: str) -> None:
        callback(LogLevel._value2member_map_.get(raw_level, raw_level), message)

    _native.set_log_callback(int(level), _bridge)


def disable_log_callback() -> None:
    """禁用当前上游全局日志回调。"""

    from . import _native

    _native.disable_log_callback()
