# sparam CLI 设计文档

## 1. 目标与范围

本文件描述 host 侧命令行工具的能力边界、命令集和典型工作流。

## 2. 入口与依赖

- 入口：`host/cli.py`
- 包：`host/sparam/`
- 运行方式：`uv run sparam ...`

运行环境：

- host 侧 Python 基线版本为 3.10+

依赖（节选）：

- `click`：命令行参数解析
- `pyserial`：串口通信
- `pyelftools`：ELF 解析

## 3. 命令集

### 3.1 端口与连接

- `list-ports`：列出可用串口
- `ping`：检查设备在线状态

### 3.2 符号与变量

- `parse-elf`：解析 ELF/MAP，列出变量

### 3.3 读写与监测

- `read`：单次读取变量
- `write`：单次写入变量
- `monitor`：周期读取并输出
- `stop`：停止监测

补充说明：

- `write --type` 的可选值由协议层统一注册表驱动，不再由 CLI 本地硬编码。
- `monitor --rate` 的范围与帮助文本由协议层采样率注册表驱动，避免多处定义漂移。

### 3.4 GUI 启动（桥接命令）

- `gui`：从 CLI 启动桌面 GUI

## 4. 常用工作流

### 4.1 快速连通性验证

1. `uv run sparam list-ports`
2. `uv run sparam ping -p COMx -b 115200 -d 1`

### 4.2 读取与调参

1. `uv run sparam parse-elf firmware.elf`
2. `uv run sparam read ...`
3. `uv run sparam write ...`

### 4.3 数据采样导出

1. `uv run sparam monitor ... --output data.csv`
2. 用外部工具分析 CSV

## 5. 参数与类型约束

- 变量地址与类型由 ELF/MAP 解析结果决定
- 写入类型需与协议编码匹配（参见 `协议设计文档.md`）
- 错误由设备层返回 ACK/NACK 与错误码

实现约束（Issue #6 后）：

- CLI 写入类型映射来自 `sparam/protocol.py` 中的统一类型注册表。
- CLI 监测速率范围来自 `sparam/protocol.py` 中的统一速率注册表。
- 目标是将类型/命令/采样率定义保持单一事实来源，降低扩展改动面。

## 6. 质量与测试

- 格式化：`uv run --extra dev ruff format .`
- 静态检查：`uv run --extra dev ruff check .`
- 类型检查：`uv run --extra dev mypy cli.py gui sparam tests`
- 测试：`uv run --extra test pytest -q`

新增覆盖（Issue #6 后）：

- `tests/test_protocol_edge_cases.py`：协议边界场景（CRC 错误、帧头错误、不完整帧、空载荷）。
- `tests/test_protocol_registry.py`：类型/命令/采样率注册表行为一致性。

## 7. 相关文档

- 总入口：`总设计文档.md`
- 协议设计：`协议设计文档.md`
- GUI 设计：`sparam-gui设计文档.md`
