-- 编译与链接选项 (Cortex-M3)
-- 注入通用 flags（不含 target 专属 linker script/map）
local function apply_common(target, configs)
    -- 通用编译选项（适用于 Cortex-M3，不包含 linker script）
    target:add("cflags", {
        "-mcpu=cortex-m3",
        "-mthumb",
        "-std=c11",
        "-Wall",
        "-fdata-sections",
        "-ffunction-sections",
        "-g",
        "-gdwarf-2"
    }, {force = true})

    target:add("asflags", {
        "-mcpu=cortex-m3",
        "-mthumb"
    }, {force = true})

    -- 通用链接选项（不包含 -T linker 脚本项，target 保留其专属 -T/-Map）
    target:add("ldflags", {
        "-mcpu=cortex-m3",
        "-mthumb",
        "-Wl,--gc-sections",
        "-lc", "-lm", "-lnosys",
        "--specs=nano.specs"
    }, {linker = true, force = true})

    -- 如果需要使用 printf/scanf 的浮点支持
    -- 自己加链接器选项，默认不启用以节省空间
    -- "-u _printf_float",
    -- "-u _scanf_float"
end

local function apply_cmsis(target, configs)
    -- 约定target必须在项目根目录的脚本目录下，
    -- 也就是target的这个脚本必须跟Drivers目录在同一级
    local root = target:scriptdir()
    local drv = path.join(root, "Drivers", "CMSIS")
    if not os.isdir(drv) then
        print(string.format(">>> Warning: cannot locate STM32F1 CMSIS for target '%s' (checked common locations). Skipping CMSIS include injection.", target:name()))
        return
    end

    local cmsis_inc_dir = path.join(root, "Drivers/CMSIS/Include")
    if not os.isdir(cmsis_inc_dir) then
        print(string.format(">>> Warning: cannot locate CMSIS includes for STM32F1 for target '%s' — checked common locations.", target:name()))
        return
    end
    target:add("includedirs", cmsis_inc_dir)

    local device_inc_dir = path.join(root, "Drivers/CMSIS/Device/ST/STM32F1xx/Include")
    if not os.isdir(device_inc_dir) then
        print(string.format(">>> Warning: cannot locate CMSIS device includes for STM32F1 for target '%s' — checked common locations.", target:name()))
        return
    end
    target:add("includedirs", device_inc_dir)
end

-- 注入 CMSIS 头文件路径 
local function apply_hal(target, configs)
    -- 约定target必须在项目根目录的脚本目录下，
    -- 也就是target的这个脚本必须跟Drivers目录在同一级
    local root = target:scriptdir()
    local drv = path.join(root, "Drivers", "STM32F1xx_HAL_Driver")
    if not os.isdir(drv) then
        print(string.format(">>> Warning: cannot locate STM32F1 HAL Drivers for target '%s' (checked common locations). Skipping HAL source injection.", target:name()))
        print(">>> root:".. root)
        print(">>> drv:".. drv)
        return
    end

    local src_dir = path.join(root, "Drivers/STM32F1xx_HAL_Driver/Src")
    local inc_dir = path.join(root, "Drivers/STM32F1xx_HAL_Driver/Inc")

    -- 仅在确实存在时添加源与头路径
    if not os.isdir(src_dir) then
        print(string.format(">>> Warning: cannot locate STM32F1 HAL Driver source directory for target '%s'.", target:name()))
        return
    end

    target:add("files", path.join(src_dir, "*.c"))
    target:remove("files", path.join(src_dir, "*_template.c"))
    target:remove("files", path.join(src_dir, "stm32f1xx_hal_flash_ramfunc.c"))

    if not os.isdir(inc_dir) then
        print(string.format(">>> Warning: cannot locate STM32F1 HAL Driver Include directory for target '%s'.", target:name()))
        return
    end
    target:add("includedirs", inc_dir)

    -- 宏
    target:add("defines", "USE_HAL_DRIVER")
end

-- 注入 CubeMX 生成的核心代码
local function apply_cubemx_gen(target, configs)
    -- 获取当前 target 的脚本目录（rule 已被共享放到其他位置时仍能正确定位）
    local root_dir = target:scriptdir()
    
    -- 添加源文件
    target:add("files", path.join(root_dir, "Core/Src/*.c"))
    target:add("includedirs", path.join(root_dir, "Core/Inc"))
end

-- rule: stm32.f1xx
-- 描述：为 STM32 F1 系列项目提供一键式配置，解析参数并委托给具体的 apply 函数。
-- 用法：add_rules("stm32.f1xx", {mcu = "STM32F103xE", ...})
--
-- 参数说明（均可在 configs 表中传入）：
--   mcu          : string  **必填**，芯片型号（如 "STM32F103xE"），用于宏定义、文件名推断等。
--   startup_file : string  可选，启动文件路径。默认从 target 所在目录查找 "startup_" .. mcu小写 .. ".s"
--   cmsis        : boolean 可选，是否添加 CMSIS 头文件路径，默认为 true。
--   hal          : boolean 可选，是否添加 HAL 库驱动，默认为 true。
--   cubemx_gen   : boolean 可选，是否添加 CubeMX 生成的代码，默认为 true。
--   link_file    : string  可选，链接脚本路径。默认从 mcu 截取前9个字符（如 "STM32F103X"）拼接 "_FLASH.ld"，在 target 目录下查找。
--   map_file     : string  可选，map 文件输出路径。默认 "build/" .. target:name() .. "/output.map"
--   out_file     : string  可选，输出文件名（含扩展名）。默认 target:name() .. ".elf"
--
-- 注意：该规则不直接修改 target，而是将解析后的完整配置表传递给各 apply_xxx 函数，
--       由那些函数负责实际添加文件、定义、编译选项等。

