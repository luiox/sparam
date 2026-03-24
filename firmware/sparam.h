#ifndef SPARAM_H
#define SPARAM_H

#include <stdint.h>

void sparam_init(uint8_t device_id);
void sparam_on_rx_done(uint8_t *data, uint16_t len);
void sparam_on_timer_tick(void);

#endif