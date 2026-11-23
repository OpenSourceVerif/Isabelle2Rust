theory Function_Result_Context_Test
  imports Rust_Base_Setup
begin

text \<open>
  Every ordinary function and closure body returns the representation printed
  on its signature. Case and equation selection may require converting a
  producer's existing callback container at that boundary. A trait signature
  remains authoritative even when its result uses the ordinary representation.
\<close>

type_synonym result_callback = "bool \<Rightarrow> bool \<Rightarrow> bool"

definition context_selected_producer :: "bool \<Rightarrow> result_callback set"
  where "context_selected_producer b = {f. f False False = b}"

definition context_conditional :: "bool \<Rightarrow> result_callback set"
  where "context_conditional b =
    (if b then context_selected_producer True else context_selected_producer False)"

definition context_case :: "bool option \<Rightarrow> result_callback set"
  where "context_case b =
    (case b of None \<Rightarrow> context_selected_producer True
     | Some c \<Rightarrow> context_selected_producer c)"

definition context_binding :: "bool \<Rightarrow> result_callback set"
  where "context_binding b =
    (case (b, False) of (c, unused) \<Rightarrow> context_selected_producer c)"

definition context_delayed :: "bool \<Rightarrow> unit \<Rightarrow> result_callback set"
  where "context_delayed b =
    (\<lambda>_. if b then context_selected_producer True else context_selected_producer False)"

fun context_equations :: "bool list \<Rightarrow> result_callback set"
  where "context_equations [] = {}"
  | "context_equations (b # bs) = context_selected_producer b"

fun context_staged :: "bool option list \<Rightarrow> result_callback set"
  where "context_staged [Some b] = context_selected_producer b"
  | "context_staged _ = {}"

class context_factory =
  fixes context_factory :: "'a \<Rightarrow> result_callback set"

instantiation bool :: context_factory
begin
definition context_factory_bool :: "bool \<Rightarrow> result_callback set"
  where "context_factory_bool b = context_selected_producer b"
instance ..
end

definition context_trait :: "bool \<Rightarrow> result_callback set"
  where "context_trait b = context_factory b"

lemma context_observations:
  "context_conditional b = context_selected_producer b"
  "context_binding b = context_selected_producer b"
  "context_delayed b () = context_selected_producer b"
  "context_trait b = context_selected_producer b"
  by (simp_all add: context_conditional_def context_binding_def context_delayed_def
      context_trait_def context_factory_bool_def)

export_code context_conditional context_case context_binding context_delayed
  context_equations context_staged context_factory context_trait
  in Rust module_name FunctionResultContext

end
