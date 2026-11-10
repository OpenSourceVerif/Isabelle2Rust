theory Runtime_Sized_Name_Test
  imports Rust_Base_Setup
begin

text \<open>
  Source datatype sized must not shadow the standard Sized trait in generated
  trait method signatures. The source class clone and its static operation
  clone also coexist with the standard Clone bound and .clone() calls. Export
  a generic operation so instance reconstruction is exercised, and a closure
  carrying the source datatype so standard capture cloning remains observable.
\<close>

datatype sized = SourceSized bool

class clone =
  fixes clone :: "'a \<Rightarrow> 'a"

instantiation sized :: clone
begin

definition clone_sized :: "sized \<Rightarrow> sized"
  where "clone_sized x = x"

instance ..
end

definition generic_clone :: "'a::clone \<Rightarrow> 'a"
  where "generic_clone x = clone x"

definition observe_sized :: "bool \<Rightarrow> bool"
  where "observe_sized b = (case generic_clone (SourceSized b) of SourceSized c \<Rightarrow> c)"

definition capture_sized :: "sized \<Rightarrow> (bool \<Rightarrow> sized) option"
  where "capture_sized x = Some (\<lambda>_. x)"

definition observe_capture :: "bool \<Rightarrow> bool"
  where "observe_capture b = (case capture_sized (SourceSized b) of
    None \<Rightarrow> False | Some f \<Rightarrow> (case f True of SourceSized c \<Rightarrow> c))"

lemma source_observations:
  "observe_sized b = b" "observe_capture b = b"
  by (simp_all add: observe_sized_def generic_clone_def clone_sized_def
    observe_capture_def capture_sized_def)

export_code generic_clone observe_sized capture_sized observe_capture
  in Rust module_name RuntimeSizedName

end
