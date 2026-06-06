theory Semigroup_Test
  imports
  Main "Rust.Rust_Setup"
begin

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+s" 65)


class monoid = semigroup +
  fixes zero :: "'a"

definition cls :: "'a::monoid \<Rightarrow> 'a \<Rightarrow> 'a" where
"cls x y = plus x y"

export_code cls in Rust

end