/* fw/tools/cycdrv.c: host driver for fw/tools/cycles.py (line execution counts by gcov). Runs fw_hop over a raw int32 word file.
 * usage: cycdrv words.i32 d2(0|1) knob=value ... ; not firmware, not part of the test binary. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "fw.h"

int main(int argc, char **argv)
{
    if (argc < 3)
        return 2;
    FILE *f = fopen(argv[1], "rb");
    if (!f)
        return 2;
    static int32_t w[1u << 22];
    size_t n = fread(w, sizeof w[0], sizeof w / sizeof w[0], f);
    fclose(f);
    int d2 = atoi(argv[2]);
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    for (int i = 3; i < argc; i++) {
        char *eq = strchr(argv[i], '=');
        if (!eq)
            return 2;
        *eq = '\0';
        for (uint32_t j = 0; j < (uint32_t)FW_KNOB_COUNT; j++)
            if (strcmp(fw_knob_meta[j].name, argv[i]) == 0 && fw_knob_set(&k, j, atoi(eq + 1)) != FW_KNOB_OK)
                return 3;
    }
    static fw_state_t st;
    static fw_taps_t t;
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    fw_init(&st, &k, 0u);
    size_t per = d2 ? 256u : 128u, hops = n / per;
    for (size_t h = 0; h < hops; h++) {
        fw_poll(&st, (uint64_t)h * 640u);
        if ((d2 ? fw_hop_d2(&st, &w[h * per], ccr, FW_CCR_MAX_PER_HOP, &t) : fw_hop(&st, &w[h * per], ccr, FW_CCR_MAX_PER_HOP, &t)) == 0u)
            return 4;
    }
    printf("%zu\n", hops);
    return 0;
}
