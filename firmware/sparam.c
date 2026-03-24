#include "sparam.h"
#include "sparam_hal.h"
#include "sparam_port.h"
#include <string.h>

#define FRAME_HEADER_H      0xAA
#define FRAME_HEADER_L      0x55

#define CMD_HEARTBEAT       0x00
#define CMD_QUERY_INFO      0x01
#define CMD_READ_SINGLE     0x10
#define CMD_READ_PERIODIC   0x11
#define CMD_STOP_SAMPLING   0x1F
#define CMD_WRITE_SINGLE    0x20
#define CMD_WRITE_BATCH     0x21
#define CMD_ACK             0xA0
#define CMD_NACK            0xA1

#define TYPE_UINT8          0x01
#define TYPE_INT8           0x02
#define TYPE_UINT16         0x03
#define TYPE_INT16          0x04
#define TYPE_UINT32         0x05
#define TYPE_INT32          0x06
#define TYPE_FLOAT          0x07

#define ERR_INVALID_ADDR    0x01
#define ERR_INVALID_TYPE    0x02
#define ERR_TABLE_FULL      0x03
#define ERR_CRC             0x04

#define SAMPLE_RATE_MASK    0x0F
#define CMD_FUNC_MASK       0xF0

typedef struct {
    uint32_t addr;
    uint8_t type;
    uint8_t rate;
    uint16_t size;
    uint16_t counter;
} var_entry_t;

static var_entry_t var_table[SPARAM_VARS_MAX_SIZE];
static uint8_t var_count = 0;
static uint8_t device_id = 0;
static uint8_t tx_buf[SPARAM_TX_BUF_SIZE];

static const uint16_t crc16_table[256] = {
    0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
    0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
    0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
    0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
    0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
    0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
    0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
    0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
    0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
    0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
    0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
    0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
    0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
    0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
    0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
    0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
    0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
    0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
    0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
    0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
    0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
    0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
    0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
    0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
    0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
    0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
    0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
    0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
    0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
    0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
    0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
    0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040
};

static uint16_t crc16_modbus(const uint8_t *data, uint16_t len)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc = (crc >> 8) ^ crc16_table[(crc ^ data[i]) & 0xFF];
    }
    return crc;
}

static uint8_t get_type_size(uint8_t type)
{
    switch (type) {
        case TYPE_UINT8:
        case TYPE_INT8:
            return 1;
        case TYPE_UINT16:
        case TYPE_INT16:
            return 2;
        case TYPE_UINT32:
        case TYPE_INT32:
        case TYPE_FLOAT:
            return 4;
        default:
            return 0;
    }
}

static void send_frame(uint8_t cmd, const uint8_t *data, uint16_t data_len)
{
    uint16_t idx = 0;
    uint16_t payload_len = 1 + data_len + 2;
    
    tx_buf[idx++] = FRAME_HEADER_H;
    tx_buf[idx++] = FRAME_HEADER_L;
    tx_buf[idx++] = (uint8_t)payload_len;
    tx_buf[idx++] = device_id;
    tx_buf[idx++] = cmd;
    
    if (data_len > 0 && data != NULL) {
        memcpy(&tx_buf[idx], data, data_len);
        idx += data_len;
    }
    
    uint16_t crc = crc16_modbus(&tx_buf[3], idx - 3);
    tx_buf[idx++] = crc & 0xFF;
    tx_buf[idx++] = (crc >> 8) & 0xFF;
    
    sparam_uart_send(tx_buf, idx);
}

static void send_ack(void)
{
    send_frame(CMD_ACK, NULL, 0);
}

static void send_nack(uint8_t err_code)
{
    send_frame(CMD_NACK, &err_code, 1);
}

static void clear_var_table(void)
{
    var_count = 0;
    memset(var_table, 0, sizeof(var_table));
}

static uint8_t add_var_to_table(uint32_t addr, uint8_t type, uint8_t rate)
{
    if (var_count >= SPARAM_VARS_MAX_SIZE) {
        return ERR_TABLE_FULL;
    }
    
    uint8_t size = get_type_size(type);
    if (size == 0) {
        return ERR_INVALID_TYPE;
    }
    
    var_table[var_count].addr = addr;
    var_table[var_count].type = type;
    var_table[var_count].rate = rate;
    var_table[var_count].size = size;
    var_table[var_count].counter = 0;
    var_count++;
    
    return 0;
}

static void handle_read(uint8_t cmd, const uint8_t *data, uint16_t len)
{
    uint8_t rate = cmd & SAMPLE_RATE_MASK;
    
    if (rate == 0) {
        uint8_t resp_buf[SPARAM_TX_BUF_SIZE];
        uint16_t resp_idx = 0;
        uint16_t addr_count = len / 4;
        
        for (uint16_t i = 0; i < addr_count; i++) {
            uint32_t addr = data[i * 4] | (data[i * 4 + 1] << 8) |
                           (data[i * 4 + 2] << 16) | (data[i * 4 + 3] << 24);
            
            resp_buf[resp_idx++] = addr & 0xFF;
            resp_buf[resp_idx++] = (addr >> 8) & 0xFF;
            resp_buf[resp_idx++] = (addr >> 16) & 0xFF;
            resp_buf[resp_idx++] = (addr >> 24) & 0xFF;
            
            volatile uint8_t *ptr = (volatile uint8_t *)addr;
            for (uint8_t j = 0; j < 4; j++) {
                resp_buf[resp_idx++] = ptr[j];
            }
        }
        
        send_frame(cmd, resp_buf, resp_idx);
    } else {
        clear_var_table();
        
        uint16_t addr_count = len / 4;
        for (uint16_t i = 0; i < addr_count; i++) {
            uint32_t addr = data[i * 4] | (data[i * 4 + 1] << 8) |
                           (data[i * 4 + 2] << 16) | (data[i * 4 + 3] << 24);
            
            uint8_t err = add_var_to_table(addr, TYPE_UINT32, rate);
            if (err != 0) {
                send_nack(err);
                clear_var_table();
                return;
            }
        }
        
        send_ack();
    }
}

