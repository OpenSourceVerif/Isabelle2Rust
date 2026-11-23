theory Nullary_Value_Sharing_Test
  imports Rust_Base_Setup
begin

text \<open>
  A nullary value's self-reference check follows the recognized Thingol case
  clauses. These clauses can share a continuation even when the primitive is
  ignored. The serializer must inspect this finite graph without unfolding its
  exponentially larger tree, then retain the existing rejection of recursive
  eager values. The graph is supplied directly through produce_code_for so the
  test isolates the backend from HOL preprocessing and code-equation sharing.
\<close>

definition sharing_false :: bool where "sharing_false = False"
definition sharing_true :: bool where "sharing_true = True"

ML \<open>
local
  open Basic_Code_Thingol;
  val sym = Code_Symbol.Constant \<^const_name>\<open>sharing_false\<close>;
  val ty = \<^type_name>\<open>bool\<close> `%% [];
  fun atom name = IConst {sym = Code_Symbol.Constant name, typargs = [],
    dicts = [], dom = [], range = ty, annotation = NONE};
  val yes = atom \<^const_name>\<open>True\<close>;
  val no = atom \<^const_name>\<open>False\<close>;
  val self = atom \<^const_name>\<open>sharing_false\<close>;
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>sharing_false\<close>];
  fun case_term scrutinee clauses primitive =
    ICase {term = scrutinee, typ = ty, clauses = clauses, primitive = primitive};
  fun layer body = case_term no [(yes, body), (no, body)] no;
  fun produce recursive body =
    let
      val program = base
        |> Code_Symbol.Graph.map_node sym (fn _ =>
            Code_Thingol.Fun ((([], ty), [(([], body), (NONE, true))]), NONE))
        |> (if recursive then Code_Symbol.Graph.add_edge (sym, sym) else I);
    in Code_Target.produce_code_for \<^context> "Rust" "NullaryValueSharing"
      NONE [] program false [sym] end;
  fun bounded f = Timeout.apply_physical (Time.fromSeconds 5) f ();
  fun check label condition =
    if condition then () else error ("nullary value sharing: " ^ label);
  fun rejected label body =
    check label
      (case Exn.capture (fn () => bounded (fn () => produce true body)) () of
        Exn.Exn (ERROR msg) =>
          String.isPrefix "Rust target does not support self-referential nullary values:" msg
      | _ => false);
  fun contents body = bounded (fn () =>
    map (fn (path, bytes) => (path, Bytes.content bytes)) (#1 (produce false body)));

  (* Both branches share the same physical continuation. A self reference in a
     later branch requires scanning the preceding, entirely nonrecursive DAG;
     short-circuiting only after the first matching constant is insufficient. *)
  val shared = funpow 80 layer no;
  val _ = rejected "shared depth 80 before a late reference"
    (case_term no [(yes, shared), (no, self)] no);
  val _ = rejected "reference in a scrutinee"
    (case_term self [(yes, yes), (no, no)] no);
  val _ = rejected "reference inside an applied abstraction"
    (((SOME "unused", ty) `|=> (self, ty)) `$ no);
  val _ = rejected "fresh search over the same shared graph"
    (case_term no [(yes, shared), (no, self)] no);

  (* Code_Thingol.add_constsyms, the previous check, deliberately omitted the
     primitive. Preserve that classification: a primitive-only reference must
     not reject the recognized nonrecursive clauses. This deliberately synthetic
     alternate representation is a classification check, not a HOL semantics
     claim about inconsistent case metadata. *)
  fun recognized primitive = case_term no [(yes, yes), (no, no)] primitive;
  val expected = contents (recognized no);
  val _ = check "primitive-only reference does not reject"
    (not (null (contents (recognized self))));
  val _ = check "fresh nonrecursive serialization after rejection"
    (contents (recognized no) = expected);
in
  val _ = writeln
    "Nullary value sharing: depth 80, late/scrutinee/lambda references, primitive omission, fresh state passed";
end
\<close>

text \<open>
  Ordinary eager constants still produce callable Rust functions with their
  original boolean results. The synthetic recursive values above remain errors.
\<close>
export_code sharing_false sharing_true in Rust module_name NullaryValueSharing

end
