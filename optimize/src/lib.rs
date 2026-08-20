mod binding_cleanup;
mod boolean_cleanup;
mod borrow_analysis;
mod bound_cleanup;
mod closure_cleanup;
mod complex_type_cleanup;
mod copy_analysis;
mod last_use_analysis;
mod match_cleanup;
mod mut_analysis;
mod rustlight_parser;
mod utils;

pub use binding_cleanup::cleanup_bindings;
pub use boolean_cleanup::{cleanup_booleans, BooleanCleanupAnalysis};
pub use borrow_analysis::{
    optimize_borrow_modules_with_paths, optimize_borrow_modules_with_paths_and_options,
    BorrowAnalysis, BorrowOptions,
};
pub use bound_cleanup::{cleanup_bounds, BoundCleanupAnalysis};
pub use closure_cleanup::{optimize_closure, ClosureOptAnalysis};
pub use complex_type_cleanup::{cleanup_complex_types, ComplexTypeCleanupAnalysis};
#[cfg(test)]
pub(crate) use copy_analysis::optimize_copy;
pub use copy_analysis::{optimize_copy_modules_with_paths, CopyAnalysis, CopyOptions};
pub use last_use_analysis::optimize_last_use;
pub use match_cleanup::{
    optimize_match_with_context, ExternalTypeFacts, MatchOptAnalysis, MatchTypeContext,
};
pub use mut_analysis::{optimize_mut, MutAnalysis};
pub use rustlight_parser::{parse_rust_source, parse_rust_type_facts};
