#[cfg(allocation_metrics)]
use std::alloc::{GlobalAlloc, Layout, System};
#[cfg(allocation_metrics)]
use std::sync::atomic::{AtomicU64, Ordering};

#[cfg(allocation_metrics)]
struct CountingAllocator;

#[cfg(allocation_metrics)]
static ALLOCATED_BYTES: AtomicU64 = AtomicU64::new(0);

#[cfg(allocation_metrics)]
unsafe impl GlobalAlloc for CountingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let pointer = unsafe { System.alloc(layout) };
        if !pointer.is_null() {
            ALLOCATED_BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        pointer
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let pointer = unsafe { System.alloc_zeroed(layout) };
        if !pointer.is_null() {
            ALLOCATED_BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        pointer
    }

    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { System.dealloc(pointer, layout) }
    }

    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        let new_pointer = unsafe { System.realloc(pointer, layout, new_size) };
        if !new_pointer.is_null() {
            ALLOCATED_BYTES.fetch_add(new_size as u64, Ordering::Relaxed);
        }
        new_pointer
    }
}

#[cfg(allocation_metrics)]
#[global_allocator]
static GLOBAL_ALLOCATOR: CountingAllocator = CountingAllocator;

pub fn reset() {
    #[cfg(allocation_metrics)]
    ALLOCATED_BYTES.store(0, Ordering::Relaxed);
}

pub fn read() -> u64 {
    #[cfg(allocation_metrics)]
    {
        return ALLOCATED_BYTES.load(Ordering::Relaxed);
    }
    #[cfg(not(allocation_metrics))]
    0
}
