theory Class_Poly_Test
  imports Main "Rust.Rust_Setup"
begin

class inc =
  fixes inc :: "'a \<Rightarrow> 'a"

instantiation option :: (inc) inc
begin

definition inc_option :: "'a option \<Rightarrow> 'a option"
  where
    "inc_option x =
       (case x of
          None \<Rightarrow> None
        | Some a \<Rightarrow> Some (inc a))"

instance ..
end

definition test_inc_option :: "'a::inc option \<Rightarrow> 'a option" where
"test_inc_option x = inc x"


export_code test_inc_option in Rust

end
