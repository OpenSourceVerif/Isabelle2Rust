theory Mapped_Declaration_Shape_Test
  imports Rust_Base_Setup
begin

text \<open>
  Registered templates retain the source declaration's type-variable relations.
  The mixed field requires a dictionary-selected function followed by a fixed
  flat callback, although both erase to the same HOL type. Reordered, repeated,
  unused and result-only variables must not be guessed from instantiated type
  equality. Repeated result variables use one representation before conversion.
\<close>

type_synonym mapped_callback = "bool \<Rightarrow> bool \<Rightarrow> bool"
datatype 'a mapped_mixed = MappedMixed "'a \<times> mapped_callback"

definition consume_mapped_mixed :: "'a::equal \<Rightarrow> 'a mapped_mixed \<Rightarrow> bool"
  where "consume_mapped_mixed f p =
    (case p of MappedMixed (g, h) \<Rightarrow> HOL.equal f g \<and> h False False)"

definition declaration_pair :: "'a \<Rightarrow> 'b \<Rightarrow> 'a \<times> 'b"
  where "declaration_pair a b = (a, b)"
definition declaration_swap :: "'a \<Rightarrow> 'b \<Rightarrow> 'b \<times> 'a"
  where "declaration_swap a b = (b, a)"
definition declaration_dup :: "'a \<Rightarrow> 'a \<times> 'a"
  where "declaration_dup a = (a, a)"
definition declaration_ignore :: "'a \<Rightarrow> 'b \<Rightarrow> 'b \<times> 'b"
  where "declaration_ignore ignored value = (value, value)"
definition declaration_plain_dup :: "'a \<Rightarrow> 'a \<times> 'a"
  where "declaration_plain_dup a = (a, a)"

code_printing
  constant declaration_pair \<rightharpoonup> (Rust) "!(_, _)"
| constant declaration_swap \<rightharpoonup> (Rust) "!(match (_, _) { (a, b) => (b, a) })"
| constant declaration_dup \<rightharpoonup> (Rust) "!(match _ { a => (a.clone(), a) })"
| constant declaration_ignore \<rightharpoonup> (Rust)
    "!(match (_, _) { (ignored, value) => (value.clone(), value) })"

definition observe_declaration_pair :: "mapped_callback \<Rightarrow> mapped_callback \<Rightarrow> bool"
  where "observe_declaration_pair f g = consume_mapped_mixed f (MappedMixed (declaration_pair f g))"
definition observe_declaration_swap :: "mapped_callback \<Rightarrow> mapped_callback \<Rightarrow> bool"
  where "observe_declaration_swap f g = consume_mapped_mixed f (MappedMixed (declaration_swap f g))"
definition observe_declaration_same :: "mapped_callback \<Rightarrow> bool"
  where "observe_declaration_same f = consume_mapped_mixed f (MappedMixed (declaration_swap f f))"
definition observe_declaration_dup :: "mapped_callback \<Rightarrow> bool"
  where "observe_declaration_dup f = consume_mapped_mixed f (MappedMixed (declaration_dup f))"
definition observe_declaration_ignore :: "bool \<Rightarrow> mapped_callback \<Rightarrow> bool"
  where "observe_declaration_ignore flag f = consume_mapped_mixed f (MappedMixed (declaration_ignore flag f))"
definition observe_plain_dup :: "mapped_callback \<Rightarrow> bool"
  where "observe_plain_dup f = consume_mapped_mixed f (MappedMixed (declaration_plain_dup f))"

datatype ('a, 'b) declaration_product = DeclarationProduct 'b 'a
code_printing
  type_constructor declaration_product \<rightharpoonup> (Rust) "!(_, _)"
| constant DeclarationProduct \<rightharpoonup> (Rust)
    "!(match (_, _) { (b, a) => (a, b) })"
datatype 'a mapped_constructor = MappedConstructor "('a, mapped_callback) declaration_product"
definition consume_mapped_constructor :: "'a::equal \<Rightarrow> 'a mapped_constructor \<Rightarrow> bool"
  where "consume_mapped_constructor f payload = HOL.equal f f"
definition observe_mapped_constructor :: "mapped_callback \<Rightarrow> mapped_callback \<Rightarrow> bool"
  where "observe_mapped_constructor f g =
    consume_mapped_constructor f (MappedConstructor (DeclarationProduct g f))"

datatype 'a mapped_optional = MappedOptional "'a option \<times> mapped_callback option"
definition declaration_empty :: "'a option \<times> 'b option"
  where "declaration_empty = (None, None)"
code_printing constant declaration_empty \<rightharpoonup> (Rust) "!(Option::None, Option::None)"
definition consume_mapped_optional :: "'a::equal \<Rightarrow> 'a mapped_optional \<Rightarrow> bool"
  where "consume_mapped_optional f payload = HOL.equal f f"
definition observe_declaration_empty :: "mapped_callback \<Rightarrow> bool"
  where "observe_declaration_empty f = consume_mapped_optional f (MappedOptional declaration_empty)"

lemma declaration_observations:
  "observe_declaration_pair f g = g False False"
  "observe_declaration_swap f g = (f = g \<and> f False False)"
  "observe_declaration_same f = f False False"
  "observe_declaration_dup f = f False False"
  "observe_declaration_ignore flag f = f False False"
  "observe_plain_dup f = f False False"
  "observe_mapped_constructor f g"
  "observe_declaration_empty f"
  by (simp_all add: observe_declaration_pair_def observe_declaration_swap_def
      observe_declaration_same_def observe_declaration_dup_def observe_declaration_ignore_def
      observe_plain_dup_def consume_mapped_mixed_def declaration_pair_def declaration_swap_def
      declaration_dup_def declaration_ignore_def declaration_plain_dup_def
      observe_mapped_constructor_def consume_mapped_constructor_def
      observe_declaration_empty_def consume_mapped_optional_def equal_eq)

export_code observe_declaration_pair observe_declaration_swap observe_declaration_same
  observe_declaration_dup observe_declaration_ignore observe_plain_dup
  observe_mapped_constructor observe_declaration_empty
  in Rust module_name MappedDeclarationShape

end
