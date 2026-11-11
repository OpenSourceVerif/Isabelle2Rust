theory Signature_Result_Graph_Test
  imports Rust_Base_Setup
begin

definition witness_identity :: "'a itself \<Rightarrow> 'a itself"
  where "witness_identity x = x"

fun witness_branch :: "bool \<Rightarrow> 'a itself \<Rightarrow> 'a itself" where
  "witness_branch True x = witness_identity x"
| "witness_branch False x = witness_identity x"

fun even_length :: "bool list \<Rightarrow> bool"
and odd_length :: "bool list \<Rightarrow> bool" where
  "even_length [] = True"
| "even_length (x # xs) = odd_length xs"
| "odd_length [] = False"
| "odd_length (x # xs) = even_length xs"

text \<open>
  Each layer has two equations calling the same preceding function. Signature
  discovery must reuse complete queries across this acyclic call graph instead
  of following exponentially many paths. The actual output has one function
  item per node and grows with depth. A fresh export checks query isolation;
  the ordinary mutual recursion above checks the existing cycle fallback.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val ctxt = Proof_Context.background_theory
    (Sign.add_consts (map (fn i =>
      (Binding.name ("witness_layer_" ^ string_of_int i),
        \<^typ>\<open>bool \<Rightarrow> 'a itself \<Rightarrow> 'a itself\<close>, NoSyn))
      (1 upto 80))) \<^context>;
  val identity = Code_Symbol.Constant \<^const_name>\<open>witness_identity\<close>;
  val root = Code_Symbol.Constant \<^const_name>\<open>witness_branch\<close>;
  val base = Code_Thingol.consts_program ctxt [\<^const_name>\<open>witness_branch\<close>];
  val node = Code_Symbol.Graph.get_node base root;
  val (scheme, eqs, origin) = (case node of
      Code_Thingol.Fun ((scheme, eqs), origin) => (scheme, eqs, origin)
    | _ => error "expected witness branch function");
  val _ = if length eqs = 2 then () else error "expected two branch equations";
  val (typevars, ty) = scheme;
  val (dom, range) = Code_Thingol.unfold_fun ty;
  fun layer previous =
    let
      val callee = IConst {sym = previous, typargs = map (ITyVar o fst) typevars,
        dicts = map (K []) typevars, dom = dom, range = range, annotation = NONE};
      fun equation ((pats, _), note) =
        ((pats, Library.foldl (op `$) (callee, pats)), note);
    in Code_Thingol.Fun ((scheme, map equation eqs), origin) end;
  fun output depth =
    let
      fun add i (previous, program) =
        let
          val sym = Code_Symbol.Constant
            ("Signature_Result_Graph_Test.witness_layer_" ^ string_of_int i);
          val current = if i = 1 then node else layer previous;
          val program' = program
            |> Code_Symbol.Graph.new_node (sym, current)
            |> Code_Symbol.Graph.add_edge (sym, if i = 1 then identity else previous);
        in (sym, program') end;
      val (last, program) = fold add (1 upto depth) (identity, base);
      val program' = if depth = 0 then program else program
        |> Code_Symbol.Graph.map_node root (K (layer last))
        |> Code_Symbol.Graph.add_edge (root, last);
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for ctxt "Rust" "SignatureResultGraph"
          NONE [] program' false [root]))) ()
    end;
  fun size output = fold (fn (_, content) => fn n => n + String.size content) output 0;
  val zero = output 0;
  val start = Time.now ();
  val middle = output 8;
  val large = output 80;
  val fresh = output 8;
  val _ = if middle = fresh andalso output 0 = zero then ()
    else error "signature query cache changed a fresh complete export";
  val _ = if size large > size middle andalso
      size large < 12 * size middle then ()
    else error "signature graph output did not grow with its function nodes";
in
  val _ = writeln ("Signature result graph: depths 0/8/80/fresh passed in " ^
    Real.fmt (StringCvt.FIX (SOME 6)) (Time.toReal (Time.- (Time.now (), start))) ^
    " seconds; bytes " ^ commas (map (string_of_int o size) [zero, middle, large]));
end
\<close>

export_code witness_identity witness_branch even_length odd_length
  in Rust module_name SignatureResultGraph

end
