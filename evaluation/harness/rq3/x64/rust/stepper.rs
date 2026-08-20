#![allow(non_snake_case)]

use isabelle_exported::X64_step_test::{
    List, x64_step_benchmark, x64_step_observe,
};
use serde::Deserialize;
use std::alloc::{GlobalAlloc, Layout, System};
use std::env;
use std::fs::File;
use std::io::BufReader;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

#[cfg(allocation_metrics)]
struct CountingAllocator;

#[cfg(allocation_metrics)]
static ALLOCATED_BYTES: AtomicU64 = AtomicU64::new(0);

#[cfg(allocation_metrics)]
unsafe impl GlobalAlloc for CountingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let pointer = unsafe { System.alloc(layout) };
        if !pointer.is_null() {
            ALLOCATED_BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        pointer
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let pointer = unsafe { System.alloc_zeroed(layout) };
        if !pointer.is_null() {
            ALLOCATED_BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        pointer
    }

    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { System.dealloc(pointer, layout) }
    }

    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        let new_pointer = unsafe { System.realloc(pointer, layout, new_size) };
        if !new_pointer.is_null() {
            ALLOCATED_BYTES.fetch_add(new_size as u64, Ordering::Relaxed);
        }
        new_pointer
    }
}

#[cfg(allocation_metrics)]
#[global_allocator]
static GLOBAL_ALLOCATOR: CountingAllocator = CountingAllocator;

#[derive(Deserialize)]
struct RawCase {
    ins: String,
    mode: i64,
    bin: Vec<i64>,
    cr: Vec<i64>,
    ir: Vec<String>,
    mem: Vec<String>,
    #[serde(default)]
    cond: bool,
    expected: Vec<String>,
}

struct BenchCase {
    name: String,
    mode: i128,
    bin: List<i128>,
    cr: List<i128>,
    ir: List<i128>,
    mem: List<i128>,
    compare: Compare,
    expected: Vec<u64>,
}

#[derive(Clone, Copy)]
enum Compare {
    Registers,
    CmpOrTest,
    RegistersAndFlags,
}

fn signed_bits(text: &str) -> i64 {
    let trimmed = text.trim();
    if let Some(hex) = trimmed
        .strip_prefix("0x")
        .or_else(|| trimmed.strip_prefix("0X"))
    {
        u64::from_str_radix(hex, 16)
            .unwrap_or_else(|error| panic!("invalid hex value {text:?}: {error}")) as i64
    } else {
        trimmed
            .parse::<i64>()
            .unwrap_or_else(|error| panic!("invalid integer {text:?}: {error}"))
    }
}

fn int(value: i64) -> i128 {
    i128::from(value)
}

fn list(values: &[i64]) -> List<i128> {
    values.iter().rev().fold(List::Nil, |tail, value| {
        List::Cons(int(*value), Box::new(tail))
    })
}

fn bit_list(values: &[String]) -> List<i128> {
    let values = values
        .iter()
        .map(|value| signed_bits(value))
        .collect::<Vec<_>>();
    list(&values)
}

fn cmp_or_test(instruction: &str) -> bool {
    matches!(
        instruction.split_whitespace().next().unwrap_or(""),
        "Ptestl_rr"
            | "Ptestl_ri"
            | "Ptestq_rr"
            | "Ptestq_ri"
            | "Pcmpl_rr"
            | "Pcmpl_ri"
            | "Pcmpq_rr"
            | "Pcmpq_ri"
    )
}

fn comparable(compare: Compare, values: &[u64]) -> Vec<u64> {
    match compare {
        Compare::Registers => values.iter().take(16).copied().collect(),
        Compare::CmpOrTest => values
            .iter()
            .take(18)
            .chain(values.iter().skip(19).take(2))
            .copied()
            .collect(),
        Compare::RegistersAndFlags => values.iter().take(21).copied().collect(),
    }
}

