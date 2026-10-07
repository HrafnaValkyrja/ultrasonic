/* fw/port_qemu/hal_fmac_qemu.c: QEMU has no FMAC model, so the L0 image runs the bit-accurate model (fw/core/fmac_model.c), exactly as
 * the host fake does. In L0_COUNT builds the SysTick ticks spent inside it are accumulated, so qemu_icount.py can report the CPU's own
 * instructions (on the U575 the FMAC does this work in parallel). */
#include "fmac_model.h"
#include "hal_fmac.h"

#if defined(L0_COUNT)
uint32_t l0_fmac_ticks;
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#endif

hal_status_t hal_fmac_fir_bank(const int16_t *coef, uint32_t n_phase, uint32_t taps, uint32_t r_gain, const int16_t *x, uint32_t n_new, int16_t *y)
{
    if (coef == 0 || x == 0 || y == 0 || taps == 0u || taps > 127u || r_gain > 7u)
        return HAL_EINVAL;
#if defined(L0_COUNT)
    uint32_t a = SYST_CVR;
#endif
    fw_fmac_model_bank(coef, n_phase, taps, r_gain, x, n_new, y);
#if defined(L0_COUNT)
    l0_fmac_ticks += (a - SYST_CVR) & 0xFFFFFFu;
#endif
    return HAL_OK;
}
