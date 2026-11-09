theory Recursive_Phantom_Test
  imports Rust_Base_Setup
begin

text \<open>
  A HOL type parameter can occur solely in recursive datatype applications.
  Rust requires a nonrecursive use, so textual occurrence is insufficient.
  Cover self recursion, mutual recursion and recursion underneath a list, and
  exercise the common marker table through constructors and case patterns.
  The productive pair is a control: its parameter reaches a real field through
  the other datatype and must not be classified as recursive-only.
\<close>

datatype ('a, 'b) recursive_phantom =
  Empty | More 'b "('a, 'b) recursive_phantom"

definition singleton_phantom :: "'b \<Rightarrow> ('a, 'b) recursive_phantom"
  where "singleton_phantom b = More b Empty"
fun is_empty_phantom :: "('a, 'b) recursive_phantom \<Rightarrow> bool"
  where "is_empty_phantom Empty = True"
  | "is_empty_phantom (More b tail) = False"

datatype 'a phantom_left = LEnd | LStep "'a phantom_right"
  and 'a phantom_right = RStep "'a phantom_left"

definition mutual_phantom :: "'a phantom_right"
  where "mutual_phantom = RStep (LStep (RStep LEnd))"
fun is_end_phantom :: "'a phantom_left \<Rightarrow> bool"
  where "is_end_phantom LEnd = True"
  | "is_end_phantom (LStep r) = False"

datatype 'a phantom_bush = Tip | Fork "'a phantom_bush list"
definition nested_phantom :: "'a phantom_bush"
  where "nested_phantom = Fork [Tip]"
fun is_tip_phantom :: "'a phantom_bush \<Rightarrow> bool"
  where "is_tip_phantom Tip = True"
  | "is_tip_phantom (Fork xs) = False"

datatype 'a productive_left = PLeft "'a productive_right"
  and 'a productive_right = PValue 'a | PAgain "'a productive_left"
definition productive_wrap :: "'a \<Rightarrow> 'a productive_left"
  where "productive_wrap a = PLeft (PValue a)"

export_code singleton_phantom is_empty_phantom mutual_phantom is_end_phantom
  nested_phantom is_tip_phantom productive_wrap in Rust

end
