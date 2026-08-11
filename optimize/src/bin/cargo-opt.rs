use std::env;
use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use isabelle2rust_optimize::{
    cleanup_bindings, cleanup_booleans, cleanup_bounds, cleanup_complex_types,
    optimize_borrow_modules_with_paths, optimize_closure, optimize_copy_modules_with_paths,
    optimize_last_use, optimize_match_with_context, optimize_mut, parse_rust_source,
    parse_rust_type_facts, CopyOptions, MatchTypeContext,
};
use rustlightast::{RustCodeGenerator, RustModule};

const OPT_DIR_NAME: &str = "opt";

fn main() -> ExitCode {
    match run() {
        Ok(summary) => {
            println!(
                "opt finished: optimized {} file(s) into {}",
                summary.optimized,
                summary.output_root.display()
            );
            println!("generated {}", summary.opt_manifest.display());
            println!("run optimized code with: cargo run-opt");
            ExitCode::SUCCESS
        }
        Err(err) => {
            eprintln!("opt failed: {err}");
            ExitCode::FAILURE
        }
    }
}

struct Config {
    target: PathBuf,
    output_root: Option<PathBuf>,
    keep_unused_copy: bool,
    pipeline: PipelineOptions,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct PipelineOptions {
    disable_copy: bool,
    disable_borrow: bool,
    disable_mut: bool,
    disable_last_use: bool,
    disable_closure: bool,
    disable_binding_cleanup: bool,
    disable_match_cleanup: bool,
}

#[cfg(test)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Stage2Pass {
    Copy,
    Borrow,
    Mut,
    LastUse,
    Closure,
}

impl PipelineOptions {
    fn enables_copy(self) -> bool {
        !self.disable_copy
    }

    fn enables_borrow(self) -> bool {
        !self.disable_borrow
    }

    fn enables_mut(self) -> bool {
        !self.disable_mut
    }

    fn enables_last_use(self) -> bool {
        !self.disable_last_use
    }

    fn enables_binding_cleanup(self) -> bool {
        !self.disable_binding_cleanup
    }

    fn enables_closure(self) -> bool {
        !self.disable_closure
    }

    fn enables_match_cleanup(self) -> bool {
        !self.disable_match_cleanup
    }

    #[cfg(test)]
    fn enabled_stage2_passes(self) -> Vec<Stage2Pass> {
        let mut passes = Vec::with_capacity(5);
        if self.enables_copy() {
            passes.push(Stage2Pass::Copy);
        }
        if self.enables_borrow() {
            passes.push(Stage2Pass::Borrow);
        }
        if self.enables_mut() {
            passes.push(Stage2Pass::Mut);
        }
        if self.enables_last_use() {
            passes.push(Stage2Pass::LastUse);
        }
        if self.enables_closure() {
            passes.push(Stage2Pass::Closure);
        }
        passes
    }
}

struct Summary {
    output_root: PathBuf,
    opt_manifest: PathBuf,
    optimized: usize,
}

struct SourceUnit {
    relative_path: PathBuf,
    output_path: PathBuf,
    module_path: Vec<String>,
    source: String,
    parsed: Option<RustModule>,
    analysis_facts: Option<RustModule>,
}

fn run() -> Result<Summary, String> {
    let config = parse_args()?;
    let package_root = find_package_root(&config.target)?;
    let source_root = package_root.join("src");

    if !source_root.is_dir() {
        return Err(format!(
            "expected a Cargo package with a src directory, but {} does not exist",
            source_root.display()
        ));
    }

    let cwd = env::current_dir().map_err(|err| err.to_string())?;
    let output_root = config
        .output_root
        .map(|path| absolute_path_from(&path, &cwd))
        .unwrap_or_else(|| package_root.join(OPT_DIR_NAME));

    if output_root == package_root {
        return Err("output directory must be different from the source package".to_string());
    }

    let opt_manifest = output_root.join("Cargo.toml");
    let mut summary = Summary {
        output_root,
        opt_manifest,
        optimized: 0,
    };
    write_optimized_sources(
        &source_root,
        config.keep_unused_copy,
        config.pipeline,
        &mut summary,
    )?;
    write_opt_manifest(&package_root, &summary)?;

    if summary.optimized == 0 {
        return Err(format!(
            "no Rust source files found under {}",
            source_root.display()
        ));
    }

    Ok(summary)
}

