from __future__ import annotations

from pathlib import Path

from pyvgmstream import BatchTranscodeSummary, SampleFormat, open_stream, transcode_tree
from tests.wav_header import inspect_wav_file


def test_transcode_tree_returns_summary_and_writes_wav(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_root = repo_root / ".temp" / "wem"
    output_root = tmp_path / "wav-out"
    source_path = next(iter(sorted(input_root.glob("*.wem"))), None)
    assert source_path is not None

    with open_stream(source_path) as stream:
        expected_sample_rate = stream.sample_rate
        expected_channels = stream.channels
        expected_sample_format = stream.sample_format
        expected_sample_size = stream.sample_size

    summary = transcode_tree(input_root, output_root, workers=1, limit=1)

    assert isinstance(summary, BatchTranscodeSummary)
    assert summary.processed_count == 1
    assert summary.failed_count == 0
    assert len(summary.results) == 1
    assert summary.results[0].success is True
    assert summary.results[0].output_path.is_file()
    header = inspect_wav_file(summary.results[0].output_path)
    expected_format_code = 3 if expected_sample_format is SampleFormat.FLOAT else 1
    assert header["format_code"] == expected_format_code
    assert header["sample_rate"] == expected_sample_rate
    assert header["channels"] == expected_channels
    assert header["bits_per_sample"] == expected_sample_size * 8
    assert header["data_size"] > 0


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
