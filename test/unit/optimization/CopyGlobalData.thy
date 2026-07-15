theory CopyGlobalData
  imports Main "Rust.Rust_Setup"
begin

datatype global_char =
  GlobalChar bool bool

datatype 'a global_list =
    GlobalNil
  | GlobalCons 'a "'a global_list"

fun duplicate_left :: "'a \<Rightarrow> 'a \<times> 'a" where
  "duplicate_left x = (x, x)"

fun duplicate_right :: "'a \<Rightarrow> 'a \<times> 'a" where
  "duplicate_right x = (x, x)"

(* Give the two generic callees the same Rust basename in distinct modules. *)
code_identifier
  constant duplicate_left  \<rightharpoonup> (Rust) "CopyGlobalLeft.duplicate"
| constant duplicate_right \<rightharpoonup> (Rust) "CopyGlobalRight.duplicate"

end
