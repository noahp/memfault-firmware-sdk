cmake_minimum_required(VERSION 3.12.4)

if(ESP_PLATFORM)
#   get_filename_component(memfault_firmare_sdk_dir ${CMAKE_CURRENT_LIST_DIR} ABSOLUTE)
  include(${CMAKE_CURRENT_LIST_DIR}/ports/esp_idf/memfault.cmake)
endif()
