set_project("sparam_demo")
set_version("0.1.0")
set_xmakever("3.0.0")

set_languages("c99")
add_rules("mode.debug", "mode.release")
add_rules("plugin.compile_commands.autoupdate", {outputdir = "."})

includes("stm32f1xx-rules.lua")
includes("arm-none-eabi-custom.lua")

target("sparam_demo")
    set_kind("binary")
    set_plat("cross")
    set_arch("arm")
    set_toolchains("arm-none-eabi-custom")

    add_rules("stm32.f1xx", {
        mcu = "STM32F103xE",
        link_file = "STM32F103XX_FLASH.ld"
    })
    add_rules("util.convert_bin_hex")

    add_includedirs("src")
    add_includedirs("../firmware")

    add_files("src/*.c")
    add_files("../firmware/sparam.c")