fn parse_args() -> Result<Config, String> {
    // Cargo invokes external subcommands as `cargo-opt opt ...`.
    // Local Cargo aliases usually invoke this binary through `cargo run`,
    // which passes no subcommand name. Supporting both forms keeps the tool
    // flexible.
    let mut target = None;
    let mut output_root = None;
    let mut keep_unused_copy = false;
    let mut pipeline = PipelineOptions::default();
    let mut args = env::args_os().skip(1).filter(|arg| arg != "opt").peekable();

    while let Some(arg) = args.next() {
        if arg == "--out-dir" {
            let value = args
                .next()
                .ok_or_else(|| "--out-dir requires a path".to_string())?;
            output_root = Some(PathBuf::from(value));
        } else if let Some(value) = arg.to_str().and_then(|arg| arg.strip_prefix("--out-dir=")) {
            output_root = Some(PathBuf::from(value));
        } else if arg == "--keep-unused-copy" {
            keep_unused_copy = true;
        } else if arg == "--disable-copy" {
            pipeline.disable_copy = true;
        } else if arg == "--disable-borrow" {
            pipeline.disable_borrow = true;
        } else if arg == "--disable-mut" {
            pipeline.disable_mut = true;
        } else if arg == "--disable-last-use" {
            pipeline.disable_last_use = true;
        } else if arg == "--disable-closure" {
            pipeline.disable_closure = true;
        } else if arg == "--disable-binding-cleanup" {
            pipeline.disable_binding_cleanup = true;
        } else if arg == "--disable-closure-cleanup" {
            // Retain the earlier fine-grained spelling as an alias.
            pipeline.disable_closure = true;
        } else if arg == "--disable-match-cleanup" {
            pipeline.disable_match_cleanup = true;
        } else if arg == "-h" || arg == "--help" {
            return Err(help_text());
        } else if target.is_none() {
            target = Some(PathBuf::from(arg));
        } else {
            return Err(format!(
                "unexpected argument {}; use: cargo opt [package-path] [--out-dir path] [--keep-unused-copy] [--disable-copy] [--disable-borrow] [--disable-mut] [--disable-last-use] [--disable-closure] [diagnostic options]",
                PathBuf::from(arg).display()
            ));
        }
    }

    Ok(Config {
        target: target.unwrap_or(env::current_dir().map_err(|err| err.to_string())?),
        output_root,
        keep_unused_copy,
        pipeline,
    })
}

fn help_text() -> String {
    "usage: cargo opt [package-path] [--out-dir path] [--keep-unused-copy] [--disable-copy] [--disable-borrow] [--disable-mut] [--disable-last-use] [--disable-closure] [diagnostic options]\n\
     writes optimized Rust files to <package-path>/opt/src by default\n\
     and generates <package-path>/opt/Cargo.toml for cargo run-opt\n\
     --keep-unused-copy keeps generated _copy functions even when no call site uses them\n\
     --disable-copy skips Copyability recovery\n\
     --disable-borrow skips Borrow analysis and rewriting\n\
     --disable-mut skips M-Shadow/M-Mut recovery\n\
     --disable-last-use skips last-use clone elimination\n\
     --disable-closure skips closure cleanup\n\
     --disable-binding-cleanup skips trailing-binding cleanup only (diagnostic option)\n\
     --disable-closure-cleanup is an alias for --disable-closure\n\
     --disable-match-cleanup skips both match-cleanup phases (diagnostic option)"
        .to_string()
}

fn find_package_root(start: &Path) -> Result<PathBuf, String> {
    // Walk upward until a Cargo.toml is found, so the tool can be run from any
    // subdirectory inside the target package.
    let start = if start.is_file() {
        start.parent().unwrap_or(start)
    } else {
        start
    };

    let mut current = start
        .canonicalize()
        .map_err(|err| format!("failed to resolve {}: {err}", start.display()))?;

    loop {
        if current.join("Cargo.toml").is_file() {
            return Ok(current);
        }
        if !current.pop() {
            return Err(format!(
                "could not find Cargo.toml from {} or any parent directory",
                start.display()
            ));
        }
    }
}

