from __future__ import annotations

import sys
from types import ModuleType

import pyvgmstream
import pytest

from pyvgmstream import LogLevel
from pyvgmstream import log as log_module
from pyvgmstream import _native


def test_set_log_callback_delegates_to_native(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_native = ModuleType("pyvgmstream._native")
    captured: dict[str, object] = {}

    def fake_set_log_callback(level: int, callback: object) -> None:
        captured["level"] = level
        captured["callback"] = callback

    def fake_disable_log_callback() -> None:
        captured["disabled"] = True

    fake_native.set_log_callback = fake_set_log_callback
    fake_native.disable_log_callback = fake_disable_log_callback
    monkeypatch.setitem(sys.modules, "pyvgmstream._native", fake_native)
    monkeypatch.setattr(pyvgmstream, "_native", fake_native, raising=False)

    events: list[tuple[LogLevel | int, str]] = []
    log_module.set_log_callback(lambda level, message: events.append((level, message)))

    assert captured["level"] == LogLevel.INFO.value
    assert callable(captured["callback"])

    captured_callback = captured["callback"]
    captured_callback(LogLevel.DEBUG.value, "hello")
    assert events == [(LogLevel.DEBUG, "hello")]


def test_set_log_callback_uses_default_stdout_when_callback_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_native = ModuleType("pyvgmstream._native")
    captured: dict[str, object] = {}

    def fake_set_log_callback(level: int, callback: object) -> None:
        captured["level"] = level
        captured["callback"] = callback

    fake_native.set_log_callback = fake_set_log_callback
    fake_native.disable_log_callback = lambda: None
    monkeypatch.setitem(sys.modules, "pyvgmstream._native", fake_native)
    monkeypatch.setattr(pyvgmstream, "_native", fake_native, raising=False)

    log_module.set_log_callback(None, level=LogLevel.DEBUG)

    assert captured == {
        "level": LogLevel.DEBUG.value,
        "callback": None,
    }


def test_disable_log_callback_delegates_to_native(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_native = ModuleType("pyvgmstream._native")
    captured: dict[str, object] = {"disabled": False}

    fake_native.set_log_callback = lambda level, callback: None
    fake_native.disable_log_callback = lambda: captured.__setitem__("disabled", True)
    monkeypatch.setitem(sys.modules, "pyvgmstream._native", fake_native)
    monkeypatch.setattr(pyvgmstream, "_native", fake_native, raising=False)

    log_module.disable_log_callback()

    assert captured["disabled"] is True


def test_native_log_bridge_invokes_python_callback() -> None:
    events: list[tuple[LogLevel | int, str]] = []

    pyvgmstream.set_log_callback(lambda level, message: events.append((level, message)))
    try:
        _native._emit_test_log_for_tests(LogLevel.INFO.value, "bridge-ok")
    finally:
        pyvgmstream.disable_log_callback()

    assert events == [(LogLevel.INFO, "bridge-ok")]


def test_native_log_bridge_stops_after_disable() -> None:
    events: list[tuple[LogLevel | int, str]] = []

    pyvgmstream.set_log_callback(lambda level, message: events.append((level, message)))
    pyvgmstream.disable_log_callback()
    _native._emit_test_log_for_tests(LogLevel.INFO.value, "ignored")

    assert events == []
