theory Instance_Parameter_Order_Test
  imports Rust_Base_Setup
begin

text \<open>
  Methods of one instance can use different names for the same type slots.
  An unused method with its code equation removed has the scheme (b, a), while
  an executable reader has (a, b). The longer unused_box_copy name makes that
  empty method the first representative in Thingol's descending symbol order.
  The impl header follows it, so the reader's types and dictionary variables
  must be renamed consistently when its body is inlined.

  Only the second field needs marked. The unit/bool call therefore also checks
  that the first field does not accidentally inherit the second field's bound.
  The one-method marked instance is a control with no variable-name mismatch.
  No test calls the deliberately absent unused_box_copy implementation.
\<close>

class marked =
  fixes marked :: "'a \<Rightarrow> bool"

instantiation bool :: marked
begin
definition marked_bool :: "bool \<Rightarrow> bool" where "marked_bool b = b"
instance ..
end

datatype ('a, 'b) pair_box = PairBox 'a 'b

instantiation pair_box :: (type, marked) marked
begin
fun marked_pair_box :: "('a, 'b) pair_box \<Rightarrow> bool"
  where "marked_pair_box (PairBox x y) = marked y"
instance ..
end

class box_probe =
  fixes unused_box_copy :: "'a \<Rightarrow> 'a"
    and box_read :: "'a \<Rightarrow> bool"

instantiation pair_box :: (type, marked) box_probe
begin
fun box_read_pair_box :: "('a, 'b) pair_box \<Rightarrow> bool"
  where "box_read_pair_box (PairBox x y) = marked y"
definition unused_box_copy_pair_box :: "('a, 'b) pair_box \<Rightarrow> ('a, 'b) pair_box"
  where "unused_box_copy_pair_box x = x"
instance ..
end

declare unused_box_copy_pair_box_def [code del]

definition right_mark :: "('a, 'b::marked) pair_box \<Rightarrow> bool"
  where "right_mark x = marked x"

definition concrete_right_mark :: "unit \<Rightarrow> bool \<Rightarrow> bool"
  where "concrete_right_mark x y = marked (PairBox x y)"

definition right_probe :: "('a, 'b::marked) pair_box \<Rightarrow> bool"
  where "right_probe x = box_read x"

definition concrete_probe :: "unit \<Rightarrow> bool \<Rightarrow> bool"
  where "concrete_probe x y = box_read (PairBox x y)"

export_code box_probe_pair_box_inst.unused_box_copy_pair_box
  marked right_mark concrete_right_mark box_read right_probe concrete_probe
  box_probe_pair_box_inst.box_read_pair_box
  in Rust module_name InstanceParameterOrder

end
