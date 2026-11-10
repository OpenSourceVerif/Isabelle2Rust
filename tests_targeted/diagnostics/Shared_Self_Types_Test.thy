theory Shared_Self_Types_Test
  imports Rust_Base_Setup
begin

text \<open>
  Trait declarations substitute their class variable by Self; executable
  instance methods substitute it by the concrete instance type. Both mappings
  must preserve shared type arguments before a registered type printer erases
  those arguments. A missing instance method also exercises the Self-based stub
  signature. No code is called through that missing method.

  Only the ML probe uses an erased itself printer. Ordinary export and runtime
  checks keep the standard Itself<Self> representation and Sized requirement.
\<close>

definition free_witness :: "'a itself \<Rightarrow> 'a itself" where
  "free_witness x = x"
declare free_witness_def [code del]

class self_probe =
  fixes self_witness :: "'a itself \<Rightarrow> 'a itself"
    and missing_self_witness :: "'a itself \<Rightarrow> 'a itself"

instantiation bool :: self_probe
begin
definition self_witness_bool :: "bool itself \<Rightarrow> bool itself" where
  "self_witness_bool x = x"
definition missing_self_witness_bool :: "bool itself \<Rightarrow> bool itself" where
  "missing_self_witness_bool x = x"
instance ..
end

declare missing_self_witness_bool_def [code del]

