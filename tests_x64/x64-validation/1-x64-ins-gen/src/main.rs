use rand::Rng;
use std::env;
use std::fmt;
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq)]
enum Register {
    RAX, RBX, RCX, RDX, RSI, RDI, RBP, RSP,
    R8, R9, R10, R11, R12, R13, R14, 
}
impl fmt::Display for Register {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Register::RAX => write!(f, "RAX"),
            Register::RBX => write!(f, "RBX"),
            Register::RCX => write!(f, "RCX"),
            Register::RDX => write!(f, "RDX"),
            Register::RSI => write!(f, "RSI"),
            Register::RDI => write!(f, "RDI"),
            Register::RBP => write!(f, "RBP"),
            Register::RSP => write!(f, "RSP"),
            Register::R8  => write!(f, "R8"),
            Register::R9  => write!(f, "R9"),
            Register::R10 => write!(f, "R10"),
            Register::R11 => write!(f, "R11"),
            Register::R12 => write!(f, "R12"),
            Register::R13 => write!(f, "R13"),
            Register::R14 => write!(f, "R14"),
        }
    }
}

fn random_register(rng: &mut impl Rng) -> Register {
    match rng.gen_range(0..15) {
        0  => Register::RAX,
        1  => Register::RBX,
        2  => Register::RCX,
        3  => Register::RDX,
        4  => Register::RSI,
        5  => Register::RDI,
        6  => Register::RBP,
        7  => Register::RSP,
        8  => Register::R8,
        9  => Register::R9,
        10 => Register::R10,
        11 => Register::R11,
        12 => Register::R12,
        13 => Register::R13,
        14 => Register::R14,
        _  => unreachable!(),
        /*_  => Register::R15,*/
    }
}

#[allow(dead_code)]
fn random_register_except_rcx(rng: &mut impl Rng) -> Register {
    loop {
        let reg = random_register(rng);
        if let Register::RCX = reg {
            continue;
        }
        return reg;
    }
}

#[allow(dead_code)]
fn random_register_except_rsp_r12(rng: &mut impl Rng) -> Register {
    loop {
        let reg = random_register(rng);
        if reg == Register::RSP || reg == Register::R12 {
            continue;
        }
        return reg;
    }
}


#[allow(dead_code)]
#[derive(Debug, Clone, Copy)]
enum TestCond {
    CondE, CondNe, CondB, CondBe, CondAe, CondA,
    CondL, CondLe, CondGe, CondG, CondP, CondNp,
}
#[allow(dead_code)]
impl fmt::Display for TestCond {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            TestCond::CondE  => "e",
            TestCond::CondNe => "ne",
            TestCond::CondB  => "b",
            TestCond::CondBe => "be",
            TestCond::CondAe => "ae",
            TestCond::CondA  => "a",
            TestCond::CondL  => "l",
            TestCond::CondLe => "le",
            TestCond::CondGe => "ge",
            TestCond::CondG  => "g",
            TestCond::CondP  => "p",
            TestCond::CondNp => "np",
        };
        write!(f, "{}", s)
    }
}
#[allow(dead_code)]
fn random_test_cond(rng: &mut impl rand::Rng) -> TestCond {
    use TestCond::*;
    match rng.gen_range(0..12) {
        0 => CondE,
        1 => CondNe,
        2 => CondB,
        3 => CondBe,
        4 => CondAe,
        5 => CondA,
        6 => CondL,
        7 => CondLe,
        8 => CondGe,
        9 => CondG,
        10 => CondP,
        _ => CondNp,  // case 11
    }
}
#[allow(dead_code)]
#[derive(Debug, Clone, Copy)]
struct AddrMode {
    base: Option<Register>,
    index: Option<(Register, u8)>,
    offset: u32,
}
#[allow(dead_code)]
impl fmt::Display for AddrMode {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let base_str = match self.base {
            Some(reg) => format!("{}", reg),
            None => "None".to_string(),
        };
        let index_str = match self.index {
            Some((reg, scale)) => format!("({}, {})", reg, scale),
            None => "None".to_string(),
        };
        write!(f, "Addrmode {} {} {}", base_str, index_str, self.offset)
    }
}
#[allow(dead_code)]
fn generate_addrmode(rng: &mut impl Rng, allow_index: bool) -> AddrMode {
    let base = Some(random_register_except_rsp_r12(rng));

    let index = if allow_index && rng.gen_bool(0.5) {
        Some((random_register_except_rsp_r12(rng), rng.gen_range(0..=3))) // scale 通常是 0~3 (scale = 2^n)
    } else {
        None
    };

    let offset = rng.gen_range(0..=100);

    AddrMode { base, index, offset }
}

