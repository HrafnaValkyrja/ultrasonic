/* fw/port_qemu/an505.ld: QEMU mps2-an505 (Cortex-M33, Arm AN505 FPGA image) for the ARM L0 test only (FWSIM-R7), not the product.
 * Secure aliases (QEMU hw/arm/mps2-tz.c, AN505): SSRAM1 code 0x10000000 (initial VTOR_S), SSRAM2/3 data 0x38000000 (4 MB). */
ENTRY(Reset_Handler)
MEMORY
{
    CODE (rx)  : ORIGIN = 0x10000000, LENGTH = 4M
    DATA (rwx) : ORIGIN = 0x38000000, LENGTH = 4M
}
_stack_size = 16K;
_estack = ORIGIN(DATA) + LENGTH(DATA);
SECTIONS
{
    .isr_vector : { KEEP(*(.isr_vector)) } > CODE
    .text : { *(.text*) *(.rodata*) . = ALIGN(4); } > CODE
    .ARM.exidx : { *(.ARM.exidx*) } > CODE
    .data : { *(.data*) . = ALIGN(4); } > DATA      /* QEMU -kernel loads the ELF segments in place: no copy needed */
    .bss (NOLOAD) : { _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; } > DATA
}
