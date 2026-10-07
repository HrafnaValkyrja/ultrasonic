#ifndef FW_TEST_PORT_REGFAKE_H
#define FW_TEST_PORT_REGFAKE_H
#include <stdint.h>
typedef struct { uint32_t addr, val; } rf_write_t;   /* val = register value after the write */
void rf_reset(void);
void rf_poke(uint32_t a, uint32_t v);
uint32_t rf_nlog(void);
const rf_write_t *rf_log(uint32_t i);
int32_t rf_find(uint32_t a, uint32_t from);
uint8_t *rf_i2c_regs(void);
void rf_i2c_hold(uint32_t on);
void rf_adc_code(uint32_t ch, uint16_t code);
void rf_sda_stuck(uint32_t clocks);
void rf_adc4_code(uint32_t ch, uint16_t code);
uint32_t rf_resets(void);
void rf_wake(uint32_t which);   /* 1 button (WUF1), 2 CHG_INT (EXTI15 falling), 3 VBUS (EXTI1 rising), 4 RTC (WUTF) */
#endif
