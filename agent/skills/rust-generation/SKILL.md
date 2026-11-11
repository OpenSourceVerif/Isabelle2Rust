---
name: rust-generation
description: Design, generate and review complete Rust implementations of Isabelle computations using coherent interfaces, source-grounded ownership choices and explicit structural costs.
---

# Rust generation

Implement original exports and the active dependency closure using source equations and scoped implementation choices. Native operations, traits and inlining may cover multiple symbols; record their realizations. Source equations define behavior; semantic-adaptation checks whether representations and native operations satisfy that behavior. This skill guides their implementation in Rust.

## Establish structure and interfaces

Identify exported signatures, constructors, recursive dependency groups and higher-order parameters before filling bodies. Coordinate module visibility, type parameters, trait bounds and calling conventions across callers. Preserve source polymorphism and constructor payload provenance; do not specialize an API to its testing instance. Add Clone, Copy, Ord, Hash or lifetime bounds only when actual operations justify them.

Preserve branch priority, order, duplicates, empty cases and numeric policy. A search key is not interchangeable with the payload of a matched node unless the source inserts that key. Inspect the equation rather than inferring helpers from names. Map adapted-away operations to their support/native realization and include them in implementation review.

## Choose ownership across the call chain

Read-only queries usually start with borrowing. Consuming transformations may move elements into an owned result. Check whether callers still need the input: removing an internal clone can force an entire input clone at each call site. An owned result from a borrow may still need payload copies.

Local mutation requires earlier versions to be unobservable. Immutable sharing is useful when versions/subtrees are actually reused; it adds reference-count and path-reconstruction work. Choose from value use, not a universal preference for Box, Rc, borrowing or cloning.

Read `rust-generation/references/ownership-examples.md` for persistent structures, interface changes, moves across branches/captures or ownership diagnostics.

## Generic and higher-order code

Choose callable traits from how the function is invoked and what captures do. Do not erase every callable or impose 'static merely to compile. Returning or storing a closure changes its lifetime and representation requirements; generic recursive callable types can also need a stable interface.

Read `rust-generation/references/closures-and-generics.md` for escaping/stored callables, recursive higher-order functions and polymorphic trait-bound problems.

## Control flow and structural cost

Inspect loops, recursion and support code for repeated shifts, scans, tail copies, intermediate containers, allocations and representation round trips. Tail recursion may become a loop when state transitions remain equivalent. Non-tail recursion has pending work that must be represented. Traversal fusion and buffer reuse require preserved order, short-circuiting, errors and callback behavior.

Read `rust-generation/references/structural-costs.md` when changing traversal, recursion, worklists, allocation or representation conversion. Treat cost arguments as static hypotheses; measured improvement requires measurement under the project protocol.

## Review the resulting implementation

The first quick-refine pass happens on the complete Rust library and support before compilation. Review completeness, idiomatic interfaces and structural cost; patch concrete problems or accept unchanged code. Later reviews focus on changes introduced during repairs and connector correctness. Review conclusions are model judgments, not successful compiler or behavior checks.

Check source/API completeness, interfaces/ownership and structural cost. Inspect controller quality_findings as leads, not verdicts. For a material choice report conditions, source basis and tradeoffs; optional minor direct translations need no report. Adapted support functions need their own semantic scrutiny: a business test may never exercise their sign or zero cases.

An Isabelle list has constant-time head/tail decomposition. A Vec translation using remove(0), insert(0) or allocating tails can add an asymptotic cost absent from that source. Inspect local queue/stack operations and preserve successor/output order. Do not defend a Rust cost merely because the code resembles a source equation.

Compiler and behavioral failures switch to code-repair. Its focused patch procedure can request these ownership, closure and structural-cost references; it does not repeat initial generation. Major business-algorithm/logical-data-structure changes remain subject to the source-optimization policy.

## Program context

Use the program model to coordinate recursive groups and caller/callee interfaces before filling bodies. program_state links source entities to declared Rust realizations, representation decisions and exact validation versions. After an interface or representation change, inspect affected callers/support and reconsider stale decisions against source facts. Compiler, behavior, generic-interface and structural-cost conclusions have separate scopes; preserve that distinction in review. This extends the existing review, not a new mandatory test stage.
