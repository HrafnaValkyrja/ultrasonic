/* fw/hal/hal_adf.h: ADF1 hop source (PDM mic -> 200.02 kS/s 24-bit words; A3 s1.1-1.2; FWSIM-R24, R34).
 * The DMA half/complete ISR fills a hop and pushes its index into the core ring (ISRs only move data and set flags, FWSIM-R3). */
#ifndef FW_HAL_ADF_H
#define FW_HAL_ADF_H
#include "hal_types.h"

#define HAL_ADF_FLAG_SATF   (1u << 0)   /* saturation */
#define HAL_ADF_FLAG_CKABF  (1u << 1)   /* clock absence */
#define HAL_ADF_FLAG_DOVRF  (1u << 2)   /* data overflow */
#define HAL_ADF_FLAG_RFOVRF (1u << 3)   /* reshape filter overrun */

hal_status_t hal_adf_start(uint32_t cck_hz);         /* CKGDEN handshake, even CCKDIV+1 (A3 s1.1) */
void hal_adf_stop(void);
const int32_t *hal_adf_hop_take(void);                /* next complete hop of 128 words, NULL if none ready */
void hal_adf_hop_release(void);                       /* return the hop buffer taken last */
uint32_t hal_adf_flags(void);                         /* HAL_ADF_FLAG_* since the last call (read-and-clear) */
#endif
