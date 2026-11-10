theory Shared_Instance_Types_Test
  imports Rust_Base_Setup
begin

text \<open>
  Instance reconstruction gathers candidate type constructors from function
  signatures whenever the program contains a class. Shared type arguments must
  not expand into an occurrence list before constructor-name deduplication.
  The test-local itself printer erases its parameter, so the missing witness
  function has fixed-size Rust output even with a deep shared signature.

  The class method places Self after a Boolean parameter. Its nested arrows
  are distinct applications of the same type constructor: treating a bucket
  name as node identity would miss the carrier type in the second arrow.
  Two real instances and an executable wrapper also check that candidate
  collection still reconstructs and dispatches to the appropriate impl.
\<close>

setup \<open>Code_Target.set_printings
  (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
    [("Rust", SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))]))\<close>

definition unused_witness :: "'a itself \<Rightarrow> bool" where
  "unused_witness _ = True"
declare unused_witness_def [code del]

class carrier_probe =
  fixes probe_tag :: "bool \<Rightarrow> 'a \<Rightarrow> bool"

instantiation bool :: carrier_probe
begin
definition probe_tag_bool :: "bool \<Rightarrow> bool \<Rightarrow> bool" where
  "probe_tag_bool flag value = (flag \<and> value)"
instance ..
end

datatype 'a carrier = Carrier 'a

instantiation carrier :: (type) carrier_probe
begin
fun probe_tag_carrier :: "bool \<Rightarrow> 'a carrier \<Rightarrow> bool" where
  "probe_tag_carrier flag (Carrier _) = flag"
instance ..
end

definition probe_values :: "bool \<Rightarrow> 'a carrier \<Rightarrow> bool \<Rightarrow> bool" where
  "probe_values flag payload b = (probe_tag flag payload \<and> probe_tag flag b)"

lemma probe_values_observation:
  "probe_values flag (Carrier payload) b = (flag \<and> b)"
  by (simp add: probe_values_def probe_tag_bool_def)

ML \<open>
local
  open Basic_Code_Thingol;
  val missing = Code_Symbol.Constant \<^const_name>\<open>unused_witness\<close>;
  val class = Code_Symbol.Type_Class \<^class>\<open>carrier_probe\<close>;
  val root_names = [\<^const_name>\<open>unused_witness\<close>,
    \<^const_name>\<open>probe_tag\<close>, \<^const_name>\<open>probe_values\<close>,
    \<^const_name>\<open>carrier_probe_bool_inst.probe_tag_bool\<close>,
    \<^const_name>\<open>carrier_probe_carrier_inst.probe_tag_carrier\<close>];
  val roots = map Code_Symbol.Constant root_names;
  val base = Code_Thingol.consts_program \<^context> root_names;
  val without_class = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>unused_witness\<close>];
  val _ = (case Code_Symbol.Graph.get_node base class of
      Code_Thingol.Class _ => ()
    | _ => error "expected the reconstruction-triggering class");
  val _ = if exists (fn ((_, stmt), _) =>
      (case stmt of Code_Thingol.Class _ => true
      | Code_Thingol.Classparam _ => true | _ => false))
      (Code_Symbol.Graph.dest without_class)
    then error "class-free control unexpectedly contains a class" else ();
  val _ = (case Code_Symbol.Graph.get_node base missing of
      Code_Thingol.Fun ((([("a", [])], _), []), _) => ()
    | _ => error "expected an unconstrained function with no equations");
  val bool = \<^type_name>\<open>bool\<close> `%% [];
  fun nested 0 = ITyVar "a"
    | nested n =
        let val child = nested (n - 1)
        in \<^type_name>\<open>prod\<close> `%% [child, child] end;
  fun output program roots depth =
    let
      val function_ty = "fun" `%%
        [\<^type_name>\<open>itself\<close> `%% [nested depth], bool];
      fun replace (Code_Thingol.Fun (((vs, _), eqs), origin)) =
            Code_Thingol.Fun (((vs, function_ty), eqs), origin)
        | replace _ = error "expected function";
      val program' = Code_Symbol.Graph.map_node missing replace program;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for \<^context> "Rust" "SharedInstanceTypes"
          NONE [] program' false roots))) ()
    end;
  val control = output without_class [missing] 0;
  val _ = if control = output without_class [missing] 80 then ()
    else error "class-free shared signature changed output";
  val _ = writeln "Shared instance types: class-free depths 0/80 passed";
  val small = output base roots 0;
  val _ = writeln "Shared instance types: class-bearing depth zero passed";
  val start = Time.now ();
  val large = output base roots 80;
  val middle = output base roots 8;
  val fresh = output base roots 0;
  val elapsed = Time.- (Time.now (), start);
  val _ = if small = large andalso small = middle andalso small = fresh then ()
    else error "shared candidate types changed complete Rust output";
in
  val _ = writeln ("Shared instance types: class-bearing depth 80/8/fresh passed in " ^
    Real.fmt (StringCvt.FIX (SOME 6)) (Time.toReal elapsed) ^ " seconds");
end
\<close>

export_code unused_witness probe_tag probe_values
  carrier_probe_bool_inst.probe_tag_bool
  carrier_probe_carrier_inst.probe_tag_carrier
  in Rust module_name SharedInstanceTypes

end
