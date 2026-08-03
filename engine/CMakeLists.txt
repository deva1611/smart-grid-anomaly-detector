cmake_minimum_required(VERSION 3.15)
project(smart_grid_engine CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The core detection logic, built as a small library so it can later be
# reused by both the demo executable, the test suite, and (from Day 5
# onward) the pybind11 module, without duplicating code.
add_library(engine_lib
    src/rolling_zscore_detector.cpp
)
target_include_directories(engine_lib PUBLIC include)

# A standalone demo executable to prove the engine works on its own,
# before wiring it up to Python, FastAPI, or anything else.
add_executable(engine_demo
    src/main.cpp
)
target_link_libraries(engine_demo PRIVATE engine_lib)

# --- Tests ---
# FetchContent downloads and builds GoogleTest automatically, so there's
# nothing to install manually — CMake handles it the first time you build.
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.15.2
)
# On Windows, force GoogleTest to use the same runtime library settings
# as the rest of this project, to avoid linker mismatches.
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_executable(engine_tests
    tests/test_detector.cpp
)
target_link_libraries(engine_tests PRIVATE engine_lib gtest_main)

include(GoogleTest)
gtest_discover_tests(engine_tests)