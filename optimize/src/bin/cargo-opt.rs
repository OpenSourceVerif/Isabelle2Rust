use std::env;
use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use isabelle2rust_optimize::{
    optimize_borrow, optimize_closure, optimize_copy_with_options, optimize_match_with_context,
    optimize_mut, parse_rust_source, CopyOptions, MatchTypeContext,
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
}

struct Summary {
    output_root: PathBuf,
    opt_manifest: PathBuf,
    optimized: usize,
    needs_nightly: bool,
}

struct SourceUnit {
    relative_path: PathBuf,
    output_path: PathBuf,
    module_path: Vec<String>,
    source: String,
    parsed: Option<RustModule>,
    needs_nightly: bool,
}

fn run() -> Result<Summary, String> {
    let config = parse_args()?;
    let package_root = find_package_root(&config.target)?;
    let source_root = package_root.join("src");
    let primary_module = primary_module_name(&package_root);

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
        needs_nightly: false,
    };
    write_optimized_sources(
        &source_root,
        &primary_module,
        config.keep_unused_copy,
        &mut summary,
    )?;
    write_opt_manifest(&package_root, &summary)?;

    if summary.needs_nightly {
        write_nightly_toolchain_file(&package_root)?;
        write_nightly_toolchain_file(&summary.output_root)?;
    }

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
        } else if arg == "-h" || arg == "--help" {
            return Err(help_text());
        } else if target.is_none() {
            target = Some(PathBuf::from(arg));
        } else {
            return Err(format!(
                "unexpected argument {}; use: cargo opt [package-path] [--out-dir path] [--keep-unused-copy]",
                PathBuf::from(arg).display()
            ));
        }
    }

    Ok(Config {
        target: target.unwrap_or(env::current_dir().map_err(|err| err.to_string())?),
        output_root,
        keep_unused_copy,
    })
}

fn help_text() -> String {
    "usage: cargo opt [package-path] [--out-dir path] [--keep-unused-copy]\n\
     writes optimized Rust files to <package-path>/opt/src by default\n\
     and generates <package-path>/opt/Cargo.toml for cargo run-opt\n\
     --keep-unused-copy keeps generated _copy functions even when no call site uses them"
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
    primary_module: &str,
    keep_unused_copy: bool,
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
        let module_name = module_name_from_path(&source_path);
        let module_path = module_path_from_relative(&relative_path);
        let needs_nightly = source.contains("#![feature(");

        let parsed = match parse_rust_source(&source, module_name.clone()) {
            Ok(module) => Some(module),
            Err(err) => {
                eprintln!(
                    "warning: passing {} through unoptimized ({err})",
                    source_path.display()
                );
                None
            }
        };

        units.push(SourceUnit {
            relative_path,
            output_path,
            module_path,
            source,
            parsed,
            needs_nightly,
        });
    }

    let mut match_context = MatchTypeContext::default();
    for unit in &units {
        if let Some(module) = &unit.parsed {
            match_context.insert_module(unit.module_path.clone(), module);
        }
    }

    for unit in units {
        if unit.needs_nightly {
            summary.needs_nightly = true;
        }

        let printed = match unit.parsed {
            Some(mut module) => optimize_source_module(
                &mut module,
                &unit.module_path,
                primary_module,
                keep_unused_copy,
                &match_context,
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

fn optimize_source_module(
    module: &mut RustModule,
    module_path: &[String],
    primary_module: &str,
    keep_unused_copy: bool,
    match_context: &MatchTypeContext,
) -> String {
    let optimize_borrow_signatures = module.name.as_str() == primary_module;

    // Current opt pipeline: Rust source -> RustLightAST -> optimization passes
    // -> rustlight_print::RustCodeGenerator.
    //
    // The RustLightAST parser does not yet cover every Rust construct the
    // Isabelle code generator can emit (e.g. `trait` items pulled in as dead
    // code by the `nat`/`int` setup). Parse failures are handled before this
    // function, so every module here can share package-level match type context.
    optimize_match_with_context(module, match_context, module_path);
    let copy_analysis = optimize_copy_with_options(module, CopyOptions { keep_unused_copy });
    if optimize_borrow_signatures {
        optimize_borrow(module, &copy_analysis.copy_types);
    }
    optimize_mut(module);
    optimize_closure(module);
    // Post-clean any discard/fallback artifacts introduced by later passes.
    optimize_match_with_context(module, match_context, module_path);

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

fn write_nightly_toolchain_file(package_root: &Path) -> Result<(), String> {
    let toolchain_path = package_root.join("rust-toolchain.toml");
    if toolchain_path.exists() {
        return Ok(());
    }

    write_file(&toolchain_path, b"[toolchain]\nchannel = \"nightly\"\n")
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

fn primary_module_name(package_root: &Path) -> String {
    package_root
        .parent()
        .and_then(Path::file_name)
        .and_then(OsStr::to_str)
        .map(sanitize_module_name)
        .unwrap_or_else(|| "module".to_string())
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
