from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path


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

    with wave.open(str(expected_output), "rb") as wav_file:
        assert wav_file.getframerate() > 0
        assert wav_file.getnchannels() > 0
        assert wav_file.getnframes() > 0
