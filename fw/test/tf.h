/* fw/test/tf.h: minimal test framework (no third-party code: Unity is not vendored yet). */
#ifndef FW_TEST_TF_H
#define FW_TEST_TF_H
#include <stdint.h>
#include <stdio.h>

extern uint32_t tf_checks, tf_fails;
extern const char *tf_current;

#define TF_CHECK(cond) do { tf_checks++; if (!(cond)) { tf_fails++; \
    fprintf(stderr, "FAIL %s %s:%d: %s\n", tf_current, __FILE__, __LINE__, #cond); } } while (0)
#define TF_CHECK_EQ(a, b) do { long long tf_a_ = (long long)(a), tf_b_ = (long long)(b); tf_checks++; if (tf_a_ != tf_b_) { tf_fails++; \
    fprintf(stderr, "FAIL %s %s:%d: %s == %s (%lld vs %lld)\n", tf_current, __FILE__, __LINE__, #a, #b, tf_a_, tf_b_); } } while (0)

typedef struct { const char *name; const char *req; void (*fn)(void); } tf_test_t;
#endif
