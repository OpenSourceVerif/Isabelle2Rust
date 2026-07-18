use rustlightast::*;

/// Summary of target-aware BigInt shift lowering.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct BigIntShiftAnalysis {
    pub push_bit_methods: usize,
    pub drop_bit_methods: usize,
    pub mask_methods: usize,
}

/// Lower Isabelle's generic `SemiringBitOperations` implementation for
/// `num_bigint::BigInt` to the corresponding native BigInt shift operators.
///
/// Stage 1 has already resolved the source type-class instance at this point,
/// so this pass deliberately matches the concrete Rust trait implementation
/// instead of rewriting arbitrary multiplication or division expressions.
pub fn lower_bigint_shifts(module: &mut RustModule) -> BigIntShiftAnalysis {
    let mut analysis = BigIntShiftAnalysis::default();
    lower_module(module, &mut analysis);
    analysis
}

fn lower_module(module: &mut RustModule, analysis: &mut BigIntShiftAnalysis) {
    for item in &mut module.items {
        match item {
            Item::Impl(impl_block) if is_bigint_bit_operations_impl(impl_block) => {
                lower_impl(impl_block, analysis);
            }
            Item::Mod(inner) => lower_module(inner, analysis),
            _ => {}
        }
    }
}

fn is_bigint_bit_operations_impl(impl_block: &ImplBlock) -> bool {
    type_name(&impl_block.target) == Some("BigInt")
        && impl_block.trait_impl.as_ref().and_then(type_name) == Some("SemiringBitOperations")
}

fn type_name(ty: &Type) -> Option<&str> {
    match ty {
        Type::Named(name) => name.rsplit("::").next(),
        Type::Path(path) => path.last().map(String::as_str),
        _ => None,
    }
}

fn lower_impl(impl_block: &mut ImplBlock, analysis: &mut BigIntShiftAnalysis) {
    for item in &mut impl_block.items {
        let ImplItem::Method(method) = item else {
            continue;
        };

        let replacement = match method.name.as_str() {
            "push_bit" if has_bigint_signature(method, 2) => {
                analysis.push_bit_methods += 1;
                Some(shift_body(method, ShiftKind::Left))
            }
            "drop_bit" if has_bigint_signature(method, 2) => {
                analysis.drop_bit_methods += 1;
                Some(shift_body(method, ShiftKind::Right))
            }
            "mask" if has_bigint_signature(method, 1) => {
                analysis.mask_methods += 1;
                Some(mask_body(method))
            }
            _ => None,
        };

        if let Some(body) = replacement {
            method.body = body;
        }
    }
}

fn has_bigint_signature(method: &FunctionDef, arity: usize) -> bool {
    method.params.len() == arity
        && method
            .params
            .iter()
            .all(|param| !param.name.is_empty() && type_name(&param.ty) == Some("BigInt"))
        && type_name(&method.return_type) == Some("BigInt")
}

#[derive(Clone, Copy)]
enum ShiftKind {
    Left,
    Right,
}

fn shift_body(method: &FunctionDef, kind: ShiftKind) -> Block {
    let count = method.params[0].name.clone();
    let value = method.params[1].name.clone();
    let shifted = Expr::BinaryOp(
        Box::new(Expr::Ident(value.clone())),
        match kind {
            ShiftKind::Left => "<<",
            ShiftKind::Right => ">>",
        }
        .to_string(),
        Box::new(Expr::Ident("shift".to_string())),
    );

    let overflow = match kind {
        ShiftKind::Left => {
            Expr::Macro("panic!(\"BigInt left-shift count exceeds usize\")".to_string())
        }
        ShiftKind::Right => huge_right_shift_result(&value),
    };

    block(Expr::Match {
        expr: Box::new(shift_count(&count)),
        arms: vec![
            match_arm("Some(shift)", shifted),
            match_arm("None", overflow),
        ],
    })
}

fn mask_body(method: &FunctionDef) -> Block {
    let count = method.params[0].name.clone();
    let one = || {
        Expr::Call(
            Box::new(Expr::Path(
                vec![
                    "num_bigint".to_string(),
                    "BigInt".to_string(),
                    "from".to_string(),
                ],
                PathType::Namespace,
            )),
            vec![Expr::Literal(Literal::Raw("1u8".to_string()))],
        )
    };
    let shifted_one = Expr::BinaryOp(
        Box::new(one()),
        "<<".to_string(),
        Box::new(Expr::Ident("shift".to_string())),
    );
    let mask = Expr::BinaryOp(
        Box::new(Expr::Parenthesized(Box::new(shifted_one))),
        "-".to_string(),
        Box::new(one()),
    );

    block(Expr::Match {
        expr: Box::new(shift_count(&count)),
        arms: vec![
            match_arm("Some(shift)", mask),
            match_arm(
                "None",
                Expr::Macro("panic!(\"BigInt mask width exceeds usize\")".to_string()),
            ),
        ],
    })
}

