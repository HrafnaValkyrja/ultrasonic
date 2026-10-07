/* fw/hal/hal_gpio.h: pins by board_pin_t (fw/gen/board_config.h, generated from docs/system/pin-contract.yaml; FWSIM-R5). */
#ifndef FW_HAL_GPIO_H
#define FW_HAL_GPIO_H
#include "hal_types.h"
#include "board_config.h"

typedef enum {
    HAL_GPIO_ANALOG = 0,   /* analog, no pull: the parked state (FWSIM-R23) */
    HAL_GPIO_INPUT,
    HAL_GPIO_INPUT_PU,
    HAL_GPIO_INPUT_PD,
    HAL_GPIO_OUTPUT_PP,
    HAL_GPIO_OUTPUT_OD,
    HAL_GPIO_AF,           /* alternate function BOARD_<id>_AF */
    HAL_GPIO_MODE_COUNT
} hal_gpio_mode_t;

hal_status_t hal_gpio_mode(board_pin_t pin, hal_gpio_mode_t mode);
void hal_gpio_write(board_pin_t pin, bool high);
bool hal_gpio_read(board_pin_t pin);
#endif
