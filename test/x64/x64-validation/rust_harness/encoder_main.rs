//! Correctness adapter for the raw Isabelle/Rust `x64_encode` export.
//!
//! The binary parses the same textual instruction language consumed by the
//! fixed OCaml runner, calls the unwrapped exported function, and compares the
//! resulting HOL `option (word8 list)` against every byte line in `step2.in`.
//! Parsing and reporting intentionally live outside the generated module so
//! the raw export remains a performance-comparison baseline.

use isabelle_exported::Rust_Word::{self, Bit0, Num1, RustWord, WordWidth};
use isabelle_exported::X64_encode::{
    Addrmode, Instruction, Ireg, List, Option as HolOption, Testcond, x64_encode,
};
use num_bigint::BigInt;
use num_traits::ToPrimitive as _;
use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::process::ExitCode;

type W1 = Num1;
type W2 = Bit0<W1>;
type W4 = Bit0<W2>;
type W8 = Bit0<W4>;
type W16 = Bit0<W8>;
type W32 = Bit0<W16>;
type W64 = Bit0<W32>;

fn word<W: WordWidth>(text: &str) -> Result<RustWord<W>, String> {
    text.parse::<BigInt>()
        .map(RustWord::from_bigint)
        .map_err(|error| format!("invalid integer {text:?}: {error}"))
}

fn register(text: &str) -> Result<Ireg, String> {
    match text {
        "RAX" => Ok(Ireg::RAX),
        "RBX" => Ok(Ireg::RBX),
        "RCX" => Ok(Ireg::RCX),
        "RDX" => Ok(Ireg::RDX),
        "RSI" => Ok(Ireg::RSI),
        "RDI" => Ok(Ireg::RDI),
        "RBP" => Ok(Ireg::RBP),
        "RSP" => Ok(Ireg::RSP),
        "R8" => Ok(Ireg::R8),
        "R9" => Ok(Ireg::R9),
        "R10" => Ok(Ireg::R10),
        "R11" => Ok(Ireg::R11),
        "R12" => Ok(Ireg::R12),
        "R13" => Ok(Ireg::R13),
        "R14" => Ok(Ireg::R14),
        "R15" => Ok(Ireg::R15),
        _ => Err(format!("unknown register {text:?}")),
    }
}

fn condition(text: &str) -> Result<Testcond, String> {
    match text {
        "e" => Ok(Testcond::CondE),
        "ne" => Ok(Testcond::CondNe),
        "b" => Ok(Testcond::CondB),
        "be" => Ok(Testcond::CondBe),
        "ae" => Ok(Testcond::CondAe),
        "a" => Ok(Testcond::CondA),
        "l" => Ok(Testcond::CondL),
        "le" => Ok(Testcond::CondLe),
        "ge" => Ok(Testcond::CondGe),
        "g" => Ok(Testcond::CondG),
        "p" => Ok(Testcond::CondP),
        "np" => Ok(Testcond::CondNp),
        _ => Err(format!("unknown condition {text:?}")),
    }
}

fn binary_register(opcode: &str, rd: Ireg, rs: Ireg) -> Result<Instruction, String> {
    match opcode {
        "Paddq_rr" => Ok(Instruction::PaddqRr(rd, rs)),
        "Psubq_rr" => Ok(Instruction::PsubqRr(rd, rs)),
        "Pandq_rr" => Ok(Instruction::PandqRr(rd, rs)),
        "Porq_rr" => Ok(Instruction::PorqRr(rd, rs)),
        "Pxorq_rr" => Ok(Instruction::PxorqRr(rd, rs)),
        "Pmovq_rr" => Ok(Instruction::PmovqRr(rd, rs)),
        "Pxchgq_rr" => Ok(Instruction::PxchgqRr(rd, rs)),
        "Paddl_rr" => Ok(Instruction::PaddlRr(rd, rs)),
        "Psubl_rr" => Ok(Instruction::PsublRr(rd, rs)),
        "Pandl_rr" => Ok(Instruction::PandlRr(rd, rs)),
        "Porl_rr" => Ok(Instruction::PorlRr(rd, rs)),
        "Pxorl_rr" => Ok(Instruction::PxorlRr(rd, rs)),
        "Pmovl_rr" => Ok(Instruction::PmovlRr(rd, rs)),
        "Pmovsl_rr" => Ok(Instruction::PmovslRr(rd, rs)),
        "Ptestq_rr" => Ok(Instruction::PtestqRr(rd, rs)),
        "Ptestl_rr" => Ok(Instruction::PtestlRr(rd, rs)),
        "Pcmpq_rr" => Ok(Instruction::PcmpqRr(rd, rs)),
        "Pcmpl_rr" => Ok(Instruction::PcmplRr(rd, rs)),
        _ => Err(format!("unsupported register-register opcode {opcode:?}")),
    }
}

