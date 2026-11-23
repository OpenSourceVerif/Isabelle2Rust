theory Shared_Datatype_Queries_Test
  imports Rust_Base_Setup
begin

text \<open>
  Datatype field analysis must traverse shared type arguments as a graph.
  Dependency discovery for recursive boxing and the least fixed point of
  nonrecursive parameter witnesses both need sets, not occurrence-expanded
  lists. The itself printer below erases its one type argument only in this
  theory, keeping Rust output bounded while these analyses inspect the entire
  nested field type.
\<close>

setup \<open>Code_Target.set_printings
  (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
    [("Rust", SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))]))\<close>

datatype ('a, 'b) field_probe = FieldProbe 'a 'b "bool itself"

text \<open>
  Only the second parameter of each mutually recursive gate datatype has a
  nonrecursive witness. The witness reaches gate_left through gate_right, so
  query caches must not retain an earlier fixed-point iteration's answer.
  The witness_pair control contains two applications of the same constructor
  with different arguments; together they witness both outer parameters.
\<close>

datatype ('a, 'b) gate_left = GateEnd | GateNext "('a, 'b) gate_right"
  and ('a, 'b) gate_right = GateValue 'b | GateAgain "('a, 'b) gate_left"

definition gate_wrap :: "'b \<Rightarrow> ('a, 'b) gate_left" where
  "gate_wrap b = GateNext (GateValue b)"
definition gate_twice :: "'b \<Rightarrow> ('a, 'b) gate_left" where
  "gate_twice b = GateNext (GateAgain (gate_wrap b))"
fun gate_read :: "('a, 'b) gate_left \<Rightarrow> 'b option" where
  "gate_read GateEnd = None"
| "gate_read (GateNext (GateValue b)) = Some b"
| "gate_read (GateNext (GateAgain rest)) = gate_read rest"

datatype ('a, 'b) witness_slot = WitnessSlot 'b
datatype ('a, 'b) witness_pair =
  WitnessPair "(('a, 'b) witness_slot \<times> ('b, 'a) witness_slot)"
definition witness_make :: "'a \<Rightarrow> 'b \<Rightarrow> ('a, 'b) witness_pair" where
  "witness_make a b = WitnessPair (WitnessSlot b, WitnessSlot a)"
fun witness_observe :: "('a, 'b) witness_pair \<Rightarrow> ('a \<times> 'b)" where
  "witness_observe (WitnessPair (WitnessSlot b, WitnessSlot a)) = (a, b)"

lemma gate_read_twice: "gate_read (gate_twice b) = Some b"
  by (simp add: gate_twice_def gate_wrap_def)
lemma witness_round_trip: "witness_observe (witness_make a b) = (a, b)"
  by (simp add: witness_make_def)

ML \<open>
local
  open Basic_Code_Thingol;
  val carrier_name = \<^type_name>\<open>field_probe\<close>;
  val carrier = Code_Symbol.Type_Constructor carrier_name;
  val root = Code_Symbol.Constant \<^const_name>\<open>FieldProbe\<close>;
  val base = Code_Thingol.consts_program \<^context> [\<^const_name>\<open>FieldProbe\<close>];
  val a = ITyVar "a";
  val b = ITyVar "b";
  val bool = \<^type_name>\<open>bool\<close> `%% [];
  val self = carrier_name `%% [a, b];
  fun pair x y = \<^type_name>\<open>prod\<close> `%% [x, y];
  fun nested 0 leaf = leaf
    | nested n leaf =
        let val child = nested (n - 1) leaf in pair child child end;
  fun output depth leaf =
    let
      val field = \<^type_name>\<open>itself\<close> `%% [nested depth leaf];
      fun replace (Code_Thingol.Datatype (["a", "b"],
            [(co, [ITyVar "a", ITyVar "b", _])])) =
            Code_Thingol.Datatype (["a", "b"], [(co, [a, b, field])])
        | replace _ = error "expected two real parameters and one erased field";
      val program = Code_Symbol.Graph.map_node carrier replace base;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for \<^context> "Rust" "SharedDatatypeQueries"
          NONE [] program false [root]))) ()
    end;
  fun compact files = space_implode ""
    (String.tokens Char.isSpace (space_implode "\n" (map snd files)));
  val checks = Unsynchronized.ref 0;
  fun check label ok =
    (checks := !checks + 1;
     if ok then () else error ("shared datatype queries: " ^ label));
  val small = output 0 bool;
  val _ = writeln "Shared datatype queries: depth zero serializer passed";
  val start = Time.now ();
  val large = output 80 bool;
  val middle = output 8 bool;
  val fresh = output 0 bool;
  val _ = check "closed field complete output"
    (small = large andalso small = middle andalso small = fresh);
  val _ = writeln ("Shared datatype queries: depth 80/8/fresh output passed in " ^
    Time.toString (Time.- (Time.now (), start)) ^ " seconds");
  val _ = check "nonrecursive erased field is not boxed"
    (not (String.isSubstring "::std::boxed::Box<()>" (compact small)));
  val parameterized = output 0 (pair a b);
  val _ = check "shared field with distinct variables"
    (parameterized = output 80 (pair a b) andalso parameterized = small);
  val recursive = output 0 self;
  val _ = check "recursive occurrence inside erased syntax retains conservative boxing"
    (String.isSubstring "::std::boxed::Box<()>" (compact recursive));
  val _ = check "deep shared recursive field"
    (recursive = output 80 self);
  val _ = check "same constructor with different children still reaches Self"
    (recursive = output 80 (pair bool (pair bool self)));
  val _ = check "fresh nonrecursive query does not reuse a recursive answer"
    (output 0 bool = small);
in
  val _ = writeln ("Shared datatype queries: " ^ string_of_int (!checks) ^
    " full-output/boxing/parameter/fresh-query checks passed");
end
\<close>

export_code FieldProbe gate_wrap gate_twice gate_read witness_make witness_observe
  in Rust module_name SharedDatatypeQueries

end
