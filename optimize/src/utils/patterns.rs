use std::collections::{HashMap, HashSet};

use rustlightast::*;

use super::types::TypeEnv;

pub(crate) fn closure_param_name(param: &ClosureParam) -> String {
    param.pattern.trim_start_matches("mut ").trim().to_string()
}

pub(crate) fn is_binding_ident(input: &str) -> bool {
    let mut chars = input.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    (first == '_' || first.is_ascii_alphabetic())
        && input != "_"
        && !is_reserved_pattern_word(input)
        && chars.all(|ch| ch == '_' || ch.is_ascii_alphanumeric())
}

fn is_reserved_pattern_word(input: &str) -> bool {
    matches!(input, "box" | "false" | "mut" | "ref" | "self" | "true")
}

pub(crate) fn pattern_binds_name(pattern: &str, name: &str) -> bool {
    if !is_binding_ident(name) {
        return false;
    }

    pattern
        .split(|ch: char| ch != '_' && !ch.is_ascii_alphanumeric())
        .any(|token| token == name)
}

pub(crate) fn strip_prefix_word<'a>(input: &'a str, word: &str) -> Option<&'a str> {
    input
        .strip_prefix(word)
        .filter(|rest| rest.starts_with(char::is_whitespace))
        .map(str::trim_start)
}

pub(crate) fn strip_binding_modifiers(mut input: &str) -> &str {
    loop {
        let trimmed = input.trim_start();
        if let Some(rest) = strip_prefix_word(trimmed, "ref") {
            input = rest;
        } else if let Some(rest) = strip_prefix_word(trimmed, "mut") {
            input = rest;
        } else {
            return trimmed;
        }
    }
}

pub(crate) fn outer_parens_inner(input: &str) -> Option<&str> {
    let input = input.trim();
    if !input.starts_with('(') || !input.ends_with(')') {
        return None;
    }

    let mut depth = 0usize;
    for (index, ch) in input.char_indices() {
        match ch {
            '(' => depth += 1,
            ')' => {
                depth = depth.checked_sub(1)?;
                if depth == 0 && index != input.len() - 1 {
                    return None;
                }
            }
            _ => {}
        }
    }

    (depth == 0).then_some(&input[1..input.len() - 1])
}

pub(crate) fn split_constructor_pattern(input: &str) -> Option<(&str, Vec<String>)> {
    let input = input.trim();
    let mut depth = 0usize;
    let mut start = None;

    for (index, ch) in input.char_indices() {
        match ch {
            '(' => {
                if depth == 0 {
                    start = Some(index);
                }
                depth += 1;
            }
            ')' => {
                depth = depth.checked_sub(1)?;
                if depth == 0 && index != input.len() - 1 {
                    return None;
                }
            }
            _ => {}
        }
    }

    if depth != 0 {
        return None;
    }

    let start = start?;
    let constructor = input[..start].trim();
    if constructor.is_empty() {
        return None;
    }

    let inner = input[start + 1..input.len() - 1].trim();
    Some((constructor, split_top_level_commas(inner)))
}

pub(crate) fn split_top_level_commas(input: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut start = 0usize;
    let mut paren = 0usize;
    let mut bracket = 0usize;
    let mut brace = 0usize;

    for (index, ch) in input.char_indices() {
        match ch {
            '(' => paren += 1,
            ')' => paren = paren.saturating_sub(1),
            '[' => bracket += 1,
            ']' => bracket = bracket.saturating_sub(1),
            '{' => brace += 1,
            '}' => brace = brace.saturating_sub(1),
            ',' if paren == 0 && bracket == 0 && brace == 0 => {
                parts.push(input[start..index].trim().to_string());
                start = index + ch.len_utf8();
            }
            _ => {}
        }
    }

    let last = input[start..].trim();
    if !last.is_empty() {
        parts.push(last.to_string());
    }
    parts
}

pub(crate) fn remove_pattern_bindings<T>(pattern: &str, values: &mut HashMap<String, T>) {
    let mut bindings = HashSet::new();
    collect_pattern_bindings(pattern, &mut bindings, true);
    for binding in bindings {
        values.remove(&binding);
    }
}

pub(crate) fn bind_pattern_types<F>(
    pattern: &str,
    expected: &Type,
    env: &mut TypeEnv,
    field_types: &mut F,
) where
    F: FnMut(&str, &Type) -> Option<Vec<Type>>,
{
    let pattern = pattern.trim();
    if pattern.is_empty() || pattern == "_" || pattern == ".." {
        return;
    }

    let pattern = strip_binding_modifiers(pattern);
    if let Some(inner) = outer_parens_inner(pattern) {
        let parts = split_top_level_commas(inner);
        if parts.len() > 1 {
            if let Type::Tuple(types) = expected {
                for (part, ty) in parts.iter().zip(types) {
                    bind_pattern_types(part, ty, env, field_types);
                }
            }
            return;
        }
    }

    if let Some((constructor, args)) = split_constructor_pattern(pattern) {
        if let Some(types) = field_types(constructor, expected) {
            for (arg, ty) in args.iter().zip(types.iter()) {
                bind_pattern_types(arg, ty, env, field_types);
            }
        }
        return;
    }

    if !pattern.contains("::") && !matches!(pattern, "true" | "false") && is_binding_ident(pattern)
    {
        env.insert(pattern.to_string(), expected.clone());
    }
}

pub(crate) fn collect_pattern_bindings(
    pattern: &str,
    bindings: &mut HashSet<String>,
    include_ref: bool,
) {
    let pattern = pattern.trim();
    if pattern.is_empty() || pattern == "_" || pattern == ".." {
        return;
    }
    if let Some(inner) = strip_prefix_word(pattern, "ref") {
        if include_ref {
            collect_pattern_bindings(inner, bindings, include_ref);
        }
        return;
    }
    if let Some(inner) = strip_prefix_word(pattern, "mut") {
        collect_pattern_bindings(inner, bindings, include_ref);
        return;
    }

    if let Some(inner) = outer_parens_inner(pattern) {
        for part in split_top_level_commas(inner) {
            collect_pattern_bindings(&part, bindings, include_ref);
        }
        return;
    }

    if let Some((_, args)) = split_constructor_pattern(pattern) {
        for arg in args {
            collect_pattern_bindings(&arg, bindings, include_ref);
        }
        return;
    }

    if pattern.contains("::") || matches!(pattern, "true" | "false") {
        return;
    }

    if is_binding_ident(pattern) {
        bindings.insert(pattern.to_string());
    }
}
