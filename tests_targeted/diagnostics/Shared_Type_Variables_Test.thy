theory Shared_Type_Variables_Test
  imports Rust_Base_Setup
begin

text \<open>
  Generic-name collection must not first expand every occurrence in a shared
  type graph. The declaration order is significant: it follows distinct names
  in reverse occurrence order, including when a subtree is reused on opposite
  sides of other variables.

  The singleton itself type has no runtime payload, so this test registers a
  unit representation with an ML type printer that intentionally ignores its
  one parameter. The missing equation exercises both name reservation and the
  exception-signature printer without evaluating a value or printing the nested
  parameter. Thus the complete Rust output must be independent of its sharing
  depth. No new representation is installed in the production setup.
\<close>

setup \<open>Code_Target.set_printings
  (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
    [("Rust", SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))]))\<close>

definition unused_witness :: "'a itself \<Rightarrow> bool" where
  "unused_witness _ = True"
declare unused_witness_def [code del]

ML \<open>
local
  open Basic_Code_Thingol;
  val sym = Code_Symbol.Constant \<^const_name>\<open>unused_witness\<close>;
  val base = Code_Thingol.consts_program \<^context> [\<^const_name>\<open>unused_witness\<close>];
  val _ = (case Code_Symbol.Graph.get_node base sym of
      Code_Thingol.Fun ((([("a", [])], _), []), _) => ()
    | _ => error "expected an unconstrained function without code equations");
  val a = ITyVar "a";
  val b = ITyVar "b";
  val c = ITyVar "c";
  val bool = \<^type_name>\<open>bool\<close> `%% [];
  fun pair x y = \<^type_name>\<open>prod\<close> `%% [x, y];
  fun arrow x y = "fun" `%% [x, y];
  fun shared 0 ty = ty
    | shared n ty = let val child = shared (n - 1) ty in pair child child end;
  fun output variables payload =
    let
      val function_ty = arrow
        (\<^type_name>\<open>itself\<close> `%% [payload]) bool;
      fun replace (Code_Thingol.Fun ((_, eqs), origin)) =
            Code_Thingol.Fun (((map (rpair []) variables, function_ty), eqs), origin)
        | replace _ = error "expected function";
      val program = Code_Symbol.Graph.map_node sym replace base;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for \<^context> "Rust" "SharedTypeVariables"
          NONE [] program false [sym]))) ()
    end;

  (* The old helper is not called directly: the failure must arise through the
     same public serializer entry point used by ordinary export_code. *)
  val small = output ["a"] a;
  val _ = writeln "Shared type variables: depth zero serializer passed";
  val start = Time.now ();
  val large = output ["a"] (shared 80 a);
  val middle = output ["a"] (shared 8 a);
  val fresh = output ["a"] a;
  val _ = if small = large andalso small = middle andalso small = fresh then ()
    else error "type sharing changed Rust output";
  val _ = writeln ("Shared type variables: depth 80/8/fresh output passed in " ^
    Time.toString (Time.- (Time.now (), start)) ^ " seconds");

  (* Retain the previous occurrence-based query as a reference on small inputs.
     Check its generic order in the actual emitted declaration, then compare the
     entire output against a canonical unshared payload with that same order. *)
  fun reference ty =
    let
      fun collect (ITyVar v, vars) = v :: vars
        | collect (_ `%% tys, vars) = List.foldl collect vars tys;
    in distinct (op =) (collect (ty, [])) end;
  fun canonical variables = fold_rev (fn v => fn tail => pair (ITyVar v) tail)
    (rev variables) bool;
  fun compact files = space_implode ""
    (String.tokens Char.isSpace (space_implode "\n" (map snd files)));
  fun header variables =
    "pubfnunused_witness" ^
      (if null variables then ""
       else "<" ^ space_implode "," (map (String.map Char.toUpper) variables) ^ ">") ^ "(";
  val checks = Unsynchronized.ref 0;
  fun check label ok =
    (checks := !checks + 1;
     if ok then () else error ("shared type variables: " ^ label));
  val ab = pair a b;
  val ca = pair c a;
  val samples = [bool, a, b, c, ab, ca, pair b a, pair a a,
    pair ab a, pair a ab, pair ab (pair c ab), pair ca ab, pair ab ca,
    arrow a b, arrow ab c, arrow a (arrow c ab), pair bool ab,
    pair ab (arrow b ca)] @ map (fn n => shared n ab) (0 upto 6);
  val _ = List.app (fn (i, payload) =>
    let
      val expected = reference payload;
      val variables = sort fast_string_ord expected;
      val actual = output variables payload;
    in
      check ("generic order " ^ string_of_int i)
        (String.isSubstring (header expected) (compact actual));
      check ("canonical bytes " ^ string_of_int i)
        (actual = output variables (canonical expected))
    end) (map_index I samples);
  val _ = check "rightmost repeated variable precedes its sibling"
    (reference (pair ab a) = ["a", "b"]);
  val _ = check "rightmost shared subtree keeps its internal order"
    (reference (pair a ab) = ["b", "a"]);
  val _ = check "a shared subtree surrounds a distinct variable"
    (reference (pair ab (pair c ab)) = ["b", "a", "c"]);
  val two_variables = output ["a", "b"] (shared 80 ab);
  val _ = check "deep shared type with two distinct variables"
    (two_variables = output ["a", "b"] ab andalso
      String.isSubstring (header ["b", "a"]) (compact two_variables));
  val closed = output [] (shared 80 bool);
  val _ = check "deep closed type contributes no generic variables"
    (closed = output [] bool);
  val _ = check "fresh query after different variable sets"
    (output ["a"] a = small);
in
  val _ = writeln ("Shared type variables: " ^ string_of_int (!checks) ^
    " generic-order/full-output/depth-80 checks passed");
end
\<close>

export_code unused_witness in Rust module_name SharedTypeVariables
end
