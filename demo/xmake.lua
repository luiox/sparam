-- 设置工程名称、版本
set_project("shuffler")
set_version("1.0.0")
set_xmakever("3.0.0")

-- 允许 c99 和 c++17 标准
set_languages("c99", "cxx17")

-- 添加调试/发布模式规则
add_rules("mode.debug", "mode.release")

add_rules("plugin.compile_commands.autoupdate", {outputdir = "."})

includes("log")
includes("third_party")

-- 加载 HAL 转换规则
includes("stm32f1xx-rules.lua")
-- 加载交叉编译工具链配置
includes("arm-none-eabi-custom.lua")

target("shuffler")
    set_kind("binary")

    -- 强制设置默认平台为交叉编译
    set_plat("cross")
    set_arch("arm")

    -- 使用 arm-none-eabi-custom.lua 里定义的工具链
    set_toolchains("arm-none-eabi-custom")

    -- 自动转换 .elf 为 .bin 和 .hex
    add_rules("util.convert_bin_hex")

    -- 添加HAL库、CMSIS等STM32项目所必须的配置
    add_rules("stm32.f1xx", {mcu = "STM32F103xE"})

    ---------------------------------------------------------------------------
    
    -- 日志库
    add_rules("segger_rtt")
    add_rules("logger", { backend="segger_rtt"})
    
    add_includedirs("log")
    add_includedirs("config")
    -- add_rules("easy_logger")
    -- add_rules("logger", { backend="easy_logger"})

    ---------------------------------------------------------------------------

    -- 用户代码
    add_includedirs(os.scriptdir())
    add_includedirs("app")
    add_includedirs("bsp")
    add_files("app/*.c")
    add_files("bsp/*.c")
