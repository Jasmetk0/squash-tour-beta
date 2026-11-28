/* Measured proposal only (#1917): cost of CPython's MT19937 seeding of a
   128-bit key, as CPython does it, versus the same output with the constant
   init_genrand(19650218) prefix precomputed and copied. Same state is asserted. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#define N 624
#define M 397
static void init_genrand(uint32_t *mt, uint32_t s) {
    mt[0] = s;
    for (int i = 1; i < N; i++) mt[i] = (1812433253U * (mt[i-1] ^ (mt[i-1] >> 30)) + i);
}
static void mix(uint32_t *mt, const uint32_t *key, size_t klen) {
    size_t i = 1, j = 0, k = (N > klen ? N : klen);
    for (; k; k--) {
        mt[i] = (mt[i] ^ ((mt[i-1] ^ (mt[i-1] >> 30)) * 1664525U)) + key[j] + (uint32_t)j;
        i++; j++; if (i >= N) { mt[0] = mt[N-1]; i = 1; } if (j >= klen) j = 0;
    }
    for (k = N-1; k; k--) {
        mt[i] = (mt[i] ^ ((mt[i-1] ^ (mt[i-1] >> 30)) * 1566083941U)) - (uint32_t)i;
        i++; if (i >= N) { mt[0] = mt[N-1]; i = 1; }
    }
    mt[0] = 0x80000000U;
}
static void twist(uint32_t *mt) {
    static const uint32_t mag01[2] = {0x0U, 0x9908b0dfU};
    uint32_t y; int kk;
    for (kk = 0; kk < N-M; kk++) { y = (mt[kk]&0x80000000U)|(mt[kk+1]&0x7fffffffU); mt[kk] = mt[kk+M] ^ (y >> 1) ^ mag01[y & 1]; }
    for (; kk < N-1; kk++) { y = (mt[kk]&0x80000000U)|(mt[kk+1]&0x7fffffffU); mt[kk] = mt[kk+(M-N)] ^ (y >> 1) ^ mag01[y & 1]; }
    y = (mt[N-1]&0x80000000U)|(mt[0]&0x7fffffffU); mt[N-1] = mt[M-1] ^ (y >> 1) ^ mag01[y & 1];
}
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
int main(void) {
    uint32_t base[N], a[N], b[N], key[4] = {0x89abcdefU, 0x01234567U, 0xdeadbeefU, 0x80000000U};
    init_genrand(base, 19650218U);
    const int R = 400000; volatile uint32_t sink = 0; double t0, t1, t2, t3;
    t0 = now();
    for (int r = 0; r < R; r++) { key[0] = r; init_genrand(a, 19650218U); mix(a, key, 4); twist(a); sink ^= a[1]; }
    t1 = now();
    for (int r = 0; r < R; r++) { key[0] = r; memcpy(b, base, sizeof b); mix(b, key, 4); twist(b); sink ^= b[1]; }
    t2 = now();
    for (int r = 0; r < R; r++) { key[0] = r; memcpy(b, base, sizeof b); mix(b, key, 4); sink ^= b[1]; }
    t3 = now();
    key[0] = 7; init_genrand(a, 19650218U); mix(a, key, 4); memcpy(b, base, sizeof b); mix(b, key, 4);
    printf("state_equal=%d\n", memcmp(a, b, sizeof a) == 0);
    printf("cpython_like_seed+twist_us=%.3f\nprecomputed_prefix_seed+twist_us=%.3f\nprecomputed_prefix_seed_only_us=%.3f\n",
           (t1-t0)/R*1e6, (t2-t1)/R*1e6, (t3-t2)/R*1e6);
    return (int)(sink & 0);
}
