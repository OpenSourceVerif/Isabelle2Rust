theory Shared_Pattern_Abstraction_Test
  imports Rust_Base_Setup
begin

text \<open>
  Lifting a one-clause case into a closure parameter queries whether the original
  lambda variable is still free in the pattern or body. Shared branches in an
  ignored abort fallback must not be expanded as a tree during that query.
  The first block exercises the full serializer using only established APIs,
  so the same final test exposes the old backend's traversal timeout.
\<close>

datatype abstraction_message = Message String.literal

definition ignored_pattern_fallback :: "(abstraction_message \<Rightarrow> bool) option" where
  "ignored_pattern_fallback = Some (\<lambda>w. case w of Message msg \<Rightarrow>
    Code.abort msg (\<lambda>_. False))"

ML \<open>
local
  open Basic_Code_Thingol;
  val sym = Code_Symbol.Constant \<^const_name>\<open>ignored_pattern_fallback\<close>;
  val ty = \<^type_name>\<open>bool\<close> `%% [];
  fun atom name = IConst {sym = Code_Symbol.Constant name, typargs = [],
    dicts = [], dom = [], range = ty, annotation = NONE};
  val yes = atom \<^const_name>\<open>True\<close>;
  val no = atom \<^const_name>\<open>False\<close>;
  fun layer body = ICase {term = no, typ = ty,
    clauses = [(yes, body), (no, body)], primitive = no};
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>ignored_pattern_fallback\<close>];
  fun output depth =
    let
      val shared = funpow depth layer no;
      val replaced = Unsynchronized.ref 0;
      val pattern_abstractions = Unsynchronized.ref 0;
      fun replace_term (t as ((IConst {sym = Code_Symbol.Constant name, ...} `$ msg) `$
            (bind `|=> (_, result_ty)))) =
            if name = \<^const_name>\<open>Code.abort\<close> then
              (replaced := !replaced + 1;
               let val (callee, _) = Code_Thingol.unfold_app t
               in callee `$ msg `$ (bind `|=> (shared, result_ty)) end)
            else replace_children t
        | replace_term t = replace_children t
      and replace_children (left `$ right) = replace_term left `$ replace_term right
        | replace_children (bind `|=> (body, result_ty)) =
            ((case (bind, body) of
                ((SOME v, _), ICase {term = IVar (SOME w), clauses = [_], ...}) =>
                  if v = w then pattern_abstractions := !pattern_abstractions + 1 else ()
              | _ => ());
             bind `|=> (replace_term body, result_ty))
        | replace_children (ICase {term, typ, clauses, primitive}) =
            ICase {term = replace_term term, typ = typ,
              clauses = map (apply2 replace_term) clauses, primitive = primitive}
        | replace_children t = t;
      fun replace (Code_Thingol.Fun ((scheme, [((pats, body), annotation)]), origin)) =
            Code_Thingol.Fun ((scheme, [((pats, replace_term body), annotation)]), origin)
        | replace _ = error "expected one equation";
      val program = Code_Symbol.Graph.map_node sym replace base;
      val _ = if !replaced = 1 andalso !pattern_abstractions = 1 then ()
        else error "expected an abort beneath one candidate pattern abstraction";
    in
      Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
        map (fn (path, bytes) => (path, Bytes.content bytes))
          (#1 (Code_Target.produce_code_for \<^context> "Rust" "PatternSharing"
            NONE [] program false [sym]))) ()
    end;
  val small = output 0;
  val large = output 80;
  val _ = if small = large andalso small = output 0 then ()
    else error "shared pattern query changed serialized Rust";
in
  val _ = writeln "Shared pattern serializer: depth 0/80 Rust bytes equal, fresh export passed";
end
\<close>

text \<open>
  The local splitter must agree with the upstream lift conditions before Rust's
  existing irrefutable/boxed-pattern filter. Cover blank and named binders,
  different scrutinees, multiple clauses, free and shadowed original variables,
  and primitive-only references. Large shared terms check both successful
  lifting and preservation of a genuinely free original binder.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val ty = ITyVar "a";
  val x = IVar (SOME "x");
  val y = IVar (SOME "y");
  val z = IVar (SOME "z");
  val blank = IVar NONE;
  fun abs v body = (v, ty) `|=> (body, ty);
  fun cases scrutinee clauses primitive =
    ICase {term = scrutinee, typ = ty, clauses = clauses, primitive = primitive};
  fun one scrutinee pat body = cases scrutinee [(pat, body)] x;
  fun layer body = cases z [(blank, body), (blank, body)] x;
  val shared = x `$ y;
  val samples =
    [x, blank, shared, one x y z,
     abs NONE (one x y z), abs (SOME "x") y,
     abs (SOME "x") (one x y z),
     abs (SOME "x") (one y y z),
     abs (SOME "x") (one x x z),
     abs (SOME "x") (one x x x),
     abs (SOME "x") (one x y x),
     abs (SOME "x") (one x y (abs (SOME "x") shared)),
     abs (SOME "x") (one x y (abs (SOME "y") shared)),
     abs (SOME "x") (one x (x `$ y) shared),
     abs (SOME "x") (one x (abs (SOME "x") shared) x),
     abs (SOME "x") (one x y (cases z [(x, shared)] x)),
     abs (SOME "x") (one x y (cases z [(x, shared), (y, shared)] x)),
     abs (SOME "x") (cases x [] x),
     abs (SOME "x") (cases x [(y, z), (blank, z)] x),
     abs (SOME "x") (one blank y z),
     abs (SOME "x") (one x y (funpow 6 layer z))];
  val checks = Unsynchronized.ref 0;
  fun check label b =
    (checks := !checks + 1;
     if b then () else error ("shared pattern query: " ^ label));
  val _ = List.app (fn (i, term) =>
    check ("upstream split " ^ string_of_int i)
      (Code_Rust.split_distinct_pat_abs term = Code_Thingol.split_pat_abs term))
    (map_index I samples);
  (* Compare physical output identities: structural equality of the large shared
     body would itself revisit exponentially many paths on equal graph copies. *)
  fun check_large label pat leaf lift =
    let
      val body = funpow 80 layer leaf;
      val original_body = one x pat body;
      val term = abs (SOME "x") original_body;
      val result = Timeout.apply_physical (Time.fromSeconds 5)
        Code_Rust.split_distinct_pat_abs term;
    in
      check label (case result of
        SOME ((actual_pat, actual_ty), actual_body) =>
          actual_ty = ty andalso actual_pat = (if lift then pat else x)
          andalso pointer_eq (actual_body, if lift then body else original_body)
      | NONE => false)
    end;
  val _ = check_large "absent original binder permits lifting" y z true;
  val _ = check_large "free original binder retains case" y x false;
  val _ = check_large "pattern rebinds original binder" x x true;
  val _ = check_large "inner lambda shadows original binder" y
    (abs (SOME "x") shared) true;
  val _ = check_large "other inner binder keeps original free" y
    (abs (SOME "y") shared) false;
  val _ = check_large "inner pattern shadows original binder" y
    (cases z [(x, shared)] x) true;
  val _ = check_large "another branch leaves original binder free" y
    (cases z [(x, shared), (y, shared)] x) false;
in
  val _ = writeln ("Shared pattern queries: " ^ string_of_int (!checks) ^
    " upstream/scope/depth-80 checks passed");
end
\<close>

export_code ignored_pattern_fallback in Rust module_name SharedPatternAbstraction
end
