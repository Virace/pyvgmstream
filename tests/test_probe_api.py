from __future__ import annotations

from pathlib import Path

import pytest

from pyvgmstream import StreamInfo, probe
from pyvgmstream import _native


def test_probe_routes_to_expected_backend_mode(tmp_path: Path) -> None:
    if _native.backend_name() == "pyvgmstream-libvgmstream":
        invalid_file = tmp_path / "dummy.wem"
        invalid_file.write_bytes(b"not-a-real-wem")

        with pytest.raises(ValueError, match="not a valid or supported stream"):
            probe(invalid_file, subsong=2)
    else:
        result = probe(Path("dummy.wem"), subsong=2)

        assert isinstance(result, StreamInfo)
        assert result.source_path == "dummy.wem"
        assert result.subsong == 2
        assert result.backend_name == "pyvgmstream-native-stub"
        assert result.subsong_count == 0
        assert result.loop_flag is False
        assert result.codec_name == ""
        assert result.layout_name == ""
        assert result.meta_name == ""
