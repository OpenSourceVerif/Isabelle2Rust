// Rust runtime micro-test harness for the exported sBPF single-step semantics.
//
// Feeds the Rust-exported `step_test` the local step vectors in
// tests_sbpf/tests/data/ocaml_in.json and asserts each self-checking call
// returns `true`.
//
// JSON path via CROSS_JSON.
#![feature(box_patterns)]
#![allow(non_snake_case)]

#[cfg(sbpf_native_int)]
use isabelle_exported::Rust_Native_Int::RustInt;
use isabelle_exported::Step_test::{step_test, List};
#[cfg(sbpf_no_bigint)]
use isabelle_exported::Step_test::{Int, Num};
#[cfg(all(not(sbpf_no_bigint), not(sbpf_native_int)))]
use num_bigint::BigInt;
use serde::Deserialize;
use std::env;
use std::fs::File;
use std::hint::black_box;
use std::io::BufReader;
use std::panic::{self, AssertUnwindSafe};
use std::process::exit;
use std::time::Instant;

#[cfg(all(sbpf_no_bigint, sbpf_native_int))]
compile_error!("sbpf_no_bigint and sbpf_native_int are mutually exclusive");

#[derive(Deserialize)]
struct Case {
    dis: String,
    lp_std: Vec<String>,
    lr_std: Vec<String>,
    lm_std: Vec<String>,
    lc_std: Vec<String>,
    v: String,
    fuel: String,
    ipc: String,
    index: String,
    result_expected: String,
}

// hex string ("0x..") -> i64 via u64 bit reinterpretation (register/result values
// are 64-bit; OCaml treats them as int64).
fn hex_i64(s: &str) -> i64 {
    let t = s.trim().trim_start_matches("0x").trim_start_matches("0X");
    u64::from_str_radix(t, 16).unwrap_or_else(|e| panic!("bad hex {}: {}", s, e)) as i64
}

#[cfg(all(not(sbpf_no_bigint), not(sbpf_native_int)))]
type ExportInt = BigInt;
#[cfg(sbpf_no_bigint)]
type ExportInt = Int;
#[cfg(sbpf_native_int)]
type ExportInt = RustInt;

// int maps to num_bigint::BigInt under Rust_BigInt_Int_Setup.
#[cfg(all(not(sbpf_no_bigint), not(sbpf_native_int)))]
fn int_of_i64(n: i64) -> BigInt {
    BigInt::from(n)
}

// Rust_Native_Int_Setup keeps values in i128 until arbitrary precision is needed.
#[cfg(sbpf_native_int)]
fn int_of_i64(n: i64) -> RustInt {
    RustInt::from_i128(i128::from(n))
}

// The no-adaptation experiment exports Isabelle's binary Num representation.
#[cfg(sbpf_no_bigint)]
fn num_of_u64(n: u64) -> Num {
    assert!(n > 0);
    if n == 1 {
        Num::One
    } else if n & 1 == 0 {
        Num::Bit0(Box::new(num_of_u64(n >> 1)))
    } else {
        Num::Bit1(Box::new(num_of_u64(n >> 1)))
    }
}

#[cfg(sbpf_no_bigint)]
fn int_of_i64(n: i64) -> Int {
    if n == 0 {
        Int::ZeroInta
    } else if n > 0 {
        Int::Pos(num_of_u64(n as u64))
    } else {
        Int::Neg(num_of_u64(n.unsigned_abs()))
    }
}

fn list_of_hex(xs: &[String]) -> List<ExportInt> {
    let mut acc = List::Nil;
    for x in xs.iter().rev() {
        acc = List::Cons(int_of_i64(hex_i64(x)), Box::new(acc));
    }
    acc
}

#[cfg(not(sbpf_stage2))]
fn run_exported(c: &Case) -> bool {
    step_test(
        list_of_hex(&c.lp_std),
        list_of_hex(&c.lr_std),
        list_of_hex(&c.lm_std),
        list_of_hex(&c.lc_std),
        int_of_i64(hex_i64(&c.v)),
        int_of_i64(hex_i64(&c.fuel)),
        int_of_i64(hex_i64(&c.ipc)),
        int_of_i64(hex_i64(&c.index)),
        int_of_i64(hex_i64(&c.result_expected)),
    )
}

struct BenchCase {
    lp: List<ExportInt>,
    lr: List<ExportInt>,
    lm: List<ExportInt>,
    lc: List<ExportInt>,
    v: ExportInt,
    fuel: ExportInt,
    ipc: ExportInt,
    index: ExportInt,
    expected: ExportInt,
}

