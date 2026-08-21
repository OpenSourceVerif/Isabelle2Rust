//! CPU cross-check adapter for the raw Isabelle/Rust `x64_step_test` export.
//!
//! JSON parsing, state slicing, and diagnostics are test infrastructure.  The
//! semantic call itself goes through `x64_step_observe`, which is appended only
//! to the `_build` copy and delegates directly to the unchanged raw export.

use isabelle_exported::X64_step_test::{List, x64_step_observe};
use num_bigint::BigInt;
use serde::Deserialize;
use std::env;
use std::fs::File;
use std::io::BufReader;
use std::panic::{self, AssertUnwindSafe};
use std::process::ExitCode;

#[derive(Deserialize)]
struct Case {
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

fn expected_bits(text: &str) -> u64 {
    signed_bits(text) as u64
}

fn list_of_i64(values: &[i64]) -> List<BigInt> {
    let mut result = List::Nil;
    for value in values.iter().rev() {
        result = List::Cons(BigInt::from(*value), Box::new(result));
    }
    result
}

fn list_of_bits(values: &[String]) -> List<BigInt> {
    let values = values
        .iter()
        .map(|value| signed_bits(value))
        .collect::<Vec<_>>();
    list_of_i64(&values)
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

fn comparable(case: &Case, values: &[u64]) -> Vec<u64> {
    if !case.cond {
        values.iter().take(16).copied().collect()
    } else if cmp_or_test(&case.ins) {
        // PF (index 18) is Vundef in the current Isabelle model.  Preserve the
        // existing OCaml rule by comparing ZF/CF and SF/OF around that slot.
        values
            .iter()
            .take(18)
            .chain(values.iter().skip(19).take(2))
            .copied()
            .collect()
    } else {
        values.iter().take(21).copied().collect()
    }
}

fn render(values: &[u64]) -> String {
    values
        .iter()
        .map(|value| format!("0x{value:016x}"))
        .collect::<Vec<_>>()
        .join("; ")
}

fn main() -> ExitCode {
    let path = env::var("X64_STEPPER_INPUT")
        .expect("X64_STEPPER_INPUT must name the CPU step4.json oracle");
    let cases: Vec<Case> =
        serde_json::from_reader(BufReader::new(File::open(&path).expect("open step4.json")))
            .expect("parse step4.json");

    // A panic in generated semantics is one failed vector and should not hide
    // later mismatches.  Suppress the default duplicate panic diagnostics.
    panic::set_hook(Box::new(|_| {}));
    let mut passed = 0usize;
    let mut failed = 0usize;
    let mut panicked = 0usize;
    for case in &cases {
        let actual = panic::catch_unwind(AssertUnwindSafe(|| {
            x64_step_observe(
                BigInt::from(case.mode),
                list_of_i64(&case.bin),
                list_of_i64(&case.cr),
                list_of_bits(&case.ir),
                list_of_bits(&case.mem),
            )
        }));
        let expected = case
            .expected
            .iter()
            .map(|value| expected_bits(value))
            .collect::<Vec<_>>();
        let ok = match &actual {
            Ok(actual) => {
                let expected = comparable(case, &expected);
                let actual = comparable(case, actual);
                (expected.first() == Some(&u64::MAX) && actual.is_empty()) || expected == actual
            }
            Err(_) => false,
        };
        if ok {
            passed += 1;
        } else {
            failed += 1;
            match actual {
                Ok(actual) => eprintln!(
                    "FAIL {}\n  CPU : [{}]\n  Rust: [{}]",
                    case.ins,
                    render(&expected),
                    render(&actual),
                ),
                Err(_) => {
                    panicked += 1;
                    eprintln!("FAIL {}\n  Rust export panicked", case.ins);
                }
            }
        }
    }

    println!("Rust semantics vs CPU: {passed} passed / {failed} failed ({panicked} panicked)");
    if failed == 0 {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
