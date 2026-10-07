/* fw/hal/hal_types.h: shared HAL types (FWSIM-R1/R2). Interface headers only: implemented by fw/port_u575 (registers) and
 * fw/port_host (stateful fakes). Core code includes fw/hal/hal_*.h and never a CMSIS/ST header (fw/tools/lint.py). */
#ifndef FW_HAL_TYPES_H
#define FW_HAL_TYPES_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    HAL_OK = 0,
    HAL_ERR = 1,       /* generic failure (fake fault injection default) */
    HAL_TIMEOUT = 2,
    HAL_NACK = 3,      /* I2C address/data not acknowledged */
    HAL_BUSY = 4,
    HAL_EINVAL = 5,    /* argument outside the contract */
    HAL_ECC = 6,       /* flash ECC double error on read */
    HAL_ENOTIMPL = 7   /* port function not written yet (port_u575 foundation stubs) */
} hal_status_t;

#endif
