include_guard(GLOBAL)

# 本地的 vendored vgmstream 适配层。
# 该文件属于 pyvgmstream 自有文件，不是从上游直接复制过来的。
# 上游溯源：
# - vendor/vgmstream @ 5d01f5717c1489101918258fbed97659a390c356
# - 当前对接的上游构建文件：
#   - vendor/vgmstream/CMakeLists.txt
#   - vendor/vgmstream/cmake/vgmstream.cmake
#   - vendor/vgmstream/src/CMakeLists.txt

function(pyvgmstream_resolve_vgmstream)
    # 如果以后构建因为上游目录、目标名或运行时文件布局变化而损坏，
    # 维护者应优先从这个本地适配层入手，再回看上面列出的 vendored 上游文件。
    set(vgm_source_dir "${CMAKE_CURRENT_SOURCE_DIR}/vendor/vgmstream")
    if(NOT EXISTS "${vgm_source_dir}/CMakeLists.txt")
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

    set(vgm_binary_dir "${CMAKE_CURRENT_BINARY_DIR}/vgmstream-local")
    set(VGM_SOURCE_DIR "${vgm_source_dir}")
    set(VGM_BINARY_DIR "${vgm_binary_dir}")
    set(VGM_SOURCE_DIR "${vgm_source_dir}" PARENT_SCOPE)
    set(VGM_BINARY_DIR "${vgm_binary_dir}" PARENT_SCOPE)
    include("${vgm_source_dir}/cmake/vgmstream.cmake")

    if(WIN32)
        file(MAKE_DIRECTORY "${vgm_binary_dir}/ext_libs")

        add_custom_command(
            OUTPUT "${vgm_binary_dir}/ext_libs/libvorbis.lib" "${vgm_binary_dir}/ext_libs/libvorbis.exp"
            COMMAND lib
            ARGS /def:${vgm_source_dir}/ext_libs/libvorbis.def /machine:x64 /out:${vgm_binary_dir}/ext_libs/libvorbis.lib
            DEPENDS "${vgm_source_dir}/ext_libs/libvorbis.def"
        )
        add_custom_target(libvorbis DEPENDS "${vgm_binary_dir}/ext_libs/libvorbis.lib")
    endif()

    add_subdirectory("${vgm_source_dir}/src" "${vgm_binary_dir}/src" EXCLUDE_FROM_ALL)

    if(NOT TARGET pyvgmstream_vgmstream)
        add_library(pyvgmstream_vgmstream INTERFACE)
        target_include_directories(pyvgmstream_vgmstream INTERFACE "${vgm_source_dir}/src")
        target_link_libraries(pyvgmstream_vgmstream INTERFACE libvgmstream)
        add_library(pyvgmstream::vgmstream ALIAS pyvgmstream_vgmstream)
    endif()

    set(runtime_files)
    if(WIN32)
        set(vorbis_dll "${vgm_source_dir}/ext_libs/libvorbis.dll")
        if(CMAKE_SIZEOF_VOID_P EQUAL 8 AND EXISTS "${vgm_source_dir}/ext_libs/dll-x64/libvorbis.dll")
            set(vorbis_dll "${vgm_source_dir}/ext_libs/dll-x64/libvorbis.dll")
        endif()

        if(EXISTS "${vorbis_dll}")
            list(APPEND runtime_files "${vorbis_dll}")
        endif()
    endif()

    set(PYVGMSTREAM_VGMSTREAM_RUNTIME_FILES "${runtime_files}" PARENT_SCOPE)
endfunction()


function(pyvgmstream_apply_vgmstream_target_defaults target_name)
    setup_target(${target_name} TRUE)
endfunction()
