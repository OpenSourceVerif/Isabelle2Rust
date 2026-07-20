mod metrics;

use serde::Deserialize;
use solana_rbpf::aligned_memory::AlignedMemory;
use solana_rbpf::ebpf;
use solana_rbpf::elf::Executable;
use solana_rbpf::error::ProgramResult;
use solana_rbpf::memory_region::MemoryRegion;
use solana_rbpf::program::{BuiltinFunction, BuiltinProgram, FunctionRegistry, SBPFVersion};
use solana_rbpf::vm::{Config, EbpfVm, TestContextObject};
use std::env;
use std::fs::File;
use std::hint::black_box;
use std::io::BufReader;
use std::sync::Arc;
use std::time::Instant;

#[derive(Deserialize)]
struct RawCase {
    dis: String,
    lp_std: Vec<i64>,
    lm_std: Vec<i64>,
    v: i64,
    fuel: i64,
    result_expected: i64,
    isok: bool,
}

struct Case {
    name: String,
    executable: &'static Executable<TestContextObject>,
    memory: Vec<u8>,
    fuel: u64,
    expected: u64,
    succeeds: bool,
}

struct Invocation {
    name: String,
    executable: &'static Executable<TestContextObject>,
    vm: EbpfVm<'static, TestContextObject>,
    expected: u64,
    succeeds: bool,
}

fn prepare_case(raw: RawCase) -> Case {
    let version = if raw.v == 1 {
        SBPFVersion::V1
    } else {
        SBPFVersion::V2
    };
    let mut config = Config {
        enable_instruction_tracing: false,
        enable_instruction_meter: true,
        ..Config::default()
    };
    config.enabled_sbpf_versions = version.clone()..=version.clone();
    let loader = Arc::new(BuiltinProgram::new_loader(
        config,
        FunctionRegistry::<BuiltinFunction<TestContextObject>>::default(),
    ));
    let bytes: Vec<u8> = raw.lp_std.into_iter().map(|value| value as u8).collect();
    let mut functions = FunctionRegistry::default();
    for pc in 0..bytes.len() / ebpf::INSN_SIZE {
        let instruction = ebpf::get_insn(&bytes, pc);
        if instruction.opc == ebpf::CALL_IMM && instruction.src == 1 && instruction.imm >= 0 {
            let target = instruction.imm as usize;
            functions
                .register_function(
                    target as u32,
                    format!("function_{target}").into_bytes(),
                    target,
                )
                .expect("register direct-call target");
        }
    }
    match raw.dis.as_str() {
        "test_callx" | "test_callx_imm" => functions
            .register_function(6, b"function_foo".to_vec(), 6)
            .expect("register callx target"),
        "test_far_jumps" => functions
            .register_function(2, b"function_a".to_vec(), 2)
            .expect("register far-jump target"),
        _ => {}
    }
    let executable = Box::leak(Box::new(
        Executable::<TestContextObject>::from_text_bytes(&bytes, loader, version, functions)
            .unwrap_or_else(|error| panic!("construct {}: {error:?}", raw.dis)),
    ));
    let mut memory: Vec<u8> = raw.lm_std.into_iter().map(|value| value as u8).collect();
    let minimum_len = match raw.dis.as_str() {
        "test_lmul128" => 16,
        "test_stxb_chain" => 10,
        _ => memory.len(),
    };
    memory.resize(minimum_len, 0);
    Case {
        name: raw.dis,
        executable,
        memory,
        fuel: raw.fuel as u64,
        expected: raw.result_expected as u64,
        succeeds: raw.isok,
    }
}

fn prepare_invocation(case: &Case) -> Invocation {
    let memory: &'static mut [u8] = Box::leak(case.memory.clone().into_boxed_slice());
    let input = MemoryRegion::new_writable(memory, ebpf::MM_INPUT_START);
    let context = Box::leak(Box::new(TestContextObject::new(case.fuel)));
    let stack = Box::leak(Box::new(AlignedMemory::zero_filled(
        case.executable.get_config().stack_size(),
    )));
    let heap = Box::leak(Box::new(AlignedMemory::with_capacity(0)));
    let stack_len = stack.len();
    let mapping =
        test_utils::create_memory_mapping(case.executable, stack, heap, vec![input], None)
            .expect("construct VM memory mapping");
    let vm = EbpfVm::new(
        case.executable.get_loader().clone(),
        case.executable.get_sbpf_version(),
        context,
        mapping,
        stack_len,
    );
    Invocation {
        name: case.name.clone(),
        executable: case.executable,
        vm,
        expected: case.expected,
        succeeds: case.succeeds,
    }
}

fn run(invocation: &mut Invocation) -> bool {
    let (_, result) = black_box(invocation.vm.execute_program(invocation.executable, true));
    match result {
        ProgramResult::Ok(value) => invocation.succeeds && value == invocation.expected,
        ProgramResult::Err(_) => !invocation.succeeds,
    }
}

fn main() {
    let input = env::var("CROSS_JSON").expect("CROSS_JSON is required");
    let raw: Vec<RawCase> = serde_json::from_reader(BufReader::new(
        File::open(&input).unwrap_or_else(|error| panic!("open {input}: {error}")),
    ))
    .expect("parse SBPF-program JSON");
    assert_eq!(raw.len(), 146, "SBPF-program input must contain 146 cases");
    let cases: Vec<Case> = raw.into_iter().map(prepare_case).collect();
    let mode = env::var("SBPF_MEASURE").unwrap_or_else(|_| "correctness".to_owned());
    let repetitions: usize = if mode == "correctness" {
        1
    } else {
        env::var("SUITE_REPETITIONS")
            .unwrap_or_else(|_| "1".to_owned())
            .parse()
            .expect("SUITE_REPETITIONS must be a positive integer")
    };
    assert!(repetitions > 0);

    // Executables, input memory, stacks, contexts, and VMs are all constructed
    // before the measurement region. Each timed execution has independent VM
    // state even when a suite is repeated.
    let mut invocations = Vec::with_capacity(cases.len() * repetitions);
    for _ in 0..repetitions {
        invocations.extend(cases.iter().map(prepare_invocation));
    }

    if mode == "correctness" {
        let mut failures = Vec::new();
        for invocation in &mut invocations {
            if !run(invocation) {
                failures.push(invocation.name.clone());
            }
        }
        println!(
            "RESULT benchmark=SBPF-program metric=correctness passed={} failed={}",
            cases.len() - failures.len(),
            failures.len()
        );
        for failure in &failures {
            eprintln!("failed_case={failure}");
        }
        assert!(
            failures.is_empty(),
            "case-study SBPF-program validation failed"
        );
        return;
    }

    metrics::reset();
    let started = Instant::now();
    let mut failures = 0usize;
    for invocation in &mut invocations {
        if !run(invocation) {
            failures += 1;
        }
    }
    let elapsed = started.elapsed().as_secs_f64();
    let allocated = metrics::read();
    assert_eq!(
        failures, 0,
        "timed case-study SBPF-program validation failed"
    );
    println!(
        "RESULT benchmark=SBPF-program metric={} process_id={} cases={} suite_repetitions={} logical_units={} elapsed_seconds={:.9} allocated_bytes={}",
        mode,
        std::process::id(),
        cases.len(),
        repetitions,
        invocations.len(),
        elapsed,
        allocated
    );
}
