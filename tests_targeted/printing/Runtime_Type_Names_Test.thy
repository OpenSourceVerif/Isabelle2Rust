theory Runtime_Type_Names_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  Generated HOL type names share Rust's type namespace with imported runtime
  types and prelude traits. Rc, BigInt, Clone, Fn, and PhantomData must remain
  available to the backend while all references to identically named source
  datatypes consistently use their allocated names. Separate exports isolate
  each collision; the combined export checks that their allocations coexist.
  Observable wrappers exercise the source constructors, closures, native
  integer arithmetic, generic cloning, and phantom markers after renaming.
\<close>

datatype rc = LocalRc bool
datatype big_int = LocalBigInt bool
datatype clone = LocalClone bool
datatype fn = LocalFn bool
datatype 'a phantom_data = PhantomTag bool

definition closure_collision :: "rc \<Rightarrow> (bool \<Rightarrow> rc) option"
  where "closure_collision x = Some (\<lambda>_. x)"
definition rc_roundtrip :: "bool \<Rightarrow> bool"
  where "rc_roundtrip b = (case closure_collision (LocalRc b) of
    None \<Rightarrow> False | Some f \<Rightarrow> (case f False of LocalRc c \<Rightarrow> c))"

definition numeric_collision :: "big_int \<Rightarrow> integer \<Rightarrow> big_int \<times> integer"
  where "numeric_collision x n = (x, n + 1)"
definition numeric_roundtrip :: "bool \<Rightarrow> integer \<Rightarrow> bool \<times> integer"
  where "numeric_roundtrip b n = (case numeric_collision (LocalBigInt b) n of
    (LocalBigInt c, m) \<Rightarrow> (c, m))"

definition clone_collision :: "'a \<Rightarrow> clone \<Rightarrow> 'a"
  where "clone_collision x tag = (case tag of LocalClone _ \<Rightarrow> x)"
definition clone_roundtrip :: "'a \<Rightarrow> 'a"
  where "clone_roundtrip b = clone_collision b (LocalClone False)"

definition fn_collision :: "fn \<Rightarrow> (bool \<Rightarrow> fn) option"
  where "fn_collision x = Some (\<lambda>_. x)"
definition fn_roundtrip :: "bool \<Rightarrow> bool"
  where "fn_roundtrip b = (case fn_collision (LocalFn b) of
    None \<Rightarrow> False | Some f \<Rightarrow> (case f True of LocalFn c \<Rightarrow> c))"

definition phantom_collision :: "bool \<Rightarrow> bool phantom_data"
  where "phantom_collision b = PhantomTag b"
fun phantom_observe :: "bool phantom_data \<Rightarrow> bool"
  where "phantom_observe (PhantomTag b) = b"

lemma observable_results:
  "rc_roundtrip b = b"
  "numeric_roundtrip b n = (b, n + 1)"
  "clone_roundtrip x = x"
  "fn_roundtrip b = b"
  "phantom_observe (phantom_collision b) = b"
  by (simp_all add: rc_roundtrip_def closure_collision_def
    numeric_roundtrip_def numeric_collision_def clone_roundtrip_def
    clone_collision_def fn_roundtrip_def fn_collision_def phantom_collision_def)

export_code closure_collision rc_roundtrip in Rust module_name RcCollision
export_code numeric_collision numeric_roundtrip in Rust module_name BigIntCollision
export_code clone_collision clone_roundtrip in Rust module_name CloneCollision
export_code fn_collision fn_roundtrip in Rust module_name FnCollision
export_code phantom_collision phantom_observe in Rust module_name PhantomDataCollision
export_code closure_collision rc_roundtrip numeric_collision numeric_roundtrip
  clone_collision clone_roundtrip fn_collision fn_roundtrip phantom_collision phantom_observe
  in Rust module_name RuntimeTypeNames

end
