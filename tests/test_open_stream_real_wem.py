from __future__ import annotations

from pathlib import Path

import pytest

from pyvgmstream import SampleFormat, StreamHandle, open_stream
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
        assert isinstance(stream.sample_format, SampleFormat)
        assert stream.sample_size > 0
        assert stream.channels > 0
        assert stream.input_channels > 0
        assert stream.channel_layout >= 0
        assert stream.stream_samples > 0
        assert stream.play_samples > 0
        assert stream.duration_seconds > 0.0
        assert stream.stream_bitrate >= 0
        assert stream.loop_start >= 0
        assert stream.loop_end >= 0
        assert isinstance(stream.play_forever, bool)

        chunk = stream.read_frames(1024)
        assert isinstance(chunk, bytes)
        assert chunk
        assert len(chunk) % (stream.channels * stream.sample_size) == 0
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
        chunk = stream.read_frames(1024)

    assert chunk
