// Rust <-> OCaml runtime cross-test harness for the exported sBPF single-step
// semantics.  Copied over the `step_test` export's src/main.rs by `make sbpf`.
//
// Feeds the Rust-exported `step_test` the OCaml-reference step vectors
// (tests_sbpf/tests/data/ocaml_in.json, whose ipc/result_expected were produced by
// the OCaml reference) and asserts each self-checking call returns `true`.
//
// Best-effort: the `step_test` Rust export currently has unresolved compile issues
// (word phantom-type machinery + closure boxing), so this may not build yet. It
// will run green automatically once those are fixed. JSON path via CROSS_JSON.
#![feature(box_patterns)]
#![allow(non_snake_case)]

pub mod Step_test;

use crate::Step_test::{step_test, List};
use num_bigint::BigInt;
use serde::Deserialize;
use std::env;
use std::fs::File;
use std::io::BufReader;
use std::panic::{self, AssertUnwindSafe};
use std::process::exit;

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

// int maps to num_bigint::BigInt under Rust_BigInt_Nat_Setup.
fn int_of_i64(n: i64) -> BigInt {
    BigInt::from(n)
}

fn list_of_hex(xs: &[String]) -> List<BigInt> {
    let mut acc = List::Nil;
    for x in xs.iter().rev() {
        acc = List::Cons(int_of_i64(hex_i64(x)), Box::new(acc));
    }
    acc
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

    // A panic in the exported code is a divergence from the OCaml reference; we
    // report it as a failed case rather than aborting the whole run.
    panic::set_hook(Box::new(|_| {}));

    let mut passed = 0usize;
    let mut failed = 0usize;
    let mut panicked = 0usize;
    for (i, c) in cases.iter().enumerate() {
        let outcome = panic::catch_unwind(AssertUnwindSafe(|| {
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

    println!("\nSummary (step cross-test, Rust export vs OCaml reference):");
    println!("{}Passed: {}{}", GREEN, passed, RESET);
    println!("{}Failed: {} (of which {} panicked){}", RED, failed, panicked, RESET);
    if failed > 0 {
        exit(1);
    }
}
