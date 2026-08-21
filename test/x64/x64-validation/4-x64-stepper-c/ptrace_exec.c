#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/user.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/mman.h>
#include <jansson.h>
#include <inttypes.h>

typedef struct {
    uint64_t rax, rbx, rcx, rdx;
    uint64_t rsi, rdi, rbp, rsp;
    uint64_t rip, r8, r9, r10, r11, r12, r13, r14, r15;
    uint64_t rflags;
} RegisterState;

void print_registers(RegisterState* regs, FILE *fp) {

    fprintf(fp,"Register State:\n");
    fprintf(fp,"  RAX: %ld\n", regs->rax);
    fprintf(fp,"  RBX: %ld\n", regs->rbx);
    fprintf(fp,"  RCX: %ld\n", regs->rcx);
    fprintf(fp,"  RDX: %ld\n", regs->rdx);
    fprintf(fp,"  RSI: %ld\n", regs->rsi);
    fprintf(fp,"  RDI: %ld\n", regs->rdi);
    fprintf(fp,"  RBP: %ld\n", regs->rbp);
    fprintf(fp,"  RSP: %ld\n", regs->rsp);
    fprintf(fp,"  R8:  %ld\n", regs->r8);
    fprintf(fp,"  R9:  %ld\n", regs->r9);
    fprintf(fp,"  R10: %ld\n", regs->r10);
    fprintf(fp,"  R11: %ld\n", regs->r11);
    fprintf(fp,"  R12: %ld\n", regs->r12);
    fprintf(fp,"  R13: %ld\n", regs->r13);
    fprintf(fp,"  R14: %ld\n", regs->r14);
    //fprintf(fp,"  R15: %ld\n", regs->r15);

    uint64_t f = regs->rflags;
    int cf = (f >>  0) & 1;   /* Carry / Borrow  */
    int pf = (f >>  2) & 1;   /* Parity          */
    int zf = (f >>  6) & 1;   /* Zero            */
    int sf = (f >>  7) & 1;   /* Sign            */
    int of = (f >> 11) & 1;   /* Overflow        */

    fprintf(fp,"  CF:%d\n", cf);
    fprintf(fp,"  PF:%d\n", pf);
    fprintf(fp,"  ZF:%d\n", zf);
    fprintf(fp,"  SF:%d\n", sf);
    fprintf(fp,"  OF:%d\n", of);

}

void get_registers(pid_t pid, RegisterState* regs) {
    struct user_regs_struct uregs;
    ptrace(PTRACE_GETREGS, pid, NULL, &uregs);
    if (errno) {
        perror("ptrace(PTRACE_GETREGS) failed");
        exit(EXIT_FAILURE);
    }
    regs->rax = uregs.rax; regs->rbx = uregs.rbx; regs->rcx = uregs.rcx;
    regs->rdx = uregs.rdx; regs->rsi = uregs.rsi; regs->rdi = uregs.rdi;
    regs->rbp = uregs.rbp; regs->rsp = uregs.rsp; regs->rip = uregs.rip;
    regs->r8 = uregs.r8; regs->r9 = uregs.r9; regs->r10 = uregs.r10;
    regs->r11 = uregs.r11; regs->r12 = uregs.r12; regs->r13 = uregs.r13;
    regs->r14 = uregs.r14; regs->r15 = uregs.r15; regs->rflags = uregs.eflags;
}

void set_registers(pid_t pid, RegisterState* regs) {
    struct user_regs_struct uregs;
    ptrace(PTRACE_GETREGS, pid, NULL, &uregs);
    uregs.rax = regs->rax; uregs.rbx = regs->rbx; uregs.rcx = regs->rcx;
    uregs.rdx = regs->rdx; uregs.rsi = regs->rsi; uregs.rdi = regs->rdi;
    uregs.rbp = regs->rbp; uregs.rsp = regs->rsp; uregs.rip = regs->rip;
    uregs.r8 = regs->r8; uregs.r9 = regs->r9; uregs.r10 = regs->r10;
    uregs.r11 = regs->r11; uregs.r12 = regs->r12; uregs.r13 = regs->r13;
    uregs.r14 = regs->r14; uregs.r15 = regs->r15; uregs.eflags = regs->rflags;
    ptrace(PTRACE_SETREGS, pid, NULL, &uregs);
}