fn shift_count(count: &str) -> Expr {
    Expr::Call(
        Box::new(Expr::Path(
            vec![
                "num_traits".to_string(),
                "ToPrimitive".to_string(),
                "to_usize".to_string(),
            ],
            PathType::Namespace,
        )),
        vec![Expr::MethodCall(
            Box::new(Expr::Ident(count.to_string())),
            "magnitude".to_string(),
            Vec::new(),
        )],
    )
}

fn huge_right_shift_result(value: &str) -> Expr {
    Expr::If {
        condition: Box::new(Expr::BinaryOp(
            Box::new(Expr::MethodCall(
                Box::new(Expr::Ident(value.to_string())),
                "sign".to_string(),
                Vec::new(),
            )),
            "==".to_string(),
            Box::new(Expr::Path(
                vec![
                    "num_bigint".to_string(),
                    "Sign".to_string(),
                    "Minus".to_string(),
                ],
                PathType::Namespace,
            )),
        )),
        then_branch: block(Expr::UnaryOp(
            "-".to_string(),
            Box::new(Expr::Call(
                Box::new(Expr::Path(
                    vec![
                        "num_bigint".to_string(),
                        "BigInt".to_string(),
                        "from".to_string(),
                    ],
                    PathType::Namespace,
                )),
                vec![Expr::Literal(Literal::Raw("1u8".to_string()))],
            )),
        )),
        else_branch: Some(block(Expr::Path(
            vec![
                "num_bigint".to_string(),
                "BigInt".to_string(),
                "ZERO".to_string(),
            ],
            PathType::Namespace,
        ))),
    }
}

fn match_arm(pattern: &str, expr: Expr) -> MatchArm {
    MatchArm {
        pattern: pattern.to_string(),
        guard: None,
        body: block(expr),
    }
}

fn block(expr: Expr) -> Block {
    Block {
        stmts: Vec::new(),
        expr: Some(Box::new(expr)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parse_rust_source;

    fn optimize(source: &str) -> (BigIntShiftAnalysis, String) {
        let mut module = parse_rust_source(source, "test").expect("source should parse");
        let analysis = lower_bigint_shifts(&mut module);
        let mut generator = RustCodeGenerator::new();
        (analysis, generator.generate_module_code(&module))
    }

    #[test]
    fn lowers_only_the_concrete_bigint_bit_operations_impl() {
        let source = r#"
impl SemiringBitOperations for BigInt {
    fn push_bit(n: BigInt, k: BigInt) -> BigInt { power(k, n) }
    fn drop_bit(n: BigInt, k: BigInt) -> BigInt { divide(k, power(two(), n)) }
    fn mask(n: BigInt) -> BigInt { subtract(power(two(), n), one()) }
}

impl OtherOperations for BigInt {
    fn drop_bit(n: BigInt, k: BigInt) -> BigInt { divide(k, power(two(), n)) }
}
"#;

        let (analysis, output) = optimize(source);

        assert_eq!(
            analysis,
            BigIntShiftAnalysis {
                push_bit_methods: 1,
                drop_bit_methods: 1,
                mask_methods: 1,
            }
        );
        assert!(output.contains("num_traits::ToPrimitive::to_usize(n.magnitude())"));
        assert!(output.contains("k << shift"));
        assert!(output.contains("k >> shift"));
        assert!(output.contains("(num_bigint::BigInt::from(1u8) << shift)"));
        assert!(output.contains("impl OtherOperations for BigInt"));
        assert!(output.contains("divide(k, power(two(), n))"));
    }

    #[test]
    fn ignores_methods_with_non_bigint_signatures() {
        let source = r#"
impl SemiringBitOperations for BigInt {
    fn drop_bit(n: usize, k: BigInt) -> BigInt { k }
}
"#;

        let (analysis, output) = optimize(source);

        assert_eq!(analysis, BigIntShiftAnalysis::default());
        assert!(output.contains("fn drop_bit(n: usize, k: BigInt) -> BigInt"));
    }
}
