# Closures, generics and interfaces

Local callable parameters can often be generic F with the required Fn/FnMut/FnOnce bound. Choose the weakest capability sufficient for the actual invocation pattern: repeated calls cannot consume a FnOnce closure each time. A mutable capture or FnMut call needs compatible access. The trait follows capture/invocation semantics, not whether the source parameter has a function type.

Passing a callable by reference can avoid repeatedly moving or wrapping it across recursion. Keep recursive argument types stable: creating successively nested closure types in a generic recursive call can lead to unbounded monomorphization. A stable borrowed callable, explicit environment or justified erased interface may be appropriate.

A closure returned from a function or stored in a structure must retain valid captures. Moving captures can create ownership; moving a reference does not extend the referent's lifetime. Do not solve escaping references by inventing 'static bounds unless the public contract actually requires them.

Stored heterogeneous callable values may need a common dynamic representation. Box owns one callable; Rc is justified when the same callable is shared. Partial application alone does not establish either need. Avoid allocation and dynamic dispatch for a local callable simply because an older backend used Rc<dyn Fn>.

For a generic source export, keep type parameters independent unless source types relate them. An index return type does not constrain the element type. Trait bounds should follow operations: equality does not establish ordering or hashing. Extra Clone/Copy/Ord/'static bounds can reduce the source API's capability even if the test instance compiles.
