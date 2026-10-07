/* fw/core/fmac_model.h: bit-accurate model of the STM32U575 FMAC FIR datapath (RM0456 Rev 7 s26.3.6-26.3.7): q1.15 operands, 16x16
 * products entering a 26-bit q4.22 accumulator that wraps, output gain 2^R, CLIPEN saturation to q1.15. Two behaviours the RM does
 * not describe are modelled as floor and pinned by a bench read-back on a real U575 (backlog FMAC-RM-UNKNOWNS):
 *   A1 product q2.30 -> q4.22: arithmetic shift right by 8 (floor);   A2 accumulator -> q1.15 output: shift right by 7 after the gain (floor).
 * Pure C (core-legal). The ports' hal_fmac_fir_bank() run this on host and QEMU so tests use the target's arithmetic; the Python twin
 * sim/fw/fmac_model.py must agree bit for bit (fwsim row dsp.fmac_model_c_vs_py). */
#ifndef FW_CORE_FMAC_MODEL_H
#define FW_CORE_FMAC_MODEL_H
#include <stdint.h>

int32_t fw_fmac_mac_floor8(int32_t prod);   /* A1 */
/* one FIR output: sum_k coef[k] x[newest - k], k < taps; x points at the newest sample */
int16_t fw_fmac_model_fir1(const int16_t *coef, uint32_t taps, uint32_t r_gain, const int16_t *x_newest);
/* polyphase bank: n_phase FIRs of `taps` taps (coef[p * taps + k]) over x[0 .. taps-2+n_new] (oldest first: taps-1 history, then n_new
 * new samples); y[s * n_phase + p] = phase p output for new sample s (interleaved: the x16 interpolator's natural order) */
void fw_fmac_model_bank(const int16_t *coef, uint32_t n_phase, uint32_t taps, uint32_t r_gain, const int16_t *x, uint32_t n_new, int16_t *y);
#endif
