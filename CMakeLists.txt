cmake_minimum_required(VERSION 3.20...3.30)

if(NOT DEFINED SKBUILD_PROJECT_NAME)
    set(SKBUILD_PROJECT_NAME "pyvgmstream")
endif()

if(NOT DEFINED SKBUILD_PROJECT_VERSION)
    set(SKBUILD_PROJECT_VERSION "0.1.1")
endif()

project(${SKBUILD_PROJECT_NAME} VERSION ${SKBUILD_PROJECT_VERSION} LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "pyvgmstream currently supports x64 builds only.")
endif()

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(resolve_vgmstream)

pyvgmstream_resolve_vgmstream()

pybind11_add_module(_native src/native/module.cpp)
if(MSVC)
    target_compile_options(_native PRIVATE /utf-8)
endif()
target_link_libraries(_native PRIVATE pyvgmstream::vgmstream)
pyvgmstream_apply_vgmstream_target_defaults(_native)

if(PYVGMSTREAM_VGMSTREAM_RUNTIME_FILES)
    install(FILES ${PYVGMSTREAM_VGMSTREAM_RUNTIME_FILES} DESTINATION pyvgmstream)
endif()

install(TARGETS _native DESTINATION pyvgmstream)
