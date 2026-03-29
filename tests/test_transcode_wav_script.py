from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pyvgmstream import SampleFormat, open_stream
from tests.wav_header import inspect_wav_file


def test_transcode_wav_script_prints_resolved_config(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_root = repo_root / ".temp" / "wem"
    output_root = tmp_path / "out"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "transcode_wav.py"),
            str(input_root),
            str(output_root),
            "--workers",
            "1",
            "--limit",
            "1",
            "--print-config",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert Path(payload["input_root"]) == input_root.resolve()
    assert Path(payload["output_root"]) == output_root.resolve()
    assert payload["workers"] == 1
    assert payload["limit"] == 1
    assert payload["chunk_frames"] > 0


def test_transcode_wav_script_writes_wav_for_real_sample(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_root = repo_root / ".temp" / "wem"
    sample = next(iter(sorted(input_root.glob("*.wem"))), None)
    assert sample is not None

    with open_stream(sample) as stream:
        expected_sample_rate = stream.sample_rate
        expected_channels = stream.channels
        expected_sample_format = stream.sample_format
        expected_sample_size = stream.sample_size

    output_root = tmp_path / "wav-out"
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "transcode_wav.py"),
            str(input_root),
            str(output_root),
            "--workers",
            "1",
            "--limit",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode == 0
    expected_output = output_root / f"{sample.stem}.wav"
    assert expected_output.is_file()
    header = inspect_wav_file(expected_output)
    expected_format_code = 3 if expected_sample_format is SampleFormat.FLOAT else 1
    assert header["format_code"] == expected_format_code
    assert header["sample_rate"] == expected_sample_rate
    assert header["channels"] == expected_channels
    assert header["bits_per_sample"] == expected_sample_size * 8
    assert header["data_size"] > 0
