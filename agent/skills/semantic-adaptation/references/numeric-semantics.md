# Numeric semantics and conversions

Separate a value's mathematical meaning, representation range and operation semantics.

## Establish a range from evidence

A position obtained by enumerating a resident Rust slice is bounded by its length; it can use usize locally. An exported arbitrary natural parameter has no such bound. A value loaded from a small test case is not a range proof. Keep source type variables independent of an index/result type: a generic search can compare large elements and return a bounded position.

For source take/drop with a mathematical nonnegative count, counts beyond the container length have the same clamped result. Compare/clamp before converting to usize. This justification does not apply to a source indexing operation with a different undefined/totalized boundary convention.

Converting u128 to i128 by `as` changes values above i128::MAX. Use a checked conversion when the destination is required, retain the unsigned computation when justified, or select a suitable arbitrary representation in arbitrary mode. Do not infer safety because a downstream cutoff happened not to change on sampled inputs.

## Inspect the operation, not only its type

HOL nat subtraction can be truncated at zero, while machine unsigned subtraction may fail or wrap. Use the source equation to choose the intended operation. For signed division/remainder inspect the source convention on negative operands; truncation toward zero and floor division differ. For division by zero, source totalization may differ from a machine panic. Shifts require checking source width, shift count semantics and the intermediate result; modulo-reducing a count without evidence changes behavior.

Source words have modular semantics at their actual width. A primitive word is suitable only when it realizes that width and the relevant operations. Non-native widths may need masking; mathematical nat must not inherit word wraparound.

## Checked and arbitrary modes

The controller supplies the current policy. In checked mode an unrepresentable mathematical intermediate must follow its explicit error contract; wrapping and hidden arbitrary fallback are not acceptable. An algebraic rewrite can avoid a large intermediate only with a source-grounded equivalence argument and preserved boundary behavior. In arbitrary mode preserve unbounded mathematical values: prefer dashu-int =0.6.2 UBig for nat and IBig for int/integer, and follow an explicit numeric_library selection when supplied. Do not expect mathematical overflow at u128/i128 limits. Preserve conversions and signed behavior; Rust library division operators alone need not match the source.

Checked-mode positive example: a nonnegative mathematical sum known to exceed u128::MAX is greater than any u128 comparison value, so an overflow-aware comparison can sometimes determine its result without materializing the sum. Negative example: using the same shortcut when signed cancellation is possible, or when the exact sum is subsequently returned.

Audit input conversion, support internals, callbacks, intermediate conversions and output conversion. Testing a few numeric results does not validate every conversion in the chain.

## Disambiguate division with a concrete sign table

“Euclidean” alone is not a sufficient implementation contract. Inspect the actual source equations. For floor quotient with divisor-signed remainder, truncating q=a/b and r=a-q*b must adjust to (q-1,r+b) exactly when r != 0 and r has the opposite sign from b. For positive-remainder Euclidean division the negative-divisor rule differs. Do not interchange the two based on library method names. Check positive/negative dividend and divisor, exact divisibility and zero-divisor totalization separately. Explain which rule the original operation specifies; these concrete checks support that choice but do not prove all input cases.

## Large bit counts with small exact results

Do not reject an arbitrary-precision bit count merely because it cannot be converted to usize. First inspect the operation and the operand's exact magnitude bit length. For natural take_bit, a count at least the operand's bit length leaves the operand unchanged. The same holds for a nonnegative integer. For signed drop_bit with floor semantics, a count at least the magnitude bit length yields zero for nonnegative operands and minus one for negative operands. A zero left-shift operand remains zero for every count. These are exact small results; no enormous power of two needs to be materialized.

Negative take_bit at a huge count and a nonzero left shift may instead require an infeasibly large output. Keep that resource limitation distinct from the small-output cases. A library magnitude-bit-length operation can justify a local range guard, but must not replace HOL bitlen on negative inputs: HOL bitlen returns zero there.

Checked left shift needs value-range checking as well as count checking. Rust checked_shl reports an invalid count but does not by itself reject all lost high value bits. Include cases such as unsigned MAX shifted by one, signed -1 shifted by127 (i128::MIN is representable), positive one shifted by127 (outside i128), and zero shifted by a huge count. For signed take_bit at127, a negative input can have a representable nonnegative remainder even though the positive modulus2^127 cannot be stored in i128; use a source-grounded exact lowering when avoiding that unnecessary intermediate.

Require independent source-contract tests for these feasible edges when the corresponding operations are exposed or reachable through private test bindings. A passing top-level square-root test does not establish all reusable support-operation contracts.

Numeric test coverage must be checked per operation and concrete type instance. For a count above usize::MAX, independently verify Nat drop, signed Int drop on both signs, Nat take on a positive operand, signed Int take on a positive operand, and zero Nat/Int push wherever the source API permits. One large-count Nat drop test does not cover signed drop or either take instance. Use library/native constructors for test inputs and literal expectations, never candidate arithmetic/conversion helpers to construct both sides. Record omitted rows with a source/type reason.
