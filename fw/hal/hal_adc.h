/* fw/hal/hal_adc.h: ADC1/ADC4 conversions with VREFINT back-calculation (FWSIM-R26). */
#ifndef FW_HAL_ADC_H
#define FW_HAL_ADC_H
#include "hal_types.h"

typedef enum { HAL_ADC_I_SENSE = 0, HAL_ADC_VBAT_SENSE, HAL_ADC_VBUS_SENSE, HAL_ADC_TS, HAL_ADC_VREFINT, HAL_ADC_CH_COUNT } hal_adc_ch_t;

hal_status_t hal_adc_read_mv(hal_adc_ch_t ch, uint16_t *mv);   /* pin voltage in mV (VDDA-corrected) */
#endif
