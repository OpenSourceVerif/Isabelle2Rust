pub mod borrow_analysis;
pub mod closure_opt;
pub mod copy_analysis;
pub mod match_opt;
pub mod mut_analysis;
pub mod rustlight_parser;

pub use borrow_analysis::{optimize_borrow, optimize_borrow_modules, BorrowAnalysis};
pub use closure_opt::{optimize_closure, ClosureOptAnalysis};
pub use copy_analysis::{optimize_copy, optimize_copy_with_options, CopyAnalysis, CopyOptions};
pub use match_opt::{
    optimize_match, optimize_match_with_context, MatchOptAnalysis, MatchTypeContext,
};
pub use mut_analysis::{optimize_mut, MutAnalysis};
pub use rustlight_parser::{parse_and_print_rust_source, parse_rust_source};
