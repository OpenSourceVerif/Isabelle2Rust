# Representation conditions

## Collections and ordering

A Vec preserves sequence order and duplicates. Slice access can coexist with owned Vec storage. Replacing a list with a set needs evidence that order and multiplicity are unobservable for every affected operation; membership-only use in one caller is not enough for a global list printing. Replacing association lookup needs the source rule for duplicate keys, not just equal behavior on unique keys.

A worklist with front removal and prefix insertion can use a local deque if insertion order reproduces the original successor sequence. Switching to a set with deduplication changes exploration and possibly callback order. That requires separate justification, not a container-cost claim.

## Native operation replacement

Before replacing a source sorting operation, establish the comparison relation, output order, stability where observable, duplicates, partial/total comparator assumptions and boundary behavior. Equal output on ordinary integers is insufficient for a polymorphic comparator. Preserve the designated business algorithm when project policy requires source-level authorization for redesign; do not hide a new algorithm behind a printing.

A string can replace a character list only under compatible character units and operations. Byte indexing, Unicode scalar indexing and grapheme indexing are different. Check actual source character representation and required operations.

## Persistence, representation and access

For immutable versions that coexist, sharing unchanged subtrees can preserve persistence with path copying. Mutation through an alias changes the old version. An exclusive temporary whose old versions are unobserved can use local mutation while preserving observable values. Choose Box/moves when ownership is unique; consider Rc when sharing is real. Shared fields do not eliminate path reconstruction, reference-count work or all payload clones.

Recursive fields need finite-size indirection. Box is one representation, not a semantic requirement. Native representations must still expose the original constructors/operations and generic capabilities required by callers.

## Functions and type classes

Local function parameters may use generic callables or borrowed callables. Stored heterogeneous functions can require a common erased representation. Partial application may require captures, but does not by itself require Rc<dyn Fn>. Inspect curried structure, capture lifetimes, source invocation patterns and required type-class operations. Rust traits can realize source nodes when their operations and bounds preserve the source interface.