static void handle_write(const uint8_t *data, uint16_t len)
{
    if (len < 6) {
        send_nack(ERR_INVALID_ADDR);
        return;
    }
    
    uint8_t var_count_req = data[0];
    uint16_t idx = 1;
    
    for (uint8_t i = 0; i < var_count_req; i++) {
        if (idx + 5 > len) {
            send_nack(ERR_INVALID_ADDR);
            return;
        }
        
        uint32_t addr = data[idx] | (data[idx + 1] << 8) |
                       (data[idx + 2] << 16) | (data[idx + 3] << 24);
        idx += 4;
        
        uint8_t type = data[idx++];
        uint8_t size = get_type_size(type);
        
        if (size == 0) {
            send_nack(ERR_INVALID_TYPE);
            return;
        }
        
        if (idx + size > len) {
            send_nack(ERR_INVALID_ADDR);
            return;
        }
        
        volatile uint8_t *ptr = (volatile uint8_t *)addr;
        for (uint8_t j = 0; j < size; j++) {
            ptr[j] = data[idx + j];
        }
        idx += size;
    }
    
    send_ack();
}

static void process_frame(const uint8_t *data, uint16_t len)
{
    if (len < 5) {
        return;
    }
    
    uint8_t rx_len = data[2];
    uint8_t rx_dev_id = data[3];
    uint8_t cmd = data[4];
    
    if (rx_dev_id != device_id && rx_dev_id != 0xFF) {
        return;
    }
    
    uint16_t crc_calc = crc16_modbus(&data[3], rx_len);
    uint16_t crc_recv = data[3 + rx_len] | (data[3 + rx_len + 1] << 8);
    
    if (crc_calc != crc_recv) {
        send_nack(ERR_CRC);
        return;
    }
    
    const uint8_t *payload = &data[5];
    uint16_t payload_len = rx_len - 3;
    
    switch (cmd) {
        case CMD_HEARTBEAT:
            send_ack();
            break;
            
        case CMD_QUERY_INFO:
            {
                uint8_t info[] = {0x01, 0x06, 's', 'p', 'a', 'r', 'a', 'm'};
                send_frame(CMD_QUERY_INFO, info, sizeof(info));
            }
            break;
            
        case CMD_STOP_SAMPLING:
            clear_var_table();
            send_ack();
            break;
            
        case CMD_WRITE_SINGLE:
        case CMD_WRITE_BATCH:
            handle_write(payload, payload_len);
            break;
            
        default:
            if ((cmd & CMD_FUNC_MASK) == 0x10) {
                handle_read(cmd, payload, payload_len);
            } else {
                send_nack(ERR_INVALID_TYPE);
            }
            break;
    }
}

void sparam_init(uint8_t dev_id)
{
    device_id = dev_id;
    var_count = 0;
    memset(var_table, 0, sizeof(var_table));
    memset(tx_buf, 0, sizeof(tx_buf));
}

void sparam_on_rx_done(uint8_t *data, uint16_t len)
{
    if (data == NULL || len < 7) {
        return;
    }
    
    if (data[0] != FRAME_HEADER_H || data[1] != FRAME_HEADER_L) {
        return;
    }
    
    process_frame(data, len);
}

void sparam_on_timer_tick(void)
{
    if (var_count == 0) {
        return;
    }
    
    static uint16_t ms_counter = 0;
    ms_counter++;
    
    uint8_t resp_buf[SPARAM_TX_BUF_SIZE];
    uint16_t resp_idx = 0;
    uint8_t has_data = 0;
    
    for (uint8_t i = 0; i < var_count; i++) {
        var_table[i].counter++;
        
        uint16_t interval_ms = 1;
        switch (var_table[i].rate) {
            case 1: interval_ms = 1; break;
            case 2: interval_ms = 5; break;
            case 3: interval_ms = 10; break;
            case 4: interval_ms = 20; break;
            case 5: interval_ms = 50; break;
            case 6: interval_ms = 100; break;
            case 7: interval_ms = 200; break;
            case 8: interval_ms = 500; break;
            default: continue;
        }
        
        if (var_table[i].counter >= interval_ms) {
            var_table[i].counter = 0;
            has_data = 1;
            
            uint32_t addr = var_table[i].addr;
            resp_buf[resp_idx++] = addr & 0xFF;
            resp_buf[resp_idx++] = (addr >> 8) & 0xFF;
            resp_buf[resp_idx++] = (addr >> 16) & 0xFF;
            resp_buf[resp_idx++] = (addr >> 24) & 0xFF;
            
            volatile uint8_t *ptr = (volatile uint8_t *)addr;
            for (uint8_t j = 0; j < var_table[i].size; j++) {
                resp_buf[resp_idx++] = ptr[j];
            }
        }
    }
    
    if (has_data && resp_idx > 0) {
        send_frame(CMD_READ_PERIODIC, resp_buf, resp_idx);
    }
}