fn immediate(opcode: &str, rd: Ireg, value: &str) -> Result<Instruction, String> {
    match opcode {
        "Pmovq_ri" => Ok(Instruction::PmovqRi(rd, word::<W64>(value)?)),
        "Pmovl_ri" => Ok(Instruction::PmovlRi(rd, word::<W32>(value)?)),
        "Paddl_ri" => Ok(Instruction::PaddlRi(rd, word::<W32>(value)?)),
        "Psubl_ri" => Ok(Instruction::PsublRi(rd, word::<W32>(value)?)),
        "Pandl_ri" => Ok(Instruction::PandlRi(rd, word::<W32>(value)?)),
        "Porl_ri" => Ok(Instruction::PorlRi(rd, word::<W32>(value)?)),
        "Pxorl_ri" => Ok(Instruction::PxorlRi(rd, word::<W32>(value)?)),
        "Ptestq_ri" => Ok(Instruction::PtestqRi(rd, word::<W32>(value)?)),
        "Ptestl_ri" => Ok(Instruction::PtestlRi(rd, word::<W32>(value)?)),
        "Pcmpq_ri" => Ok(Instruction::PcmpqRi(rd, word::<W32>(value)?)),
        "Pcmpl_ri" => Ok(Instruction::PcmplRi(rd, word::<W32>(value)?)),
        "Paddw_ri" => Ok(Instruction::PaddwRi(rd, word::<W16>(value)?)),
        "Pshlq_ri" => Ok(Instruction::PshlqRi(rd, word::<W8>(value)?)),
        "Pshrq_ri" => Ok(Instruction::PshrqRi(rd, word::<W8>(value)?)),
        "Psarq_ri" => Ok(Instruction::PsarqRi(rd, word::<W8>(value)?)),
        "Prorq_ri" => Ok(Instruction::ProrqRi(rd, word::<W8>(value)?)),
        "Pshll_ri" => Ok(Instruction::PshllRi(rd, word::<W8>(value)?)),
        "Pshrl_ri" => Ok(Instruction::PshrlRi(rd, word::<W8>(value)?)),
        "Psarl_ri" => Ok(Instruction::PsarlRi(rd, word::<W8>(value)?)),
        "Prorl_ri" => Ok(Instruction::ProrlRi(rd, word::<W8>(value)?)),
        "Prolw_ri" => Ok(Instruction::ProlwRi(rd, word::<W8>(value)?)),
        _ => Err(format!("unsupported register-immediate opcode {opcode:?}")),
    }
}

fn unary(opcode: &str, rd: Ireg) -> Result<Instruction, String> {
    match opcode {
        "Pmulq_r" => Ok(Instruction::PmulqR(rd)),
        "Pimulq_r" => Ok(Instruction::PimulqR(rd)),
        "Pdivq_r" => Ok(Instruction::PdivqR(rd)),
        "Pidivq_r" => Ok(Instruction::PidivqR(rd)),
        "Pnegq" => Ok(Instruction::Pnegq(rd)),
        "Pshlq_r" => Ok(Instruction::PshlqR(rd)),
        "Pshrq_r" => Ok(Instruction::PshrqR(rd)),
        "Psarq_r" => Ok(Instruction::PsarqR(rd)),
        "Pbswapq" => Ok(Instruction::Pbswapq(rd)),
        "Pmull_r" => Ok(Instruction::PmullR(rd)),
        "Pimull_r" => Ok(Instruction::PimullR(rd)),
        "Pdivl_r" => Ok(Instruction::PdivlR(rd)),
        "Pidivl_r" => Ok(Instruction::PidivlR(rd)),
        "Pnegl" => Ok(Instruction::Pnegl(rd)),
        "Pshll_r" => Ok(Instruction::PshllR(rd)),
        "Pshrl_r" => Ok(Instruction::PshrlR(rd)),
        "Psarl_r" => Ok(Instruction::PsarlR(rd)),
        "Pbswapl" => Ok(Instruction::Pbswapl(rd)),
        _ => Err(format!("unsupported unary opcode {opcode:?}")),
    }
}

