theory Semigroup_Option_Test
  imports Main "Rust.Rust_Setup"
begin

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+s" 65)

instantiation option :: (semigroup) semigroup
begin

fun plus_option :: "'a option \<Rightarrow> 'a option \<Rightarrow> 'a option" where
  "None +s None = None"
| "Some x +s None = Some x"
| "None +s Some x = Some x"
| "Some x +s Some y = Some (x +s y)"

instance ..
end

definition plus0_option :: "'a::semigroup option \<Rightarrow> 'a option " where
  "plus0_option x = x +s None"

export_code plus0_option in Rust

end
