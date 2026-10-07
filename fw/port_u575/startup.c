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

#define U575_IRQ_COUNT 125u   /* STM32U575 external interrupts (RM0456 Rev 7 NVIC table; unverified count, foundation) */
typedef void (*vec_t)(void);
__attribute__((section(".isr_vector"), used)) const vec_t vector_table[16u + U575_IRQ_COUNT] = {
    (vec_t)(uintptr_t)&_estack, Reset_Handler, NMI_Handler, HardFault_Handler, MemManage_Handler, BusFault_Handler,
    UsageFault_Handler, SecureFault_Handler, 0, 0, 0, SVC_Handler, DebugMon_Handler, 0, PendSV_Handler, SysTick_Handler,
    [16 ... 16u + U575_IRQ_COUNT - 1u] = Default_Handler,
};

#define SCB_CPACR (*(volatile uint32_t *)0xE000ED88u)

void Reset_Handler(void)
{
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
