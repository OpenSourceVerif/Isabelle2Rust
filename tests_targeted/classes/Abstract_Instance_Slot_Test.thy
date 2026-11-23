theory Abstract_Instance_Slot_Test
  imports Rust_Base_Setup
begin

text \<open>
  An abstract code type has a single Datatype statement and no constructor
  statement in its dependency component. A reconstructed subclass instance
  can require superclass closure impls for that type. Emitting Datas and
  InstGroup in the same component used to overfill its one output slot and
  raise Subscript in Code_Namespace's padding. Host the closure impls at the
  existing explicit instance representative instead; retain the abstract
  type's PhantomData and the executable subclass method.
\<close>

class slot_parent =
  fixes slot_parent_op :: "'a \<Rightarrow> bool"

class slot_child = slot_parent +
  fixes slot_child_op :: "'a itself \<Rightarrow> bool"

typedecl 'a slot_abstract

instantiation slot_abstract :: (slot_child) slot_parent
begin
definition slot_parent_op_slot_abstract :: "'a slot_abstract \<Rightarrow> bool"
  where "slot_parent_op_slot_abstract _ = True"
instance ..
end

instantiation slot_abstract :: (slot_child) slot_child
begin
definition slot_child_op_slot_abstract :: "'a slot_abstract itself \<Rightarrow> bool"
  where "slot_child_op_slot_abstract _ = slot_child_op TYPE('a)"
instance ..
end

definition slot_result :: "'a::slot_child slot_abstract itself \<Rightarrow> bool"
  where "slot_result x = slot_child_op x"

export_code slot_result in Rust module_name AbstractSlot

text \<open>
  When the parent method is itself reachable, its explicit impl already exists.
  Export that control separately to check that host assignment creates neither
  a second parent impl nor a lost method.
\<close>
definition slot_parent_result :: "'a::slot_child slot_abstract \<Rightarrow> bool"
  where "slot_parent_result x = slot_parent_op x"

export_code slot_result slot_parent_result in Rust module_name AbstractSlotComplete

end
