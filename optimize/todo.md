# Optimizer TODO

## Eliminate redundant non-exhaustive fallback arms

Stage 1 conservatively appends `_ => panic!("non-exhaustive match")` to
generated `match` expressions. Add a Stage-2 optimization that removes this
fallback only when the scrutinee has a known enum type and the preceding,
unguarded arms cover every variant.

The fallback must remain for incomplete matches, guarded arms, unknown
scrutinee types, and patterns whose exhaustiveness cannot be established.
Add a regression based on `Count_True_Test` that checks that the optimized
`count` function contains no fallback panic and that the Stage-2 crate still
compiles.
