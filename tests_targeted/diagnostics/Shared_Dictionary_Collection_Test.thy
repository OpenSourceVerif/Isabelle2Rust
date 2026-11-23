theory Shared_Dictionary_Collection_Test
  imports Rust_Base_Setup
begin

text \<open>
  Type-class evidence inside an instance method can be a shared DAG even when
  its surrounding term traversal already preserves sharing. The source method
  contains equality of a product in Code.abort's delayed argument. The first ML
  block replaces that product with depth-80 shared products, updating term types,
  constructor payloads and product-equality dictionaries consistently.

  Code.abort omits the delayed computation in Rust. Serialization must therefore
  finish with exactly the depth-zero output: neither output size nor execution
  of the source computation accounts for traversal of 2^80 dictionary paths.
  This first block uses existing APIs so it also exposes the old backend timeout.
\<close>

class dict_probe = fixes dict_probe :: "'a \<Rightarrow> String.literal \<Rightarrow> bool"
datatype 'a dict_box = DictBox 'a
instantiation dict_box :: (equal) dict_probe
begin
fun dict_probe_dict_box :: "'a dict_box \<Rightarrow> String.literal \<Rightarrow> bool"
  where "dict_probe_dict_box (DictBox x) msg =
    Code.abort msg (\<lambda>_. HOL.equal (x, x) (x, x))"
instance ..
end
ML \<open>
local
  open Basic_Code_Thingol;
  val method = Code_Symbol.Constant
    \<^const_name>\<open>dict_probe_dict_box_inst.dict_probe_dict_box\<close>;
  val classop = Code_Symbol.Constant \<^const_name>\<open>dict_probe\<close>;
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>dict_probe\<close>,
     \<^const_name>\<open>dict_probe_dict_box_inst.dict_probe_dict_box\<close>];
  val bool = \<^type_name>\<open>bool\<close> `%% [];
  val prod = \<^type_name>\<open>prod\<close>;
  val eqclass = \<^class>\<open>equal\<close>;
  fun nested 0 = (ITyVar "a", IVar (SOME "x"),
        Dict ([], Dict_Var {var = "a", index = 0, length = 1,
          class = eqclass, unique = true}))
    | nested n =
        let
          val (ty, value, evidence) = nested (n - 1);
          val product = prod `%% [ty, ty];
          val pair = IConst {sym = Code_Symbol.Constant \<^const_name>\<open>Pair\<close>,
            typargs = [ty, ty], dicts = [[], []], dom = [ty, ty],
            range = product, annotation = NONE};
        in (product, pair `$ value `$ value,
          Dict ([], Dict_Const ((prod, eqclass), [(ty, [evidence]), (ty, [evidence])])))
        end;
  fun output depth =
    let
      val (ty, value, evidence) = nested depth;
      val product = prod `%% [ty, ty];
      val pair = IConst {sym = Code_Symbol.Constant \<^const_name>\<open>Pair\<close>,
        typargs = [ty, ty], dicts = [[], []], dom = [ty, ty],
        range = product, annotation = NONE} `$ value `$ value;
      val equal = IConst {sym = Code_Symbol.Constant
          \<^const_name>\<open>equal_prod_inst.equal_prod\<close>,
        typargs = [ty, ty], dicts = [[evidence], [evidence]],
        dom = [product, product], range = bool, annotation = NONE};
      fun replace (Code_Thingol.Fun ((scheme, [((pats, body), note)]), origin)) =
            let
              val (callee, args) = Code_Thingol.unfold_app body;
              val fallback = (case nth args 1 of
                bind `|=> (_, result) => bind `|=> (equal `$ pair `$ pair, result)
              | _ => error "expected delayed abort argument");
            in Code_Thingol.Fun
              ((scheme, [((pats, callee `$ hd args `$ fallback), note)]), origin) end
        | replace _ = error "expected one method equation";
      val program = Code_Symbol.Graph.map_node method replace base;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for \<^context> "Rust" "SharedDictionaryCollection"
          NONE [] program false [classop, method]))) ()
    end;
  val small = output 0;
  val _ = writeln "Shared dictionary serializer: depth zero serializer passed";
  val start = Time.now ();
  val large = output 80;
  val _ = if small = large andalso small = output 0 then ()
    else error "dictionary sharing changed Rust output";
in
  val _ = writeln ("Shared dictionary serializer: depth 80 and fresh output passed in " ^
    Time.toString (Time.- (Time.now (), start)) ^ " seconds");
end
\<close>


text \<open>
  Compare the dictionary query with the original leaf collection on small
  evidence graphs. Instance identity is only a bucket key: dictionaries for the
  same instance can contain different variable/class leaves. Relation paths,
  repeated roots, empty evidence, accumulator seeds and fresh queries must keep
  the original reverse first-occurrence order. The final shared graph has only
  linear physical size despite its exponentially many unfolded occurrences.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val ty = ITyVar "a";
  fun variable v cls = Dict ([], Dict_Var
    {var = v, index = 0, length = 1, class = cls, unique = true});
  val a = variable "a" "HOL.equal";
  val b = variable "b" "Orderings.ord";
  val c = variable "a" "Enum.enum";
  fun branch left right = Dict ([], Dict_Const
    (("Product_Type.prod", "HOL.equal"), [(ty, [left]), (ty, [right])]));
  val shared = branch a b;
  val other = branch a c;
  val rewrapped = (case shared of Dict (_, plain) =>
    Dict ([("derived", "base")], plain));
  val empty = Dict ([], Dict_Const (("HOL.bool", "HOL.equal"), []));
  fun reference (Dict (_, plain)) acc =
        (case plain of
          Dict_Var {var, class, ...} => insert (op =) (var, class) acc
        | Dict_Const (_, dss) => fold (fn (_, ds) => fold reference ds) dss acc);
  fun reference_all dictss = fold (fold reference) dictss;
  val samples =
    [[], [[]], [[a]], [[a], [a]], [[a, b, c]], [[shared]],
     [[shared, other]], [[rewrapped, shared, c]], [[empty, shared]],
     [[branch shared shared, branch other shared]], [[b], [a, c], []]];
  val seeds = [[], [("seed", "class")], [("a", "HOL.equal"), ("seed", "class")]];
  val checks = Unsynchronized.ref 0;
  fun check label ok =
    (checks := !checks + 1;
     if ok then () else error ("shared dictionaries: " ^ label));
  val _ = List.app (fn (i, dictss) =>
    List.app (fn seed =>
      check ("reference/order/seed " ^ string_of_int i)
        (Code_Rust.add_distinct_dict_vars dictss seed = reference_all dictss seed))
      seeds) (map_index I samples);
  val huge = funpow 80 (fn child => branch child child) shared;
  val _ = Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
    List.app (fn seed =>
      check "shared depth 80"
        (Code_Rust.add_distinct_dict_vars [[huge, other]] seed =
          reference_all [[shared, other]] seed)) seeds) ();
  val _ = check "same instance, changed payload in a fresh query"
    (Code_Rust.add_distinct_dict_vars [[other, shared]] [] =
      reference_all [[other, shared]] []);
in
  val _ = writeln ("Shared dictionary collection: " ^ string_of_int (!checks) ^
    " payload/order/seed/relation/sharing checks passed");
end
\<close>

export_code dict_probe dict_probe_dict_box_inst.dict_probe_dict_box in Rust module_name SharedDictionaryCollection
end
