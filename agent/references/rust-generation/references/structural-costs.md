# Structural costs and equivalent local changes

## Worklists and sequences

Repeated remove(0) from Vec shifts the remaining elements. A local VecDeque can remove that shift when the worklist needs front operations; preserve successor order when inserting a prefix. Negative example: replacing a stack-like traversal with FIFO order changes the computation. A set-based deduplication is a further semantic change, not implied by container substitution.

Repeated tail.to_vec(), concatenation or row-tail rebuilding may allocate/copy on every recursive step. Borrowed slices or index ranges can preserve access without rebuilding. A consuming iterator retained across steps can move owned elements without rebuilding its tail. Recreating into_iter, taking next, then collecting the remainder every iteration still consumes the tail in linear work; absence of clone or allocator reuse does not make it constant time.

For an owned worklist that prepends a successor list, a local VecDeque can use pop_front and push_front in reversed successor order. Scan accumulated results in their original order; append/prepend changes must preserve short-circuit callback order. Convert to the public Vec result once at the boundary. This is a local sequence representation change, not authority to change traversal order, deduplicate with a set, or replace the algorithm. Check lifetimes and returned ownership before choosing.

## Recursion and intermediates

For tail recursion identify the explicit next-state tuple and termination behavior, then update it in a loop. For non-tail recursion preserve pending computations, order and stack structure; an accumulator is valid only when its relationship to the source result is established. Do not introduce memoization or replace the business algorithm as an incidental Rust optimization.

Traversal fusion can avoid intermediate containers if callback order, short-circuiting and failure behavior agree. Two passes and one interleaved pass may observe errors differently. A reusable buffer requires old contents to be unobservable and no escaped borrow to depend on them.

## Costs across boundaries

Inspect representation conversions in callers and support as well as the main function. Eliminating a conversion in one function can merely move it into every caller. Query/consuming interface choices can dominate the cost of a local clone removal. Count the work implied by the structure, then describe the tradeoff without claiming measured speed.

For each material finding report the code location, source and Rust costs separately, candidate change, semantic conditions and choice to change or retain. Source immutable list head/tail and cons are constant-time operations; rebuilding a Vec tail/cons is a representation cost, not a source requirement. An actual source size bound, API constraint or persistence requirement may justify retaining it; small observed test inputs do not establish such a condition. No container or clone is universally forbidden.
