cmake_minimum_required(VERSION 3.20...3.30)

if(NOT DEFINED SKBUILD_PROJECT_NAME)
    set(SKBUILD_PROJECT_NAME "pyvgmstream")
endif()

if(NOT DEFINED SKBUILD_PROJECT_VERSION)
    set(SKBUILD_PROJECT_VERSION "0.1.0")
endif()

project(${SKBUILD_PROJECT_NAME} VERSION ${SKBUILD_PROJECT_VERSION} LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "pyvgmstream currently supports x64 builds only.")
endif()

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_native src/native/module.cpp)

set(VGM_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/vendor/vgmstream")
if(NOT EXISTS "${VGM_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "vendored vgmstream source is required under vendor/vgmstream")
endif()

set(USE_MPEG OFF CACHE BOOL "" FORCE)
set(USE_VORBIS ON CACHE BOOL "" FORCE)
set(USE_FFMPEG OFF CACHE BOOL "" FORCE)
set(USE_G719 OFF CACHE BOOL "" FORCE)
set(USE_ATRAC9 OFF CACHE BOOL "" FORCE)
set(USE_CELT OFF CACHE BOOL "" FORCE)
set(USE_SPEEX OFF CACHE BOOL "" FORCE)

set(BUILD_CLI OFF CACHE BOOL "" FORCE)
set(BUILD_FB2K OFF CACHE BOOL "" FORCE)
set(BUILD_WINAMP OFF CACHE BOOL "" FORCE)
set(BUILD_XMPLAY OFF CACHE BOOL "" FORCE)
set(BUILD_V123 OFF CACHE BOOL "" FORCE)
set(BUILD_AUDACIOUS OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(BUILD_STATIC OFF CACHE BOOL "" FORCE)

set(VGM_BINARY_DIR "${CMAKE_CURRENT_BINARY_DIR}/vgmstream-local")
set(CMAKE_MODULE_PATH "${VGM_SOURCE_DIR}/cmake;${CMAKE_MODULE_PATH}")

include(vgmstream)

if(WIN32)
    file(MAKE_DIRECTORY "${VGM_BINARY_DIR}/ext_libs")

    add_custom_command(
        OUTPUT "${VGM_BINARY_DIR}/ext_libs/libvorbis.lib" "${VGM_BINARY_DIR}/ext_libs/libvorbis.exp"
        COMMAND lib
        ARGS /def:${VGM_SOURCE_DIR}/ext_libs/libvorbis.def /machine:x64 /out:${VGM_BINARY_DIR}/ext_libs/libvorbis.lib
        DEPENDS "${VGM_SOURCE_DIR}/ext_libs/libvorbis.def"
    )
    add_custom_target(libvorbis DEPENDS "${VGM_BINARY_DIR}/ext_libs/libvorbis.lib")
endif()

add_subdirectory("${VGM_SOURCE_DIR}/src" "${VGM_BINARY_DIR}/src" EXCLUDE_FROM_ALL)

target_include_directories(_native PRIVATE "${VGM_SOURCE_DIR}/src")
target_link_libraries(_native PRIVATE libvgmstream)
setup_target(_native TRUE)

if(WIN32)
    set(PYVGMSTREAM_VORBIS_DLL "${VGM_SOURCE_DIR}/ext_libs/libvorbis.dll")
    if(CMAKE_SIZEOF_VOID_P EQUAL 8 AND EXISTS "${VGM_SOURCE_DIR}/ext_libs/dll-x64/libvorbis.dll")
        set(PYVGMSTREAM_VORBIS_DLL "${VGM_SOURCE_DIR}/ext_libs/dll-x64/libvorbis.dll")
    endif()

    if(EXISTS "${PYVGMSTREAM_VORBIS_DLL}")
        install(FILES "${PYVGMSTREAM_VORBIS_DLL}" DESTINATION pyvgmstream)
    endif()
endif()

install(TARGETS _native DESTINATION pyvgmstream)
