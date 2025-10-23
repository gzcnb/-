cmake_minimum_required(VERSION 3.10)
project(MyStaticLibrary_Azitide)

# 设置C++标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)
#忽略这些与参数传递约定变化相关的警告
add_compile_options(-Wno-psabi)
# 包含头文件目录
include_directories(include)
# 设置库文件输出目录
set(MY_LIB_PATH "${CMAKE_SOURCE_DIR}/lib") 
# 设置可执行文件路径


set(LibGrbot_DIR ${MY_LIB_PATH}/libGrbot.so)
include_directories(${PROJECT_SOURCE_DIR}/include)


add_executable(MyApp src/main.cpp)
set (EXECUTABLE_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/bin)
# 链接静态库
target_link_libraries(MyApp PRIVATE ${LibGrbot_DIR})