#[allow(dead_code)]
#[derive(Debug, Clone, Copy)]
enum MemChunk {
    M8, M16, M32, M64
}


#[allow(dead_code)]
#[derive(Debug)]
enum Instruction {
    
    Add(Register, Register),
    Sub(Register, Register),
    And(Register, Register),
    Or(Register, Register), 
    Xor(Register, Register),
    Mov(Register, Register),
    Xchg(Register, Register),
    MovImm(Register, i64),  // ocaml int64 cannot handle numbers larger than 2^63-1, so we use i64 here
    ShlImm(Register, u8),
    ShrImm(Register, u8),
    SarImm(Register, u8),
    RorImm(Register, u8),
    Neg(Register),
    Mul(Register),
    Imul(Register),
    Div(Register),
    Idiv(Register),
    Shl(Register),
    Shr(Register),
    Sar(Register),
    Bswap(Register),
    Cqo, // sign-extend RAX into RDX:RAX for division

    Add32(Register, Register),
    Sub32(Register, Register),
    And32(Register, Register),
    Or32(Register, Register), 
    Xor32(Register, Register),
    Mov32(Register, Register),
    Movxd32(Register, Register), 
    MovImm32(Register, u32),
    AddImm32(Register, u32),
    SubImm32(Register, u32),
    AndImm32(Register, u32),
    OrImm32(Register, u32), 
    XorImm32(Register, u32),
    ShlImm32(Register, u8),
    ShrImm32(Register, u8),
    SarImm32(Register, u8),
    RorImm32(Register, u8),
    Neg32(Register),
    Mul32(Register),
    Imul32(Register),
    Div32(Register),
    Idiv32(Register),
    Shl32(Register),
    Shr32(Register),
    Sar32(Register),
    Bswap32(Register),
    Cdq,  // sign-extend EAX into EDX:EAX for division

    AddImm16 (Register, u16),
    RolImm16 (Register, u8),

    Cmov(TestCond, Register, Register),
    Cmov32(TestCond, Register, Register),

    Test(Register, Register),
    TestImm(Register, u32),
    Test32(Register, Register),    
    TestImm32(Register, u32),
    Cmp(Register, Register),
    CmpImm(Register, u32),
    Cmp32(Register, Register),    
    CmpImm32(Register, u32),

    Lea(Register, AddrMode),

    JmpImm32(u32),//Near Jmp
    JccImm32(TestCond, u32), // Conditional Jump

}

impl fmt::Display for Instruction {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Instruction::Add(r1, r2) => write!(f, "Paddq_rr {} {}", r1, r2),
            Instruction::Sub(r1, r2) => write!(f, "Psubq_rr {} {}", r1, r2),
            Instruction::And(r1, r2) => write!(f, "Pandq_rr {} {}", r1, r2),
            Instruction::Or(r1, r2) => write!(f, "Porq_rr {} {}", r1, r2),
            Instruction::Xor(r1, r2) => write!(f, "Pxorq_rr {} {}", r1, r2),
            Instruction::Mov(r1, r2) => write!(f, "Pmovq_rr {} {}", r1, r2),
            Instruction::Xchg(r1, r2) => write!(f, "Pxchgq_rr {} {}", r1, r2),
            Instruction::MovImm(r1, i) => write!(f, "Pmovq_ri {} {}", r1, i),
            Instruction::ShlImm(r, i) => write!(f, "Pshlq_ri {} {}", r, i),
            Instruction::ShrImm(r, i) => write!(f, "Pshrq_ri {} {}", r, i),
            Instruction::SarImm(r, i) => write!(f, "Psarq_ri {} {}", r, i),
            Instruction::RorImm(r, i) => write!(f, "Prorq_ri {} {}", r, i),
            Instruction::Mul(r) => write!(f, "Pmulq_r {}", r),
            Instruction::Imul(r) => write!(f, "Pimulq_r {}", r),
            Instruction::Div(r) => write!(f, "Pdivq_r {}", r),
            Instruction::Idiv(r) => write!(f, "Pidivq_r {}", r),
            Instruction::Neg(r) => write!(f, "Pnegq {}", r),
            Instruction::Shl(r) => write!(f, "Pshlq_r {}", r),
            Instruction::Shr(r) => write!(f, "Pshrq_r {}", r),
            Instruction::Sar(r) => write!(f, "Psarq_r {}", r),
            Instruction::Bswap(r) => write!(f, "Pbswapq {}", r),
            Instruction::Cqo => write!(f, "Pcqo"),

