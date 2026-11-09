cmake_minimum_required(VERSION 3.12)
project(aetherhound_dsp LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/O2 /W3 /openmp)
else()
    add_compile_options(-O3 -Wall -fPIC -fopenmp)
endif()

add_library(aetherhound_dsp SHARED
    dsp_core.cpp
    dsp_core.h
)

set_target_properties(aetherhound_dsp PROPERTIES
    OUTPUT_NAME "aetherhound_dsp"
    PREFIX ""
)
