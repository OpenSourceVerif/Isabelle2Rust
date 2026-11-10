theory Instance_Receiver_Position_Test
  imports Rust_Base_Setup
begin

text \<open>
  A class carrier can occur below an unrelated type constructor with the same
  short name. Both instances below return the carrier inside the standard
  option and product types. The specialized method's fully qualified identity,
  rather than the first matching short name in its result type, must determine
  which type receives the Rust impl. The generic method keeps the trait visible,
  and polymorphic wrappers preserve all parameters of each user datatype.
\<close>

class nested_seed =
  fixes nested_seed :: "'a Option.option \<times> bool"

setup \<open>Sign.add_path "ProductCase"\<close>
datatype ('a, 'b) prod = EmptyProduct | ProductPayload 'a 'b

instantiation prod :: (type, type) nested_seed
begin
definition nested_seed_prod :: "('a, 'b) prod Option.option \<times> bool"
  where "nested_seed_prod = (Some EmptyProduct, True)"
instance ..
end
setup \<open>Sign.parent_path\<close>

setup \<open>Sign.add_path "OptionCase"\<close>
datatype 'a option = EmptyOption | OptionPayload 'a

instantiation option :: (type) nested_seed
begin
definition nested_seed_option :: "'a option Option.option \<times> bool"
  where "nested_seed_option = (Some EmptyOption, False)"
instance ..
end
setup \<open>Sign.parent_path\<close>

instantiation bool :: nested_seed
begin
definition nested_seed_bool :: "bool Option.option \<times> bool"
  where "nested_seed_bool = (Some True, True)"
instance ..
end

definition product_seed :: "('a, 'b) ProductCase.prod Option.option \<times> bool"
  where "product_seed = nested_seed"
definition option_seed :: "'a OptionCase.option Option.option \<times> bool"
  where "option_seed = nested_seed"
definition bool_seed :: "bool Option.option \<times> bool"
  where "bool_seed = nested_seed"

lemma product_seed_value:
  "product_seed = (Some EmptyProduct, True)"
  by (simp add: product_seed_def nested_seed_prod_def)

lemma option_seed_value:
  "option_seed = (Some EmptyOption, False)"
  by (simp add: option_seed_def nested_seed_option_def)

export_code nested_seed product_seed option_seed bool_seed
  in Rust module_name InstanceReceiverPosition

end
