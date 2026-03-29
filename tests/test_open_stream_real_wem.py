from __future__ import annotations

from pathlib import Path

import pytest

from pyvgmstream import StreamHandle, open_stream
from pyvgmstream import _native


def test_open_stream_real_wem_supports_read_and_seek() -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    wem_dir = Path(".temp") / "wem"
    sample = next(iter(sorted(wem_dir.glob("*.wem"))), None)
    if sample is None:
        pytest.skip("no real .wem sample is available under .temp/wem")

    with open_stream(sample) as stream:
        assert isinstance(stream, StreamHandle)
        assert stream.sample_rate > 0
        assert stream.channels > 0

        chunk = stream.read_pcm16(1024)
        assert isinstance(chunk, bytes)
        assert chunk
        assert len(chunk) % (stream.channels * 2) == 0
        assert stream.tell_samples() > 0
        assert stream.tell_seconds() >= 0.0

        stream.seek_samples(0)
        assert stream.tell_samples() == 0

        stream.reset()
        assert stream.tell_samples() == 0


def test_open_stream_real_wem_supports_unicode_path(tmp_path: Path) -> None:
    if _native.backend_name() != "pyvgmstream-libvgmstream":
        pytest.skip("real libvgmstream backend is not enabled")

    wem_dir = Path(".temp") / "wem"
    sample = next(iter(sorted(wem_dir.glob("*.wem"))), None)
    if sample is None:
        pytest.skip("no real .wem sample is available under .temp/wem")

    unicode_dir = tmp_path / "中文目录"
    unicode_dir.mkdir()
    unicode_sample = unicode_dir / "样本.wem"
    unicode_sample.write_bytes(sample.read_bytes())

    with open_stream(unicode_sample) as stream:
        chunk = stream.read_pcm16(1024)

    assert chunk
