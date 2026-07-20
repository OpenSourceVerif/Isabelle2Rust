// Rust runtime macro-test harness for the exported SBPF interpreter.
//
// This file is copied over the `interp_test` export's src/main.rs by `make macro_sbpf`.
// It feeds the Rust-exported `bpf_interp_test` the local macro inputs from
// tests_sbpf/tests/data/interp_in.json (extracted from sbpf_ocaml/test.ml by
// the shared gen_interp_json.py) and asserts each self-checking call returns
// `true`.
//
// The JSON path is taken from the CROSS_JSON env var (set by the Makefile) so the
// harness is independent of cargo's working directory.
#![allow(non_snake_case)]

use isabelle_exported::Interp_test::{bpf_interp_test, List};
#[cfg(sbpf_no_bigint)]
use isabelle_exported::Interp_test::{Int, Num};
#[cfg(sbpf_native_int)]
use isabelle_exported::Rust_Native_Int::RustInt;
#[cfg(all(not(sbpf_no_bigint), not(sbpf_native_int)))]
use num_bigint::BigInt;
use std::env;
use std::fs;
use std::hint::black_box;
use std::io::{self, Write};
use std::panic::{self, AssertUnwindSafe};
use std::process::exit;
use std::time::Instant;

#[cfg(all(sbpf_no_bigint, sbpf_native_int))]
compile_error!("sbpf_no_bigint and sbpf_native_int are mutually exclusive");

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

struct JsonParser<'a> {
    input: &'a [u8],
    pos: usize,
}

impl<'a> JsonParser<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            input: input.as_bytes(),
            pos: 0,
        }
    }

    fn skip_ws(&mut self) {
        while self.pos < self.input.len() && self.input[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }

    fn expect(&mut self, expected: u8) {
        self.skip_ws();
        let got = self.input.get(self.pos).copied();
        if got != Some(expected) {
            panic!(
                "expected '{}' at byte {}, got {:?}",
                expected as char,
                self.pos,
                got.map(|b| b as char)
            );
        }
        self.pos += 1;
    }

    fn consume(&mut self, expected: u8) -> bool {
        self.skip_ws();
        if self.input.get(self.pos) == Some(&expected) {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn parse_string(&mut self) -> String {
        self.expect(b'"');
        let mut out = String::new();
        while self.pos < self.input.len() {
            let b = self.input[self.pos];
            self.pos += 1;
            match b {
                b'"' => return out,
                b'\\' => {
                    let esc = self.input[self.pos];
                    self.pos += 1;
                    match esc {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let hex = std::str::from_utf8(&self.input[self.pos..self.pos + 4])
                                .expect("utf8 in unicode escape");
                            self.pos += 4;
                            let code = u32::from_str_radix(hex, 16)
                                .expect("hex unicode escape");
                            out.push(char::from_u32(code).unwrap_or('\u{fffd}'));
                        }
                        other => panic!("bad string escape: {}", other as char),
                    }
                }
                other => out.push(other as char),
            }
        }
        panic!("unterminated string")
    }

    fn parse_i64(&mut self) -> i64 {
        self.skip_ws();
        let start = self.pos;
        if self.input.get(self.pos) == Some(&b'-') {
            self.pos += 1;
        }
        while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() {
            self.pos += 1;
        }
        let s = std::str::from_utf8(&self.input[start..self.pos]).expect("utf8 number");
        s.parse::<i64>().expect("i64 number")
    }

    fn parse_bool(&mut self) -> bool {
        self.skip_ws();
        if self.input[self.pos..].starts_with(b"true") {
            self.pos += 4;
            true
        } else if self.input[self.pos..].starts_with(b"false") {
            self.pos += 5;
            false
        } else {
            panic!("expected bool at byte {}", self.pos)
        }
    }

    fn parse_i64_array(&mut self) -> Vec<i64> {
        self.expect(b'[');
        let mut xs = Vec::new();
        if self.consume(b']') {
            return xs;
        }
        loop {
            xs.push(self.parse_i64());
            if self.consume(b',') {
                continue;
            }
            self.expect(b']');
            return xs;
        }
    }

    fn parse_case(&mut self) -> Case {
        let mut dis = String::new();
        let mut lp_std = Vec::new();
        let mut lm_std = Vec::new();
        let mut lc_std = Vec::new();
        let mut v = 0;
        let mut fuel = 0;
        let mut result_expected = 0;
        let mut isok = false;

        self.expect(b'{');
        loop {
            if self.consume(b'}') {
                break;
            }
            let key = self.parse_string();
            self.expect(b':');
            match key.as_str() {
                "dis" => dis = self.parse_string(),
                "lp_std" => lp_std = self.parse_i64_array(),
                "lm_std" => lm_std = self.parse_i64_array(),
                "lc_std" => lc_std = self.parse_i64_array(),
                "v" => v = self.parse_i64(),
                "fuel" => fuel = self.parse_i64(),
                "result_expected" => result_expected = self.parse_i64(),
                "isok" => isok = self.parse_bool(),
                _ => panic!("unexpected case field: {}", key),
            }
            if self.consume(b',') {
                continue;
            }
            self.expect(b'}');
            break;
        }

        Case {
            dis,
            lp_std,
            lm_std,
            lc_std,
            v,
            fuel,
            result_expected,
            isok,
        }
    }

    fn parse_cases(&mut self) -> Vec<Case> {
        self.expect(b'[');
        let mut cases = Vec::new();
        if self.consume(b']') {
            return cases;
        }
        loop {
            cases.push(self.parse_case());
            if self.consume(b',') {
                continue;
            }
            self.expect(b']');
            return cases;
        }
    }
}

fn read_cases(path: &str) -> Vec<Case> {
    let src = fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("read {}: {}", path, e));
    JsonParser::new(&src).parse_cases()
}

