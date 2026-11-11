# Verified API reference: dashu-int =0.6.2

This reference applies only to the exact dependency version `dashu-int =0.6.2`. It describes library APIs, not Isabelle operation semantics. For another version inspect that version's API; do not assume these names/contracts apply. The Isabelle source equations remain authoritative.

Import `dashu_int::{UBig, IBig}` for the concrete types, or use the program's actual aliases. Trait methods require their trait in scope.

- Import `dashu_int::ops::BitTest` to use `x.bit_len()`. Both `UBig` and `IBig` implement it; it returns a `usize` magnitude bit length. Zero has length 0. `IBig::from(-5).bit_len()` is 3. It does not implement HOL's signed `bitlen` behavior for negative operands. No decimal conversion, repeated division, magnitude clone or invented `magnitude()` method is needed merely to query magnitude bit length.
- Use `usize::try_from(&ubig)` or `u128::try_from(&ubig)` for exact checked conversion. Both borrowed and owned forms are implemented; conversion fails outside the target range. Do not invent `to_u64()` or replace it with a floating-point conversion. Source boundary cases must be resolved before narrowing an unbounded count; a failed count conversion alone does not prove the source result is unrepresentable.
- `IBig::sign(&self)` returns `dashu_int::Sign`; zero uses `Sign::Positive`. `into_parts(self)` consumes an `IBig` and yields `(Sign, UBig)`. `IBig::from_parts(sign, magnitude)` constructs the signed value. Cloning to call `into_parts` has a cost; borrow the original and use `bit_len()` when only its magnitude length is needed.
- Borrowed integer division and remainder (`&a / &b`, `&a % &b`) truncate toward zero for signed values: -5 / 2 = -2, -5 % 2 = -1. Do not equate these operators with source floor division or source totalized division-by-zero. Derive and test the source lowering separately.
- Primitive constructors such as `UBig::from(5u32)` and `IBig::from(-5i32)` and constants `UBig::ZERO`, `UBig::ONE` are available. A Rust type alias does not bring the aliased type's original short name into scope.

Primary implementation inspected: `dashu-int-0.6.2/src/ops.rs` (BitTest re-export), `src/bits.rs` (BitTest implementations for UBig and IBig), `src/convert.rs` (borrowed/owned TryFrom), `src/ibig.rs` (sign and parts). These examples were also compiled and executed with the locked crate. This is a selected API guide, not a complete dependency oracle or proof of the translated program.
