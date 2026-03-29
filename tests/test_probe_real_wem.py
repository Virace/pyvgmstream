from __future__ import annotations

from pathlib import Path

import pytest

from pyvgmstream import StreamInfo, probe
from pyvgmstream import _native


def test_probe_real_wem_returns_basic_metadata() -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    wem_dir = Path(".temp") / "wem"
    sample = next(iter(sorted(wem_dir.glob("*.wem"))), None)
    if sample is None:
        pytest.skip("no real .wem sample is available under .temp/wem")

    result = probe(sample)

    assert isinstance(result, StreamInfo)
    assert result.backend_name == "pyvgmstream-libvgmstream"
    assert result.source_path.endswith(".wem")
    assert result.sample_rate > 0
    assert result.channels > 0
    assert result.subsong_count >= 0
    assert isinstance(result.loop_flag, bool)
    assert result.codec_name
    assert result.layout_name
    assert result.meta_name