impl From<&Case> for BenchCase {
    fn from(c: &Case) -> Self {
        Self {
            lp: list_of_hex(&c.lp_std),
            lr: list_of_hex(&c.lr_std),
            lm: list_of_hex(&c.lm_std),
            lc: list_of_hex(&c.lc_std),
            v: int_of_i64(hex_i64(&c.v)),
            fuel: int_of_i64(hex_i64(&c.fuel)),
            ipc: int_of_i64(hex_i64(&c.ipc)),
            index: int_of_i64(hex_i64(&c.index)),
            expected: int_of_i64(hex_i64(&c.result_expected)),
        }
    }
}

#[cfg(not(sbpf_stage2))]
fn run_bench(c: &BenchCase) -> bool {
    step_test(
        c.lp.clone(),
        c.lr.clone(),
        c.lm.clone(),
        c.lc.clone(),
        c.v.clone(),
        c.fuel.clone(),
        c.ipc.clone(),
        c.index.clone(),
        c.expected.clone(),
    )
}

#[cfg(sbpf_stage2)]
fn run_bench(c: &BenchCase) -> bool {
    step_test(
        &c.lp,
        c.lr.clone(),
        c.lm.clone(),
        &c.lc,
        c.v.clone(),
        &c.fuel,
        c.ipc.clone(),
        c.index.clone(),
        c.expected.clone(),
    )
}

#[cfg(sbpf_stage2)]
fn run_exported(c: &Case) -> bool {
    let lp = list_of_hex(&c.lp_std);
    let lc = list_of_hex(&c.lc_std);
    let fuel = int_of_i64(hex_i64(&c.fuel));
    step_test(
        &lp,
        list_of_hex(&c.lr_std),
        list_of_hex(&c.lm_std),
        &lc,
        int_of_i64(hex_i64(&c.v)),
        &fuel,
        int_of_i64(hex_i64(&c.ipc)),
        int_of_i64(hex_i64(&c.index)),
        int_of_i64(hex_i64(&c.result_expected)),
    )
}

fn main() {
    const GREEN: &str = "\x1b[32m";
    const RED: &str = "\x1b[31m";
    const RESET: &str = "\x1b[0m";

    let path = env::var("CROSS_JSON")
        .expect("set CROSS_JSON to the step-vector json path");
    let file = File::open(&path)
        .unwrap_or_else(|e| panic!("open {}: {}", path, e));
    let cases: Vec<Case> = serde_json::from_reader(BufReader::new(file))
        .expect("parse step json");

    if let Ok(repeats) = env::var("SBPF_BENCH_REPEATS") {
        let repeats = repeats.parse::<usize>()
            .expect("SBPF_BENCH_REPEATS must be a usize");
        let cases: Vec<BenchCase> = cases.iter().map(BenchCase::from).collect();
        assert!(cases.iter().all(run_bench), "warm-up validation failed");
        let start = Instant::now();
        let mut failures = 0usize;
        for _ in 0..repeats {
            for case in &cases {
                if !black_box(run_bench(case)) {
                    failures += 1;
                }
            }
        }
        let seconds = start.elapsed().as_secs_f64();
        assert_eq!(failures, 0);
        let executions = cases.len() * repeats;
        println!(
            "cases={} repeats={} executions={} seconds={:.9} executions_per_second={:.3}",
            cases.len(),
            repeats,
            executions,
            seconds,
            executions as f64 / seconds
        );
        return;
    }

    // A panic in the exported code is a failed case; report it instead of
    // aborting the whole run.
    panic::set_hook(Box::new(|_| {}));

    let mut passed = 0usize;
    let mut failed = 0usize;
    let mut panicked = 0usize;
    for (i, c) in cases.iter().enumerate() {
        let outcome = panic::catch_unwind(AssertUnwindSafe(|| run_exported(c)));
        let (result, note) = match outcome {
            Ok(true) => (true, ""),
            Ok(false) => (false, ""),
            Err(_) => (false, " (panic in exported code)"),
        };
        let color = if result { GREEN } else { RED };
        if result {
            passed += 1;
        } else {
            failed += 1;
            if !note.is_empty() {
                panicked += 1;
            }
        }
        println!(
            "{}{} {:<40} result: {}{}{}{}",
            color,
            i + 1,
            c.dis,
            color,
            result,
            note,
            RESET
        );
    }

    println!("\nSummary (step micro test, Rust export):");
    println!("{}Passed: {}{}", GREEN, passed, RESET);
    println!("{}Failed: {} (of which {} panicked){}", RED, failed, panicked, RESET);
    if failed > 0 {
        exit(1);
    }
}
