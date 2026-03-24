#include "sparam_hal.h"
#include "sparam_port.h"
#include "stm32f1xx_hal.h"

extern UART_HandleTypeDef huart1;

static uint8_t tx_dma_buf[SPARAM_TX_BUF_SIZE];
static volatile uint8_t tx_busy = 0;

void sparam_uart_send(uint8_t *data, uint16_t len)
{
    if (tx_busy) {
        return;
    }
    
    if (len > SPARAM_TX_BUF_SIZE) {
        len = SPARAM_TX_BUF_SIZE;
    }
    
    memcpy(tx_dma_buf, data, len);
    tx_busy = 1;
    HAL_UART_Transmit_DMA(&huart1, tx_dma_buf, len);
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart1) {
        tx_busy = 0;
    }
}