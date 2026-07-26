theory Type_Nested_Rec_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Regression test for H2 (D.2): recursion hidden inside a type ARGUMENT of
   another datatype.

   `tree list` references `tree` only through list's type argument. The old
   Box analysis (both the type-level is_inf_typeco and the term-level
   is_invdependent_typecos) only inspected the *head* of each argument type
   (`list`) and the polymorphic deps of that head, so it never saw the `tree`
   buried in the argument. Result: the `Tree` field was emitted as
   `Tree(List<Tree>)` with no Box, which is an infinite-size Rust type (E0072).

   With the unified type_reaches analysis the field is boxed consistently at
   both the type level (`Tree(Box<List<Tree>>)`) and the term level
   (`Box::new(..)` on construction, `box ..` on the pattern), so it compiles. *)

datatype tree = Leaf | Tree "tree list"

(* construction: exercises the term-level Box (Box::new) on a Tree field *)
fun wrap :: "tree \<Rightarrow> tree" where
  "wrap t = Tree [t]"

(* pattern match: exercises the box pattern on a Tree field *)
fun is_leaf :: "tree \<Rightarrow> bool" where
  "is_leaf Leaf = True"
| "is_leaf (Tree ts) = False"

export_code wrap is_leaf in Rust

end
