#include <time.h>

#include <caml/alloc.h>
#include <caml/fail.h>
#include <caml/memory.h>
#include <caml/mlvalues.h>

CAMLprim value i2r_monotonic_seconds(value unit)
{
    CAMLparam1(unit);
    struct timespec timestamp;

    if (clock_gettime(CLOCK_MONOTONIC, &timestamp) != 0) {
        caml_failwith("clock_gettime(CLOCK_MONOTONIC) failed");
    }

    CAMLreturn(caml_copy_double(
        (double)timestamp.tv_sec + (double)timestamp.tv_nsec / 1000000000.0));
}
