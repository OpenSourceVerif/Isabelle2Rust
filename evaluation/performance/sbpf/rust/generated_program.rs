#![allow(non_snake_case)]

use isabelle_exported::Interp_test::{List, bpf_interp_test};
use isabelle_exported::Rust_Native_Int::RustInt;
use serde::Deserialize;
use std::alloc::{GlobalAlloc, Layout, System};
use std::env;
use std::fs::File;
use std::hint::black_box;
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
    dis: String,
    lp_std: Vec<i64>,
    lm_std: Vec<i64>,
    lc_std: Vec<i64>,
    v: i64,
    fuel: i64,
    result_expected: i64,
    isok: bool,
}

struct BenchCase {
    name: String,
    lp: List<RustInt>,
    lm: List<RustInt>,
    lc: List<RustInt>,
    v: RustInt,
    fuel: RustInt,
    expected: RustInt,
    succeeds: bool,
}

fn int_of_i64(value: i64) -> RustInt {
    RustInt::from_i128(i128::from(value))
}

fn list_of_i64s(values: &[i64]) -> List<RustInt> {
    values.iter().rev().fold(List::Nil, |tail, value| {
        List::Cons(int_of_i64(*value), Box::new(tail))
    })
}

impl From<RawCase> for BenchCase {
    fn from(case: RawCase) -> Self {
        Self {
            name: case.dis,
            lp: list_of_i64s(&case.lp_std),
            lm: list_of_i64s(&case.lm_std),
            lc: list_of_i64s(&case.lc_std),
            v: int_of_i64(case.v),
            fuel: int_of_i64(case.fuel),
            expected: int_of_i64(case.result_expected),
            succeeds: case.isok,
        }
    }
}

#[cfg(not(sbpf_borrowed))]
fn run(case: &BenchCase) -> bool {
    bpf_interp_test(
        case.lp.clone(),
        case.lm.clone(),
        case.lc.clone(),
        case.v.clone(),
        case.fuel.clone(),
        case.expected.clone(),
        case.succeeds,
    )
}

#[cfg(sbpf_borrowed)]
fn run(case: &BenchCase) -> bool {
    bpf_interp_test(
        case.lp.clone(),
        case.lm.clone(),
        &case.lc,
        case.v.clone(),
        case.fuel.clone(),
        case.expected.clone(),
        case.succeeds,
    )
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
    .expect("parse SBPF-program JSON");
    assert_eq!(raw.len(), 146, "SBPF-program input must contain 146 cases");
    let cases: Vec<BenchCase> = raw.into_iter().map(BenchCase::from).collect();
    let mode = env::var("SBPF_MEASURE").unwrap_or_else(|_| "correctness".to_owned());

    if mode == "correctness" {
        let failures: Vec<&str> = cases
            .iter()
            .filter(|case| !run(case))
            .map(|case| case.name.as_str())
            .collect();
        println!(
            "RESULT benchmark=SBPF-program metric=correctness passed={} failed={}",
            cases.len() - failures.len(),
            failures.len()
        );
        for failure in &failures {
            eprintln!("failed_case={failure}");
        }
        assert!(failures.is_empty(), "SBPF-program validation failed");
        return;
    }

    let repetitions: usize = env::var("SUITE_REPETITIONS")
        .unwrap_or_else(|_| "1".to_owned())
        .parse()
        .expect("SUITE_REPETITIONS must be a positive integer");
    assert!(repetitions > 0);
    reset_allocated_bytes();
    let started = Instant::now();
    let mut failures = 0usize;
    for _ in 0..repetitions {
        for case in &cases {
            if !black_box(run(case)) {
                failures += 1;
            }
        }
    }
    let elapsed = started.elapsed().as_secs_f64();
    let allocated = allocated_bytes();
    assert_eq!(failures, 0, "timed SBPF-program validation failed");
    println!(
        "RESULT benchmark=SBPF-program metric={} process_id={} cases={} suite_repetitions={} logical_units={} elapsed_seconds={:.9} allocated_bytes={}",
        mode,
        std::process::id(),
        cases.len(),
        repetitions,
        cases.len() * repetitions,
        elapsed,
        allocated
    );
}
