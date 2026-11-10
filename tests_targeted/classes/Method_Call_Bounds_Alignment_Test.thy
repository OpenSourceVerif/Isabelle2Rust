theory Method_Call_Bounds_Alignment_Test
  imports Rust_Base_Setup
begin

text \<open>
  An absent method selects the instance parameter names (b, a), while the
  executable method uses (a, b). Its product-equality call requires equal only
  for the second constructor parameter. Propagating the callee's bounds by raw
  variable name would incorrectly constrain the first parameter as well.

  The opaque first field is never compared. Its equal implementation is not
  reachable from these roots, so the concrete wrapper catches that extra bound
  during Rust compilation. The generic wrapper also permits external Rust
  inhabitants with no generated Equal instance in their first slot.
\<close>

class pair_compare =
  fixes unused_pair_copy :: "'a \<Rightarrow> 'a"
    and pair_compare :: "'a \<Rightarrow> 'a \<Rightarrow> bool"

datatype opaque_payload = OpaquePayload bool
datatype ('a, 'b) payload_pair = PayloadPair 'a 'b

instantiation payload_pair :: (type, equal) pair_compare
begin
fun pair_compare_payload_pair :: "('a, 'b) payload_pair \<Rightarrow> ('a, 'b) payload_pair \<Rightarrow> bool"
  where "pair_compare_payload_pair (PayloadPair x y) (PayloadPair u v) =
    HOL.equal (y, y) (v, v)"
definition unused_pair_copy_payload_pair :: "('a, 'b) payload_pair \<Rightarrow> ('a, 'b) payload_pair"
  where "unused_pair_copy_payload_pair x = x"
instance ..
end

declare unused_pair_copy_payload_pair_def [code del]

definition compare_payloads :: "('a, 'b::equal) payload_pair \<Rightarrow> ('a, 'b) payload_pair \<Rightarrow> bool"
  where "compare_payloads x y = pair_compare x y"

definition compare_opaque :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "compare_opaque p x q y =
    compare_payloads (PayloadPair (OpaquePayload p) x) (PayloadPair (OpaquePayload q) y)"

lemma compare_opaque_observation:
  "compare_opaque p x q y = (x = y)"
  by (simp add: compare_opaque_def compare_payloads_def equal_prod_def equal_bool_def)

export_code pair_compare_payload_pair_inst.unused_pair_copy_payload_pair
  pair_compare pair_compare_payload_pair_inst.pair_compare_payload_pair
  compare_payloads compare_opaque
  in Rust module_name MethodCallBoundsAlignment

end
