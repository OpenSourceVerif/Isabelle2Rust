#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <jansson.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define CASE_COUNT 6000
#define MAX_CODE_SIZE 48
#define OBSERVABLES 21

typedef struct {
    uint64_t rax, rbx, rcx, rdx;
    uint64_t rsi, rdi, rbp, rsp;
    uint64_t rip, r8, r9, r10, r11, r12, r13, r14, r15;
    uint64_t rflags;
} RegisterState;

typedef struct {
    const char *name;
    uint8_t code[MAX_CODE_SIZE];
    size_t code_size;
    uint64_t registers[15];
    uint64_t flags[5];
    uint64_t expected[OBSERVABLES];
    size_t compare_count;
    int skip_parity;
} TestCase;

static uint8_t *exec_page;
static volatile uint64_t result_sink;
static uint64_t allocated_bytes;
static int count_allocations;

/*
 * The native baseline is linked with --wrap for the allocation functions
 * below.  As in the Rust harness, the counter records cumulative requested
 * bytes and does not subtract deallocations.
 */
void *__real_malloc(size_t size);
void *__real_calloc(size_t count, size_t size);
void *__real_realloc(void *pointer, size_t size);

void *__wrap_malloc(size_t size) {
    void *result = __real_malloc(size);
    if (count_allocations && result != NULL) allocated_bytes += (uint64_t)size;
    return result;
}

void *__wrap_calloc(size_t count, size_t size) {
    void *result = __real_calloc(count, size);
    if (count_allocations && result != NULL) {
        allocated_bytes += (uint64_t)count * (uint64_t)size;
    }
    return result;
}

void *__wrap_realloc(void *pointer, size_t size) {
    void *result = __real_realloc(pointer, size);
    if (count_allocations && result != NULL) allocated_bytes += (uint64_t)size;
    return result;
}

static void begin_allocation_measurement(void) {
    allocated_bytes = 0;
    count_allocations = 1;
}

static uint64_t end_allocation_measurement(void) {
    count_allocations = 0;
    return allocated_bytes;
}

static void verify_allocation_measurement(void) {
    const size_t probe_size = 17;
    begin_allocation_measurement();
    void *(*volatile allocate)(size_t) = malloc;
    void *probe = allocate(probe_size);
    if (probe == NULL) {
        fprintf(stderr, "native allocation-counter probe failed to allocate\n");
        exit(EXIT_FAILURE);
    }
    uint64_t probe_bytes = end_allocation_measurement();
    free(probe);
    if (probe_bytes != probe_size) {
        fprintf(stderr,
                "native allocation-counter probe recorded %" PRIu64
                " bytes instead of %zu\n",
                probe_bytes, probe_size);
        exit(EXIT_FAILURE);
    }
}

static void fail_errno(const char *operation) {
    perror(operation);
    exit(EXIT_FAILURE);
}

static long checked_ptrace(enum __ptrace_request request, pid_t pid, void *address,
                           void *data, const char *operation) {
    errno = 0;
    long result = ptrace(request, pid, address, data);
    if (result == -1 && errno != 0) {
        fail_errno(operation);
    }
    return result;
}

static void get_registers(pid_t pid, RegisterState *regs) {
    struct user_regs_struct raw;
    checked_ptrace(PTRACE_GETREGS, pid, NULL, &raw, "ptrace(PTRACE_GETREGS)");
    regs->rax = raw.rax; regs->rbx = raw.rbx; regs->rcx = raw.rcx;
    regs->rdx = raw.rdx; regs->rsi = raw.rsi; regs->rdi = raw.rdi;
    regs->rbp = raw.rbp; regs->rsp = raw.rsp; regs->rip = raw.rip;
    regs->r8 = raw.r8; regs->r9 = raw.r9; regs->r10 = raw.r10;
    regs->r11 = raw.r11; regs->r12 = raw.r12; regs->r13 = raw.r13;
    regs->r14 = raw.r14; regs->r15 = raw.r15; regs->rflags = raw.eflags;
}

