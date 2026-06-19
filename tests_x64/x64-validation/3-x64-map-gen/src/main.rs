use anyhow::{Context, Result};
use rand::{thread_rng, Rng};
use serde::Serialize;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};

#[derive(Debug)]
struct HexI64 {
    value: i64,
    bits: u32,
}

impl Serialize for HexI64 {
    fn serialize<S>(&self, s: S) -> Result<S::Ok, S::Error>
    where S: serde::Serializer,
    {
        let hex_str = match self.bits {
            16 => format!("0x{:04X}", self.value as u16),
            32 => format!("0x{:08X}", self.value as u32),
            _  => format!("0x{:016X}", self.value as u64),
        };
        s.serialize_str(&hex_str)
    }
}

#[derive(Serialize)]
struct TestCase {
    ins: String,
    mode: u32,
    bin: Vec<i64>,
    cr: Vec<i64>,
    ir: Vec<HexI64>,
    mem: Vec<HexI64>,
    cond: bool,
    rd: u8,
    rs: u8,
}

fn parse_numbers(line: &str) -> Vec<i64> {
    line.split_whitespace().filter_map(|s| s.parse::<i64>().ok()).collect()
}

fn manifest_path(relative: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(relative)
}

fn rand_vec_by_mode(n: usize, bits: u32) -> Vec<i64> {
    let mut rng = thread_rng();
    match bits {
        32 => (0..n).map(|_| rng.r#gen::<i32>() as i64).collect(),
        16 => (0..n).map(|_| rng.r#gen::<i16>() as i64).collect(),
        _  => (0..n).map(|_| rng.r#gen::<i64>()).collect(),
    }
}

fn wrap_hex_vec(v: Vec<i64>, bits: u32) -> Vec<HexI64> {
    v.into_iter().map(|x| HexI64 { value: x, bits }).collect()
}

fn is_mem_op(ins: &str) -> bool {
    ins.contains("_rm") || ins.contains("_mr") || ins.contains("_mi")
}

fn uses_flags(ins: &str) -> bool {
    let l = ins.to_ascii_lowercase();
    l.contains("cmp")  || l.contains("cmov") || l.contains("test")
}

fn parse_register(reg: &str) -> u8 {
    match reg {
        "RAX" => 0,  "RBX" => 1,  "RCX" => 2,  "RDX" => 3,
        "RSI" => 4,  "RDI" => 5,  "RBP" => 6,  "RSP" => 7,
        "R8"  => 8,  "R9"  => 9,  "R10" => 10, "R11" => 11,
        "R12" => 12, "R13" => 13, "R14" => 14, "R15" => 15,
        _ => u8::MAX,
    }
}

const DIV_OPS: &[&str] = &["Pdivq_r", "Pdivl_r", "Pidivq_r", "Pidivl_r"];
const SHIFT_OPS: &[&str] = &[
    "Pshlq_r", "Pshrq_r", "Psarq_r", "Pshrl_r", "Pshll_r", "Psarl_r"
];

fn main() -> Result<()> {
    let inp_path = manifest_path("../0-data/step2.in");
    let file = File::open(&inp_path).with_context(|| format!("Cannot open {}", inp_path.display()))?;
    let mut lines = BufReader::new(file).lines();

    let mut cases = Vec::new();

    while let (Some(Ok(ins_line)), Some(Ok(bin_line))) = (lines.next(), lines.next()) {
        let tokens: Vec<&str> = ins_line.split_whitespace().collect();
        let opcode = tokens.get(0).copied().unwrap_or("");
        let bits = match opcode {
            "Paddw_ri" | "Prolw_ri" => 16,
            "Paddl_rr" | "Paddl_ri" | "Psubl_rr" | "Psubl_ri" |
            "Pandl_rr" | "Pandl_ri" | "Porl_rr"  | "Porl_ri"  |
            "Pxorl_rr" | "Pxorl_ri" | "Pmovl_rr" | "Pmovl_ri" |
            "Pshll_r"  | "Pshll_ri" | "Pshrl_r"  | "Pshrl_ri" |
            "Psarl_r"  | "Psarl_ri" | "Prorl_ri" | "Pnegl"    |
            "Pmull_r"  | "Pimull_r" | "Pdivl_r"  | "Pidivl_r" |
            "Pmovsl_rr"| "Pcmovl"   | "Pcdq"     | "Pbswapl"  |
            "Ptestl_rr"| "Ptestl_ri"| "Pcmpl_rr" | "Pcmpl_ri" |
            "Pjcc"     | "Pjmp"      => 32,
            _ => 64,
        };

        let mut ir_raw = rand_vec_by_mode(15, bits);

        // --- DIV/IDIV特判 ---
        let mut rd: u8 = u8::MAX;
        let mut rs: u8 = u8::MAX;

        if DIV_OPS.contains(&opcode) {
            if let Some(regstr) = tokens.get(1) {
                rs = parse_register(regstr);
            }
            let mut rng = thread_rng();
            if bits == 64 {
                if opcode == "Pdivq_r" {
                    let d: u64 = rng.gen_range(1..=u64::MAX);
                    let q: u64 = rng.r#gen();
                    let r: u64 = rng.gen_range(0..d);
                    let dividend = (q as u128) * (d as u128) + (r as u128);
                    ir_raw[0] = dividend as u64 as i64;
                    ir_raw[3] = (dividend >> 64) as u64 as i64;
                    if rs < 15 { ir_raw[rs as usize] = d as i64; }
                } else { // signed
                    let d: i64 = loop { let x = rng.r#gen(); if x != 0 { break x; }};
                    let q: i64 = rng.r#gen();
                    let r: i64 = rng.gen_range(0..d.abs());
                    let dividend = (q as i128) * (d as i128) + (r as i128);
                    ir_raw[0] = dividend as u64 as i64;
                    ir_raw[3] = (dividend >> 64) as u64 as i64;
                    if rs < 15 { ir_raw[rs as usize] = d; }
                }
            } else {
                if opcode == "Pdivl_r" {
                    let d: u32 = rng.gen_range(1..=u32::MAX);
                    let q: u32 = rng.r#gen();
                    let r: u32 = rng.gen_range(0..d);
                    let dividend = (q as u64) * (d as u64) + (r as u64);
                    ir_raw[0] = dividend as u32 as i64;
                    ir_raw[3] = (dividend >> 32) as u32 as i64;
                    if rs < 15 { ir_raw[rs as usize] = d as i64; }
                } else {
                    let d: i32 = loop { let x = rng.r#gen(); if x != 0 { break x; }};
                    let q: i32 = rng.r#gen();
                    let r: i32 = rng.gen_range(0..d.abs());
                    let dividend = (q as i64) * (d as i64) + (r as i64);
                    ir_raw[0] = dividend as u32 as i64;
                    ir_raw[3] = (dividend >> 32) as u32 as i64;
                    if rs < 15 { ir_raw[rs as usize] = d as i64; }
                }
            }
        } else if opcode == "Pmovsl_rr" {
            // PMOVXD: rd = r1, rs = r2
            if let (Some(r1), Some(r2)) = (tokens.get(1), tokens.get(2)) {
                rd = parse_register(r1);
                rs = parse_register(r2);
            }
        }

        if SHIFT_OPS.contains(&opcode) {
            ir_raw[2] = thread_rng().gen_range(0..=255);
        }

        let mut cr_raw = vec![0; 5];
        if opcode == "Pcmovl" || opcode == "Pcmovq" || opcode == "Pjcc" {
            cr_raw = (0..5).map(|_| if thread_rng().gen_bool(0.5) { 1 } else { 0 }).collect();
        }

        let mem_raw = if is_mem_op(&ins_line) {
            rand_vec_by_mode(100, bits)
        } else {
            Vec::new()
        };

        cases.push(TestCase {
            ins: ins_line.clone(),
            mode: bits,
            bin: parse_numbers(&bin_line),
            cr: cr_raw,
            ir: wrap_hex_vec(ir_raw, bits),
            mem: wrap_hex_vec(mem_raw, bits),
            cond: uses_flags(&ins_line),
            rd,
            rs,
        });
    }

    let out_path = manifest_path("../0-data/step3.json");
    let out = File::create(&out_path).with_context(|| format!("Cannot create {}", out_path.display()))?;

    serde_json::to_writer_pretty(out, &cases)
        .with_context(|| format!("Cannot write {}", out_path.display()))?;

    println!("x64 machine state generated → {}", out_path.display());
    Ok(())
}
