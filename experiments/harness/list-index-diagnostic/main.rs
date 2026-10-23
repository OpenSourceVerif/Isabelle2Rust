use num_bigint::BigInt;
use exported::Reference::{self as r, Equal, List};
use std::{hint::black_box, rc::Rc, time::Instant};
mod candidate;

// Instrumentation is compiled separately; timed binaries have no allocator wrapper.
#[cfg(feature = "alloc")]
mod allocation {
    use std::alloc::{GlobalAlloc, Layout, System};
    use std::sync::atomic::{AtomicUsize, Ordering::Relaxed};
    pub static CALLS: AtomicUsize = AtomicUsize::new(0);
    pub static BYTES: AtomicUsize = AtomicUsize::new(0);
    pub struct Counter;
    unsafe impl GlobalAlloc for Counter {
        unsafe fn alloc(&self, l: Layout) -> *mut u8 {
            CALLS.fetch_add(1, Relaxed); BYTES.fetch_add(l.size(), Relaxed);
            unsafe { System.alloc(l) }
        }
        unsafe fn dealloc(&self, p: *mut u8, l: Layout) { unsafe { System.dealloc(p, l) } }
        unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
            CALLS.fetch_add(1, Relaxed); BYTES.fetch_add(n, Relaxed);
            unsafe { System.realloc(p, l, n) }
        }
    }
}
#[cfg(feature = "alloc")]
#[global_allocator]
static ALLOCATOR: allocation::Counter = allocation::Counter;

#[derive(Clone)]
struct Value(BigInt);
impl Equal for Value { fn equal(a: Self, b: Self) -> bool { a.0 == b.0 } }
#[derive(Clone)]
struct Shared(Rc<BigInt>);
impl Equal for Shared { fn equal(a: Self, b: Self) -> bool { a.0 == b.0 } }
fn list(xs: Vec<BigInt>) -> List<Value> {
    xs.into_iter().rev().fold(List::Nil, |tail, x| List::Cons(Value(x), Box::new(tail)))
}
fn run(mut f: impl FnMut(), iterations: usize) {
    for _ in 0..10 { f(); }
    #[cfg(feature = "alloc")]
    {
        use std::sync::atomic::Ordering::Relaxed;
        allocation::CALLS.store(0, Relaxed); allocation::BYTES.store(0, Relaxed);
        f();
        let calls = allocation::CALLS.load(Relaxed);
        let bytes = allocation::BYTES.load(Relaxed);
        println!("{calls} {bytes}");
    }
    #[cfg(not(feature = "alloc"))]
    {
        let start = Instant::now();
        for _ in 0..iterations { f(); }
        println!("{} {}", start.elapsed().as_nanos(), iterations);
    }
}
fn main() {
    let args: Vec<_> = std::env::args().collect();
    let op = args[1].as_str();
    let n: usize = args[2].parse().unwrap();
    let mode = args[3].as_str();
    let large = args[4] == "large";
    let iterations = args[5].parse().unwrap();
    let offset = if large { BigInt::from(1) << 130 } else { BigInt::from(0) };
    let xs: Vec<BigInt> = (0..n).map(|i| &offset + BigInt::from(i)).collect();
    let q = match mode { "first" => 0, "last" => n-1, "absent" => n+1, _ => panic!() };
    let x = &offset + BigInt::from(q);
    let expected = BigInt::from(if mode == "absent" { n } else { q });
    let linked = list(xs.clone());
    let shared = xs.iter().rev().fold(List::Nil, |tail, v| List::Cons(Shared(Rc::new(v.clone())), Box::new(tail)));
    let sx = Shared(Rc::new(x.clone()));
    assert_eq!(candidate::last_index(&xs, &x), expected);
    assert_eq!(r::last_index(&linked, Value(x.clone())), expected);
    assert_eq!(r::last_index(&shared, sx.clone()), expected);
    match op {
        "clone_drop" => run(|| { drop(black_box(black_box(&xs).clone())); drop(black_box(black_box(&x).clone())); }, iterations),
        "candidate_e2e" => run(|| {
            let a = black_box(xs.clone()); let b = black_box(x.clone());
            drop(black_box(candidate::last_index(&a, &b)));
        }, iterations),
        "candidate_kernel" => run(|| { drop(black_box(candidate::last_index(black_box(&xs), black_box(&x)))); }, iterations),
        "prepare_list" => run(|| { drop(black_box(list(black_box(xs.clone())))); drop(black_box(x.clone())); }, iterations),
        "stage2_e2e" => run(|| {
            let a = list(black_box(xs.clone())); let b = black_box(x.clone());
            drop(black_box(r::last_index(&a, Value(b))));
        }, iterations),
        "stage2_kernel" => run(|| { drop(black_box(r::last_index(black_box(&linked), Value(black_box(x.clone()))))); }, iterations),
        "stage2_shared_kernel" => run(|| { drop(black_box(r::last_index(black_box(&shared), black_box(sx.clone())))); }, iterations),
        "list_clone_drop" => run(|| { drop(black_box(black_box(&linked).clone())); }, iterations),
        "reverse_clone" => run(|| { drop(black_box(r::rev(black_box(&linked).clone()))); }, iterations),
        "length" => run(|| { drop(black_box(r::size_list(black_box(&linked)))); }, iterations),
        _ => panic!("unknown operation"),
    }
}
