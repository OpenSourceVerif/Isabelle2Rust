theory Constructor_Shape_Control_Test
  imports Rust_Base_Setup
begin

text \<open>
  Explicit constructor type arguments must preserve the Rust representation
  selected by a class dictionary. A nested function instance is represented as
  two unary Rc closures; the nullary carrier constructor must use that contextual
  shape rather than force a flat two-argument closure from the HOL arrow type.
\<close>

class shape_probe =
  fixes shape_probe :: "'a \<Rightarrow> bool"

instantiation bool :: shape_probe
begin
definition shape_probe_bool :: "bool \<Rightarrow> bool"
  where "shape_probe_bool x = x"
instance ..
end

instantiation "fun" :: (type, shape_probe) shape_probe
begin
definition shape_probe_fun :: "('a \<Rightarrow> 'b) \<Rightarrow> bool"
  where "shape_probe_fun _ = True"
instance ..
end

datatype 'a shape_carrier = ShapeVacant | ShapeChosen 'a

instantiation shape_carrier :: (shape_probe) shape_probe
begin
fun shape_probe_shape_carrier :: "'a shape_carrier \<Rightarrow> bool"
  where "shape_probe_shape_carrier ShapeVacant = True"
  | "shape_probe_shape_carrier (ShapeChosen x) = shape_probe x"
instance ..
end

definition probe_empty_function :: bool
  where "probe_empty_function = shape_probe (ShapeVacant :: (bool \<Rightarrow> bool \<Rightarrow> bool) shape_carrier)"

export_code probe_empty_function in Rust module_name ConstructorShape

end
