/* fw/port_qemu/startup.c: minimal Cortex-M33 start for QEMU mps2-an505 (L0 test only): FPU on, FPSCR.FZ = 1 (determinism rules,
 * as fw/port_u575 Reset_Handler), .bss zeroed, main(). */
#include <stdint.h>

extern uint32_t _sbss, _ebss, _estack;
int main(void);

void Reset_Handler(void)
{
    *(volatile uint32_t *)0xE000ED88u |= 0xFu << 20;              /* CPACR: CP10/CP11 full access */
    __asm__ volatile("dsb\n isb");
    uint32_t fpscr;
    __asm__ volatile("vmrs %0, fpscr" : "=r"(fpscr));
    fpscr |= 1u << 24;                                              /* FZ: flush-to-zero */
    __asm__ volatile("vmsr fpscr, %0" ::"r"(fpscr));
    for (uint32_t *p = &_sbss; p < &_ebss; p++)
        *p = 0u;
    (void)main();
    for (;;) {}
}

static void Default_Handler(void)
{
    for (;;) {}
}

__attribute__((section(".isr_vector"), used)) static void (*const vectors[16])(void) = {
    (void (*)(void))(&_estack), Reset_Handler, Default_Handler, Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    0, 0, 0, 0, Default_Handler, Default_Handler, 0, Default_Handler, Default_Handler};