#[cfg(all(not(sbpf_no_bigint), not(sbpf_native_int)))]
type ExportInt = BigInt;
#[cfg(sbpf_no_bigint)]
type ExportInt = Int;
#[cfg(sbpf_native_int)]
type ExportInt = RustInt;

// int64 -> exported BigInt when the BigInt setup is active.
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

fn list_of_i64s(xs: &[i64]) -> List<ExportInt> {
    let mut acc = List::Nil;
    for &x in xs.iter().rev() {
        acc = List::Cons(int_of_i64(x), Box::new(acc));
    }
    acc
}

#[cfg(not(sbpf_stage2))]
fn run_exported(c: &Case) -> bool {
    bpf_interp_test(
        list_of_i64s(&c.lp_std),
        list_of_i64s(&c.lm_std),
        list_of_i64s(&c.lc_std),
        int_of_i64(c.v),
        int_of_i64(c.fuel),
        int_of_i64(c.result_expected),
        c.isok,
    )
}

#[cfg(sbpf_stage2)]
fn run_exported(c: &Case) -> bool {
    let lc = list_of_i64s(&c.lc_std);
    bpf_interp_test(
        list_of_i64s(&c.lp_std),
        list_of_i64s(&c.lm_std),
        &lc,
        int_of_i64(c.v),
        int_of_i64(c.fuel),
        int_of_i64(c.result_expected),
        c.isok,
    )
}

fn main() {
    const GREEN: &str = "\x1b[32m";
    const RED: &str = "\x1b[31m";
    const RESET: &str = "\x1b[0m";

    let path = env::var("CROSS_JSON")
        .expect("set CROSS_JSON to the interp_in.json path");
    let cases = read_cases(&path);
    if env::var("SBPF_BENCH").as_deref() == Ok("1") {
        assert!(cases.iter().all(run_exported), "warm-up validation failed");
        let start = Instant::now();
        let failures = cases.iter()
            .filter(|case| !black_box(run_exported(case)))
            .count();
        let seconds = start.elapsed().as_secs_f64();
        assert_eq!(failures, 0);
        println!(
            "cases={} seconds={:.9} cases_per_second={:.3}",
            cases.len(),
            seconds,
            cases.len() as f64 / seconds
        );
        return;
    }
    let case_index = env::var("CROSS_CASE_INDEX")
        .ok()
        .map(|s| s.parse::<usize>().expect("CROSS_CASE_INDEX must be a usize"));

    // Silence default panic output: a panic in the exported code is a failed
    // macro case, which we report ourselves.
    panic::set_hook(Box::new(|_| {}));

    let mut passed = 0usize;
    let mut failed = 0usize;
    let mut panicked = 0usize;
    for (i, c) in cases.iter().enumerate() {
        if let Some(target) = case_index {
            if i != target {
                continue;
            }
        }
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
        io::stdout().flush().ok();
    }

    if case_index.is_none() {
        println!("\nSummary (interp macro test, Rust export):");
        println!("{}Passed: {}{}", GREEN, passed, RESET);
        println!("{}Failed: {} (of which {} panicked){}", RED, failed, panicked, RESET);
    }
    if failed > 0 {
        exit(1);
    }
}
