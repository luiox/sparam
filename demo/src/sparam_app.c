#include "sparam_app.h"

#include <string.h>

#include "main.h"
#include "sparam.h"
#include "sparam_hal.h"
#include "sparam_port.h"
#include "tim.h"
#include "usart.h"

static uint8_t s_rx_byte = 0;
static uint8_t s_tx_dma_buf[SPARAM_TX_BUF_SIZE];
static volatile uint8_t s_tx_busy = 0;

static void sparam_start_rx_it(void)
{
    if (HAL_UART_Receive_IT(&huart1, &s_rx_byte, 1) != HAL_OK) {
        Error_Handler();
    }
}

void sparam_app_init(void)
{
    s_rx_byte = 0;
    memset(s_tx_dma_buf, 0, sizeof(s_tx_dma_buf));

    sparam_init(SPARAM_DEVICE_ID);

    sparam_start_rx_it();

    if (HAL_TIM_Base_Start_IT(&htim2) != HAL_OK) {
        Error_Handler();
    }
}

int32_t g_step = 1;
int32_t g_counter = 0;
int32_t g_delay_ms = 1000;

void sparam_app_process(void)
{
    while(1) {
        g_counter += g_step;
        HAL_Delay(g_delay_ms);
    }
}

void sparam_uart_send(uint8_t *data, uint16_t len)
{
    if (s_tx_busy) {
        return;
    }

    if (len > SPARAM_TX_BUF_SIZE) {
        len = SPARAM_TX_BUF_SIZE;
    }

    memcpy(s_tx_dma_buf, data, len);
    s_tx_busy = 1;
    if (HAL_UART_Transmit_DMA(&huart1, s_tx_dma_buf, len) != HAL_OK) {
        s_tx_busy = 0;
    }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart1) {
        s_tx_busy = 0;
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart1) {
        sparam_on_rx_done(&s_rx_byte, 1);
        sparam_start_rx_it();
    }
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim == &htim2) {
        sparam_on_timer_tick();
    }
}
