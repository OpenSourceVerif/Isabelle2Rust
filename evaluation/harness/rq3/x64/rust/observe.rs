// Performance and correctness glue appended only to copied benchmark crates.
// Timed calls return unit after black-boxing the raw generated outcome, so
// state observation and comparison are excluded from the semantic timing.

fn x64_observed_int(value: i128) -> u64 {
    value as u64
}

fn x64_observed_word<W>(word: crate::Rust_Word::RustWord<W>) -> u64 {
    x64_observed_int(crate::Rust_Word::to_int(word))
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

fn x64_observe_outcome(outcome: Outcome) -> Vec<u64> {
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

#[cfg(not(x64_borrowed))]
pub fn x64_step_observe(
    bits: i128,
    lbin: List<i128>,
    lc: List<i128>,
    lr: List<i128>,
    lm: List<i128>,
) -> Vec<u64> {
    x64_observe_outcome(x64_step_test(bits, lbin, lc, lr, lm))
}

#[cfg(x64_borrowed)]
pub fn x64_step_observe(
    bits: i128,
    lbin: &List<i128>,
    lc: &List<i128>,
    lr: &List<i128>,
    lm: &List<i128>,
) -> Vec<u64> {
    x64_observe_outcome(x64_step_test(bits, lbin, lc, lr, lm))
}

#[cfg(not(x64_borrowed))]
pub fn x64_step_benchmark(
    bits: i128,
    lbin: List<i128>,
    lc: List<i128>,
    lr: List<i128>,
    lm: List<i128>,
) {
    std::hint::black_box(x64_step_test(bits, lbin, lc, lr, lm));
}

#[cfg(x64_borrowed)]
pub fn x64_step_benchmark(
    bits: i128,
    lbin: &List<i128>,
    lc: &List<i128>,
    lr: &List<i128>,
    lm: &List<i128>,
) {
    std::hint::black_box(x64_step_test(bits, lbin, lc, lr, lm));
}
