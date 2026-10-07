/* fw/core/ring.h: single-producer (ISR) / single-consumer (main loop) index ring: the only ISR -> core channel (FWSIM-R3).
 * Capacity FW_RING_CAP - 1. Single core: volatile head/tail + the ISR being the only writer of head is sufficient. */
#ifndef FW_CORE_RING_H
#define FW_CORE_RING_H
#include <stdbool.h>
#include <stdint.h>

#define FW_RING_CAP 8u
typedef struct {
    volatile uint32_t head;   /* written by the producer only */
    volatile uint32_t tail;   /* written by the consumer only */
    volatile uint32_t dropped;
    uint8_t idx[FW_RING_CAP];
} fw_ring_t;

static inline bool fw_ring_push(fw_ring_t *r, uint8_t v)
{
    uint32_t h = r->head, n = (h + 1u) % FW_RING_CAP;
    if (n == r->tail) {
        r->dropped = r->dropped + 1u;
        return false;
    }
    r->idx[h] = v;
    r->head = n;
    return true;
}

static inline bool fw_ring_pop(fw_ring_t *r, uint8_t *v)
{
    uint32_t t = r->tail;
    if (t == r->head)
        return false;
    *v = r->idx[t];
    r->tail = (t + 1u) % FW_RING_CAP;
    return true;
}
#endif
