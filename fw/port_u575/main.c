/* fw/port_u575/main.c: target entry. Everything above the HAL is the portable core (fw/core/app.c). */
#include "app.h"

static fw_app_t app;

int main(void)
{
    fw_app_boot(&app);
    for (;;) {
        fw_app_step(&app);
        __asm volatile("wfi");
    }
}
