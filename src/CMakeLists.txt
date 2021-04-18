cmake_minimum_required (VERSION 3.9)

project(WDPMCL)

find_package(OpenCL REQUIRED)

IF (UNIX AND NOT APPLE)
	message(STATUS "current platform : Linux")
	SET(SRC WDPMCL.c)
ELSEIF(APPLE)
	message(STATUS "current platform: MacOS")
	SET(SRC WDPMCL.c)
ELSE()
	message(STATUS "curent platform : windows")
	add_executable(WDPMCL WDPMCL-threshold6.c)
ENDIF()

add_executable(WDPMCL ${SRC})
target_include_directories(WDPMCL PRIVATE ${OpenCL_INCLUDE_DIRS})
target_link_libraries(WDPMCL PRIVATE ${OpenCL_LIBRARIES})

if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
	target_compile_options(WDPMCL PRIVATE -Wall -pedantic)
else()
	target_compile_options(WDPMCL PRIVATE)
endif()
