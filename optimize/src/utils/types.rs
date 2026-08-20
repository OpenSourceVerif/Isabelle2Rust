use std::collections::{HashMap, HashSet};

use rustlightast::*;

use super::patterns::is_binding_ident;

pub(crate) type TypeEnv = HashMap<String, Type>;

pub(crate) fn function_type_env(function: &FunctionDef) -> TypeEnv {
    function
        .params
        .iter()
        .filter(|param| !param.name.is_empty())
        .map(|param| (param.name.clone(), param.ty.clone()))
        .collect()
}

pub(crate) fn generic_names_with_bound(function: &FunctionDef, bound: &str) -> HashSet<String> {
    function
        .generics
        .iter()
        .filter(|generic| generic.bounds.iter().any(|candidate| candidate == bound))
        .map(|generic| generic.name.clone())
        .collect()
}

pub(crate) fn is_reference_type(ty: &Type) -> bool {
    matches!(ty, Type::Reference(_, true, _))
}

pub(crate) fn type_is_copy_trait(ty: &Type) -> bool {
    match ty {
        Type::Named(name) => name == "Copy",
        Type::Path(path) => path.last().is_some_and(|name| name == "Copy"),
        _ => false,
    }
}

pub(crate) fn types_equal(left: &Type, right: &Type) -> bool {
    match (left, right) {
        (Type::Path(left), Type::Path(right)) => left == right,
        (Type::Named(left), Type::Named(right)) => left == right,
        (Type::Generic(left_name, left_args), Type::Generic(right_name, right_args)) => {
            left_name == right_name
                && left_args.len() == right_args.len()
                && left_args
                    .iter()
                    .zip(right_args)
                    .all(|(left, right)| types_equal(left, right))
        }
        (Type::CallableTrait(left), Type::CallableTrait(right)) => {
            std::mem::discriminant(&left.qualifier) == std::mem::discriminant(&right.qualifier)
                && left.trait_name == right.trait_name
                && left.args.len() == right.args.len()
                && left
                    .args
                    .iter()
                    .zip(&right.args)
                    .all(|(left, right)| types_equal(left, right))
                && types_equal(&left.return_type, &right.return_type)
        }
        (
            Type::Reference(left, left_ref, left_mut),
            Type::Reference(right, right_ref, right_mut),
        ) => left_ref == right_ref && left_mut == right_mut && types_equal(left, right),
        (Type::Tuple(left), Type::Tuple(right)) => {
            left.len() == right.len()
                && left
                    .iter()
                    .zip(right)
                    .all(|(left, right)| types_equal(left, right))
        }
        (Type::Slice(left), Type::Slice(right)) => types_equal(left, right),
        (Type::Array(left, left_len), Type::Array(right, right_len)) => {
            left_len == right_len && types_equal(left, right)
        }
        (Type::Unit, Type::Unit) | (Type::Never, Type::Never) => true,
        _ => false,
    }
}

pub(crate) fn type_name_leaf(name: &str) -> &str {
    name.rsplit("::").next().unwrap_or(name)
}

pub(crate) fn type_substitution(generics: &[String], ty: &Type) -> HashMap<String, Type> {
    match ty {
        Type::Generic(_, params) if params.len() == generics.len() => generics
            .iter()
            .cloned()
            .zip(params.iter().cloned())
            .collect(),
        _ => HashMap::new(),
    }
}

pub(crate) fn apply_type_subst(ty: &Type, subst: &HashMap<String, Type>) -> Type {
    match ty {
        Type::Named(name) => subst
            .get(name)
            .cloned()
            .unwrap_or_else(|| Type::Named(name.clone())),
        Type::Generic(name, params) => Type::Generic(
            name.clone(),
            params
                .iter()
                .map(|param| apply_type_subst(param, subst))
                .collect(),
        ),
        Type::Tuple(types) => Type::Tuple(
            types
                .iter()
                .map(|element| apply_type_subst(element, subst))
                .collect(),
        ),
        Type::Array(inner, len) => Type::Array(Box::new(apply_type_subst(inner, subst)), *len),
        Type::Reference(inner, is_ref, mutable) => {
            Type::Reference(Box::new(apply_type_subst(inner, subst)), *is_ref, *mutable)
        }
        Type::Slice(inner) => Type::Slice(Box::new(apply_type_subst(inner, subst))),
        Type::CallableTrait(callable) => Type::CallableTrait(CallableTraitType {
            qualifier: callable.qualifier.clone(),
            trait_name: callable.trait_name.clone(),
            args: callable
                .args
                .iter()
                .map(|arg| apply_type_subst(arg, subst))
                .collect(),
            return_type: Box::new(apply_type_subst(&callable.return_type, subst)),
        }),
        Type::Path(_) | Type::Unit | Type::Never => ty.clone(),
    }
}

pub(crate) fn callable_return_type(ty: &Type) -> Option<Type> {
    match ty {
        Type::CallableTrait(callable) => Some(callable.return_type.as_ref().clone()),
        Type::Generic(name, params)
            if matches!(type_name_leaf(name), "Rc" | "Arc" | "Box") && params.len() == 1 =>
        {
            callable_return_type(&params[0])
        }
        Type::Reference(inner, _, _) => callable_return_type(inner),
        _ => None,
    }
}

pub(crate) fn infer_block_type<F, B, U>(
    block: &Block,
    env: &TypeEnv,
    mut infer_expr: F,
    mut bind_pattern: B,
    mut unknown_pattern: U,
) -> Option<Type>
where
    F: FnMut(&Expr, &TypeEnv) -> Option<Type>,
    B: FnMut(&str, &Type, &mut TypeEnv),
    U: FnMut(&str, &mut TypeEnv),
{
    let mut block_env = env.clone();
    for stmt in &block.stmts {
        let Statement::Let(let_stmt) = stmt else {
            continue;
        };
        let inferred = let_stmt.ty.clone().or_else(|| {
            let_stmt
                .init
                .as_ref()
                .and_then(|init| infer_expr(init, &block_env))
        });
        if let Some(ty) = inferred {
            if is_binding_ident(&let_stmt.name) {
                block_env.insert(let_stmt.name.clone(), ty);
            } else {
                bind_pattern(&let_stmt.name, &ty, &mut block_env);
            }
        } else {
            unknown_pattern(&let_stmt.name, &mut block_env);
        }
    }
    block
        .expr
        .as_ref()
        .and_then(|expr| infer_expr(expr, &block_env))
}

pub(crate) fn strip_path_segment_generics(segment: &str) -> &str {
    let before_args = segment.split_once('<').map_or(segment, |(head, _)| head);
    before_args
        .trim()
        .strip_suffix("::")
        .unwrap_or(before_args.trim())
        .trim()
}

pub(crate) fn explicit_identity_return_type(callee: &Expr) -> Option<Type> {
    let segment = match callee {
        Expr::Ident(segment) => segment,
        Expr::Path(path, PathType::Namespace) => path.last()?,
        Expr::Parenthesized(inner) => return explicit_identity_return_type(inner),
        _ => return None,
    };
    (strip_path_segment_generics(segment) == "identity")
        .then(|| crate::rustlight_parser::first_explicit_type_argument(segment))
        .flatten()
}
