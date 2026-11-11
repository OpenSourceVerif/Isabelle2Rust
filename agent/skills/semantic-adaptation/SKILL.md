---
name: semantic-adaptation
description: Analyze and implement Isabelle-to-Rust representations and operation mappings from source contracts, numeric requirements and scoped source-to-Rust realizations.
---

# Semantic adaptation

Choose target representations and operations from the behavior actually required by source equations, types and callers. In analysis, identify opportunities, conditions and missing evidence; implementation happens during generation. Recommendations remain revisable. Source names, small test instances and previous backend conventions do not establish a semantic contract.

For an important choice identify the source operations and observable behavior, target choice, evidence for its conditions, differences requiring a wrapper, and affected bindings/support/callers. Reuse the analysis fields sources, usage, suggestion, conditions and basis. Conditions should be checkable: “this index originates in the resident container” is useful; “keep semantics” is not. Direct mappings need no long report, and no confidence rating is required.

## Numeric behavior

Distinguish input, intermediate, result and local index ranges. Follow the supplied numeric policy; arbitrary mathematical values retain arbitrary range, checked values explicitly report unrepresentable intermediates/results. Sample bounds do not establish an intermediate bound. Word operations retain the source modular width.

Inspect conversions as well as arithmetic. A natural value is not safely signed just because both types have the same bit width. For source-clamping take/drop, establish the clamp in the source numeric domain before narrowing. For indexing and other operations, inspect their own boundary definitions. Native subtraction, division, remainder, shifts and zero cases need the defining source operation, not an inference from the name.

Read `semantic-adaptation/references/numeric-semantics.md` when mapping mathematical integers, changing widths/signs or implementing division, shifts or source totalized arithmetic.

## Representation and operation selection

Identify observable order, duplicates, comparison relation, empty behavior, old-version persistence and polymorphic operations. Existing libraries are a useful starting choice when they cover the contract; add a thin wrapper for semantic differences. Custom infrastructure needs a concrete reason, such as missing operations or unsuitable representation costs. No specific library is mandatory.

A list is not automatically a set; UTF-8 byte/string operations are not automatically HOL character-list operations. A native operation can replace source machinery only under its complete required contract. Local loopification or representation changes must preserve state transitions and observable behavior. Major business algorithm or logical-data-structure redesign follows the project's source-optimization policy.

Read `semantic-adaptation/references/representation-conditions.md` for collection replacement, persistent structures, ordering, higher-order representation and native-operation substitution.

## Scoped implementation choices

In source-v6, semantic adaptation produces an implementation plan, not Isabelle printing declarations. Choose representations and operations with explicit scope: an entire source type, a type instance, a function or a use site. A local bound never justifies globally narrowing natural numbers. Coordinate support and callers when an interface changes.

Record source IDs, actual Rust items, implementation kind, source basis and conditions. A native/inline/replacement boundary covers the source entity's full required behavior, including dependencies implemented inside it. Original definitions remain available for review. Multiple source helpers may share one Rust implementation; preserve original exports and polymorphism. Mapping coverage is traceability, not equivalence proof. Source-v6 does not install or load code_printing. The legacy isabelle-syntax reference is only for historical printer workflows.

External-interface choices require source declarations/artifacts. An OCaml name or missing equation alone is not evidence of FFI; retain unknowns and request definitions.

## Program context

Use program_model source specifications, execution equations, instantiated use sites, types/classes and implementation boundaries together. For a representation or operation choice, request callers and dependencies of the affected entity before assuming a local condition holds globally. An occurrence edge does not prove uniqueness, persistence, range or non-escape. Record unresolved conditions explicitly. Cite stable entity IDs and equation/use paths in decisions; associate affected_symbols with the choice so repair can retrieve its source context.
