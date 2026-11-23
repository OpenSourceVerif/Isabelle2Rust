theory Constructor_Inference_Test
  imports Rust_Base_Setup
begin

text \<open>
  A datatype parameter used by one constructor is not a phantom parameter of
  the datatype, but its nullary constructors carry no runtime evidence of it.
  HOL still fixes each occurrence's type, including generic comparisons and
  tuples whose constructor-valued component is subsequently discarded.
\<close>

datatype 'a inference_choice = Vacant | Chosen 'a

fun same_shape :: "'a inference_choice \<Rightarrow> 'a inference_choice \<Rightarrow> bool"
  where "same_shape Vacant Vacant = True"
  | "same_shape (Chosen _) (Chosen _) = True"
  | "same_shape _ _ = False"

definition compare_vacant :: "'a itself \<Rightarrow> bool"
  where "compare_vacant _ = same_shape (Vacant :: 'a inference_choice) Vacant"

definition discarded_choice :: "'a itself \<Rightarrow> bool \<Rightarrow> bool"
  where "discarded_choice _ b =
    (case (if b then (Vacant :: 'a inference_choice, True) else (Vacant, False)) of
      (_, result) \<Rightarrow> result)"

definition concrete_vacant :: bool
  where "concrete_vacant = same_shape (Vacant :: bool inference_choice) Vacant"

definition nested_vacant :: "'a itself \<Rightarrow> bool"
  where "nested_vacant _ =
    same_shape (Chosen (Vacant :: 'a inference_choice)) (Chosen Vacant)"

datatype ('a, 'b) partial_choice = Both 'a 'b | OnlyFirst 'a

text \<open>
  Only the second parameter lacks a field witness in OnlyFirst. The explicit
  constructor path should supply that parameter while allowing Rust to infer
  the first from its boolean field.
\<close>
definition partially_witnessed :: "'a itself \<Rightarrow> bool \<Rightarrow> bool"
  where "partially_witnessed _ b =
    (case (if b then (OnlyFirst True :: (bool, 'a) partial_choice) else OnlyFirst False) of
       OnlyFirst x \<Rightarrow> x | Both _ _ \<Rightarrow> False)"

export_code compare_vacant discarded_choice concrete_vacant nested_vacant partially_witnessed
  in Rust module_name ConstructorInference

end
