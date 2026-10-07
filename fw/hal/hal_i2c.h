/* fw/hal/hal_i2c.h: I2C2 master to the BQ25180 charger (0x6A; FWSIM-R20, R27). */
#ifndef FW_HAL_I2C_H
#define FW_HAL_I2C_H
#include "hal_types.h"

hal_status_t hal_i2c_write(uint8_t addr7, uint8_t reg, const uint8_t *buf, size_t len);
hal_status_t hal_i2c_read(uint8_t addr7, uint8_t reg, uint8_t *buf, size_t len);
hal_status_t hal_i2c_recover(void);                  /* 9 SCL clocks + STOP */
#endif
