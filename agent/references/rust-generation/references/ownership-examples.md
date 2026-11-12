# Ownership, sharing and persistence

## Borrow or consume

For a query after which a caller continues to use a collection, &[T] avoids transferring ownership. An owned returned element may need T: Clone; returning a reference changes lifetime/API requirements and is only valid when it matches the intended interface.

For an owned transformation whose input is dead, into_iter and destructuring can transfer payloads directly into the result. Negative example: changing a reusable tree query to consume Tree<T> makes callers clone the tree before querying. Inspect the callers and required old versions before calling this an optimization.

## Persistent versus exclusive updates

Multiple live tree versions can share immutable subtrees through Rc and rebuild only a changed path. Costs include reference operations, new path nodes and cloning payloads that cannot be moved from shared ownership. Rc::clone shares an allocation; cloning Box/tree values can be deep. Verify which clone is invoked.

Unique ownership may permit moving fields from Box nodes. Local mutation can reuse an exclusive buffer once old logical versions are unobserved. Neither textual last use nor variable renaming establishes uniqueness: account for branches, captures and surviving borrows.

## Diagnostics and reconstruction

If a field needs T but an expression has &T, inspect whether the source requires the existing node's payload, a borrowed result or a fresh independent value. Cloning the reference does not produce the payload. Do not add Copy to all exported generic types merely because the current test uses integers.

When reconstructing a matched tree after searching, retain its original payload and child order unless the defining equation explicitly replaces them. A search key can compare equal while carrying different data. Treat this as variable provenance, not just an ownership error.

For a borrow-checker error caused by competing views, narrow borrow lifetimes or separate reads from exclusive updates when source order allows. If it requires a different ownership interface, update affected callers together and reconsider any earlier cost claims.