fn instruction(line: &str) -> Result<Instruction, String> {
    let tokens: Vec<&str> = line.split_whitespace().collect();
    match tokens.as_slice() {
        ["Pcdq"] => Ok(Instruction::Pcdq),
        ["Pcqo"] => Ok(Instruction::Pcqo),
        ["Pjmp", displacement] => Ok(Instruction::Pjmp(word::<W32>(displacement)?)),
        ["Pjcc", cond, displacement] => Ok(Instruction::Pjcc(
            condition(cond)?,
            word::<W32>(displacement)?,
        )),
        [opcode @ ("Pcmovq" | "Pcmovl"), cond, rd, rs] => {
            let values = (condition(cond)?, register(rd)?, register(rs)?);
            match (*opcode, values) {
                ("Pcmovq", (cc, dst, src)) => Ok(Instruction::Pcmovq(cc, dst, src)),
                ("Pcmovl", (cc, dst, src)) => Ok(Instruction::Pcmovl(cc, dst, src)),
                _ => unreachable!(),
            }
        }
        // The current random generator emits base-only address modes as
        // `(Addrmode <base> None <disp>)`.  Index-bearing and memory cases are
        // deliberately outside the present non-memory validation scope.
        ["Pleaq", rd, "(Addrmode", base, "None", displacement] => {
            let displacement = displacement
                .strip_suffix(')')
                .ok_or_else(|| format!("unterminated address mode in {line:?}"))?;
            let base = if *base == "None" {
                HolOption::None
            } else {
                HolOption::Some(register(base)?)
            };
            Ok(Instruction::Pleaq(
                register(rd)?,
                Addrmode::Addrmode(base, HolOption::None, word::<W32>(displacement)?),
            ))
        }
        [opcode, operand] => unary(opcode, register(operand)?),
        [opcode, first, second] => {
            let rd = register(first)?;
            if let Ok(rs) = register(second) {
                binary_register(opcode, rd, rs)
            } else {
                immediate(opcode, rd, second)
            }
        }
        _ => Err(format!("unsupported instruction syntax {line:?}")),
    }
}

fn bytes(mut list: List<RustWord<W8>>) -> Vec<u8> {
    let mut result = Vec::new();
    loop {
        match list {
            List::Nil => return result,
            List::Cons(value, tail) => {
                result.push(
                    Rust_Word::to_bigint(value)
                        .to_u8()
                        .expect("exported word8 must fit u8"),
                );
                list = *tail;
            }
        }
    }
}

fn main() -> ExitCode {
    let path = env::var("X64_ENCODER_INPUT")
        .expect("X64_ENCODER_INPUT must name the OCaml step2.in oracle");
    let lines: Vec<String> = BufReader::new(File::open(&path).expect("open step2.in"))
        .lines()
        .collect::<Result<_, _>>()
        .expect("read step2.in");
    if lines.len() % 2 != 0 {
        eprintln!("ERROR: {path} contains an unmatched instruction line");
        return ExitCode::FAILURE;
    }

    let mut passed = 0usize;
    let mut failed = 0usize;
    for pair in lines.chunks_exact(2) {
        let line = pair[0].trim();
        let expected = pair[1]
            .split_whitespace()
            .map(|text| text.parse::<u8>().expect("OCaml byte must fit u8"))
            .collect::<Vec<_>>();
        let actual = instruction(line).and_then(|ins| match x64_encode(ins) {
            HolOption::Some(encoded) => Ok(bytes(encoded)),
            HolOption::None => Err(format!("raw x64_encode returned None for {line:?}")),
        });
        match actual {
            Ok(actual) if actual == expected => passed += 1,
            Ok(actual) => {
                failed += 1;
                eprintln!("FAIL {line}\n  OCaml: {expected:?}\n  Rust : {actual:?}");
            }
            Err(error) => {
                failed += 1;
                eprintln!("FAIL {line}\n  {error}");
            }
        }
    }

    println!("Rust encoder cross-check: {passed} passed / {failed} failed");
    if failed == 0 {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
