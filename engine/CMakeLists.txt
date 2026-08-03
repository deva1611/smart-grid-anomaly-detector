cmake_minimum_required(VERSION 3.15)
project(smart_grid_engine CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The core detection logic, built as a small library so it can be reused
# by the demo executable, the test suite, and the pybind11 module below,
# without duplicating code.
add_library(engine_lib
    src/rolling_zscore_detector.cpp
)
target_include_directories(engine_lib PUBLIC include)

# A standalone demo executable to prove the engine works on its own.
add_executable(engine_demo
    src/main.cpp
)
target_link_libraries(engine_demo PRIVATE engine_lib)

# --- Tests ---
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.15.2
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_executable(engine_tests
    tests/test_detector.cpp
)
target_link_libraries(engine_tests PRIVATE engine_lib gtest_main)

include(GoogleTest)
gtest_discover_tests(engine_tests)

# --- Python bindings (pybind11) ---
# Wraps engine_lib as an importable Python module named smart_grid_engine.
# Requires pybind11_DIR to be passed at configure time, e.g.:
#   cmake -S . -B build -Dpybind11_DIR="<path from pybind11.get_cmake_dir()>"
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(smart_grid_engine
    bindings/bindings.cpp
)
target_link_libraries(smart_grid_engine PRIVATE engine_lib)