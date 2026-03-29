from __future__ import annotations



def test_native_extension_module_reports_backend_mode() -> None:
    from pyvgmstream import _native

    backend_name = _native.backend_name()

    assert backend_name == "pyvgmstream-libvgmstream"
    assert _native.vgmstream_version() > 0
