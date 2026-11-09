theory Bounded_Diagnostics_Test
  imports Rust_Base_Setup
begin

text \<open>
  Thingol diagnostics are auxiliary observations, including when the recognized
  case clauses share a continuation (not only the elided primitive). A small
  object must keep its exact format. Large shared terms, deep types/dictionaries,
  long lists, and large names must stop during construction and identify the
  truncation. Each public rendering call has its own budget.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val ty = ITyVar "a";
  val x = IVar (SOME "x");
  fun statement body = Code_Thingol.Fun
    ((([], ty), [(([x], body), (NONE, true))]), NONE);
  fun check label b = if b then () else error ("bounded diagnostics: " ^ label);
  fun bounded label text =
    check (label ^ " (bytes=" ^ Int.toString (size text) ^ ", tail=" ^
      String.extract (text, Int.max (0, size text - 80), NONE) ^ ")")
      (size text <= 16412 andalso
      String.isSuffix "... <debug output truncated>" text);
  fun layer t = ICase {term = x, typ = ty, clauses = [(x, t), (x, t)],
    primitive = x};
  val small = statement x;
  val expected = "Fun=(vs_ty=([], a), eqs=[([x])=>x])";
  val _ = check "small format"
    (Code_Debug_Info.print_debug_info_thingol_stmt small = expected);

  (* Depth 10 is safe even for the old printer and already exceeds the bound.
     Keep it first so an old-backend run fails without unfolding depth 80. *)
  val _ = bounded "shared clauses at depth 10"
    (Code_Debug_Info.print_debug_info_thingol_stmt (statement (funpow 10 layer x)));
  val huge = funpow 80 layer x;
  val _ = bounded "shared clauses at depth 80"
    (Code_Debug_Info.print_debug_info_thingol_stmt (statement huge));
  val _ = bounded "direct term entry point" (Code_Debug_Info.print_debug_info_iterm huge);
  val primitive_only = ICase {term = x, typ = ty, clauses = [(x, x)], primitive = huge};
  val _ = check "primitive remains elided"
    (Code_Debug_Info.print_debug_info_iterm primitive_only =
      "{term: x, typ: a, clauses: [(x, x)], primitive: <elided>}");
  val _ = bounded "deep type"
    (Code_Debug_Info.print_debug_info_itype (funpow 1000 (fn t => "f" `%% [t]) ty));
  val dv = Dict_Var {var = "a", index = 0, length = 1, class = "c", unique = true};
  val deep_dict = funpow 1000
    (fn d => Dict ([], Dict_Const (("f", "c"), [(ty, [d])]))) (Dict ([], dv));
  val _ = bounded "deep dictionary" (Code_Debug_Info.print_debug_info_dict deep_dict);
  val _ = bounded "large name"
    (Code_Debug_Info.print_debug_info_sym
      (Code_Symbol.Constant (replicate_string 1000000 "x")));
  val wide = Code_Thingol.Datatype ([], replicate 20000 (("C", []), [ty]));
  val _ = bounded "wide statement" (Code_Debug_Info.print_debug_info_thingol_stmt wide);
  val _ = bounded "whole node"
    (Code_Debug_Info.print_debug_info_node ((Code_Symbol.Constant "f", wide),
      [Code_Symbol.Type_Constructor "t"]));
  val _ = check "fresh budget after truncation"
    (Code_Debug_Info.print_debug_info_thingol_stmt small = expected);
in
  val _ = writeln "Bounded diagnostics: exact small format, shared depth 80, depth/width/name limits passed";
end
\<close>

text \<open>
  Ordinary export still emits the same bool function. Diagnostic truncation is
  not a transformation of executable HOL terms or generated Rust.
\<close>
definition diagnostic_boolean :: "bool \<Rightarrow> bool" where
  "diagnostic_boolean b = (\<not> b)"

export_code diagnostic_boolean in Rust module_name BoundedDiagnostics

end
