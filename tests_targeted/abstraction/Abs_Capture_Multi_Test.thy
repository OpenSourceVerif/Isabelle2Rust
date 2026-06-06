theory Abs_Capture_Multi_Test
  imports Main "Rust.Rust_Setup"
begin

(* Regression test for closure capture handling.
   Before the fix, a `move` closure consumed every captured outer variable,
   making subsequent closures or uses fail to compile in Rust.
   The fix pre-copies each captured variable into a fresh `_cap` binding
   and rewrites free occurrences inside the closure body accordingly.
   This case exercises multiple captures shared by multiple closures, with
   the captured variables still used afterwards. *)

definition multi_caps :: "int" where
"multi_caps = (let a::int = 3 in
                let b::int = 4 in
                let f = (\<lambda>x::int. x + a + b) in
                let g = (\<lambda>x::int. a * x + b) in
                let s::int = a + b in
                (f s) + (g s))"

export_code multi_caps in Rust

end
