theory Registered_Result_Test
  imports Rust_Base_Setup
begin

text \<open>
  Registered target syntax consumes its own prefix of arguments; further HOL
  arrows can belong to a returned function. Instantiating the polymorphic
  identity at bool => bool => bool and applying only one returned-function
  argument used to zip unlike-sized lists (UnequalLengths). Complete returned
  applications must use Rust call syntax, and partial ones need eta expansion.
  Also cover a zero-placeholder callable expression and a plain runtime path.
\<close>

definition mapped_id :: "'a \<Rightarrow> 'a" where "mapped_id x = x"
definition native_and :: "bool \<Rightarrow> bool \<Rightarrow> bool"
  where "native_and x y = (x \<and> y)"
definition plain_not :: "bool \<Rightarrow> bool" where "plain_not x = (\<not> x)"

code_printing
  constant mapped_id \<rightharpoonup> (Rust) "_"
| constant native_and \<rightharpoonup> (Rust) "!std::rc::Rc::new(|x: bool, y: bool| x && y)"
| constant plain_not \<rightharpoonup> (Rust) "std::ops::Not::not"

definition syntax_partial :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> (bool \<Rightarrow> bool) option"
  where "syntax_partial f = Some (mapped_id f True)"
definition syntax_full :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "syntax_full f x y = mapped_id f x y"
definition syntax_native_partial :: "(bool \<Rightarrow> bool) option"
  where "syntax_native_partial = Some (native_and True)"
definition syntax_native_whole :: "(bool \<Rightarrow> bool \<Rightarrow> bool) option"
  where "syntax_native_whole = Some native_and"
definition syntax_plain_value :: "(bool \<Rightarrow> bool) option"
  where "syntax_plain_value = Some plain_not"
definition syntax_plain_call :: "bool \<Rightarrow> bool"
  where "syntax_plain_call x = plain_not x"

export_code syntax_partial syntax_full syntax_native_partial syntax_native_whole
  syntax_plain_value syntax_plain_call in Rust module_name RegisteredResult

end