static void set_registers(pid_t pid, const RegisterState *regs) {
    struct user_regs_struct raw;
    checked_ptrace(PTRACE_GETREGS, pid, NULL, &raw, "ptrace(PTRACE_GETREGS)");
    raw.rax = regs->rax; raw.rbx = regs->rbx; raw.rcx = regs->rcx;
    raw.rdx = regs->rdx; raw.rsi = regs->rsi; raw.rdi = regs->rdi;
    raw.rbp = regs->rbp; raw.rsp = regs->rsp; raw.rip = regs->rip;
    raw.r8 = regs->r8; raw.r9 = regs->r9; raw.r10 = regs->r10;
    raw.r11 = regs->r11; raw.r12 = regs->r12; raw.r13 = regs->r13;
    raw.r14 = regs->r14; raw.r15 = regs->r15; raw.eflags = regs->rflags;
    checked_ptrace(PTRACE_SETREGS, pid, NULL, &raw, "ptrace(PTRACE_SETREGS)");
}

static int execute_instruction(pid_t pid, const TestCase *test, RegisterState *regs) {
    size_t breakpoint = test->code_size;
    size_t alternate_breakpoint = SIZE_MAX;
    if (test->code_size >= 5 && test->code[0] == 0xe9) {
        int32_t displacement;
        memcpy(&displacement, test->code + 1, sizeof(displacement));
        int64_t target = 5 + (int64_t)displacement;
        if (target < 0 || target >= 4095) return 0;
        breakpoint = (size_t)target;
    } else if (test->code_size >= 6 && test->code[0] == 0x0f &&
               (test->code[1] & 0xf0) == 0x80) {
        int32_t displacement;
        memcpy(&displacement, test->code + 2, sizeof(displacement));
        int64_t target = 6 + (int64_t)displacement;
        if (target < 0 || target >= 4095) return 0;
        alternate_breakpoint = (size_t)target;
    }

    for (size_t index = 0; index < test->code_size; ++index) {
        checked_ptrace(PTRACE_POKETEXT, pid, exec_page + index,
                       (void *)(uintptr_t)test->code[index], "ptrace(PTRACE_POKETEXT)");
    }
    checked_ptrace(PTRACE_POKETEXT, pid, exec_page + breakpoint,
                   (void *)(uintptr_t)0xcc, "ptrace(PTRACE_POKETEXT)");
    if (alternate_breakpoint != SIZE_MAX && alternate_breakpoint != breakpoint) {
        checked_ptrace(PTRACE_POKETEXT, pid, exec_page + alternate_breakpoint,
                       (void *)(uintptr_t)0xcc, "ptrace(PTRACE_POKETEXT)");
    }

    regs->rip = (uint64_t)exec_page;
    set_registers(pid, regs);
    checked_ptrace(PTRACE_CONT, pid, NULL, NULL, "ptrace(PTRACE_CONT)");
    int status;
    if (waitpid(pid, &status, 0) < 0) fail_errno("waitpid");
    if (!WIFSTOPPED(status) || WSTOPSIG(status) != SIGTRAP) return 0;
    get_registers(pid, regs);
    return 1;
}

static uint64_t parse_bits(const char *text) {
    char *end = NULL;
    errno = 0;
    uint64_t result = strtoull(text, &end, 0);
    if (errno != 0 || end == text || *end != '\0') {
        fprintf(stderr, "invalid integer value: %s\n", text);
        exit(EXIT_FAILURE);
    }
    return result;
}

static int cmp_or_test(const char *instruction) {
    static const char *names[] = {
        "Ptestl_rr", "Ptestl_ri", "Ptestq_rr", "Ptestq_ri",
        "Pcmpl_rr", "Pcmpl_ri", "Pcmpq_rr", "Pcmpq_ri",
    };
    size_t length = strcspn(instruction, " \t");
    for (size_t index = 0; index < sizeof(names) / sizeof(names[0]); ++index) {
        if (strlen(names[index]) == length &&
            strncmp(instruction, names[index], length) == 0) return 1;
    }
    return 0;
}

