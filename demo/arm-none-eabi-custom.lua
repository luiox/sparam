toolchain("arm-none-eabi-custom")
    set_kind("standalone")

    -- 1. 定义一个检查函数：看某个目录下有没有 arm-gcc
    local function check_gcc_in(bin_dir)
        local ext = is_host("windows") and ".exe" or ""
        local gcc_path = path.join(bin_dir, "arm-none-eabi-gcc" .. ext)
        return os.isfile(gcc_path)
    end

    on_load(function (toolchain)
        import("lib.detect.find_tool")
        
        local sdk_root = nil
        local bin_dir = nil

        -- 优先尝试：用户配置的 sdk 路径 (xmake f --sdk=xxx)
        local config_sdk = toolchain:config("sdk")

        if config_sdk then
            sdk_root = config_sdk
            bin_dir = path.join(sdk_root, "bin")
        end

        -- 其次尝试：环境变量 ARM_GCC_SDK
        if not sdk_root then
            local env_sdk = os.getenv("ARM_GCC_SDK")
            if env_sdk and os.isdir(env_sdk) then
                sdk_root = env_sdk
                bin_dir = path.join(sdk_root, "bin")
                print(">>> Using ARM_GCC_SDK from environment: " .. sdk_root)
            end
        end

        -- 最后尝试：自动从 PATH 中查找
        if not sdk_root then
            local tool = find_tool("arm-none-eabi-gcc")
            if tool then
                bin_dir = path.directory(tool.program)
                sdk_root = path.directory(bin_dir)
                print(">>> Auto-detected ARM Toolchain SDK Root: " .. sdk_root)
            end
        end

        -- 如果找到了路径，就应用设置（保守且兼容 xmake 内部查找）
        if sdk_root and bin_dir and check_gcc_in(bin_dir) then
            local function trim(s)
                if not s then return s end
                return s:match("^%s*(.-)%s*$")
            end
            sdk_root = trim(sdk_root)
            bin_dir = trim(bin_dir)

            if bin_dir:lower():endswith("bin") then
                sdk_root = path.directory(bin_dir)
            end

            -- 只注册 sdkdir/bindir（xmake 会根据 bindir + basename 解析实际可执行文件），
            -- 并打印诊断信息帮助排查（避免在 toolchain scope 写入绝对路径导致内部映射问题）。
            toolchain:set("sdkdir", sdk_root)
            toolchain:set("bindir", bin_dir)

            local function has(prog)
                return os.isfile(path.join(bin_dir, prog .. (is_host("windows") and ".exe" or "")))
            end
            print(" >>> ARM Toolchain SDK Root: " .. sdk_root)
            print(" >>> ARM Toolchain Bin Dir: " .. bin_dir)
            print(string.format(" >>> Quick check: as=%s, gcc=%s, g++=%s, objcopy=%s",
                has("arm-none-eabi-as") and "ok" or "missing",
                has("arm-none-eabi-gcc") and "ok" or "missing",
                has("arm-none-eabi-g++") and "ok" or "missing",
                has("arm-none-eabi-objcopy") and "ok" or "missing"))

            print(">>> Registered bindir/sdkdir — if xmake 仍报 'cannot get program', 重启 VS Code/终端 或 使用 `setx` 做永久变量 并重启终端。")
        else
            print(">>> Warning: ARM Toolchain not found! Please check PATH or set ARM_GCC_SDK.")
        end
    end)

    -- 设置工具集映射
    set_toolset("cc", "arm-none-eabi-gcc")
    set_toolset("cxx", "arm-none-eabi-g++")
    set_toolset("as", "arm-none-eabi-gcc") -- 使用 gcc 作为汇编入口，处理 .S 文件更方便
    set_toolset("ld", "arm-none-eabi-gcc") -- 使用 gcc 作为链接入口
    set_toolset("ar", "arm-none-eabi-ar")
    set_toolset("objcopy", "arm-none-eabi-objcopy")
    set_toolset("size", "arm-none-eabi-size")
    
toolchain_end()

