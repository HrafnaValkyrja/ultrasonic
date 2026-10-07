/* fw/port_u575/startup.c: vector table and reset for the STM32U575 (Cortex-M33). Register code lives only in fw/port_u575. */
#include <stdint.h>
#include <string.h>

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;
int main(void);
void Reset_Handler(void);
void Default_Handler(void);

void Default_Handler(void)
{
    for (;;) {
    }
}

#define WEAK_DEFAULT __attribute__((weak, alias("Default_Handler")))
void NMI_Handler(void) WEAK_DEFAULT;
void HardFault_Handler(void) WEAK_DEFAULT;
void MemManage_Handler(void) WEAK_DEFAULT;
void BusFault_Handler(void) WEAK_DEFAULT;
void UsageFault_Handler(void) WEAK_DEFAULT;
void SecureFault_Handler(void) WEAK_DEFAULT;
void SVC_Handler(void) WEAK_DEFAULT;
void DebugMon_Handler(void) WEAK_DEFAULT;
void PendSV_Handler(void) WEAK_DEFAULT;
void SysTick_Handler(void) WEAK_DEFAULT;
void OTG_FS_IRQHandler(void) WEAK_DEFAULT;   /* IRQ 73, vector 0x164 (RM0456 Rev 7 NVIC table) */

#define U575_IRQ_COUNT 125u   /* STM32U575 external interrupts (RM0456 Rev 7 NVIC table; unverified count, foundation) */
typedef void (*vec_t)(void);
__attribute__((section(".isr_vector"), used)) const vec_t vector_table[16u + U575_IRQ_COUNT] = {
    (vec_t)(uintptr_t)&_estack, Reset_Handler, NMI_Handler, HardFault_Handler, MemManage_Handler, BusFault_Handler,
    UsageFault_Handler, SecureFault_Handler, 0, 0, 0, SVC_Handler, DebugMon_Handler, 0, PendSV_Handler, SysTick_Handler,
    [16 ... 16u + 72u] = Default_Handler,
    [16u + 73u] = OTG_FS_IRQHandler,
    [16u + 74u ... 16u + U575_IRQ_COUNT - 1u] = Default_Handler,
};

#define SCB_CPACR (*(volatile uint32_t *)0xE000ED88u)

/* FWSIM-R21 DFU entry: hal_usb_dfu_request left FW_DFU_MAGIC in TAMP_BKP0R and reset. Checked first, with only PWR/RTC-APB clocks
 * turned on; the flag is cleared before the jump so the loader's own reset returns to the application. */
static void dfu_check(void)
{
    volatile uint32_t *const ahb3 = (volatile uint32_t *)0x46020C94u, *const apb3 = (volatile uint32_t *)0x46020CA8u;
    volatile uint32_t *const dbpr = (volatile uint32_t *)0x46020828u, *const bkp0 = (volatile uint32_t *)0x46007D00u;
    *ahb3 |= 1u << 2;                                          /* PWREN */
    *apb3 |= 1u << 21;                                         /* RTCAPBEN */
    __asm volatile("dsb" ::: "memory");
    if (*bkp0 != 0xDF00B007u)
        return;
    *dbpr |= 1u;
    *bkp0 = 0u;
    *dbpr &= ~1u;
    const volatile uint32_t *rom = (const volatile uint32_t *)0x0BF90000u;
    uint32_t sp = rom[0], pc = rom[1];
    __asm volatile("msr msp, %0\n bx %1" ::"r"(sp), "r"(pc) : "memory");
}

void Reset_Handler(void)
{
    dfu_check();
    SCB_CPACR |= 0xFu << 20;                                  /* CP10/CP11 full access: FPU on */
    __asm volatile("dsb\n isb" ::: "memory");
    uint32_t fpscr;
    __asm volatile("vmrs %0, fpscr" : "=r"(fpscr));
    fpscr |= 1u << 24;                                        /* FPSCR.FZ: flush-to-zero (determinism rules) */
    __asm volatile("vmsr fpscr, %0" ::"r"(fpscr));
    memcpy(&_sdata, &_sidata, (size_t)((uintptr_t)&_edata - (uintptr_t)&_sdata));
    memset(&_sbss, 0, (size_t)((uintptr_t)&_ebss - (uintptr_t)&_sbss));
    (void)main();
    for (;;) {
    }
}