ML \<open>
local
  open Basic_Code_Thingol;
  val ctxt = Proof_Context.background_theory
    (Code_Target.set_printings
      (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
        [("Rust", SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))])))
    \<^context>;
  val free = Code_Symbol.Constant \<^const_name>\<open>free_witness\<close>;
  val class = Code_Symbol.Type_Class \<^class>\<open>self_probe\<close>;
  val classops = [\<^const_name>\<open>self_witness\<close>,
    \<^const_name>\<open>missing_self_witness\<close>];
  val methods = [\<^const_name>\<open>self_probe_bool_inst.self_witness_bool\<close>,
    \<^const_name>\<open>self_probe_bool_inst.missing_self_witness_bool\<close>];
  val plain_program = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>free_witness\<close>];
  val class_program = Code_Thingol.consts_program \<^context> classops;
  val instance_program = Code_Thingol.consts_program \<^context> (classops @ methods);
  val _ = (case Code_Symbol.Graph.get_node instance_program (Code_Symbol.Constant (hd methods)) of
      Code_Thingol.Fun ((_, [(([IVar (SOME x)], IVar (SOME y)), _)]), _) =>
        if x = y then () else error "expected identity method"
    | _ => error "expected one executable witness method");
  val _ = (case Code_Symbol.Graph.get_node instance_program (Code_Symbol.Constant (nth methods 1)) of
      Code_Thingol.Fun ((_, []), _) => ()
    | _ => error "expected a missing-equation instance method");
  val bool = \<^type_name>\<open>bool\<close> `%% [];
  fun pair x y = \<^type_name>\<open>prod\<close> `%% [x, y];
  fun arrow x y = "fun" `%% [x, y];
  fun shared 0 leaf = leaf
    | shared n leaf =
        let val child = shared (n - 1) leaf in pair child child end;
  fun witness payload = \<^type_name>\<open>itself\<close> `%% [payload];
  fun witness_type payload = arrow (witness payload) (witness payload);
  fun produce program roots =
    Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for ctxt "Rust" "SharedSelfTypes"
          NONE [] program false roots))) ();
  fun plain_output depth =
    let
      fun replace (Code_Thingol.Fun (((vs, _), eqs), origin)) =
            Code_Thingol.Fun (((vs, witness_type (shared depth (ITyVar "a"))), eqs), origin)
        | replace _ = error "expected plain witness function";
    in produce (Code_Symbol.Graph.map_node free replace plain_program) [free] end;
  val _ = if plain_output 0 = plain_output 80 then ()
    else error "class-free signature control changed output";
  val _ = writeln "Shared Self types: class-free depths 0/80 passed";
  fun output with_instance depth leaf =
    let
      val base = if with_instance then instance_program else class_program;
      val self_var = (case Code_Symbol.Graph.get_node base class of
          Code_Thingol.Class (v, _) => v | _ => error "expected class");
      val declaration_payload = shared depth (leaf (ITyVar self_var));
      val concrete_payload = shared depth (leaf bool);
      val concrete_witness = witness concrete_payload;
      val concrete_type = witness_type concrete_payload;
      fun replace_class (Code_Thingol.Class (v, (supers, cps))) =
            Code_Thingol.Class (v, (supers,
              map (fn (name, _) => (name, witness_type declaration_payload)) cps))
        | replace_class _ = error "expected class";
      fun replace_method (Code_Thingol.Fun (((vs, _), eqs), origin)) =
            Code_Thingol.Fun (((vs, concrete_type), eqs), origin)
        | replace_method _ = error "expected instance method";
      fun replace_const (c as {sym, typargs, dicts, annotation, ...}: Code_Thingol.const) =
        if member (op =) (map Code_Symbol.Constant methods) sym then
          {sym = sym, typargs = typargs, dicts = dicts,
            dom = [concrete_witness], range = concrete_witness, annotation = annotation}
        else c;
      fun replace_instance (Code_Thingol.Classinst
            {class, tyco, vs, superinsts, inst_params, superinst_params}) =
            Code_Thingol.Classinst {class = class, tyco = tyco, vs = vs, superinsts = superinsts,
              inst_params = map (apfst (apsnd (apfst replace_const))) inst_params,
              superinst_params = map (apfst (apsnd (apfst replace_const))) superinst_params}
        | replace_instance stmt = stmt;
      val program = base
        |> Code_Symbol.Graph.map_node class replace_class
        |> (if with_instance then
            fold (fn name => Code_Symbol.Graph.map_node (Code_Symbol.Constant name) replace_method) methods
            #> Code_Symbol.Graph.map (K replace_instance)
            else I);
    in produce program (map Code_Symbol.Constant
      (classops @ (if with_instance then methods else []))) end;
  fun exercise label with_instance =
    let
      val small = output with_instance 0 I;
      val _ = writeln ("Shared Self types: " ^ label ^ " depth zero passed");
      val start = Time.now ();
      val large = output with_instance 80 I;
      val middle = output with_instance 8 I;
      val fresh = output with_instance 0 I;
      val elapsed = Time.- (Time.now (), start);
      val _ = if small = large andalso small = middle andalso small = fresh then ()
        else error "shared Self substitution changed complete Rust output";
      val _ = writeln ("Shared Self types: " ^ label ^
        " depth 80/8/fresh passed in " ^
        Real.fmt (StringCvt.FIX (SOME 6)) (Time.toReal elapsed) ^ " seconds");
      val leaves = [fn a => pair a bool, fn a => arrow a bool,
        fn a => arrow bool (arrow a bool),
        fn a => pair (arrow a bool) (arrow bool a),
        fn a => arrow (arrow a bool) (arrow bool a), fn a => pair bool a];
      val _ = List.app (fn leaf =>
        if output with_instance 0 leaf = output with_instance 80 leaf then ()
        else error "shared Self substitution changed payload output") leaves;
      val _ = writeln ("Shared Self types: " ^ label ^
        " six function/container-output checks passed");
      (* Self remains in the last field after a shared closed prefix. Receiver
         discovery must reject that prefix without unfolding every occurrence. *)
      val prefixed = output with_instance 0 (pair bool);
      val _ = writeln ("Shared Self types: " ^ label ^ " prefix depth zero passed");
      val start = Time.now ();
      val deep_prefix = output with_instance 0 (fn a => pair (shared 80 bool) a);
      val elapsed = Time.- (Time.now (), start);
      val _ = if prefixed = deep_prefix then ()
        else error "shared closed prefix changed Self output";
    in writeln ("Shared Self types: " ^ label ^ " prefix depth 80 passed in " ^
      Real.fmt (StringCvt.FIX (SOME 6)) (Time.toReal elapsed) ^ " seconds") end;
in
  val _ = exercise "trait" false;
  val _ = exercise "instance" true;
end
\<close>

export_code free_witness self_witness missing_self_witness
  self_probe_bool_inst.self_witness_bool
  self_probe_bool_inst.missing_self_witness_bool
  in Rust module_name SharedSelfTypes

end
