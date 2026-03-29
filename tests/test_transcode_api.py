from __future__ import annotations

import wave
from pathlib import Path

from pyvgmstream import BatchTranscodeSummary, transcode_tree


def test_transcode_tree_returns_summary_and_writes_wav(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_root = repo_root / ".temp" / "wem"
    output_root = tmp_path / "wav-out"

    summary = transcode_tree(input_root, output_root, workers=1, limit=1)

    assert isinstance(summary, BatchTranscodeSummary)
    assert summary.processed_count == 1
    assert summary.failed_count == 0
    assert len(summary.results) == 1
    assert summary.results[0].success is True
    assert summary.results[0].output_path.is_file()

    with wave.open(str(summary.results[0].output_path), "rb") as wav_file:
        assert wav_file.getframerate() > 0
        assert wav_file.getnchannels() > 0
        assert wav_file.getnframes() > 0


def test_transcode_tree_preserves_relative_layout(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sample = next(iter(sorted((repo_root / ".temp" / "wem").glob("*.wem"))), None)
    assert sample is not None

    input_root = tmp_path / "nested-in"
    nested_dir = input_root / "角色" / "皮肤" / "SFX"
    nested_dir.mkdir(parents=True)
    nested_sample = nested_dir / "样本.wem"
    nested_sample.write_bytes(sample.read_bytes())

    output_root = tmp_path / "nested-out"
    summary = transcode_tree(input_root, output_root, workers=1)

    assert summary.processed_count == 1
    assert summary.failed_count == 0
    expected_output = output_root / "角色" / "皮肤" / "SFX" / "样本.wav"
    assert summary.results[0].output_path == expected_output
    assert expected_output.is_file()
