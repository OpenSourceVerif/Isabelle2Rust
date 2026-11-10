theory Shared_Constant_Collection_Test
  imports Rust_Base_Setup
begin

text \<open>
  Instance dictionary collection and called-method bound propagation visit
  distinct physical Thingol nodes. A large graph with many unrelated constants
  must not search all previously visited nodes for every new node. The large
  balanced term below isolates that lookup cost from recursion depth and uses
  a table accumulator so callback insertion is not itself quadratic.

  Bucket keys are only discriminators. The smaller cases compare the complete
  constant payload and first-occurrence order against the original traversal:
  equal symbols with different types, dictionaries or annotations must survive,
  including constants reachable only through a case primitive. Each call owns
  fresh state, and repeated continuation branches must still be shared.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val ty = ITyVar "a";
  fun atom name = IConst {sym = Code_Symbol.Constant name, typargs = [],
    dicts = [], dom = [], range = ty, annotation = NONE};
  fun payload types dictionaries annotation =
    IConst {sym = Code_Symbol.Constant "same_symbol", typargs = types,
      dicts = dictionaries, dom = [], range = ty, annotation = annotation};
  val dict = Code_Thingol.Dict ([], Code_Thingol.Dict_Var
    {var = "a", index = 0, length = 1, class = "operational", unique = true});
  val p0 = payload [ty] [] NONE;
  val p1 = payload [ITyVar "b"] [] NONE;
  val p2 = payload [ty] [[dict]] NONE;
  val p3 = payload [ty] [] (SOME (ITyVar "annotated"));
  val blank = IVar NONE;
  val scrutinee = atom "scrutinee";
  val pattern = atom "pattern";
  fun cases primitive body =
    ICase {term = scrutinee, typ = ty, primitive = primitive,
      clauses = [(pattern, body), (blank, body)]};
  fun layer body = cases (atom "primitive" `$ body) body;
  fun abs body = (SOME "x", ty) `|=> (body, ty);
  fun reference f (IConst c) = f c
    | reference _ (IVar _) = I
    | reference f (left `$ right) = reference f left #> reference f right
    | reference f (_ `|=> (body, _)) = reference f body
    | reference f (ICase {term, primitive, clauses, ...}) =
        reference f term #> reference f primitive #>
          fold (fn (pat, body) => reference f pat #> reference f body) clauses;
  fun collect prefix (c: Code_Thingol.const) = insert (op =) (prefix, c);
  val samples =
    [blank, IVar (SOME "x"), p0, p0 `$ p0,
     p0 `$ p1, p2 `$ p3, abs (p0 `$ p2),
     cases p1 p0, cases p2 p0,
     (* The two cases have identical bucket prefixes but distinct primitives. *)
     cases p1 p0 `$ cases p2 p0,
     funpow 4 layer p0 `$ funpow 4 layer p3,
     funpow 6 layer (p0 `$ p1 `$ p2 `$ p3)];
  val checks = Unsynchronized.ref 0;
  fun check label ok =
    (checks := !checks + 1;
     if ok then () else error ("shared constant collection: " ^ label));
  val seed = collect "seed" (case atom "existing" of IConst c => c
    | _ => error "expected constant") [];
  val _ = List.app (fn (i, term) =>
    List.app (fn prefix =>
      List.app (fn initial =>
        check ("payload/order/seed " ^ string_of_int i)
          (Code_Rust.fold_distinct_iterm_constants (collect prefix) term initial =
            reference (collect prefix) term initial))
        [[], seed]) ["first", "changed callback"])
    (map_index I samples);
  val huge = funpow 80 layer (p0 `$ p1 `$ p2 `$ p3);
  val small = funpow 6 layer (p0 `$ p1 `$ p2 `$ p3);
  val _ = Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
    List.app (fn prefix =>
      check "depth 80 sharing and fresh traversal"
        (Code_Rust.fold_distinct_iterm_constants (collect prefix) huge seed =
          reference (collect prefix) small seed)) ["first", "changed callback"]) ();

  val _ = writeln ("Shared constant collection: " ^ string_of_int (!checks) ^
    " payload/order/seed/sharing checks passed; starting 65536-leaf lookup");

  fun tree lo hi =
    if hi - lo = 1 then atom ("wide." ^ string_of_int lo)
    else let val mid = (lo + hi) div 2 in tree lo mid `$ tree mid hi end;
  val wide = tree 0 65536;
  val started = Time.now ();
  val collected = Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
    Code_Rust.fold_distinct_iterm_constants
      (fn {sym, ...} => Code_Symbol.Table.update (sym, ()))
      wide Code_Symbol.Table.empty) ();
  val _ = check "all 65536 unrelated constant payloads retained"
    (Code_Symbol.Table.size collected = 65536 andalso
      List.all (fn n => Code_Symbol.Table.defined collected
        (Code_Symbol.Constant ("wide." ^ string_of_int n))) (0 upto 65535));
in
  val _ = writeln ("Shared constant collection: " ^ string_of_int (!checks) ^
    " payload/order/seed/sharing checks; 65536 leaves in " ^
    Time.toString (Time.- (Time.now (), started)) ^ " seconds");
end
\<close>

text \<open>
  The ordinary export retains a generic class operation and its concrete
  generated equality instance, exercising both instance-bound collection and
  called-method bound propagation in the serializer after the ML probes.
\<close>

datatype 'a collected_payload = Collected 'a bool

definition collected_equal :: "'a::equal collected_payload \<Rightarrow> 'a collected_payload \<Rightarrow> bool"
  where "collected_equal x y = (x = y)"

export_code HOL.equal equal_collected_payload_inst.equal_collected_payload collected_equal
  in Rust module_name SharedConstantCollection

end
