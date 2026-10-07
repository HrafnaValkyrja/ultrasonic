/* fw/test/port/regfake.c: recorded-register fake for the U575 port register layer (FW_REG_RECORD). Sparse register file with RM0456 reset
 * values where they matter (GPIO MODER), a write log, and the rc_w0 semantics of TIMx_SR. */
#include <stdint.h>
#include <string.h>

#include "regfake.h"
#include "reg.h"

static uint32_t addr_[512], val_[512], n_;
static rf_write_t log_[4096];
static uint32_t nlog_;

static uint32_t reset_value(uint32_t a)
{
    if (a >= 0x42020000u && a < 0x42022400u && (a & 0x3FFu) == GPIO_MODER) {
        uint32_t port = (a - 0x42020000u) / 0x400u;
        return port == 0u ? 0xABFFFFFFu : (port == 1u ? 0xFFFFFEBFu : 0xFFFFFFFFu);   /* RM0456 GPIOx_MODER reset values */
    }
    return 0u;
}

static uint32_t *slot(uint32_t a)
{
    for (uint32_t i = 0; i < n_; i++)
        if (addr_[i] == a)
            return &val_[i];
    if (n_ >= 512u)
        return NULL;
    addr_[n_] = a;
    val_[n_] = reset_value(a);
    return &val_[n_++];
}

void rf_reset(void)
{
    n_ = 0u;
    nlog_ = 0u;
}

void reg_write(uint32_t a, uint32_t v)
{
    uint32_t *s = slot(a);
    if (s == NULL)
        return;
    if (a == TIM1_BASE + TIM_SR)
        *s &= v;                                       /* rc_w0 */
    else
        *s = v;
    if (nlog_ < 4096u) {
        log_[nlog_].addr = a;
        log_[nlog_].val = *s;
        nlog_++;
    }
}

uint32_t reg_read(uint32_t a)
{
    uint32_t *s = slot(a);
    return s ? *s : 0u;
}

void rf_poke(uint32_t a, uint32_t v)                   /* hardware-side change (no log) */
{
    uint32_t *s = slot(a);
    if (s)
        *s = v;
}

uint32_t rf_nlog(void) { return nlog_; }
const rf_write_t *rf_log(uint32_t i) { return &log_[i]; }
int32_t rf_find(uint32_t a, uint32_t from)
{
    for (uint32_t i = from; i < nlog_; i++)
        if (log_[i].addr == a)
            return (int32_t)i;
    return -1;
}