            Instruction::Add32(r1, r2) => write!(f, "Paddl_rr {} {}", r1, r2),
            Instruction::Sub32(r1, r2) => write!(f, "Psubl_rr {} {}", r1, r2),
            Instruction::And32(r1, r2) => write!(f, "Pandl_rr {} {}", r1, r2),
            Instruction::Or32(r1, r2) => write!(f, "Porl_rr {} {}", r1, r2),
            Instruction::Xor32(r1, r2) => write!(f, "Pxorl_rr {} {}", r1, r2),
            Instruction::Mov32(r1, r2) => write!(f, "Pmovl_rr {} {}", r1, r2),
            Instruction::Movxd32(r1, r2) => write!(f, "Pmovsl_rr {} {}", r1, r2),
            Instruction::MovImm32(r1, i) => write!(f, "Pmovl_ri {} {}", r1, i),
            Instruction::AddImm32(r1, i) => write!(f, "Paddl_ri {} {}", r1, i),
            Instruction::SubImm32(r1, i) => write!(f, "Psubl_ri {} {}", r1, i),
            Instruction::AndImm32(r1, i) => write!(f, "Pandl_ri {} {}", r1, i),  
            Instruction::OrImm32(r1, i) => write!(f, "Porl_ri {} {}", r1, i),
            Instruction::XorImm32(r1, i) => write!(f, "Pxorl_ri {} {}", r1, i),                      
            Instruction::ShlImm32(r, i) => write!(f, "Pshll_ri {} {}", r, i),
            Instruction::ShrImm32(r, i) => write!(f, "Pshrl_ri {} {}", r, i),
            Instruction::SarImm32(r, i) => write!(f, "Psarl_ri {} {}", r, i),
            Instruction::RorImm32(r, i) => write!(f, "Prorl_ri {} {}", r, i),
            Instruction::Neg32(r) => write!(f, "Pnegl {}", r),
            Instruction::Mul32(r) => write!(f, "Pmull_r {}", r),
            Instruction::Imul32(r) => write!(f, "Pimull_r {}", r),
            Instruction::Div32(r) => write!(f, "Pdivl_r {}", r),
            Instruction::Idiv32(r) => write!(f, "Pidivl_r {}", r),
            Instruction::Shl32(r) => write!(f, "Pshll_r {}", r),
            Instruction::Shr32(r) => write!(f, "Pshrl_r {}", r),
            Instruction::Sar32(r) => write!(f, "Psarl_r {}", r),
            Instruction::Bswap32(r) => write!(f, "Pbswapl {}", r),
            Instruction::Cdq => write!(f, "Pcdq"),

            Instruction::Cmov(cond, r1, r2) => write!(f, "Pcmovq {} {} {}", cond, r1, r2),
            Instruction::Cmov32(cond, r1, r2) => write!(f, "Pcmovl {} {} {}", cond, r1, r2),

            Instruction::Test(r1, r2) => write!(f, "Ptestq_rr {} {}", r1, r2),
            Instruction::TestImm(r, i) => write!(f, "Ptestq_ri {} {}", r, i),
            Instruction::Test32(r1, r2) => write!(f, "Ptestl_rr {} {}", r1, r2),
            Instruction::TestImm32(r, i) => write!(f, "Ptestl_ri {} {}", r, i),
            Instruction::Cmp(r1, r2) => write!(f, "Pcmpq_rr {} {}", r1, r2),
            Instruction::CmpImm(r, i) => write!(f, "Pcmpq_ri {} {}", r, i),
            Instruction::Cmp32(r1, r2) => write!(f, "Pcmpl_rr {} {}", r1, r2),
            Instruction::CmpImm32(r, i) => write!(f, "Pcmpl_ri {} {}", r, i),

            Instruction::AddImm16(r, i) => write!(f, "Paddw_ri {} {}", r, i),
            Instruction::RolImm16(r, i) => write!(f, "Prolw_ri {} {}", r, i),
            
            Instruction::Lea(r, am) =>  write!(f, "Pleaq {} ({})", r, am),

            Instruction::JmpImm32(rel) => write!(f, "Pjmp {}", rel),
            Instruction::JccImm32(cond, rel) => write!(f, "Pjcc {} {}", cond, rel),

        }
    }
}



