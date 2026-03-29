from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import subprocess
import sys


def test_package_ships_typing_metadata() -> None:
    package_dir = files("pyvgmstream")

    assert package_dir.joinpath("_native.pyi").is_file()
    assert package_dir.joinpath("py.typed").is_file()


def test_cmake_uses_vendored_vgmstream_checkout() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_text = repo_root.joinpath("CMakeLists.txt").read_text(encoding="utf-8")

    assert "vendor/vgmstream" in cmake_text
    assert ".temp/vgmstream" not in cmake_text
    assert "PYVGMSTREAM_VGMSTREAM_ROOT" not in cmake_text


def test_repo_ships_local_build_scripts() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    assert repo_root.joinpath("scripts", "update_upstream.py").is_file()
    assert repo_root.joinpath("scripts", "build_wheels.ps1").is_file()
    assert repo_root.joinpath("scripts", "build_wheels.sh").is_file()


def test_update_upstream_script_targets_vendored_checkout() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "update_upstream.py"),
            "--print-target",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert result.stdout.strip().endswith(str(Path("vendor") / "vgmstream"))


def test_repo_tracks_vgmstream_as_git_submodule() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    gitmodules_text = repo_root.joinpath(".gitmodules").read_text(encoding="utf-8")

    assert '[submodule "vendor/vgmstream"]' in gitmodules_text
    assert "path = vendor/vgmstream" in gitmodules_text
    assert "url = https://github.com/vgmstream/vgmstream" in gitmodules_text

    result = subprocess.run(
        ["git", "ls-files", "--stage", "vendor/vgmstream"],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("160000 ")


def test_pytest_runtime_temp_stays_under_dot_temp() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject_text = repo_root.joinpath("pyproject.toml").read_text(encoding="utf-8")

    assert 'addopts = "-ra --basetemp=.temp/pytest-tmp"' in pyproject_text
    assert 'cache_dir = ".temp/.pytest_cache"' in pyproject_text


def test_cmake_isolates_windows_specific_runtime_packaging() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_text = repo_root.joinpath("CMakeLists.txt").read_text(encoding="utf-8")

    assert "if(WIN32)" in cmake_text
    assert 'COMMAND lib' in cmake_text
    assert 'install(FILES "${PYVGMSTREAM_VORBIS_DLL}" DESTINATION pyvgmstream)' in cmake_text


def test_readme_clarifies_wav_only_scope_and_build_flow() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    readme_text = repo_root.joinpath("README.md").read_text(encoding="utf-8")

    assert "decode_to_wav_file()" in readme_text
    assert "decode_to_wav_bytes()" in readme_text
    assert "uv build --wheel" in readme_text
    assert "pip install ." in readme_text
    assert "uv pip install ." in readme_text
    assert "git submodule update --init --recursive" in readme_text
