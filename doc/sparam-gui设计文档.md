# sparam GUI 设计文档

## 1. 目标与范围

本文件描述 host 侧图形界面的结构、交互和 M3 设计方向，覆盖变量浏览、监测、单次读写和界面布局演进。

## 2. GUI 目录结构

```
host/gui/
├── __init__.py
├── main.py
├── main_window.py
├── mock_preview.py
├── styles/
└── widgets/
```

关键职责：

- `main_window.py`：主窗口与布局编排、设备联动
- `widgets/sidebar.py`：连接/监测/单次读写/变量列表交互
- `widgets/waveform_plot.py`：实时波形渲染
- `styles/catppuccin.py`：样式主题

## 3. 当前功能

### 3.1 连接管理

- 串口选择
- 设备ID配置
- 连接状态显示

### 3.2 变量浏览

- 加载 ELF/MAP 文件
- 显示变量列表（名称、地址、类型、大小）
- 搜索过滤
- 双击添加监测项
- `Remove Selected` 显式移除监测项

### 3.3 监测工作区

- 采样速率配置
- 实时数值卡片
- 实时波形绘制
- 导出 PNG / CSV

### 3.4 参数标定

- Read Once：单次读取
- Write Once：单次写入
- 显式类型选择（uint/int/float）

## 4. M3 设计决策（Issue #3）

本轮已确认：

1. 圆角策略：默认全部无圆角
2. 布局策略：左 Sidebar / 中 Waveform / 右 Inspector
3. 架构策略：子面板改为 Dock，可停靠、可拉伸
4. 持久化策略：布局持久化为 M3 必做项（重启恢复）

## 5. M3 实施状态（已完成）

### 5.1 样式改造（默认无圆角）

- `styles/catppuccin.py` 已统一为直角风格（`border-radius: 0px`）
- 主要面板、按钮、输入框、列表项、状态芯片已切换为无圆角
- `widgets/value_card.py` 左侧色条去除圆角硬编码

### 5.2 Dock 化布局（左-中-右）

- `main_window.py` 使用 `QDockWidget` 承载 Sidebar 与 Inspector
- 左侧：`sidebarDock`（Sidebar）
- 中央：Waveform + Signal Cards
- 右侧：`inspectorDock`（Connection/Monitor Summary + Log）

### 5.3 布局持久化

- `main_window.py` 使用 `QSettings` 保存与恢复窗口布局
- 保存内容：`window/geometry` 与 `window/state`
- 恢复时机：窗口初始化阶段
- 保存时机：`closeEvent`

### 5.4 左侧三 Dock 精细化拆分

- 左侧区域拆分为三段独立 Dock：
	- Control（Transport / Monitor / Capture）
	- Single Read/Write
	- Variables
- 默认纵向分布，默认宽度 260 px，可拖拽调整。
- 各 Dock 设置稳定 objectName，保障布局持久化可恢复。

### 5.5 紧凑密度与折叠交互

- 全局样式密度下调（间距、控件占高、标题尺寸）。
- Sidebar 分区支持单独折叠。
- 支持一键收起/展开全部分区。

### 5.6 稳定性与诊断收敛

- 变量选中时自动同步 Read/Write 数据类型。
- Read Once / Write Once 异常路径加兜底，避免界面直接退出。
- 布局恢复加入版本门控与可见区域夹紧，降低几何异常风险。
- 运行时诊断日志落盘到 `host/sparam_gui_runtime.log`，记录 Qt 消息与未处理异常。
- 串口接收线程生命周期与监测流程绑定，降低 Windows 下 read/close 并发崩溃风险。

## 6. 风险与验证点

风险点：

- Dock 拖拽与高频交互下的 UI 事件竞态
- 跨平台窗口管理差异
- 串口读写线程并发导致的底层驱动不稳定

验证点：

- 快速双击变量不崩溃
- Read Once / Write Once 稳定
- Dock 可停靠、可拖出、可拉伸
- 重启后布局恢复一致
- 写入失败场景不触发进程异常退出

当前回归结果：

- `ruff format`, `ruff check`, `mypy`, `pytest` 全部通过

## 7. 相关文档

- 总入口：`总设计文档.md`
- 协议设计：`协议设计文档.md`
- CLI 设计：`sparam-cli设计文档.md`
- 任务归档：`plans/2026-03-28-issue3-m3-dock-archive.md`
