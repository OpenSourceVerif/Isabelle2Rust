theory Shared_Case_Constraints_Test
  imports Rust_Base_Setup
begin

text \<open>
  A many-constructor datatype creates Quickcheck continuation cases whose
  primitive and recognized branches share the next continuation. Exporting its
  generated instance must finish without unfolding that shared graph as a tree.
  The ML checks also retain primitive-only constants, first-visit order, initial
  bounds, and fresh traversal state when the callback changes between passes.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val ty = ITyVar "a";
  fun atom name = IConst {sym = Code_Symbol.Constant name, typargs = [],
    dicts = [], dom = [], range = ty, annotation = NONE};
  val leaf = atom "leaf";
  val primitive_only = atom "primitive_only";
  val pattern_only = atom "pattern_only";
  fun layer t = ICase {term = atom "scrutinee", typ = ty,
    primitive = primitive_only `$ t, clauses = [(pattern_only, t)]};
  fun reference f (IConst c) = f c
    | reference _ (IVar _) = I
    | reference f (a `$ b) = reference f a #> reference f b
    | reference f (_ `|=> (body, _)) = reference f body
    | reference f (ICase {term, primitive, clauses, ...}) =
        reference f term #> reference f primitive #>
          fold (fn (p, b) => reference f p #> reference f b) clauses;
  fun collect prefix {sym, ...} = insert (op =) (prefix, sym);
  fun check b = if b then () else error "shared case constant collection";
  val small = funpow 8 layer leaf;
  val _ = List.app (fn prefix =>
    List.app (fn initial =>
      check (Code_Rust.fold_distinct_iterm_constants (collect prefix) small initial =
        reference (collect prefix) small initial))
      [[], [("seed", Code_Symbol.Constant "existing")]])
    ["first", "changed bounds"];
  (* The old occurrence traversal would require more than 2^80 visits. *)
  val large = funpow 80 layer leaf;
  val names = Code_Rust.fold_distinct_iterm_constants (collect "large") large [];
  val _ = check (map snd names =
    map Code_Symbol.Constant ["pattern_only", "leaf", "primitive_only", "scrutinee"]);
in
  val _ = writeln "Shared case collection: equivalence, fresh state, and depth 80 passed";
end
\<close>

datatype many_choices = Choice00 bool | Choice01 bool | Choice02 bool | Choice03 bool | Choice04 bool | Choice05 bool | Choice06 bool | Choice07 bool | Choice08 bool | Choice09 bool | Choice10 bool | Choice11 bool | Choice12 bool | Choice13 bool | Choice14 bool | Choice15 bool | Choice16 bool | Choice17 bool | Choice18 bool | Choice19 bool | Choice20 bool | Choice21 bool | Choice22 bool | Choice23 bool | Choice24 bool | Choice25 bool | Choice26 bool | Choice27 bool | Choice28 bool | Choice29 bool | Choice30 bool | Choice31 bool | Choice32 bool | Choice33 bool | Choice34 bool | Choice35 bool | Choice36 bool | Choice37 bool | Choice38 bool | Choice39 bool | Choice40 bool | Choice41 bool | Choice42 bool | Choice43 bool | Choice44 bool | Choice45 bool | Choice46 bool | Choice47 bool

text \<open>
  Export the polymorphic class operation as well as the concrete method: this
  retains the class node and forces impl reconstruction and both bound passes.
  Exporting only the monomorphic method can emit an ordinary function and would
  fail to exercise the original exponential instance-collection path.
\<close>

export_code Quickcheck_Exhaustive.full_exhaustive full_exhaustive_many_choices_inst.full_exhaustive_many_choices in Rust

end