fn generate_instruction() -> Instruction {
    use Instruction::*;
    let mut rng = rand::thread_rng();
    match rng.gen_range(0..64) {
        0  => Add(random_register(&mut rng), random_register(&mut rng)),
        1  => Sub(random_register(&mut rng), random_register(&mut rng)),
        2  => And(random_register(&mut rng), random_register(&mut rng)),
        3  => Or(random_register(&mut rng), random_register(&mut rng)),
        4  => Xor(random_register(&mut rng), random_register(&mut rng)),
        5  => Mov(random_register(&mut rng), random_register(&mut rng)),
        6  => Xchg(random_register(&mut rng), random_register(&mut rng)),
        7  => MovImm(random_register(&mut rng), rng.r#gen::<i64>()),
        8  => ShlImm(random_register(&mut rng), rng.r#gen::<u8>()),
        9  => ShrImm(random_register(&mut rng), rng.r#gen::<u8>()),
        10 => SarImm(random_register(&mut rng), rng.r#gen::<u8>()),
        11 => RorImm(random_register(&mut rng), rng.r#gen::<u8>()),
        12 => Mul(random_register(&mut rng)),
        13 => Imul(random_register(&mut rng)),
        14 => Div(random_register(&mut rng)),
        15 => Idiv(random_register(&mut rng)),
        16 => Neg(random_register(&mut rng)),
        17 => Shl(random_register_except_rcx(&mut rng)),
        18 => Shr(random_register_except_rcx(&mut rng)),
        19 => Sar(random_register_except_rcx(&mut rng)),
        20 => Bswap(random_register(&mut rng)),
        21 => Cqo,

        22 => Add32(random_register(&mut rng), random_register(&mut rng)),
        23 => Sub32(random_register(&mut rng), random_register(&mut rng)),
        24 => And32(random_register(&mut rng), random_register(&mut rng)),
        25 => Or32(random_register(&mut rng), random_register(&mut rng)),
        26 => Xor32(random_register(&mut rng), random_register(&mut rng)),
        27 => Mov32(random_register(&mut rng), random_register(&mut rng)),
        28 => Movxd32(random_register(&mut rng), random_register(&mut rng)),
        29 => MovImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        30 => AddImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        31 => SubImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        32 => AndImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        33 => OrImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        34 => XorImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        35 => ShlImm32(random_register(&mut rng), rng.r#gen::<u8>()),
        36 => ShrImm32(random_register(&mut rng), rng.r#gen::<u8>()),
        37 => SarImm32(random_register(&mut rng), rng.r#gen::<u8>()),
        38 => RorImm32(random_register(&mut rng), rng.r#gen::<u8>()),
        39 => Neg32(random_register(&mut rng)),
        40 => Mul32(random_register(&mut rng)),
        41 => Imul32(random_register(&mut rng)),
        42 => Div32(random_register(&mut rng)),
        43 => Idiv32(random_register(&mut rng)),
        44 => Shl32(random_register_except_rcx(&mut rng)),
        45 => Shr32(random_register_except_rcx(&mut rng)),
        46 => Sar32(random_register_except_rcx(&mut rng)),
        47 => Bswap32(random_register(&mut rng)),
        48 => Cdq,

        49 => Cmov(random_test_cond(&mut rng), random_register(&mut rng), random_register(&mut rng)),
        50 => Cmov32(random_test_cond(&mut rng), random_register(&mut rng), random_register(&mut rng)),

        51 => AddImm16(random_register(&mut rng), rng.r#gen::<i16>() as u16),
        52 => RolImm16(random_register(&mut rng), rng.r#gen::<i8>() as u8),
        53  => Lea(random_register(&mut rng), generate_addrmode(&mut rng, false)),
        54 => JmpImm32(rng.gen_range(0..10)),
        55 => JccImm32(random_test_cond(&mut rng), rng.gen_range(0..10)),
        56 => Test(random_register(&mut rng), random_register(&mut rng)),
        57 => TestImm(random_register(&mut rng), rng.r#gen::<u32>()),
        58 => Test32(random_register(&mut rng), random_register(&mut rng)),
        59 => TestImm32(random_register(&mut rng), rng.r#gen::<u32>()),
        60 => Cmp(random_register(&mut rng), random_register(&mut rng)),
        61 => CmpImm(random_register(&mut rng), rng.r#gen::<u32>()),
        62 => Cmp32(random_register(&mut rng), random_register(&mut rng)),
        63 => CmpImm32(random_register(&mut rng), rng.r#gen::<u32>()),


    _   => unreachable!(),
    }
}

fn main() {
    let n = env::args()
        .nth(1)
        .map(|arg| arg.parse::<usize>().unwrap_or_else(|_| panic!("invalid instruction count: {}", arg)))
        .unwrap_or(100000);
    let out_path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../0-data/step1.in");
    let mut file = File::create(&out_path).unwrap();
    for _ in 0..n {
        let instruction = generate_instruction();
        writeln!(file, "{}", instruction).unwrap();
    }
    
    println!("Generated {} x64 instructions in {}", n, out_path.display());
}

        
        /*0  => Add  (random_register(&mut rng), random_register(&mut rng)),
        1  => Sub  (random_register(&mut rng), random_register(&mut rng)),
        2  => And  (random_register(&mut rng), random_register(&mut rng)),
        3  => Or   (random_register(&mut rng), random_register(&mut rng)),
        4  => Xor  (random_register(&mut rng), random_register(&mut rng)),
        5  => Mov  (random_register(&mut rng), random_register(&mut rng)),
        6  => Xchg (random_register(&mut rng), random_register(&mut rng)),
        7  => MovImm (random_register(&mut rng), rng.r#gen::<i64>()),
        8  => Neg  (random_register(&mut rng)),
        9  => Mul   (random_register(&mut rng)),
        10 => Imul  (random_register(&mut rng)),
        11 => Div   (random_register(&mut rng)),
        12 => Idiv  (random_register(&mut rng)),
        13 => Shl    (random_register_except_rcx(&mut rng)),
        14 => Shr    (random_register_except_rcx(&mut rng)),
        15 => Sar    (random_register_except_rcx(&mut rng)),
        16 => ShlImm (random_register(&mut rng), rng.gen_range(0..64) as u8),
        17 => ShrImm (random_register(&mut rng), rng.gen_range(0..64) as u8),
        18 => SarImm (random_register(&mut rng), rng.gen_range(0..64) as u8),


        19 => Add32  (random_register(&mut rng), random_register(&mut rng)),
        20 => Sub32  (random_register(&mut rng), random_register(&mut rng)),
        21 => And32  (random_register(&mut rng), random_register(&mut rng)),
        22 => Or32   (random_register(&mut rng), random_register(&mut rng)),
        23 => Xor32  (random_register(&mut rng), random_register(&mut rng)),
        24 => Mov32  (random_register(&mut rng), random_register(&mut rng)),
        25 => Movxd32(random_register(&mut rng), random_register(&mut rng)),
        26 => MovImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        27 => Neg32  (random_register(&mut rng)),
        28 => AddImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        29 => SubImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        30 => AndImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        31 => OrImm32 (random_register(&mut rng), rng.r#gen::<i32>() as u32),
        32 => XorImm32(random_register(&mut rng), rng.r#gen::<i32>() as u32),
        33 => Shl32   (random_register_except_rcx(&mut rng)),
        34 => Shr32   (random_register_except_rcx(&mut rng)),
        35 => Sar32   (random_register_except_rcx(&mut rng)),
        36 => ShlImm32(random_register(&mut rng), rng.r#gen::<u8>()),
        37 => ShrImm32(random_register(&mut rng), rng.r#gen::<u8>()),
        38 => SarImm32(random_register(&mut rng), rng.r#gen::<u8>()),
        39 => Mul32   (random_register(&mut rng)),
        40 => Imul32  (random_register(&mut rng)),
        41 => Div32   (random_register(&mut rng)),
        42 => Idiv32  (random_register(&mut rng)),
        43 => Cmov(random_test_cond(&mut rng), random_register(&mut rng), random_register(&mut rng)),
        44 => Cmov32(random_test_cond(&mut rng), random_register(&mut rng), random_register(&mut rng)),
        0 => Cqo,
        1 => Cdq, 
        17 => RorImm (random_register(&mut rng), rng.gen_range(0..64) as u8),
        17 => RorImm32 (random_register(&mut rng), rng.gen_range(0..64) as u8)
        0 => AddImm16 (random_register(&mut rng), rng.r#gen::<i16>() as u16),
        1 => RolImm16 (random_register(&mut rng), rng.r#gen::<i8>() as u8),
        0  => Bswap   (random_register(&mut rng)),
        1  => Bswap32   (random_register(&mut rng)),*/
