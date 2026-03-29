from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_play_wem_script_prints_default_config() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    expected_sample = next(iter(sorted((repo_root / ".temp" / "wem").glob("*.wem"))))

    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "play_wem.py"), "--print-config"],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert Path(payload["source_path"]) == expected_sample.resolve()
    assert payload["volume_percent"] == 10.0