-- 规则：将 ELF 转换为 BIN/HEX（使用 objcopy）
-- 触发：链接完成后（after_build）
-- 作用：定位合适的 arm-none-eabi-objcopy 并由生成的 ELF 导出 .bin/.hex
-- 说明：优先使用 toolchain 的 bindir 或环境变量 ARM_OBJCOPY；找不到时给出明确的错误提示和修复建议。
rule("util.convert_bin_hex")
    after_build(function (target)
        import("lib.detect.find_tool")

        -- 1. 获取目标文件路径
        local targetfile = target:targetfile()
        
        -- 2. 智能查找 objcopy 工具
        local objcopy = nil
        local toolchain = nil
        
        -- 优先：直接从 target 的 toolchains 中使用其 bindir 下的可执行文件（更确定且无需 PATH 查找）
        for _, tc in ipairs(target:toolchains()) do
            if tc:name() == "arm-none-eabi-custom" or tc:name() == "arm-none-eabi" then
                toolchain = tc
                break
            end
        end
        if toolchain then
            local bindir = toolchain:bindir()
            if bindir then
                local ext = is_host("windows") and ".exe" or ""
                local prog = path.join(bindir, "arm-none-eabi-objcopy" .. ext)
                if os.isfile(prog) then
                    -- 构造与 find_tool 返回格式相兼容的表
                    objcopy = { program = prog }
                end
            end
        end

        -- 回退：在全局环境中查找（保留原有行为以兼容特殊环境）
        if not objcopy then
            -- 强制按 program 名称查找以避免匹配到系统 objcopy
            objcopy = find_tool("arm-none-eabi-objcopy", {program = "arm-none-eabi-objcopy"})
        end

        -- 如果还没找到报错
        if not objcopy then
            print(">>> Error: arm-none-eabi-objcopy not found! Cannot generate hex/bin.")
            return
        end

        local objcopy_prog = objcopy.program

        -- 3. 处理 .elf 后缀问题（更鲁棒的检测）
        -- 说明：不同平台/配置下 linker 输出路径可能带或不带 .elf 后缀，
        -- 本段尝试定位真实的 ELF 文件并保证在首次构建后可用。
        local function exists(p) return p and os.isfile(p) end
        local elf_file_candidates = {
            targetfile,
            targetfile .. ".elf",
            path.join(path.directory(targetfile), path.filename(targetfile) .. ".elf")
        }
        local elf_file = nil
        for _, c in ipairs(elf_file_candidates) do
            if exists(c) then
                elf_file = c
                break
            end
        end

        -- 如果还没找到，尝试扫同目录下具有相同 basename 的 .elf（防止 xmake 在首次运行时使用临时名）
        if not elf_file then
            local dir = path.directory(targetfile)
            local base = path.filename(targetfile)
            for _, f in ipairs(os.match(path.join(dir, base .. "*.elf")) or {}) do
                if exists(f) then
                    elf_file = f
                    break
                end
            end
        end

        -- 最终兜底：如果 linker 输出为无后缀文件（rare），把它当作 ELF 使用
        if not elf_file and exists(targetfile) then
            elf_file = targetfile
        end

        if not elf_file or not exists(elf_file) then
            print(string.format(">>> Error: cannot locate ELF for target (tried: %s). Skipping objcopy.", table.concat(elf_file_candidates, ", ")))
            return
        end

        -- 4. 生成输出文件名（基于 ELF 的实际路径）
        local out_base = elf_file:gsub("%.elf$", "")
        local bin_file = out_base .. ".bin"
        local hex_file = out_base .. ".hex"

        -- 5. 在执行 objcopy 前后打印诊断并保留 ELF 到 artifacts 目录，保证首次运行即可找到
        print(">>> Using ELF: " .. elf_file)
        print(">>> Generating BIN: " .. bin_file)

        os.vrunv(objcopy_prog, {"-O", "binary", elf_file, bin_file})

        print(">>> Generating HEX: " .. hex_file)
        os.vrunv(objcopy_prog, {"-O", "ihex", elf_file, hex_file})

        -- 把 ELF 拷贝到一个稳定的 artifacts 目录，便于 CI/用户快速获取并防止被后续清理移除
        local artifacts_dir = path.join(os.projectdir(), "build", "artifacts")
        if not os.isdir(artifacts_dir) then os.mkdir(artifacts_dir) end
        local preserved_elf = path.join(artifacts_dir, path.filename(elf_file))
        os.cp(elf_file, preserved_elf)
        print(">>> ELF preserved to: " .. preserved_elf)

        print(">>> Build Artifacts Generated Successfully!")
    end)
rule_end()