fn write_optimized_sources(
    source_root: &Path,
    keep_unused_copy: bool,
    pipeline: PipelineOptions,
    summary: &mut Summary,
) -> Result<(), String> {
    let mut sources = rust_sources_under(source_root)?;
    sources.sort();
    let mut units = Vec::with_capacity(sources.len());

    for source_path in sources {
        let relative_path = relative_to(&source_path, source_root);
        let output_path = summary.output_root.join("src").join(&relative_path);
        let source = fs::read_to_string(&source_path)
            .map_err(|err| format!("failed to read {}: {err}", source_path.display()))?;
        ensure_stable_source(&source_path, &source)?;
        let module_name = module_name_from_path(&source_path);
        let module_path = module_path_from_relative(&relative_path);

        let (parsed, analysis_facts) = match parse_rust_source(&source, module_name.clone()) {
            Ok(module) => (Some(module), None),
            Err(err) => {
                eprintln!(
                    "warning: passing {} through unoptimized ({err})",
                    source_path.display()
                );
                (
                    None,
                    parse_rust_type_facts(&source, module_name.clone()).ok(),
                )
            }
        };

        units.push(SourceUnit {
            relative_path,
            output_path,
            module_path,
            source,
            parsed,
            analysis_facts,
        });
    }

    let mut match_context = MatchTypeContext::default();
    for unit in &units {
        if let Some(module) = &unit.parsed {
            match_context.insert_module(unit.module_path.clone(), module);
        }
    }

    for unit in &mut units {
        if let Some(module) = unit.parsed.as_mut() {
            if pipeline.enables_match_cleanup() {
                optimize_match_with_context(module, &match_context, &unit.module_path);
            }
        }
    }

    let inferred_copy_types = if pipeline.enables_copy() {
        let mut modules: Vec<(Vec<String>, &mut RustModule)> = units
            .iter_mut()
            .filter_map(|unit| {
                unit.parsed
                    .as_mut()
                    .or(unit.analysis_facts.as_mut())
                    .map(|module| (unit.module_path.clone(), module))
            })
            .collect();
        optimize_copy_modules_with_paths(&mut modules, CopyOptions { keep_unused_copy })
            .inferred_copy_types
    } else {
        // Disable only facts inferred and materialized by the Copy pass.
        // Borrow still discovers source derives and explicit Copy impls.
        Default::default()
    };

    if pipeline.enables_borrow() {
        let mut modules: Vec<(Vec<String>, &mut RustModule)> = units
            .iter_mut()
            .filter_map(|unit| {
                unit.parsed
                    .as_mut()
                    .or(unit.analysis_facts.as_mut())
                    .map(|module| (unit.module_path.clone(), module))
            })
            .collect();
        optimize_borrow_modules_with_paths(&mut modules, &inferred_copy_types);
    }

    let mut post_match_context = MatchTypeContext::default();
    for unit in &units {
        if let Some(module) = &unit.parsed {
            post_match_context.insert_module(unit.module_path.clone(), module);
        }
    }

    for unit in units {
        let printed = match unit.parsed {
            Some(mut module) => finish_source_module(
                &mut module,
                &unit.module_path,
                &post_match_context,
                pipeline,
            ),
            None => unit.source,
        };

        write_file(&unit.output_path, printed.as_bytes())?;
        println!("optimized src/{}", unit.relative_path.display());
        summary.optimized += 1;
    }

    Ok(())
}

fn rust_sources_under(root: &Path) -> Result<Vec<PathBuf>, String> {
    // Use an explicit stack instead of recursion to collect every Rust file in
    // src, including nested module directories.
    let mut pending = vec![root.to_path_buf()];
    let mut sources = Vec::new();

    while let Some(path) = pending.pop() {
        let entries = fs::read_dir(&path)
            .map_err(|err| format!("failed to read directory {}: {err}", path.display()))?;

        for entry in entries {
            let entry = entry.map_err(|err| err.to_string())?;
            let path = entry.path();
            let file_type = entry
                .file_type()
                .map_err(|err| format!("failed to inspect {}: {err}", path.display()))?;

            if file_type.is_dir() {
                pending.push(path);
            } else if file_type.is_file() && is_input_rust_file(&path) {
                sources.push(path);
            }
        }
    }

    Ok(sources)
}

fn finish_source_module(
    module: &mut RustModule,
    module_path: &[String],
    match_context: &MatchTypeContext,
    pipeline: PipelineOptions,
) -> String {
    // Current opt pipeline: Rust source -> RustLightAST -> optimization passes
    // -> rustlight_print::RustCodeGenerator.
    //
    // The RustLightAST parser does not yet cover every Rust construct the
    // Isabelle code generator can emit (e.g. `trait` items pulled in as dead
    // code by the `nat`/`int` setup). Parse failures are handled before this
    // function, so every module here can share package-level match type context.
    if pipeline.enables_mut() {
        optimize_mut(module);
    }
    if pipeline.enables_last_use() {
        optimize_last_use(module);
    }
    if pipeline.enables_binding_cleanup() {
        cleanup_bindings(module);
    }
    if pipeline.enables_closure() {
        optimize_closure(module);
    }
    if pipeline.enables_match_cleanup() {
        // Post-clean any discard/fallback artifacts introduced by later passes.
        optimize_match_with_context(module, match_context, module_path);
    }
    cleanup_booleans(module);
    cleanup_bounds(module);
    cleanup_complex_types(module);

    let mut generator = RustCodeGenerator::new();
    generator.generate_module_code(module)
}

fn write_opt_manifest(package_root: &Path, summary: &Summary) -> Result<(), String> {
    let manifest_path = package_root.join("Cargo.toml");
    let manifest = fs::read_to_string(&manifest_path)
        .map_err(|err| format!("failed to read {}: {err}", manifest_path.display()))?;
    let lib_path = summary.output_root.join("src").join("lib.rs");

    if !lib_path.is_file() {
        return Err(format!(
            "cannot generate optimized Cargo.toml: optimized crate entry {} does not exist",
            lib_path.display()
        ));
    }

    write_file(&summary.opt_manifest, manifest.as_bytes())
}

