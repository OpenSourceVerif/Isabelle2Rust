theory Existing_Container_Conversion_Test
  imports Rust_Base_Setup
begin

text \<open>
  Existing values retain their declared flat callback fields. Class dictionaries
  consume recursively unary function instances below lists, sets, products,
  options and a recursive datatype. Check both directions across a fixed field.
\<close>

type_synonym callback = "bool \<Rightarrow> bool \<Rightarrow> bool"
datatype callback_box = Callback_Box "callback list"
datatype 'a callback_tree = Tip 'a | Fork "'a callback_tree list"

definition equal_callback_lists :: "callback list \<Rightarrow> callback list \<Rightarrow> bool"
  where "equal_callback_lists xs ys = HOL.equal xs ys"
definition equal_callback_sets :: "callback set \<Rightarrow> callback set \<Rightarrow> bool"
  where "equal_callback_sets xs ys = HOL.equal xs ys"
definition equal_callback_nested ::
  "(bool \<times> (callback list \<times> callback option)) \<Rightarrow>
   (bool \<times> (callback list \<times> callback option)) \<Rightarrow> bool"
  where "equal_callback_nested xs ys = HOL.equal xs ys"
definition equal_callback_trees ::
  "callback callback_tree \<Rightarrow> callback callback_tree \<Rightarrow> bool"
  where "equal_callback_trees xs ys = HOL.equal xs ys"

definition equal_callback_matrix ::
  "callback list list \<Rightarrow> callback list list \<Rightarrow> bool"
  where "equal_callback_matrix xs ys = HOL.equal xs ys"

definition equal_callback_consumers ::
  "(callback \<Rightarrow> bool) list \<Rightarrow> (callback \<Rightarrow> bool) list \<Rightarrow> bool"
  where "equal_callback_consumers xs ys = HOL.equal xs ys"
definition equal_polymorphic_callbacks ::
  "(bool \<Rightarrow> bool \<Rightarrow> 'a::equal) list \<Rightarrow>
   (bool \<Rightarrow> bool \<Rightarrow> 'a) list \<Rightarrow> bool"
  where "equal_polymorphic_callbacks xs ys = HOL.equal xs ys"

definition selected_callback_list :: "'a::equal list \<Rightarrow> 'a list"
  where "selected_callback_list xs = (if xs = [] then [] else xs)"
definition rebox_callbacks :: "callback list \<Rightarrow> callback_box"
  where "rebox_callbacks xs = Callback_Box (selected_callback_list xs)"
fun observe_callback_box :: "callback_box \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool list"
  where "observe_callback_box (Callback_Box fs) x y = map (\<lambda>f. f x y) fs"
definition observe_roundtrip :: "callback list \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool list"
  where "observe_roundtrip fs x y = observe_callback_box (rebox_callbacks fs) x y"


definition conversion_apply :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b"
  where "conversion_apply f x = f x"
definition fixed_callback_consumer :: "bool \<Rightarrow> callback list \<Rightarrow> bool list"
  where "fixed_callback_consumer x fs = observe_callback_box (Callback_Box fs) x False"
definition returned_callback_consumer :: "callback list \<Rightarrow> bool list"
  where "returned_callback_consumer fs =
    conversion_apply fixed_callback_consumer True (selected_callback_list fs)"

definition conversion_named_parameter :: "callback list \<Rightarrow> bool"
  where "conversion_named_parameter rust_convert = HOL.equal rust_convert []"

lemma observations:
  "equal_callback_lists [(\<lambda>x y. x \<and> y)] [(\<lambda>x y. y \<and> x)]"
  "\<not> equal_callback_lists [(\<lambda>x y. x \<and> y)] [(\<lambda>x y. x \<or> y)]"
  "equal_callback_sets {(\<lambda>x y. x \<and> y)} {(\<lambda>x y. y \<and> x)}"
  "equal_callback_nested (True, ([\<lambda>x y. x], None)) (True, ([\<lambda>x y. x], None))"
  "equal_callback_trees (Fork [Tip (\<lambda>x y. x \<and> y)]) (Fork [Tip (\<lambda>x y. y \<and> x)])"
  "observe_roundtrip [(\<lambda>x y. x \<and> y), (\<lambda>x y. x \<or> y)] True False = [False, True]"
  by (eval)+

export_code equal_callback_lists equal_callback_sets equal_callback_nested
  equal_callback_trees equal_callback_matrix equal_callback_consumers equal_polymorphic_callbacks observe_roundtrip
  returned_callback_consumer conversion_named_parameter in Rust module_name ExistingContainerConversion

end
