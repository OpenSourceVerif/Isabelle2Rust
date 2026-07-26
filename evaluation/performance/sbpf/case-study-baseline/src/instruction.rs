mod metrics;

use serde::Deserialize;
use solana_rbpf::aligned_memory::AlignedMemory;
use solana_rbpf::assembler::assemble;
use solana_rbpf::ebpf;
use solana_rbpf::elf::Executable;
use solana_rbpf::memory_region::MemoryRegion;
use solana_rbpf::program::{BuiltinFunction, BuiltinProgram, FunctionRegistry, SBPFVersion};
use solana_rbpf::vm::{Config, EbpfVm, TestContextObject};
use std::env;
use std::fs::File;
use std::hint::black_box;
use std::io::BufReader;
use std::sync::Arc;
use std::time::Instant;

#[derive(Clone, Deserialize)]
struct RawCase {
    dis: String,
    lr_std: Vec<String>,
    lm_std: Vec<String>,
    v: String,
    fuel: String,
    ipc: String,
    index: String,
    result_expected: String,
}

struct Invocation {
    name: String,
    executable: &'static Executable<TestContextObject>,
    vm: EbpfVm<'static, TestContextObject>,
    registers: Vec<(String, i64)>,
    rx_index: usize,
    is_store: bool,
    is_load: bool,
    expected_pc: u64,
    expected_result: u64,
}

fn hex(value: &str) -> u64 {
    u64::from_str_radix(
        value
            .trim()
            .trim_start_matches("0x")
            .trim_start_matches("0X"),
        16,
    )
    .unwrap_or_else(|error| panic!("bad hex {value}: {error}"))
}

fn prepare(raw: RawCase) -> Invocation {
    let version = if hex(&raw.v) == 1 {
        SBPFVersion::V1
    } else {
        SBPFVersion::V2
    };
    let mut config = Config {
        enable_instruction_tracing: false,
        enable_instruction_meter: false,
        ..Config::default()
    };
    config.enabled_sbpf_versions = version.clone()..=version.clone();
    let loader = Arc::new(BuiltinProgram::new_loader(
        config,
        FunctionRegistry::<BuiltinFunction<TestContextObject>>::default(),
    ));
    let executable = Box::leak(Box::new(
        assemble::<TestContextObject>(&raw.dis, loader)
            .unwrap_or_else(|error| panic!("assemble {}: {error}", raw.dis)),
    ));
    let registers = raw
        .lr_std
        .iter()
        .enumerate()
        .map(|(index, value)| (format!("r{index}"), hex(value) as i64))
        .collect();
    let memory: &'static mut [u8] = Box::leak(
        raw.lm_std
            .iter()
            .map(|value| hex(value) as u8)
            .collect::<Vec<_>>()
            .into_boxed_slice(),
    );
    let input = MemoryRegion::new_writable(memory, ebpf::MM_INPUT_START);
    let context = Box::leak(Box::new(TestContextObject::new(0)));
    let stack = Box::leak(Box::new(AlignedMemory::zero_filled(
        executable.get_config().stack_size(),
    )));
    let heap = Box::leak(Box::new(AlignedMemory::with_capacity(0)));
    let stack_len = stack.len();
    let mapping = test_utils::create_memory_mapping(executable, stack, heap, vec![input], None)
        .expect("construct VM memory mapping");
    let vm = EbpfVm::new(
        executable.get_loader().clone(),
        executable.get_sbpf_version(),
        context,
        mapping,
        stack_len,
    );
    let is_store = hex(&raw.fuel) == 2;
    let is_load = !is_store && !raw.lm_std.is_empty();
    Invocation {
        name: raw.dis,
        executable,
        vm,
        registers,
        rx_index: hex(&raw.index) as usize,
        is_store,
        is_load,
        expected_pc: hex(&raw.ipc),
        expected_result: hex(&raw.result_expected),
    }
}

fn run(case: &mut Invocation) -> bool {
    let result = black_box(case.vm.execute_step(
        case.executable,
        &case.registers,
        case.rx_index,
        case.is_store,
        case.is_load,
    ));
    result.0 && result.2 == case.expected_result && result.3 == case.expected_pc
}

fn main() {
    let input = env::var("CROSS_JSON").expect("CROSS_JSON is required");
    let raw: Vec<RawCase> = serde_json::from_reader(BufReader::new(
        File::open(&input).unwrap_or_else(|error| panic!("open {input}: {error}")),
    ))
    .expect("parse SBPF-instruction JSON");
    assert_eq!(
        raw.len(),
        6000,
        "SBPF-instruction input must contain 6,000 vectors"
    );
    let case_count = raw.len();
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

    // All executable, VM, and input-state construction finishes here, before
    // either the timer or allocation counter is reset.
    let mut cases = Vec::with_capacity(case_count * repetitions);
    for _ in 0..repetitions {
        cases.extend(raw.iter().cloned().map(prepare));
    }

    if mode == "correctness" {
        let mut failures = Vec::new();
        for case in &mut cases {
            if !run(case) {
                failures.push(case.name.clone());
            }
        }
        println!(
            "RESULT benchmark=SBPF-instruction metric=correctness passed={} failed={}",
            case_count - failures.len(),
            failures.len()
        );
        for failure in &failures {
            eprintln!("failed_case={failure}");
        }
        assert!(
            failures.is_empty(),
            "case-study SBPF-instruction validation failed"
        );
        return;
    }

    metrics::reset();
    let started = Instant::now();
    let mut failures = 0usize;
    for case in &mut cases {
        if !run(case) {
            failures += 1;
        }
    }
    let elapsed = started.elapsed().as_secs_f64();
    let allocated = metrics::read();
    assert_eq!(
        failures, 0,
        "timed case-study SBPF-instruction validation failed"
    );
    println!(
        "RESULT benchmark=SBPF-instruction metric={} process_id={} cases={} suite_repetitions={} logical_units={} elapsed_seconds={:.9} allocated_bytes={}",
        mode,
        std::process::id(),
        case_count,
        repetitions,
        cases.len(),
        elapsed,
        allocated
    );
}
