find_package(pybind11 REQUIRED)

# Include your public headers
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# ===== Uncertainty =====
add_library(logngine_uncertainty STATIC
        uncertainty/hello.cpp
)
target_include_directories(logngine_uncertainty PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

pybind11_add_module(_uncertainty_core bindings/py_uncertainty.cpp)
target_link_libraries(_uncertainty_core PRIVATE logngine_uncertainty)
target_include_directories(_uncertainty_core PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
# Place output in the Python package: logngine/uncertainty/_core/
set_target_properties(_uncertainty_core PROPERTIES
        OUTPUT_NAME "_uncertainty_core"
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/src/logngine/uncertainty/_core
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/src/logngine/uncertainty/_core
        ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/build/libs
        RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/src/logngine/uncertainty/_core
        LIBRARY_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/src/logngine/uncertainty/_core
        ARCHIVE_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/build/libs
)

# ===== Thermo =====
add_library(logngine_thermo STATIC
        thermo/hello.cpp
)
target_include_directories(logngine_thermo PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

pybind11_add_module(_thermo_core bindings/py_thermo.cpp)
target_link_libraries(_thermo_core PRIVATE logngine_thermo)
target_include_directories(_thermo_core PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
set_target_properties(_thermo_core PROPERTIES
        OUTPUT_NAME "_thermo_core"
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/src/logngine/thermo/_core
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/src/logngine/thermo/_core
        ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/build/libs
        RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/src/logngine/thermo/_core
        LIBRARY_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/src/logngine/thermo/_core
        ARCHIVE_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/build/libs
)

# ===== Materials =====
add_library(logngine_materials STATIC
        materials/hello.cpp
)
target_include_directories(logngine_materials PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

pybind11_add_module(_materials_core bindings/py_materials.cpp)
target_link_libraries(_materials_core PRIVATE logngine_materials)
target_include_directories(_materials_core PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
set_target_properties(_materials_core PROPERTIES
        OUTPUT_NAME "_materials_core"
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/src/logngine/materials/_core
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/src/logngine/materials/_core
        ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/build/libs
        RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/src/logngine/materials/_core
        LIBRARY_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/src/logngine/materials/_core
        ARCHIVE_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/build/libs
)