rule("stm32.f1xx")
    on_load(function (target)
        -- 1. 获取传入的配置参数（用户通过 add_rules 的第二个参数传入）
        local configs = target:extraconf("rules", "stm32.f1xx") or {}

        -- 2. 校验必须参数
        local mcu = configs.mcu
        if not mcu then
            raise("stm32.f1xx rule: missing required parameter 'mcu'")
        end
        
        -- 3. 生成默认值并合并到 configs 表（供后续 apply 函数使用）
        --    注意：不要覆盖用户显式传入的值
        
        -- 芯片小写名（用于默认启动文件）
        local mcu_lower = mcu:lower()
        
        -- 芯片系列前缀（用于默认链接脚本文件名，取前9个字符，例如 "STM32F103X"）
        local series_prefix = mcu:sub(1, 9)  -- 可根据实际需要调整截取长度
        
        -- 目标所在目录（用于定位默认启动文件、链接脚本等）
        local target_dir = target:scriptdir()
        
        -- 启动文件默认值
        if configs.startup_file == nil then
            configs.startup_file = path.join(target_dir, "startup_" .. mcu_lower .. ".s")
        end
        
        -- CMSIS 开关
        if configs.cmsis == nil then
            configs.cmsis = true
        end
        
        -- HAL 开关
        if configs.hal == nil then
            configs.hal = true
        end
        
        -- CubeMX 生成代码开关
        if configs.cubemx_gen == nil then
            configs.cubemx_gen = true
        end
        
        -- 链接脚本默认值
        if configs.link_file == nil then
            configs.link_file = path.join(target_dir, series_prefix .. "XX_FLASH.ld")
        end
        
        -- map 文件默认值
        if configs.map_file == nil then
            configs.map_file = path.join("build", target:name(), "output.map")
        end

        -- out_file 输出文件名字默认值
        if configs.out_file == nil then
            configs.out_file = target:name() .. ".elf"
        end

        -- 打印配置
        print(string.format(">>> Configuring target '%s' with STM32F1xx rule:", target:name()))
        for k, v in pairs(configs) do
            print(string.format("    %s: %s", k, tostring(v)))
        end
        
        -- 4. 调用各个 apply_xxx 函数，将完整 configs 传递过去
        --    注意：这些函数需要你自己实现，它们应该接收 target 和 configs 两个参数，
        --    并负责添加文件、定义、编译选项等。
        
        -- 应用通用编译选项（对应之前的 stm32.f1xx.common）
        if apply_common then
            apply_common(target, configs)
        end
        
        -- 应用 CMSIS 头文件路径
        if configs.cmsis and apply_cmsis then
            apply_cmsis(target, configs)
        end
        
        -- 应用 HAL 库驱动
        if configs.hal and apply_hal then
            apply_hal(target, configs)
        end
        
        -- 添加宏定义（根据芯片型号而定）
        target:add("defines", mcu)

        -- 添加启动文件
        if configs.startup_file and os.isfile(configs.startup_file) then
            target:add("files", configs.startup_file)
        else
            -- 如果文件不存在，发出警告（或可根据需要改为错误）
            raise("startup file not found: %s", configs.startup_file)
        end
        
        -- 添加链接脚本和 map 文件生成
        if configs.map_file then
            local map_dir = path.directory(configs.map_file)
            if map_dir and not os.isdir(map_dir) then
                os.mkdir(map_dir)
            end
            target:add("ldflags", "-Wl,-Map=" .. configs.map_file, {force = true})
        end
        if os.isfile(configs.link_file) then
            target:add("ldflags", "-T" .. configs.link_file, {force = true})
        else
            warn("linker script not found: %s", configs.link_file)
        end
        
        -- 应用 CubeMX 生成的代码
        if configs.cubemx_gen and apply_cubemx_gen then
            apply_cubemx_gen(target, configs)
        end
        
        -- 设置文件输出名字，默认输出elf文件
        target:set("filename", configs.out_file)

        -- 6. 可选：将解析后的 configs 存入 target 的 values，供其他规则或调试使用
        target:set("values", "stm32_configs", configs)

        -- 保存芯片信号数据，这样子src下的这些包就可以通过 target:values("mcu") 来获取当前芯片型号以免重复传参
        target:set("values", "mcu", mcu)  -- 保存芯片型号
    end)

rule_end()

-- 规则：由 CubeMX 提供的 FreeRTOS 源（兼容 CMSIS）
-- 触发：配置阶段（on_load）
-- 作用：添加 FreeRTOS 源码与头路径（包含 portable 与 CMSIS-RTOS V2），将 RTOS 编入目标中
-- 说明：CubeMX 可能在 Core/Src 中生成应用相关的钩子/文件，项目应显式维护这些文件。
rule("stm32.f1xx.hal.freertos")
    on_load(function (target)
        -- 获取当前 target 的脚本目录（rule 已被共享放到其他位置时仍能正确定位）
        local root_dir = target:scriptdir()
        
        -- 添加源文件
        target:add("files", {
            path.join(root_dir, "Middlewares/Third_Party/FreeRTOS/Source/*.c"),
            path.join(root_dir, "Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS_V2/*.c"),
            path.join(root_dir, "Middlewares/Third_Party/FreeRTOS/Source/portable/MemMang/heap_4.c"),
            path.join(root_dir, "Middlewares/Third_Party/FreeRTOS/Source/portable/GCC/ARM_CM3/*.c")
        })

        -- 添加头文件路径
        target:add("includedirs", {
            path.join(root_dir, "Middlewares/Third_Party/FreeRTOS/Source/include"),
            path.join(root_dir, "Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS_V2"),
            path.join(root_dir, "Middlewares/Third_Party/FreeRTOS/Source/portable/GCC/ARM_CM3"),
        })
    end)
rule_end()