static uint8_t* exec_page = NULL;
int execute_instruction(pid_t pid, uint8_t* code, size_t code_size, RegisterState* regs) {
    if (exec_page == NULL) {
        fprintf(stderr, "Executable memory not allocated.\n");
        return 0;
    }

        int is_pc_control = 0;
        size_t target_offset = 0;

        // Case 1: jmp rel32
        if (code_size >= 5 && code[0] == 0xE9) {
            int32_t disp = *((int32_t*)(code + 1));
            target_offset = 5 + disp;
            is_pc_control = 1;
        }

        // Case 2: jcc rel32 (0F 8x ...)
        else if (code_size >= 6 && code[0] == 0x0F && (code[1] & 0xF0) == 0x80) {
            int32_t disp = *((int32_t*)(code + 2));
            target_offset = 6 + disp;
            is_pc_control = 1;
        }

    for (size_t i = 0; i < code_size; ++i) {
        ptrace(PTRACE_POKETEXT, pid, exec_page + i, (void*)(uint64_t)code[i]);
    }

    if (is_pc_control) {
        for (size_t i = code_size; i <= target_offset + 16; ++i) {
            ptrace(PTRACE_POKETEXT, pid, exec_page + i, (void*)0xCC);
        }
    } else {
        ptrace(PTRACE_POKETEXT, pid, exec_page + code_size, (void*)0xCC);
    }

    regs->rip = (uint64_t)exec_page;
    set_registers(pid, regs);
    ptrace(PTRACE_CONT, pid, NULL, NULL);

    int status;
    waitpid(pid, &status, 0);
    if (!WIFSTOPPED(status) || WSTOPSIG(status) != SIGTRAP)
        return 0;

    get_registers(pid, regs);
    return 1;
}



static uint64_t parse_hex_str(const char *hexstr) {
    uint64_t val = 0;
    if (sscanf(hexstr, "0x%" SCNx64, &val) == 1) {
        return val;
    } else {
        fprintf(stderr, "Failed to parse hex string: %s\n", hexstr);
        exit(EXIT_FAILURE);
    }
}

static void load_regs_from_json(RegisterState *r, const json_t *ir_arr, const json_t *cr_arr) {
    #define JHEX(idx) parse_hex_str(json_string_value(json_array_get(ir_arr, idx)))

    r->rax = JHEX(0); r->rbx = JHEX(1); r->rcx = JHEX(2); r->rdx = JHEX(3);
    r->rsi = JHEX(4); r->rdi = JHEX(5); r->rbp = JHEX(6); r->rsp = JHEX(7);
    r->r8  = JHEX(8); r->r9  = JHEX(9); r->r10 = JHEX(10); r->r11 = JHEX(11);
    r->r12 = JHEX(12); r->r13 = JHEX(13); r->r14 = JHEX(14);

    uint64_t flags = 0;
    if (json_integer_value(json_array_get(cr_arr, 0))) flags |= 1ULL << 6;  // ZF
    if (json_integer_value(json_array_get(cr_arr, 1))) flags |= 1ULL << 0;  // CF
    if (json_integer_value(json_array_get(cr_arr, 2))) flags |= 1ULL << 2;  // PF
    if (json_integer_value(json_array_get(cr_arr, 3))) flags |= 1ULL << 7;  // SF
    if (json_integer_value(json_array_get(cr_arr, 4))) flags |= 1ULL << 11; // OF
    r->rflags = flags;
}

/*
static void _load_regs_from_json1(RegisterState *r, const json_t *ir_arr, const json_t *cr_arr) {
    #define JINT(idx)   (uint64_t)json_integer_value(json_array_get(ir_arr, idx))
    r->rax = JINT(0); r->rbx = JINT(1); r->rcx = JINT(2); r->rdx = JINT(3);
    r->rsi = JINT(4); r->rdi = JINT(5); r->rbp = JINT(6); r->rsp = JINT(7);
    r->r8  = JINT(8); r->r9  = JINT(9); r->r10 = JINT(10); r->r11 = JINT(11);
    r->r12 = JINT(12); r->r13 = JINT(13); r->r14 = JINT(14);
    uint64_t flags = 0;
    if (json_integer_value(json_array_get(cr_arr, 0))) flags |= 1ULL << 6;  // ZF
    if (json_integer_value(json_array_get(cr_arr, 1))) flags |= 1ULL << 0;  // CF
    if (json_integer_value(json_array_get(cr_arr, 2))) flags |= 1ULL << 2;  // PF
    if (json_integer_value(json_array_get(cr_arr, 3))) flags |= 1ULL << 7;  // SF
    if (json_integer_value(json_array_get(cr_arr, 4))) flags |= 1ULL << 11; // OF
    r->rflags = flags;
}*/

