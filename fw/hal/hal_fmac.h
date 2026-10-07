/* fw/hal/hal_fmac.h: FMAC math accelerator (RM0456 s26). A PURE function of its arguments (coefficients, history and inputs are passed
 * every call; the target driver may cache coefficients by pointer): the one HAL family core entry points may call (FWSIM-R3 exemption,
 * test_abi_pure). Host fake, QEMU port and (until the register driver lands, E4) the U575 port all run fw/core/fmac_model.c, so
 * every test tier sees the FMAC's arithmetic. Errors (fault injection, busy peripheral) make the core fall back to its CPU path. */
#ifndef FW_HAL_FMAC_H
#define FW_HAL_FMAC_H
#include "hal_types.h"

/* n_phase FIRs of `taps` q1.15 taps over x (taps-1 history + n_new new, oldest first), gain 2^r_gain, saturated q1.15 outputs
 * y[s * n_phase + p]. Limits: taps <= 127, n_phase * taps + taps - 1 + n_new + 1 <= 256 (local memory) for one-shot use */
hal_status_t hal_fmac_fir_bank(const int16_t *coef, uint32_t n_phase, uint32_t taps, uint32_t r_gain, const int16_t *x, uint32_t n_new, int16_t *y);
#endif
