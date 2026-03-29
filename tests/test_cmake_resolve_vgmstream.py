from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RESOLVE_VGMSTREAM = REPO_ROOT / "cmake" / "resolve_vgmstream.cmake"


def test_rewrite_system_vorbis_link_interface_replaces_bare_library_names(tmp_path: Path) -> None:
    cmake = shutil.which("cmake")
    if cmake is None:
        pytest.skip("cmake 不在当前 PATH 中，跳过该构建配置测试。")

    source_dir = tmp_path / "src"
    build_dir = tmp_path / "build"
    source_dir.mkdir()

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.20)",
                "project(resolve_vgmstream_link_interface NONE)",
                f'include(\"{RESOLVE_VGMSTREAM.as_posix()}\")',
                "add_library(libvgmstream STATIC IMPORTED)",
                'set_target_properties(libvgmstream PROPERTIES INTERFACE_LINK_LIBRARIES "vorbisfile;vorbis;ogg;m")',
                "add_library(Vorbis::VorbisFile UNKNOWN IMPORTED)",
                "add_library(Vorbis::Vorbis UNKNOWN IMPORTED)",
                "add_library(Ogg::Ogg UNKNOWN IMPORTED)",
                "pyvgmstream_rewrite_system_vorbis_link_interface(libvgmstream)",
                'get_target_property(link_items libvgmstream INTERFACE_LINK_LIBRARIES)',
                'file(WRITE "${CMAKE_BINARY_DIR}/link-items.txt" "${link_items}")',
            ]
        ),
        encoding="utf-8",
    )

    configure = subprocess.run(
        [cmake, "-S", str(source_dir), "-B", str(build_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert configure.returncode == 0, configure.stderr or configure.stdout

    link_items = (build_dir / "link-items.txt").read_text(encoding="utf-8")
    assert link_items == "Vorbis::VorbisFile;Vorbis::Vorbis;Ogg::Ogg;m"


def test_rewrite_system_vorbis_link_interface_replaces_link_only_library_names(tmp_path: Path) -> None:
    cmake = shutil.which("cmake")
    if cmake is None:
        pytest.skip("cmake 不在当前 PATH 中，跳过该构建配置测试。")

    source_dir = tmp_path / "src"
    build_dir = tmp_path / "build"
    source_dir.mkdir()

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.20)",
                "project(resolve_vgmstream_link_only NONE)",
                f'include(\"{RESOLVE_VGMSTREAM.as_posix()}\")',
                "add_library(libvgmstream STATIC IMPORTED)",
                'set_target_properties(libvgmstream PROPERTIES INTERFACE_LINK_LIBRARIES "$<LINK_ONLY:vorbisfile>;$<LINK_ONLY:vorbis>;$<LINK_ONLY:ogg>;$<LINK_ONLY:m>")',
                "add_library(Vorbis::VorbisFile UNKNOWN IMPORTED)",
                "add_library(Vorbis::Vorbis UNKNOWN IMPORTED)",
                "add_library(Ogg::Ogg UNKNOWN IMPORTED)",
                "pyvgmstream_rewrite_system_vorbis_link_interface(libvgmstream)",
                'get_target_property(link_items libvgmstream INTERFACE_LINK_LIBRARIES)',
                'file(WRITE "${CMAKE_BINARY_DIR}/link-items.txt" "${link_items}")',
            ]
        ),
        encoding="utf-8",
    )

    configure = subprocess.run(
        [cmake, "-S", str(source_dir), "-B", str(build_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert configure.returncode == 0, configure.stderr or configure.stdout

    link_items = (build_dir / "link-items.txt").read_text(encoding="utf-8")
    assert (
        link_items
        == "$<LINK_ONLY:Vorbis::VorbisFile>;$<LINK_ONLY:Vorbis::Vorbis>;$<LINK_ONLY:Ogg::Ogg>;$<LINK_ONLY:m>"
    )
