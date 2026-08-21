// Rust-only observation glue appended to the generated module in `_build`.
//
// `x64_step_test` returns an `Outcome` containing register and memory closures.
// Its register constructors are private implementation details, so an external
// test binary cannot enumerate the observable state.  This adapter calls the
// raw export unchanged and extracts exactly the state slice used by the fixed
// OCaml runner: PC, RAX through R14, then ZF/CF/PF/SF/OF.  It intentionally
// ignores the returned memory closure because random memory cases are not part
// of the current validation scope.

fn x64_observed_word<W>(word: crate::Rust_Word::RustWord<W>) -> u64 {
    let (_, digits) = crate::Rust_Word::to_bigint(word).to_u64_digits();
    digits.first().copied().unwrap_or(0)
}

fn x64_observed_val(value: Val) -> u64 {
    match value {
        Val::Vundef => 0,
        Val::Vbyte(word) => x64_observed_word(word),
        Val::Vshort(word) => x64_observed_word(word),
        Val::Vint(word) => x64_observed_word(word),
        Val::Vlong(word) => x64_observed_word(word),
    }
}

pub fn x64_step_observe(
    bits: BigInt,
    lbin: List<BigInt>,
    lc: List<BigInt>,
    lr: List<BigInt>,
    lm: List<BigInt>,
) -> Vec<u64> {
    let outcome = x64_step_test(bits, lbin, lc, lr, lm);
    let registers = match outcome {
        Outcome::Stuck => return Vec::new(),
        Outcome::Next(registers, _) => registers,
    };
    let observable = vec![
        Preg::PC,
        Preg::IR(Ireg::RAX),
        Preg::IR(Ireg::RBX),
        Preg::IR(Ireg::RCX),
        Preg::IR(Ireg::RDX),
        Preg::IR(Ireg::RSI),
        Preg::IR(Ireg::RDI),
        Preg::IR(Ireg::RBP),
        Preg::IR(Ireg::RSP),
        Preg::IR(Ireg::R8),
        Preg::IR(Ireg::R9),
        Preg::IR(Ireg::R10),
        Preg::IR(Ireg::R11),
        Preg::IR(Ireg::R12),
        Preg::IR(Ireg::R13),
        Preg::IR(Ireg::R14),
        Preg::CR(Crbit::ZF),
        Preg::CR(Crbit::CF),
        Preg::CR(Crbit::PF),
        Preg::CR(Crbit::SF),
        Preg::CR(Crbit::OF),
    ];
    observable
        .into_iter()
        .map(|register| x64_observed_val(registers(register)))
        .collect()
}