static TestCase *load_cases(const char *path, json_t **root_out) {
    json_error_t error;
    json_t *root = json_load_file(path, 0, &error);
    if (root == NULL || !json_is_array(root)) {
        fprintf(stderr, "cannot parse %s: %s (%d:%d)\n", path, error.text,
                error.line, error.column);
        exit(EXIT_FAILURE);
    }
    if (json_array_size(root) != CASE_COUNT) {
        fprintf(stderr, "x64-stepper input must contain %d vectors, got %zu\n",
                CASE_COUNT, json_array_size(root));
        exit(EXIT_FAILURE);
    }
    TestCase *cases = calloc(CASE_COUNT, sizeof(*cases));
    if (cases == NULL) fail_errno("calloc");
    for (size_t case_index = 0; case_index < CASE_COUNT; ++case_index) {
        json_t *object = json_array_get(root, case_index);
        TestCase *test = &cases[case_index];
        test->name = json_string_value(json_object_get(object, "ins"));
        json_t *code = json_object_get(object, "bin");
        test->code_size = json_array_size(code);
        if (test->code_size > MAX_CODE_SIZE) {
            fprintf(stderr, "instruction too long: %s\n", test->name);
            exit(EXIT_FAILURE);
        }
        for (size_t index = 0; index < test->code_size; ++index) {
            test->code[index] = (uint8_t)json_integer_value(json_array_get(code, index));
        }
        json_t *registers = json_object_get(object, "ir");
        json_t *flags = json_object_get(object, "cr");
        json_t *expected = json_object_get(object, "expected");
        for (size_t index = 0; index < 15; ++index) {
            test->registers[index] =
                parse_bits(json_string_value(json_array_get(registers, index)));
        }
        for (size_t index = 0; index < 5; ++index) {
            test->flags[index] =
                (uint64_t)json_integer_value(json_array_get(flags, index));
        }
        for (size_t index = 0; index < OBSERVABLES; ++index) {
            test->expected[index] =
                parse_bits(json_string_value(json_array_get(expected, index)));
        }
        int cond = json_is_true(json_object_get(object, "cond"));
        test->skip_parity = cond && cmp_or_test(test->name);
        test->compare_count = cond ? OBSERVABLES : 16;
    }
    *root_out = root;
    return cases;
}

static void initial_registers(const TestCase *test, RegisterState *regs) {
    regs->rax = test->registers[0]; regs->rbx = test->registers[1];
    regs->rcx = test->registers[2]; regs->rdx = test->registers[3];
    regs->rsi = test->registers[4]; regs->rdi = test->registers[5];
    regs->rbp = test->registers[6]; regs->rsp = test->registers[7];
    regs->r8 = test->registers[8]; regs->r9 = test->registers[9];
    regs->r10 = test->registers[10]; regs->r11 = test->registers[11];
    regs->r12 = test->registers[12]; regs->r13 = test->registers[13];
    regs->r14 = test->registers[14];
    regs->rflags = (test->flags[0] << 6) | (test->flags[1] << 0) |
                   (test->flags[2] << 2) | (test->flags[3] << 7) |
                   (test->flags[4] << 11);
}

static void observe(const RegisterState *regs, uint64_t values[OBSERVABLES]) {
    values[0] = regs->rip - (uint64_t)exec_page - 1;
    values[1] = regs->rax; values[2] = regs->rbx; values[3] = regs->rcx;
    values[4] = regs->rdx; values[5] = regs->rsi; values[6] = regs->rdi;
    values[7] = regs->rbp; values[8] = regs->rsp; values[9] = regs->r8;
    values[10] = regs->r9; values[11] = regs->r10; values[12] = regs->r11;
    values[13] = regs->r12; values[14] = regs->r13; values[15] = regs->r14;
    values[16] = (regs->rflags >> 6) & 1;
    values[17] = (regs->rflags >> 0) & 1;
    values[18] = (regs->rflags >> 2) & 1;
    values[19] = (regs->rflags >> 7) & 1;
    values[20] = (regs->rflags >> 11) & 1;
}

static int equal_observation(const TestCase *test, const uint64_t actual[OBSERVABLES]) {
    for (size_t index = 0; index < test->compare_count; ++index) {
        if (test->skip_parity && index == 18) continue;
        if (test->expected[index] != actual[index]) return 0;
    }
    return 1;
}

