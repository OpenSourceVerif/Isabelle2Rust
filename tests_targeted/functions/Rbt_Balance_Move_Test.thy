theory Rbt_Balance_Move_Test
  imports "HOL-Library.RBT_Impl" "Rust.Rust_Base_Setup"
begin

(* hol-stress guidance test (Generate.thy: RBT_Impl.rs `balance` -- E0382
   "borrow of moved value: `s` / `t`: value borrowed here after move").

   `balance` takes parameters `s`, `t`, then inside a match arm rebinds locals of
   the SAME names (`let s = p0b; let t = p0c;`) and reuses each in two output
   nodes via an alias:

       let s = p0b; let t = p0c;
       let y = s;   let z = t;         // moves the non-Copy locals s, t
       Rbt::Branch(.., s.clone(), t.clone(), .. y.clone(), z.clone() ..)

   The clone-insertion pass, confused by the parameter/local name shadowing under
   deep nesting, emits `let y = s;` as a MOVE, so the following `s.clone()` is a
   use-after-move  =>  E0382.

   A hand-minimised alias (`let y = s.clone()` for a pattern-bound local) is
   already cloned correctly, so this pins the real trigger by re-exporting the
   library `balance` itself. The fix must clone/borrow an alias whose source is
   still live, robustly under shadowing. *)

export_code RBT_Impl.balance in Rust

end
