/* fw/port_u575/boot/stub.c: the boot stub image (flash page 0, stub.ld). Runs on the reset clock (MSIS 4 MHz), touches only PWR/RTC-APB
 * (TAMP flag) and GPIOA (button PA0, VBUS_SENSE PA1), returns them to their reset state, then jumps to the app or the ROM loader.
 * The jump happens straight after a reset, so IWDG is not running and no peripheral is configured (FWSIM-R21). */
#include "boot.h"

#define R(a) (*(volatile uint32_t *)(a))
#define RCC_AHB2ENR1 0x46020C8Cu
#define RCC_AHB3ENR 0x46020C94u
#define RCC_APB3ENR 0x46020CA8u
#define PWR_DBPR 0x46020828u
#define TAMP_BKP0R 0x46007D00u
#define GPIOA 0x42020000u
#define SCB_VTOR 0xE000ED08u
#define ROM_LOADER 0x0BF90000u

extern uint32_t _stub_estack;
void stub_reset(void);
void stub_fault(void);
void stub_fault(void)
{
    for (;;) {                                               /* a fault in the stub: hang; IWDG is off, SWD or BOOT0 recovers */
    }
}
__attribute__((section(".stub_vectors"), used)) const uintptr_t stub_vectors[16] = {
    (uintptr_t)&_stub_estack, (uintptr_t)stub_reset, [2 ... 15] = (uintptr_t)stub_fault};

static void jump(uint32_t base)
{
    const volatile uint32_t *v = (const volatile uint32_t *)base;
    R(SCB_VTOR) = base;
    __asm volatile("dsb\n isb\n msr msp, %0\n bx %1" ::"r"(v[0]), "r"(v[1]) : "memory");
}

void stub_reset(void)
{
    R(RCC_AHB3ENR) |= 1u << 2;                               /* PWREN */
    R(RCC_APB3ENR) |= 1u << 21;                              /* RTCAPBEN: TAMP */
    R(RCC_AHB2ENR1) |= 1u;                                   /* GPIOAEN */
    __asm volatile("dsb" ::: "memory");
    uint32_t flag = R(TAMP_BKP0R);
    if (flag == BOOT_DFU_MAGIC) {
        R(PWR_DBPR) |= 1u;
        R(TAMP_BKP0R) = 0u;                                  /* one-shot: the loader's own reset returns to the app */
        R(PWR_DBPR) &= ~1u;
    }
    /* PA0 BTN (active high) with pull-down, PA1 VBUS_SENSE plain input; button must read high on 32 samples over ~30 ms */
    R(GPIOA + 0x00u) &= ~0xFu;                               /* MODER0/1 = input */
    R(GPIOA + 0x0Cu) = (R(GPIOA + 0x0Cu) & ~0xFu) | 2u;      /* PUPDR0 = pull-down */
    uint32_t held = 1u;
    for (uint32_t i = 0; i < 32u; i++) {
        for (volatile uint32_t d = 0; d < 1000u; d++) {
        }
        held &= R(GPIOA + 0x10u) & 1u;
    }
    bool vbus = (R(GPIOA + 0x10u) >> 1) & 1u;
    R(GPIOA + 0x0Cu) &= ~0xFu;                               /* back to reset state: no pull, analog */
    R(GPIOA + 0x00u) |= 0xFu;
    R(RCC_AHB2ENR1) &= ~1u;
    boot_action_t a = boot_decide(flag, held != 0u, vbus, (const uint8_t *)BOOT_APP_BASE, BOOT_APP_MAX);
    jump(a == BOOT_APP ? BOOT_APP_BASE : ROM_LOADER);
    for (;;) {
    }
}