impl From<RawCase> for BenchCase {
    fn from(case: RawCase) -> Self {
        let compare = if !case.cond {
            Compare::Registers
        } else if cmp_or_test(&case.ins) {
            Compare::CmpOrTest
        } else {
            Compare::RegistersAndFlags
        };
        Self {
            name: case.ins,
            mode: int(case.mode),
            bin: list(&case.bin),
            cr: list(&case.cr),
            ir: bit_list(&case.ir),
            mem: bit_list(&case.mem),
            compare,
            expected: case
                .expected
                .iter()
                .map(|value| signed_bits(value) as u64)
                .collect(),
        }
    }
}

#[cfg(not(x64_borrowed))]
fn observe(case: &BenchCase) -> Vec<u64> {
    x64_step_observe(
        case.mode,
        case.bin.clone(),
        case.cr.clone(),
        case.ir.clone(),
        case.mem.clone(),
    )
}

#[cfg(x64_borrowed)]
fn observe(case: &BenchCase) -> Vec<u64> {
    x64_step_observe(case.mode, &case.bin, &case.cr, &case.ir, &case.mem)
}

#[cfg(not(x64_borrowed))]
fn run(case: &BenchCase) {
    x64_step_benchmark(
        case.mode,
        case.bin.clone(),
        case.cr.clone(),
        case.ir.clone(),
        case.mem.clone(),
    )
}

#[cfg(x64_borrowed)]
fn run(case: &BenchCase) {
    x64_step_benchmark(case.mode, &case.bin, &case.cr, &case.ir, &case.mem)
}

fn allocated_bytes() -> u64 {
    #[cfg(allocation_metrics)]
    {
        return ALLOCATED_BYTES.load(Ordering::Relaxed);
    }
    #[cfg(not(allocation_metrics))]
    0
}

fn reset_allocated_bytes() {
    #[cfg(allocation_metrics)]
    ALLOCATED_BYTES.store(0, Ordering::Relaxed);
}

fn main() {
    let input = env::var("CROSS_JSON").expect("CROSS_JSON is required");
    let raw: Vec<RawCase> = serde_json::from_reader(BufReader::new(
        File::open(&input).unwrap_or_else(|error| panic!("open {input}: {error}")),
    ))
    .expect("parse x64-stepper JSON");
    assert_eq!(raw.len(), 6000, "x64-stepper input must contain 6,000 vectors");
    let cases: Vec<BenchCase> = raw.into_iter().map(BenchCase::from).collect();
    let mode = env::var("X64_MEASURE").unwrap_or_else(|_| "correctness".to_owned());

    if mode == "correctness" {
        let mut failures = Vec::new();
        for case in &cases {
            let actual = observe(case);
            let expected = comparable(case.compare, &case.expected);
            let actual = comparable(case.compare, &actual);
            if !((expected.first() == Some(&u64::MAX) && actual.is_empty())
                || expected == actual)
            {
                failures.push(case.name.as_str());
            }
        }
        println!(
            "RESULT benchmark=x64-stepper metric=correctness passed={} failed={}",
            cases.len() - failures.len(),
            failures.len()
        );
        for failure in &failures {
            eprintln!("failed_case={failure}");
        }
        assert!(failures.is_empty(), "x64-stepper validation failed");
        return;
    }

    let repetitions: usize = env::var("SUITE_REPETITIONS")
        .unwrap_or_else(|_| "1".to_owned())
        .parse()
        .expect("SUITE_REPETITIONS must be a positive integer");
    assert!(repetitions > 0);
    reset_allocated_bytes();
    let started = Instant::now();
    for _ in 0..repetitions {
        for case in &cases {
            run(case);
        }
    }
    let elapsed = started.elapsed().as_secs_f64();
    let allocated = allocated_bytes();
    println!(
        "RESULT benchmark=x64-stepper metric={} process_id={} cases={} suite_repetitions={} logical_units={} elapsed_seconds={:.9} allocated_bytes={}",
        mode,
        std::process::id(),
        cases.len(),
        repetitions,
        cases.len() * repetitions,
        elapsed,
        allocated
    );
}
