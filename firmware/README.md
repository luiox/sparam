# sparam 固件使用说明

## 文件结构

```
firmware/
├── sparam.h           # 公开API头文件
├── sparam.c           # 核心实现
├── sparam_hal.h       # HAL抽象层接口定义
├── sparam_port.h      # 用户配置文件
└── stm32/
    └── sparam_stm32.c # STM32 HAL适配层参考实现
```

## 集成步骤

### 1. 复制文件

将以下文件复制到你的工程目录：
- `sparam.h`
- `sparam.c`
- `sparam_hal.h`
- `sparam_port.h`

### 2. 配置参数

编辑 `sparam_port.h`：

```c
#define SPARAM_DEVICE_ID        1       // 设备ID（0-255）
#define SPARAM_VARS_MAX_SIZE    32      // 最大周期监测变量数
#define SPARAM_RX_BUF_SIZE      256     // 接收缓冲区大小
#define SPARAM_TX_BUF_SIZE      512     // 发送缓冲区大小
```

### 3. 实现HAL接口

在 `sparam_hal.h` 中定义了一个必须实现的函数：

```c
void sparam_uart_send(uint8_t *data, uint16_t len);
```

该函数负责通过串口DMA发送数据。STM32参考实现见 `stm32/sparam_stm32.c`。

### 4. 调用API

```c
#include "sparam.h"

// 初始化
sparam_init(SPARAM_DEVICE_ID);

// DMA接收完成回调中调用
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart1) {
        sparam_on_rx_done(rx_buf, len);
    }
}

// 1ms定时器中断中调用
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim == &htim6) {
        sparam_on_timer_tick();
    }
}
```

## API 说明

### sparam_init

```c
void sparam_init(uint8_t device_id);
```

初始化sparam模块，设置设备ID。

### sparam_on_rx_done

```c
void sparam_on_rx_done(uint8_t *data, uint16_t len);
```

在DMA接收完成时调用，传入接收到的完整数据帧。

### sparam_on_timer_tick

```c
void sparam_on_timer_tick(void);
```

在1ms定时器中断中调用，用于周期性采样和发送。

## 注意事项

1. **接收缓冲区**：建议使用乒乓缓冲区，确保接收完整性
2. **定时器配置**：定时器周期应为1ms
3. **串口波特率**：建议115200及以上，高速采样时需要更高波特率
4. **中断优先级**：定时器中断优先级应低于DMA中断