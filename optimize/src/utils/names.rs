use std::collections::HashMap;

use rustlightast::*;

pub(crate) fn collect_imports(items: &[Item]) -> HashMap<String, Vec<String>> {
    let mut imports = HashMap::new();
    for item in items {
        if let Item::Use(use_stmt) = item {
            collect_import(&mut imports, use_stmt);
        }
    }
    imports
}

fn collect_import(imports: &mut HashMap<String, Vec<String>>, use_stmt: &UseStatement) {
    match &use_stmt.kind {
        UseKind::Simple => {
            if let Some((source, local)) = imported_leaf(use_stmt.path.last()) {
                let mut path = use_stmt.path.clone();
                if let Some(last) = path.last_mut() {
                    *last = source;
                }
                imports.insert(local, path);
            }
        }
        UseKind::Nested(items) => {
            for item in items {
                if let Some((source, local)) = imported_leaf(Some(item)) {
                    let mut path = use_stmt.path.clone();
                    path.push(source);
                    imports.insert(local, path);
                }
            }
        }
        UseKind::Glob => {}
    }
}

fn imported_leaf(leaf: Option<&String>) -> Option<(String, String)> {
    let leaf = leaf?.trim();
    if let Some((source, local)) = leaf.split_once(" as ") {
        Some((source.trim().to_string(), local.trim().to_string()))
    } else {
        Some((leaf.to_string(), leaf.to_string()))
    }
}

pub(crate) fn resolve_name_path(
    module_path: &[String],
    imports: &HashMap<String, Vec<String>>,
    name: &str,
) -> Vec<String> {
    if let Some(path) = imports.get(name) {
        return path.clone();
    }

    let mut path = module_path.to_vec();
    path.push(name.to_string());
    path
}

pub(crate) fn resolve_segments(
    module_path: &[String],
    imports: &HashMap<String, Vec<String>>,
    segments: &[String],
) -> Vec<String> {
    let Some((first, rest)) = segments.split_first() else {
        return Vec::new();
    };

    match first.as_str() {
        "crate" => segments.to_vec(),
        "self" => {
            let mut path = module_path.to_vec();
            path.extend(rest.iter().cloned());
            path
        }
        "super" => {
            let mut path = module_path.to_vec();
            let mut remaining = segments;
            while matches!(remaining.first().map(String::as_str), Some("super")) {
                path.pop();
                remaining = &remaining[1..];
            }
            path.extend(remaining.iter().cloned());
            path
        }
        _ => {
            if let Some(imported) = imports.get(first) {
                let mut path = imported.clone();
                path.extend(rest.iter().cloned());
                path
            } else if segments.len() == 1 {
                resolve_name_path(module_path, imports, first)
            } else {
                let mut path = vec!["crate".to_string()];
                path.extend(segments.iter().cloned());
                path
            }
        }
    }
}
