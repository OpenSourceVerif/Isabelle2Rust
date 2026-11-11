---
name: ownership-optimization
description: Implement complete Thingol programs in Rust with program-specific borrowing, moves and sharing, optionally exploring at most three meaningful ownership alternatives.
---

The complete final Thingol program and effective bindings define the task.
Translate every remaining symbol; report how class/instance machinery is
realized or inlined as well as ordinary functions. Keep the source algorithm,
constructor relationships and value behavior. A mapping report is traceability,
not a proof of Rust equivalence.

Analyze actual lifetimes and reuse before choosing ownership. Borrow read-only
inputs, move uniquely consumed values, reuse exclusive buffers, and consider
immutable Rc sharing where old versions/subtrees are used by multiple results.
Box and move may be preferable when sharing is unnecessary. Arc is relevant only
when cross-thread sharing is required. Do not replace necessary work with clone
everywhere, or introduce clones merely to distinguish candidates.

Choose one to three genuinely different ownership plans for this program. A
simple read-only query may only need one. Alternatives share the same numerical
and collection adaptation decisions. Document each alternative's concrete reason
and any minimally necessary structural adjustment. Do not redesign the source
algorithm or data structure merely to create a second candidate.

Support code supplied during preprocessing is an initial implementation, not a
blanket immutable file. Ownership changes may update support, signatures,
constructors and callers consistently. If an Isabelle printing or code_module
also mentions the old ownership representation, return an ownership_adapter
revision for Isabelle reloading. Keep numerical semantics, source definitions and
the logical mapping unchanged. Do not turn ownership exploration into semantic
profile search. Each candidate retains its exact final support and bindings.

Compile/test failures are repaired in the existing candidate. Prefer explicit
local edits and preserve working code. Inspect the actual assembled crate and
avoid duplicate imports of controller-supplied root names. Repeated identical
code/errors mean no progress, not a successful repair. Rustc and behavior tests
decide acceptance; performance selection compares only passing candidates and
does not initiate another Rust optimization loop.

Preserve source polymorphism in both the plan and generated public API. A UBig
observation wrapper is one instantiation, not the exported program's full type
domain. Generic index, heap, sorting and reachability operations must retain
appropriate type parameters/traits. Borrowing plans should use &[T], Tree<T>,
etc. where the original Thingol is polymorphic. Report concrete Rust parameter
names for exported type variables; changing ownership never justifies dropping
a source type parameter.
