pub mod borrow_analysis;
pub mod closure_cleanup;
pub mod copy_analysis;
pub mod if_cleanup;
pub mod match_cleanup;
pub mod mut_analysis;
pub mod rustlight_parser;

pub use borrow_analysis::{
    optimize_borrow, optimize_borrow_modules, optimize_borrow_modules_with_paths, BorrowAnalysis,
};
pub use closure_cleanup::{optimize_closure, ClosureOptAnalysis};
pub use copy_analysis::{
    optimize_copy, optimize_copy_modules, optimize_copy_modules_with_paths,
    optimize_copy_with_options, CopyAnalysis, CopyOptions,
};
pub use if_cleanup::{cleanup_if, IfCleanupAnalysis};
pub use match_cleanup::{
    optimize_match, optimize_match_with_context, ExternalTypeFacts, MatchOptAnalysis,
    MatchTypeContext,
};
pub use mut_analysis::{optimize_mut, MutAnalysis};
pub use rustlight_parser::{parse_and_print_rust_source, parse_rust_source};
