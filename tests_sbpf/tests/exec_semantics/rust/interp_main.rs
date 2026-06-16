// Rust <-> OCaml runtime cross-test harness for the exported sBPF interpreter.
//
// This file is copied over the `interp_test` export's src/main.rs by `make sbpf`.
// It feeds the Rust-exported `bpf_interp_test` the SAME inputs the OCaml reference
// uses (tests_sbpf/tests/data/interp_in.json, extracted from test.ml by
// gen_interp_json.py) and asserts each self-checking call returns `true` -- i.e.
// the Rust export agrees, case-for-case, with the OCaml-validated expected values.
//
// The JSON path is taken from the CROSS_JSON env var (set by the Makefile) so the
// harness is independent of cargo's working directory.
#![feature(box_patterns)]
#![allow(non_snake_case)]

pub mod Interp_test;

use crate::Interp_test::{bpf_interp_test, Int, List, Num};
use serde::Deserialize;
use std::env;
use std::fs::File;
use std::io::BufReader;
use std::panic::{self, AssertUnwindSafe};
use std::process::exit;

#[derive(Deserialize)]
struct Case {
    dis: String,
    lp_std: Vec<i64>,
    lm_std: Vec<i64>,
    lc_std: Vec<i64>,
    v: i64,
    fuel: i64,
    result_expected: i64,
    isok: bool,
}

// int64 -> exported Int / Num, mirroring glue.ml's num_of_int / int_of_standard_int.
fn num_of_pos(n: u64) -> Num {
    if n == 1 {
        Num::One
    } else if n % 2 == 0 {
        Num::Bit0(Box::new(num_of_pos(n / 2)))
    } else {
        Num::Bit1(Box::new(num_of_pos(n / 2)))
    }
}

fn int_of_i64(n: i64) -> Int {
    if n == 0 {
        Int::ZeroInta
    } else if n > 0 {
        Int::Pos(num_of_pos(n as u64))
    } else {
        // magnitude of a negative i64 (incl. i64::MIN) always fits in u64
        let mag = (n as i128).unsigned_abs() as u64;
        Int::Neg(num_of_pos(mag))
    }
}

fn list_of_i64s(xs: &[i64]) -> List<Int> {
    let mut acc = List::Nil;
    for &x in xs.iter().rev() {
        acc = List::Cons(int_of_i64(x), Box::new(acc));
    }
    acc
}

fn main() {
    const GREEN: &str = "\x1b[32m";
    const RED: &str = "\x1b[31m";
    const RESET: &str = "\x1b[0m";

    let path = env::var("CROSS_JSON")
        .expect("set CROSS_JSON to the interp_in.json path");
    let file = File::open(&path)
        .unwrap_or_else(|e| panic!("open {}: {}", path, e));
    let cases: Vec<Case> = serde_json::from_reader(BufReader::new(file))
        .expect("parse interp_in.json");

    // Silence default panic output: a panic in the exported code is a divergence
    // from the OCaml reference, which we report as a failed case ourselves.
    panic::set_hook(Box::new(|_| {}));

    let mut passed = 0usize;
    let mut failed = 0usize;
    let mut panicked = 0usize;
    for (i, c) in cases.iter().enumerate() {
        let outcome = panic::catch_unwind(AssertUnwindSafe(|| {
            bpf_interp_test(
                list_of_i64s(&c.lp_std),
                list_of_i64s(&c.lm_std),
                list_of_i64s(&c.lc_std),
                int_of_i64(c.v),
                int_of_i64(c.fuel),
                int_of_i64(c.result_expected),
                c.isok,
            )
        }));
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

    println!("\nSummary (interp cross-test, Rust export vs OCaml reference):");
    println!("{}Passed: {}{}", GREEN, passed, RESET);
    println!("{}Failed: {} (of which {} panicked){}", RED, failed, panicked, RESET);
    if failed > 0 {
        exit(1);
    }
}
