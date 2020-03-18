cmake_minimum_required(VERSION 3.1)
project (modele-control)
enable_language(Fortran)
set(CMAKE_CXX_STANDARD 11)


# Where to look first for project cmake modules,
# before ${CMAKE_ROOT}/Modules/ is checked
set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)

include(PreventInSourceBuild)
include(setup_rpath)

# When building with Spack, include all directories of our
# transitive dependencies.  This ensures that #include statements
# will all work, without having to worry about chasing down
# transitive dependencies ourself.
#include_directories($ENV{SPACK_TRANSITIVE_INCLUDE_PATH})


# ===================================================
# Initial Defaults
# ===================================================

# Always include srcdir and builddir in include path
# This saves typing ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY} in
# about every subdir
# since cmake 2.4.0
# https://cmake.org/cmake/help/v3.0/variable/CMAKE_INCLUDE_CURRENT_DIR.html
set(CMAKE_INCLUDE_CURRENT_DIR ON)

# Put the include dirs from the source or build tree
# before all other include dirs, so the headers in the sources
# are prefered over the already installed ones
# since cmake 2.4.1
set(CMAKE_INCLUDE_DIRECTORIES_PROJECT_BEFORE ON)

# Use colored output
# since cmake 2.4.0
# set(CMAKE_COLOR_MAKEFILE ON)

#include_directories($ENV{SPACK_TRANSITIVE_INCLUDE_PATH})

# ------- Process Configure Options

if (NOT DEFINED BUILD_PYTHON)
    set(BUILD_PYTHON YES)
endif()
if (BUILD_PYTHON)
    find_package(Everytrace)
endif()

if(${BUILD_PYTHON})
    install(DIRECTORY ${PROJECT_SOURCE_DIR}/lib/ DESTINATION lib/python${PYTHON_VERSION}/site-packages
        FILES_MATCHING PATTERN "*.py")

    install(DIRECTORY ${PROJECT_SOURCE_DIR}/bin/ DESTINATION bin
        ectl els epy)
endif()
