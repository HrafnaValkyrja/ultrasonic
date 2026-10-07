/* fw/test/test_main.c: host test runner. Prints one JSON line per test (fwsim parses it). FTZ|DAZ on, as on the MCU
 * (FPSCR.FZ, determinism rules). Exit 1 on any failure. */
#include <stdio.h>
#include <string.h>
#if defined(__SSE__)
#include <xmmintrin.h>
#endif

#include "fake.h"
#include "tf.h"
#include "tests.h"

uint32_t tf_checks, tf_fails;
const char *tf_current = "";

#define FW_TEST_ROW(fn, req) {#fn, req, fn},
static const tf_test_t tests[] = {FW_TESTS(FW_TEST_ROW)};
#undef FW_TEST_ROW

int main(int argc, char **argv)
{
#if defined(__SSE__)
    _mm_setcsr(_mm_getcsr() | 0x8040u);   /* FTZ (bit 15) | DAZ (bit 6) */
#endif
    uint32_t failed = 0;
    for (size_t i = 0; i < sizeof tests / sizeof tests[0]; i++) {
        if (argc > 1 && strcmp(argv[1], tests[i].name) != 0)
            continue;
        uint32_t c0 = tf_checks, f0 = tf_fails;
        tf_current = tests[i].name;
        fake_reset();
        tests[i].fn();
        uint32_t nf = tf_fails - f0;
        failed += nf != 0u;
        printf("{\"test\": \"%s\", \"req\": \"%s\", \"checks\": %u, \"fails\": %u}\n", tests[i].name, tests[i].req, tf_checks - c0, nf);
    }
    printf("{\"total_checks\": %u, \"total_fails\": %u, \"tests_failed\": %u}\n", tf_checks, tf_fails, failed);
    return failed ? 1 : 0;
}
