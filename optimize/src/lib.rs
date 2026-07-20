pub mod bigint_shift;
pub mod boolean_cleanup;
pub mod borrow_analysis;
pub mod bound_cleanup;
pub mod closure_cleanup;
pub mod complex_type_cleanup;
pub mod copy_analysis;
pub mod match_cleanup;
pub mod mut_analysis;
pub mod rustlight_parser;

pub use bigint_shift::{lower_bigint_shifts, BigIntShiftAnalysis};
pub use boolean_cleanup::{cleanup_booleans, BooleanCleanupAnalysis};
pub use borrow_analysis::{
    optimize_borrow, optimize_borrow_modules, optimize_borrow_modules_with_paths, BorrowAnalysis,
};
pub use bound_cleanup::{cleanup_bounds, BoundCleanupAnalysis};
pub use closure_cleanup::{optimize_closure, ClosureOptAnalysis};
pub use complex_type_cleanup::{cleanup_complex_types, ComplexTypeCleanupAnalysis};
pub use copy_analysis::{
    optimize_copy, optimize_copy_modules, optimize_copy_modules_with_paths,
    optimize_copy_with_options, CopyAnalysis, CopyOptions,
};
pub use match_cleanup::{
    optimize_match, optimize_match_with_context, ExternalTypeFacts, MatchOptAnalysis,
    MatchTypeContext,
};
pub use mut_analysis::{optimize_mut, MutAnalysis};
pub use rustlight_parser::{parse_and_print_rust_source, parse_rust_source, parse_rust_type_facts};