fn write_file(output_path: &Path, contents: &[u8]) -> Result<(), String> {
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|err| format!("failed to create {}: {err}", parent.display()))?;
    }

    fs::write(output_path, contents)
        .map_err(|err| format!("failed to write {}: {err}", output_path.display()))
}

fn ensure_stable_source(source_path: &Path, source: &str) -> Result<(), String> {
    for (index, line) in source.lines().enumerate() {
        let compact = line
            .chars()
            .filter(|character| !character.is_whitespace())
            .collect::<String>();
        if compact.starts_with("#![feature(") {
            return Err(format!(
                "{}:{} enables an unstable Rust feature; Stage 2 accepts stable Rust sources only",
                source_path.display(),
                index + 1
            ));
        }
    }
    Ok(())
}

fn is_input_rust_file(path: &Path) -> bool {
    path.extension() == Some(OsStr::new("rs")) && !is_generated_rust_file(path)
}

fn is_generated_rust_file(path: &Path) -> bool {
    path.extension() == Some(OsStr::new("rs"))
        && path
            .file_stem()
            .and_then(OsStr::to_str)
            .is_some_and(|stem| stem.ends_with("-opt"))
}

fn module_name_from_path(source_path: &Path) -> String {
    let stem = source_path
        .file_stem()
        .and_then(OsStr::to_str)
        .unwrap_or("module");
    sanitize_module_name(stem)
}

fn module_path_from_relative(relative_path: &Path) -> Vec<String> {
    let mut module_path = vec!["crate".to_string()];
    let mut components = relative_path
        .components()
        .filter_map(|component| component.as_os_str().to_str())
        .collect::<Vec<_>>();

    let Some(file_name) = components.pop() else {
        return module_path;
    };

    for component in components {
        module_path.push(sanitize_module_name(component));
    }

    let stem = Path::new(file_name)
        .file_stem()
        .and_then(OsStr::to_str)
        .unwrap_or(file_name);
    if !matches!(stem, "lib" | "main" | "mod") {
        module_path.push(sanitize_module_name(stem));
    }

    module_path
}

fn sanitize_module_name(stem: &str) -> String {
    // The AST stores a module name, so derive a conservative Rust identifier
    // from the file stem even if the file name contains punctuation.
    let mut out = String::new();

    for (idx, ch) in stem.chars().enumerate() {
        let valid = ch == '_' || ch.is_ascii_alphanumeric();
        if idx == 0 && ch.is_ascii_digit() {
            out.push('_');
        }
        out.push(if valid { ch } else { '_' });
    }

    if out.is_empty() {
        "module".to_string()
    } else {
        out
    }
}

fn relative_to(path: &Path, base: &Path) -> PathBuf {
    path.strip_prefix(base).unwrap_or(path).to_path_buf()
}

fn absolute_path_from(path: &Path, cwd: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        cwd.join(path)
    }
}

#[cfg(test)]
mod tests {
    use std::path::Path;

    use super::{ensure_stable_source, PipelineOptions, Stage2Pass};

    #[test]
    fn full_pipeline_enables_all_available_stage2_passes() {
        assert_eq!(
            PipelineOptions::default().enabled_stage2_passes(),
            vec![
                Stage2Pass::Copy,
                Stage2Pass::Borrow,
                Stage2Pass::Mut,
                Stage2Pass::LastUse,
                Stage2Pass::Closure,
            ]
        );
    }

    #[test]
    fn pass_level_switches_are_independent() {
        let options = PipelineOptions {
            disable_copy: true,
            disable_borrow: true,
            disable_mut: true,
            disable_last_use: true,
            disable_closure: true,
            ..PipelineOptions::default()
        };
        assert!(options.enabled_stage2_passes().is_empty());
        assert!(!options.enables_copy());
        assert!(!options.enables_borrow());
        assert!(!options.enables_mut());
        assert!(!options.enables_last_use());
        assert!(!options.enables_closure());
    }

    #[test]
    fn accepts_stable_source_without_feature_gates() {
        assert!(
            ensure_stable_source(Path::new("src/lib.rs"), "pub fn id(x: u64) -> u64 { x }").is_ok()
        );
    }

    #[test]
    fn rejects_unstable_feature_gates() {
        let error = ensure_stable_source(
            Path::new("src/lib.rs"),
            "  #! [ feature(box_patterns) ]\npub fn id(x: u64) -> u64 { x }",
        )
        .unwrap_err();
        assert!(error.contains("src/lib.rs:1"));
        assert!(error.contains("stable Rust sources only"));
    }
}
