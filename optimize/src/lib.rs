pub mod copy_analysis;
pub mod rustlight_parser;

pub use copy_analysis::{optimize_copy, CopyAnalysis};
pub use rustlight_parser::{parse_and_print_rust_source, parse_rust_source};
