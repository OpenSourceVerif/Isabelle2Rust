theory Closure_Pattern_Test
  imports Rust_Base_Setup
begin

text \<open>
  A one-clause case in a lambda can be lifted by Thingol into a pattern
  abstraction. Rust closure parameters must be irrefutable and cannot match
  through Box fields. Keep such cases in the body, where ordinary case lowering
  supplies staged Box extraction and the existing partial-match failure path.
  The tuple and single-constructor controls remain valid callable closures.
\<close>

datatype closure_core = Seen bool | Missing
datatype closure_wrapper = Wrapped closure_core bool
datatype closure_single = Sole bool

definition refutable_closure :: "(closure_wrapper \<Rightarrow> bool) option"
  where "refutable_closure = Some (\<lambda>w. case w of Wrapped (Seen x) _ \<Rightarrow> x)"

definition nested_list_closure :: "(bool list \<Rightarrow> bool) option"
  where "nested_list_closure = Some (\<lambda>xs. case xs of [x, y] \<Rightarrow> x \<and> y)"

definition capture_closure :: "bool \<Rightarrow> (closure_wrapper \<Rightarrow> bool) option"
  where "capture_closure flag = Some (\<lambda>w. case w of Wrapped (Seen x) _ \<Rightarrow> flag \<and> x)"

definition tuple_closure :: "((bool \<times> bool) \<Rightarrow> bool) option"
  where "tuple_closure = Some (\<lambda>(x, y). x \<and> y)"

definition single_closure :: "(closure_single \<Rightarrow> bool) option"
  where "single_closure = Some (\<lambda>z. case z of Sole x \<Rightarrow> x)"

text \<open>
  Retaining the case must also preserve a function-valued branch result. The
  existing eta expansion should still produce a callable two-argument closure.
\<close>
definition result_closure :: "(closure_wrapper \<Rightarrow> bool \<Rightarrow> bool) option"
  where "result_closure = Some (\<lambda>w. case w of Wrapped (Seen x) _ \<Rightarrow> (\<lambda>b. x \<and> b))"

export_code refutable_closure nested_list_closure capture_closure tuple_closure single_closure result_closure
  in Rust module_name ClosurePatterns

end
