theory Qualified_Instance_Identity_Test
  imports Rust_Base_Setup
begin

text \<open>
  Distinct qualified HOL types may have the same final name. Their instance
  methods then share the short probe_token_inst segment but belong to separate
  implementations. Each implementation must retain both methods and its own
  parameter bounds. Left delegates to its payload's probe; Right reads its
  Boolean field and imposes no class constraint on the payload.
\<close>

class probe =
  fixes read_probe :: "'a \<Rightarrow> bool"
    and flip_probe :: "'a \<Rightarrow> bool"

instantiation bool :: probe
begin
definition read_probe_bool :: "bool \<Rightarrow> bool" where "read_probe_bool b = b"
definition flip_probe_bool :: "bool \<Rightarrow> bool" where "flip_probe_bool b = (\<not>b)"
instance ..
end

setup \<open>Sign.add_path "Left"\<close>
datatype 'a token = LeftToken 'a

instantiation token :: (probe) probe
begin
fun read_probe_token :: "'a token \<Rightarrow> bool"
  where "read_probe_token (LeftToken x) = read_probe x"
fun flip_probe_token :: "'a token \<Rightarrow> bool"
  where "flip_probe_token (LeftToken x) = flip_probe x"
instance ..
end
setup \<open>Sign.parent_path\<close>

setup \<open>Sign.add_path "Right"\<close>
datatype 'a token = RightToken bool 'a

instantiation token :: (type) probe
begin
fun read_probe_token :: "'a token \<Rightarrow> bool"
  where "read_probe_token (RightToken b x) = b"
fun flip_probe_token :: "'a token \<Rightarrow> bool"
  where "flip_probe_token (RightToken b x) = (\<not>b)"
instance ..
end
setup \<open>Sign.parent_path\<close>

definition read_left :: "'a::probe Left.token \<Rightarrow> bool"
  where "read_left x = read_probe x"
definition flip_left :: "'a::probe Left.token \<Rightarrow> bool"
  where "flip_left x = flip_probe x"
definition read_right :: "'a Right.token \<Rightarrow> bool"
  where "read_right x = read_probe x"
definition flip_right :: "'a Right.token \<Rightarrow> bool"
  where "flip_right x = flip_probe x"

definition left_values :: "bool \<Rightarrow> bool \<times> bool"
  where "left_values b = (read_probe (LeftToken b), flip_probe (LeftToken b))"
definition right_values :: "bool \<Rightarrow> 'a \<Rightarrow> bool \<times> bool"
  where "right_values b x = (read_probe (RightToken b x), flip_probe (RightToken b x))"

export_code read_probe flip_probe read_left flip_left read_right flip_right left_values right_values
  in Rust module_name QualifiedInstanceIdentity

end
