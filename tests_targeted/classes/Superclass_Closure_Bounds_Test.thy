theory Superclass_Closure_Bounds_Test
  imports Rust_Base_Setup
begin

text \<open>
  Two independent subclasses share an executable superclass. Their lifted
  instances have different parameter constraints. When the superclass method
  is absent from the export, its legality-only impl must use bounds guaranteed by both
  descendants, not those of whichever sibling method is visited first.
  Both generic roots must compile without requiring the other sibling class.
\<close>

class closure_base =
  fixes closure_base_op :: "'a \<Rightarrow> bool"

class closure_parent = closure_base +
  fixes closure_parent_op :: "'a \<Rightarrow> bool"

class closure_left = closure_parent +
  fixes closure_left_op :: "'a \<Rightarrow> bool"

class closure_right = closure_parent +
  fixes closure_right_op :: "'a \<Rightarrow> bool"

datatype 'a closure_box = ClosureBox 'a

instantiation closure_box :: (closure_base) closure_base
begin
fun closure_base_op_closure_box :: "'a closure_box \<Rightarrow> bool"
  where "closure_base_op_closure_box (ClosureBox x) = closure_base_op x"
instance ..
end

instantiation closure_box :: (closure_parent) closure_parent
begin
fun closure_parent_op_closure_box :: "'a closure_box \<Rightarrow> bool"
  where "closure_parent_op_closure_box (ClosureBox x) = closure_parent_op x"
instance ..
end

instantiation closure_box :: (closure_left) closure_left
begin
fun closure_left_op_closure_box :: "'a closure_box \<Rightarrow> bool"
  where "closure_left_op_closure_box (ClosureBox x) = closure_left_op x"
instance ..
end

instantiation closure_box :: (closure_right) closure_right
begin
fun closure_right_op_closure_box :: "'a closure_box \<Rightarrow> bool"
  where "closure_right_op_closure_box (ClosureBox x) = closure_right_op x"
instance ..
end

definition closure_left_result :: "'a::closure_left closure_box \<Rightarrow> bool"
  where "closure_left_result x = closure_left_op x"

definition closure_right_result :: "'a::closure_right closure_box \<Rightarrow> bool"
  where "closure_right_result x = closure_right_op x"

export_code closure_left_result closure_right_result
  in Rust module_name ClosureBounds

text \<open>
  Making the superclass method reachable must keep its real implementation
  and avoid a duplicate closure impl. The generic superclass operation also
  keeps its class node in the generated program.
\<close>

definition closure_base_result :: "'a::closure_base closure_box \<Rightarrow> bool"
  where "closure_base_result x = closure_base_op x"

export_code closure_left_result closure_right_result closure_base_result
  in Rust module_name ClosureComplete

text \<open>
  An explicit base implementation can add an operational equality requirement
  absent from its logical HOL sort. The intermediate parent remains missing.
  Its closure bounds must retain equality inherited by both child instances.
\<close>

datatype 'a closure_pair = ClosurePair 'a 'a

instantiation closure_pair :: (type) closure_base
begin
fun closure_base_op_closure_pair :: "'a closure_pair \<Rightarrow> bool"
  where "closure_base_op_closure_pair (ClosurePair x y) = (x = y)"
instance ..
end

instantiation closure_pair :: (closure_parent) closure_parent
begin
fun closure_parent_op_closure_pair :: "'a closure_pair \<Rightarrow> bool"
  where "closure_parent_op_closure_pair (ClosurePair x y) = closure_parent_op x"
instance ..
end

instantiation closure_pair :: (closure_left) closure_left
begin
fun closure_left_op_closure_pair :: "'a closure_pair \<Rightarrow> bool"
  where "closure_left_op_closure_pair (ClosurePair x y) = closure_left_op x"
instance ..
end

instantiation closure_pair :: (closure_right) closure_right
begin
fun closure_right_op_closure_pair :: "'a closure_pair \<Rightarrow> bool"
  where "closure_right_op_closure_pair (ClosurePair x y) = closure_right_op y"
instance ..
end

definition closure_pair_left :: "'a::closure_left closure_pair \<Rightarrow> bool"
  where "closure_pair_left x = closure_left_op x"

definition closure_pair_right :: "'a::closure_right closure_pair \<Rightarrow> bool"
  where "closure_pair_right x = closure_right_op x"

definition closure_pair_base :: "'a closure_pair \<Rightarrow> bool"
  where "closure_pair_base x = closure_base_op x"

export_code closure_pair_left closure_pair_right closure_pair_base
  in Rust module_name ClosureOperational

end
