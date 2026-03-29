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
    adapter_text = repo_root.joinpath("cmake", "resolve_vgmstream.cmake").read_text(encoding="utf-8")

    assert 'include(resolve_vgmstream)' in cmake_text
    assert 'pyvgmstream_resolve_vgmstream(' in cmake_text
    assert 'pyvgmstream::vgmstream' in cmake_text
    assert "vendor/vgmstream" not in cmake_text
    assert ".temp/vgmstream" not in cmake_text
    assert "PYVGMSTREAM_VGMSTREAM_ROOT" not in cmake_text

    assert "vendor/vgmstream" in adapter_text
    assert 'include("${vgm_source_dir}/cmake/vgmstream.cmake")' in adapter_text
    assert 'add_subdirectory("${vgm_source_dir}/src" "${vgm_binary_dir}/src" EXCLUDE_FROM_ALL)' in adapter_text
    assert 'add_library(pyvgmstream::vgmstream ALIAS pyvgmstream_vgmstream)' in adapter_text


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
    adapter_text = repo_root.joinpath("cmake", "resolve_vgmstream.cmake").read_text(encoding="utf-8")

    assert "if(WIN32)" in adapter_text
    assert 'COMMAND lib' in adapter_text
    assert 'list(APPEND runtime_files "${vorbis_dll}")' in adapter_text


def test_readme_clarifies_wav_only_scope_and_build_flow() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    readme_text = repo_root.joinpath("README.md").read_text(encoding="utf-8")

    assert "decode_to_wav_file()" in readme_text
    assert "decode_to_wav_bytes()" in readme_text
    assert "uv build --wheel" in readme_text
    assert "pip install ." in readme_text
    assert "uv pip install ." in readme_text
    assert "git submodule update --init --recursive" in readme_text


def test_native_module_centralizes_upstream_bridge_helpers() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    native_text = repo_root.joinpath("src", "native", "module.cpp").read_text(encoding="utf-8")

    assert "struct DecodePolicy" in native_text
    assert "build_default_decode_policy" in native_text
    assert "apply_decode_policy" in native_text
    assert "build_default_decode_config" in native_text
    assert "snapshot_format" in native_text
    assert "snapshot_decoder" in native_text
    assert "resolve_subsong_index" in native_text
    assert "vendor/vgmstream @ 5d01f5717c1489101918258fbed97659a390c356" in native_text


def test_developer_binding_doc_tracks_current_upstream_revision_and_file_mapping() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    doc_text = repo_root.joinpath("docs", "developer-upstream-binding.md").read_text(encoding="utf-8")

    result = subprocess.run(
        ["git", "-C", str(repo_root / "vendor" / "vgmstream"), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert result.stdout.strip() in doc_text
    assert "本地文件" in doc_text
    assert "上游文件" in doc_text
    assert "src/native/module.cpp" in doc_text
    assert "cmake/resolve_vgmstream.cmake" in doc_text
    assert "vendor/vgmstream/src/libvgmstream.h" in doc_text
    assert "vendor/vgmstream/cmake/vgmstream.cmake" in doc_text


def test_developer_binding_doc_includes_maintainer_entrypoints() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    doc_text = repo_root.joinpath("docs", "developer-upstream-binding.md").read_text(encoding="utf-8")

    assert "维护入口" in doc_text
    assert "常见变更场景" in doc_text
    assert "先看哪个本地文件" in doc_text
    assert "再看哪个上游文件" in doc_text
    assert "验证方式" in doc_text
