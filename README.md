# sparam

一款简单的MCU参数监测和标定工具，通过串口和ELF文件实现通用变量读写，无需专用调试器。

## 特性

- **零代码侵入**：上位机直接解析ELF/MAP文件获取变量地址
- **传输无关**：协议与传输介质解耦
- **多设备支持**：支持多下位机并行监测
- **双界面**：GUI和CLI两种使用方式

## 项目结构

```
sparam/
├── doc/                    # 设计文档
├── firmware/               # 下位机固件
│   ├── sparam.c           # 核心实现
│   ├── sparam.h           # 公开API
│   ├── sparam_hal.h       # HAL抽象层
│   ├── sparam_port.h      # 配置文件
│   └── stm32/             # STM32参考实现
└── host/                   # 上位机工具（待实现）
```

## 快速开始

### 下位机集成

1. 将 `firmware/` 下的文件复制到工程
2. 配置 `sparam_port.h` 中的参数
3. 实现 `sparam_uart_send()` 函数
4. 在初始化时调用 `sparam_init()`
5. 在DMA接收回调中调用 `sparam_on_rx_done()`
6. 在1ms定时器中断中调用 `sparam_on_timer_tick()`

详见 [firmware/README.md](firmware/README.md)

## 协议

详见 [doc/总设计文档.md](doc/总设计文档.md)

## 许可证

MIT License