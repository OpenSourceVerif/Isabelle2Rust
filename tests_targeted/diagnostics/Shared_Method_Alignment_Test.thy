theory Shared_Method_Alignment_Test
  imports Rust_Base_Setup
begin

text \<open>
  The absent copy method chooses the instance variables (b, a), while the
  executable method uses (a, b). Its delayed product equality therefore needs
  alpha-renaming when printed inside the impl. The ML block asserts this trigger
  and supplies shared nested product terms, types and dictionaries directly to
  the serializer, avoiding any cost of parsing exponentially large HOL text.

  Code.abort omits the delayed computation, so depths 0, 1, 8 and 80 and a fresh
  depth-zero serialization must have exactly the same Rust bytes. The original
  backend already preserves term sharing but expands type/dictionary payloads.
  The companion Method_Call_Bounds_Alignment_Test separately checks the variable
  scope of propagated bounds with executable calls.
\<close>

class align_probe =
  fixes unused_align_copy :: "'a \<Rightarrow> 'a"
    and align_probe :: "'a \<Rightarrow> String.literal \<Rightarrow> bool"

datatype ('a, 'b) align_box = AlignBox 'a 'b

instantiation align_box :: (type, equal) align_probe
begin
fun align_probe_align_box :: "('a, 'b) align_box \<Rightarrow> String.literal \<Rightarrow> bool"
  where "align_probe_align_box (AlignBox x y) msg =
    Code.abort msg (\<lambda>_. HOL.equal (y, y) (y, y))"
definition unused_align_copy_align_box :: "('a, 'b) align_box \<Rightarrow> ('a, 'b) align_box"
  where "unused_align_copy_align_box x = x"
instance ..
end

declare unused_align_copy_align_box_def [code del]

ML \<open>
local
  open Basic_Code_Thingol;
  val method = Code_Symbol.Constant
    \<^const_name>\<open>align_probe_align_box_inst.align_probe_align_box\<close>;
  val missing = Code_Symbol.Constant
    \<^const_name>\<open>align_probe_align_box_inst.unused_align_copy_align_box\<close>;
  val classop = Code_Symbol.Constant \<^const_name>\<open>align_probe\<close>;
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>align_probe_align_box_inst.unused_align_copy_align_box\<close>,
     \<^const_name>\<open>align_probe\<close>,
     \<^const_name>\<open>align_probe_align_box_inst.align_probe_align_box\<close>];
  fun variables symbol =
    (case Code_Symbol.Graph.get_node base symbol of
      Code_Thingol.Fun (((vs, _), _), _) => map fst vs
    | _ => error "expected method function");
  val _ = if variables missing = ["b", "a"] andalso variables method = ["a", "b"]
    then writeln "Shared method alignment: distinct source parameter orders confirmed"
    else error "expected a nonempty method-variable renaming";
  val bool = \<^type_name>\<open>bool\<close> `%% [];
  val prod = \<^type_name>\<open>prod\<close>;
  val eqclass = \<^class>\<open>equal\<close>;
  fun nested 0 = (ITyVar "b", IVar (SOME "y"),
        Dict ([], Dict_Var {var = "b", index = 0, length = 1,
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
        (#1 (Code_Target.produce_code_for \<^context> "Rust" "SharedMethodAlignment"
          NONE [] program false [missing, classop, method]))) ()
    end;
  val small = output 0;
  val _ = writeln "Shared method alignment: depth zero serializer passed";
  val start = Time.now ();
  val large = output 80;
  val middle = output 8;
  val shallow = output 1;
  val fresh = output 0;
  val _ = if small = large andalso small = middle andalso small = shallow andalso small = fresh then ()
    else error "dictionary sharing changed Rust output";
in
  val _ = writeln ("Shared method alignment: depth 80 and fresh output passed in " ^
    Time.toString (Time.- (Time.now (), start)) ^ " seconds");
end
\<close>
export_code align_probe_align_box_inst.unused_align_copy_align_box
  align_probe align_probe_align_box_inst.align_probe_align_box
  in Rust module_name SharedMethodAlignment
end
