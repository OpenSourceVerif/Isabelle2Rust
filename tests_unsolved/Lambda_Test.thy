theory Lambda_Test
  imports Main "Rust.Rust_Setup"
begin

definition id :: "'a \<Rightarrow> 'a" where
  "id \<equiv> (\<lambda>x. x)"


(*
pub mod lambda {
    pub fn id<T>(x: T) -> T {
        (|xa: T| xa)(x)
    }
}
*)

definition inc :: "int \<Rightarrow> int" where
  "inc \<equiv> (\<lambda>x. x + 1)"


definition add_n :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "add_n n \<equiv> (\<lambda>x. x + n)"

 definition add_n_2 ::  "int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "add_n_2 n \<equiv> (\<lambda>x. (\<lambda>y. x + y + n))"

 definition add_n_3 ::  "int \<Rightarrow> (int \<Rightarrow> int \<Rightarrow> int)" where
  "add_n_3 n \<equiv> (\<lambda>x y. x + y + n)"

definition test_add_n_2 :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "test_add_n_2 x \<equiv> (\<lambda>y. ((add_n_2 1) x) y)"

definition int_pair :: "int \<Rightarrow> (int \<times> int)" where
  "int_pair x = (x, x)"

definition app :: "(int \<Rightarrow> int) \<Rightarrow> int \<Rightarrow> int" where
  "app f x = f x"

definition app2 :: "int \<Rightarrow> (int \<Rightarrow> int) \<Rightarrow> int" where
  "app2 x f = f x"

definition add3 :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "add3 x y z = x + y + z"

export_code id in Rust
export_code inc in Rust

export_code add_n in Rust

export_code add_n_2 add_n_3 test_add_n_2 in Rust

export_code add_n int_pair app app2 add3 in Rust

end