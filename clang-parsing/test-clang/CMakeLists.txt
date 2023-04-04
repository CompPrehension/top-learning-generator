cmake_minimum_required(VERSION 3.25)
project(CompPhTaskGenerator VERSION 1.0)

## todo fix /GR opting for MSVC
set(CMAKE_CXX_STANDARD 17)
add_compile_options(-fexceptions)
add_compile_options(-frtti)

set(LLVM_LINK_COMPONENTS support)

#find_package(LLVM REQUIRED CONFIG)

#message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
#message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

# Set your project compile flags.
# E.g. if using the C++ header files
# you will need to enable C++11 support
# for your compiler.

#include_directories(${LLVM_INCLUDE_DIRS})
#separate_arguments(LLVM_DEFINITIONS_LIST NATIVE_COMMAND ${LLVM_DEFINITIONS})
#add_definitions(${LLVM_DEFINITIONS_LIST})

add_clang_executable(compph-task-generator
  main.cpp
  helpers.cpp
  expression-domain-functions.cpp
  cntrl-flow-domain-funtions.cpp
  )
target_link_libraries(compph-task-generator
  PRIVATE
  clangAST
  clangASTMatchers
  clangBasic
  clangFrontend  
  clangLex
  clangTooling
  clangSerialization
  )