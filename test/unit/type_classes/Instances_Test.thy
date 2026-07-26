theory Instances_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Concrete and parametric instances become Rust impl blocks. *)

class inc =
  fixes inc :: "'a \<Rightarrow> 'a"

instantiation nat :: inc
begin

definition inc_nat where
  "inc (n::nat) = n + 1"

instance ..
end

fun add2 :: "nat \<Rightarrow> nat" where
  "add2 x = inc x"

instantiation option :: (inc) inc
begin

definition inc_option :: "'a option \<Rightarrow> 'a option" where
  "inc_option x =
    (case x of
       None \<Rightarrow> None
     | Some a \<Rightarrow> Some (inc a))"

instance ..
end

definition inc_option_apply :: "'a::inc option \<Rightarrow> 'a option" where
  "inc_option_apply x = inc x"

datatype 'a wrap = Wrap 'a

instantiation wrap :: (inc) inc
begin

fun inc_wrap :: "'a::inc wrap \<Rightarrow> 'a wrap" where
  "inc_wrap (Wrap x) = Wrap (inc x)"

instance ..
end

definition inc_wrap_apply :: "'a::inc wrap \<Rightarrow> 'a wrap" where
  "inc_wrap_apply x = inc x"

export_code
  add2 inc_option_apply inc_wrap_apply
  in Rust

end
