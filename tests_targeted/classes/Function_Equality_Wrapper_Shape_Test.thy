theory Function_Equality_Wrapper_Shape_Test
  imports "HOL.Transfer" "Rust.Rust_Base_Setup"
begin

(* Transfer's `is_equality` compares a binary relation with HOL equality through
   the ordinary polymorphic helper `HOL.eq`, rather than calling the `Equal`
   class parameter directly.  The helper's type argument is a function and its
   dictionary is the recursively constructed function-equality instance, so its
   two Rust arguments must be nested unary trait objects while the exported
   wrapper still accepts the backend's ordinary flat binary relation.

   Printing the helper arguments only from their erased itype instead selects
   `Rc<dyn Fn(bool, bool) -> bool>` as the generic Rust type and fails with E0277,
   because the reconstructed function `Equal` impl is unary and recursive.

   The existential example additionally places a three-argument function type
   inside the predicate argument of the ordinary `HOL.ex` wrapper.  Its closure
   parameter annotation must be printed from the nested `Enum` dictionary shape,
   not from the flattened semantic binder type. *)

definition boolean_relation_is_equality ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool" where
  "boolean_relation_is_equality r \<longleftrightarrow> is_equality r"

definition has_boolean_ternary_function :: bool where
  "has_boolean_ternary_function \<longleftrightarrow>
    (\<exists>f :: bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool.
      f True False True)"

export_code boolean_relation_is_equality has_boolean_ternary_function in Rust

end
