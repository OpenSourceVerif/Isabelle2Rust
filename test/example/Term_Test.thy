theory Term_Test
  imports Main "Rust.Rust_Base_Setup"
begin

definition make_pair :: "int \<Rightarrow> (int \<Rightarrow> int) \<times> int" where
  "make_pair y = ((\<lambda>x. x + y), y)"

definition carry3 ::
  "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool \<times> bool \<times> bool" where
  "carry3 c = (\<lambda>x y. (c, x, y))"

definition call_returned ::
  "bool \<Rightarrow> bool \<Rightarrow> bool \<times> bool \<times> bool" where
  "call_returned c x = ((carry3 c) x) False"

fun drop_two :: "int list \<Rightarrow> int list" where
  "drop_two xs =
    (case xs of
       Cons _ (Cons _ rest) \<Rightarrow> rest
     | _ \<Rightarrow> [])"

export_code make_pair carry3 call_returned drop_two in Rust

end
