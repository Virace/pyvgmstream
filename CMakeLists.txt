cmake_minimum_required(VERSION 3.20)

project(pyvgmstream LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The native binding target is introduced incrementally.
# Keep the top-level build shell cross-platform from day one.