static pid_t start_child(RegisterState *initial) {
    pid_t pid = fork();
    if (pid < 0) fail_errno("fork");
    if (pid == 0) {
        uint8_t *page = mmap(NULL, 4096, PROT_READ | PROT_WRITE | PROT_EXEC,
                             MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (page == MAP_FAILED) fail_errno("mmap");
        __asm__ volatile("mov %0, %%r15" : : "r"(page));
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) == -1) fail_errno("PTRACE_TRACEME");
        raise(SIGSTOP);
        for (;;) pause();
    }
    int status;
    if (waitpid(pid, &status, 0) < 0) fail_errno("waitpid");
    if (!WIFSTOPPED(status)) {
        fprintf(stderr, "native x64 child did not stop\n");
        exit(EXIT_FAILURE);
    }
    get_registers(pid, initial);
    exec_page = (uint8_t *)(uintptr_t)initial->r15;
    return pid;
}

static void stop_child(pid_t pid) {
    checked_ptrace(PTRACE_DETACH, pid, NULL, NULL, "ptrace(PTRACE_DETACH)");
    kill(pid, SIGKILL);
    int status;
    waitpid(pid, &status, 0);
}

static double seconds_between(struct timespec start, struct timespec end) {
    return (double)(end.tv_sec - start.tv_sec) +
           (double)(end.tv_nsec - start.tv_nsec) / 1000000000.0;
}

int main(void) {
    verify_allocation_measurement();

    const char *path = getenv("CROSS_JSON");
    if (path == NULL) {
        fprintf(stderr, "CROSS_JSON is required\n");
        return EXIT_FAILURE;
    }
    const char *mode = getenv("X64_MEASURE");
    if (mode == NULL) mode = "correctness";
    const char *repetition_text = getenv("SUITE_REPETITIONS");
    long repetitions = repetition_text == NULL ? 1 : strtol(repetition_text, NULL, 10);
    if (repetitions <= 0) {
        fprintf(stderr, "SUITE_REPETITIONS must be positive\n");
        return EXIT_FAILURE;
    }

    json_t *root;
    TestCase *cases = load_cases(path, &root);
    RegisterState base;
    pid_t child = start_child(&base);
    size_t failures = 0;
    uint64_t measured_allocated_bytes = 0;
    struct timespec started = {0}, finished = {0};
    if (strcmp(mode, "runtime") == 0 || strcmp(mode, "pilot") == 0) {
        clock_gettime(CLOCK_MONOTONIC, &started);
    } else if (strcmp(mode, "allocation") == 0) {
        begin_allocation_measurement();
    }
    for (long repetition = 0; repetition < repetitions; ++repetition) {
        for (size_t case_index = 0; case_index < CASE_COUNT; ++case_index) {
            RegisterState registers = base;
            initial_registers(&cases[case_index], &registers);
            int executed = execute_instruction(child, &cases[case_index], &registers);
            uint64_t actual[OBSERVABLES] = {0};
            if (executed) observe(&registers, actual);
            if (strcmp(mode, "correctness") == 0) {
                int expected_stuck = cases[case_index].expected[0] == UINT64_MAX;
                if ((!executed && !expected_stuck) ||
                    (executed && !equal_observation(&cases[case_index], actual))) {
                    ++failures;
                    if (failures <= 20) fprintf(stderr, "failed_case=%s\n", cases[case_index].name);
                }
            } else {
                result_sink ^= actual[0] ^ actual[1] ^ actual[15];
            }
        }
    }
    if (strcmp(mode, "runtime") == 0 || strcmp(mode, "pilot") == 0) {
        clock_gettime(CLOCK_MONOTONIC, &finished);
    } else if (strcmp(mode, "allocation") == 0) {
        measured_allocated_bytes = end_allocation_measurement();
    }
    stop_child(child);

    if (strcmp(mode, "correctness") == 0) {
        printf("RESULT benchmark=x64-stepper metric=correctness passed=%zu failed=%zu\n",
               CASE_COUNT - failures, failures);
    } else {
        double elapsed = (strcmp(mode, "allocation") == 0)
                             ? 0.0
                             : seconds_between(started, finished);
        printf("RESULT benchmark=x64-stepper metric=%s process_id=%ld cases=%d suite_repetitions=%ld logical_units=%ld elapsed_seconds=%.9f allocated_bytes=%" PRIu64 "\n",
               mode, (long)getpid(), CASE_COUNT, repetitions,
               (long)CASE_COUNT * repetitions, elapsed, measured_allocated_bytes);
    }
    free(cases);
    json_decref(root);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
