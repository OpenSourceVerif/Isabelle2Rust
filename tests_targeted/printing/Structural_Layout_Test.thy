theory Structural_Layout_Test
  imports Rust_Base_Setup
begin

datatype layout_tree = Leaf bool | Node layout_tree layout_tree

fun nested_layout :: "layout_tree \<Rightarrow> bool" where
  "nested_layout (Node (Leaf a) (Leaf b)) = (a \<and> b)"
| "nested_layout _ = False"

definition layout_if :: "bool \<Rightarrow> bool \<Rightarrow> bool" where
  "layout_if b c = (if b then c else \<not> c)"

definition layout_operand :: "bool \<Rightarrow> bool \<Rightarrow> bool" where
  "layout_operand b c = ((if b then c else \<not> c) \<and> c)"

definition layout_argument :: "bool \<Rightarrow> bool \<Rightarrow> bool" where
  "layout_argument b c = layout_if (if b then c else \<not> c) c"

ML \<open>
local
  val files = #1 (Code_Target.produce_code \<^context> false
    [\<^const_name>\<open>layout_if\<close>, \<^const_name>\<open>nested_layout\<close>,
     \<^const_name>\<open>layout_operand\<close>, \<^const_name>\<open>layout_argument\<close>] "Rust" "StructuralLayout" NONE []);
  val source = String.concat (map (Bytes.content o snd) files);
  val expected = "pub fn layout_if (b: bool, c: bool) -> bool {\n    if b.clone() {\n        c.clone()\n    } else {\n        ! c.clone()\n    }\n}";
  val snippets = [expected,
    "    match x0 {\n        LayoutTree::Node (p0, p0a) => match *p0 {\n            LayoutTree::Leaf (a) => match *p0a {\n                LayoutTree::Leaf (b) => a.clone() && b.clone(),",
    "    (if b.clone() {\n        c.clone()\n    } else {\n        ! c.clone()\n    }) && c.clone()",
    "    layout_if(\n        if b.clone() {\n            c.clone()\n        } else {\n            ! c.clone()\n        },\n        c.clone()\n    )"];
in
  val _ = if forall (fn s => String.isSubstring s source) snippets then ()
    else error ("Structural layout differs:\n" ^ source)
end
\<close>

export_code nested_layout layout_if layout_operand layout_argument
  in Rust module_name StructuralLayout

end