static size_t load_bin_from_json(const json_t *bin_arr, uint8_t *buf, size_t buf_cap) {
    size_t n = json_array_size(bin_arr);
    if (n > buf_cap) n = buf_cap;
    for (size_t i = 0; i < n; ++i)
        buf[i] = (uint8_t)json_integer_value(json_array_get(bin_arr, i));
    return n;
}

int main() {
    pid_t pid = fork();

    FILE *fp = fopen("../0-data/step4.json", "w");  
    if (fp == NULL) {
        perror("can't open file");
        exit(EXIT_FAILURE);
    }

    if (pid == 0) {
        exec_page = mmap(NULL, 4096, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (exec_page == MAP_FAILED) {
            perror("mmap failed in child");
            exit(1);
        }
        __asm__ volatile("mov %0, %%r15" : : "r"(exec_page));
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        raise(SIGSTOP);
        while (1) pause();
        return 0;
    } else {
        RegisterState regs;
        int status;
        waitpid(pid, &status, 0);

        struct user_regs_struct uregs;
        ptrace(PTRACE_GETREGS, pid, NULL, &uregs);
        exec_page = (uint8_t*)uregs.r15;

        json_error_t jerr;
        json_t *root = json_load_file("../0-data/step3.json", 0, &jerr);
        if (!root || !json_is_array(root)) {
            fprintf(stderr, "JSON parse error: %s (%d:%d)\n", jerr.text, jerr.line, jerr.column);
            exit(EXIT_FAILURE);
        }

        uint8_t code_buf[48];
        size_t case_cnt = json_array_size(root);
        for (size_t c = 0; c < case_cnt; ++c) {
            json_t *obj = json_array_get(root, c);
            const char *ins = json_string_value(json_object_get(obj, "ins"));
            json_t *bin_arr = json_object_get(obj, "bin");
            json_t *ir_arr  = json_object_get(obj, "ir");
            json_t *cr_arr  = json_object_get(obj, "cr");

            get_registers(pid, &regs);
            load_regs_from_json(&regs, ir_arr, cr_arr);
            size_t code_len = load_bin_from_json(bin_arr, code_buf, sizeof(code_buf));

            
            int _flag = execute_instruction(pid, code_buf, code_len, &regs);

            //print_registers(&regs, fp);

            uint64_t pc_delta = regs.rip - (uint64_t)exec_page - 1;
            uint64_t gp[15] = {
                regs.rax, regs.rbx, regs.rcx, regs.rdx,
                regs.rsi, regs.rdi, regs.rbp, regs.rsp,
                regs.r8 , regs.r9 , regs.r10, regs.r11,
                regs.r12, regs.r13, regs.r14
            };

            uint64_t flags = regs.rflags;
            uint64_t crbit[5] = {
                (flags >> 6) & 1,   /* ZF */
                (flags >> 0) & 1,   /* CF */
                (flags >> 2) & 1,   /* PF */
                (flags >> 7) & 1,   /* SF */
                (flags >> 11) & 1   /* OF */
            };

            char buf[64];
            json_t *exp = json_array();

            sprintf(buf, "0x%llx", (unsigned long long)pc_delta);
            json_array_append_new(exp, json_string(buf));

            for (int i = 0; i < 15; ++i) {
                sprintf(buf, "0x%llx", (unsigned long long)gp[i]);
                json_array_append_new(exp, json_string(buf));
            }

            for (int i = 0; i < 5;  ++i) {
                sprintf(buf, "%lld", (unsigned long long)crbit[i]);
                json_array_append_new(exp, json_string(buf));
            }

            json_object_set_new(obj, "expected", exp);

            json_t *sorted = json_object();
            json_object_set(sorted, "ins",      json_object_get(obj, "ins"));
            json_object_set(sorted, "bin",      json_object_get(obj, "bin"));
            json_object_set(sorted, "cr",       json_object_get(obj, "cr"));
            json_object_set(sorted, "ir",       json_object_get(obj, "ir"));
            json_object_set(sorted, "mem",      json_object_get(obj, "mem"));
            json_object_set(sorted, "expected", json_object_get(obj, "expected"));

        }

        if (json_dump_file(root, "../0-data/step4.json", JSON_INDENT(2)))
            perror("json_dump_file");
        else
            puts("Complete test cases generated");

        json_decref(root);
        ptrace(PTRACE_DETACH, pid, NULL, NULL);
        kill(pid, SIGKILL);
        waitpid(pid, &status, 0);
    }
    fclose(fp);
    return 0;
}
