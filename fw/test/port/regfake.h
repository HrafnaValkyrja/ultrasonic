#ifndef FW_TEST_PORT_REGFAKE_H
#define FW_TEST_PORT_REGFAKE_H
#include <stdint.h>
typedef struct { uint32_t addr, val; } rf_write_t;   /* val = register value after the write */
void rf_reset(void);
void rf_poke(uint32_t a, uint32_t v);
uint32_t rf_nlog(void);
const rf_write_t *rf_log(uint32_t i);
int32_t rf_find(uint32_t a, uint32_t from);
#endif
