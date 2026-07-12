theory BigInt_Divmod_Dispatch_Test
  imports Main "Rust.Rust_BigInt_Nat_Setup"
begin

(* hol-stress guidance test (Generate.thy: Arith.rs `divmod` implementation --
   E0277/E0308 from mixing `Num` with the BigInt-backed integer instance).

   Isabelle's numeral div/mod equations recurse over the internal `num`
   datatype while producing values of the selected integer representation.  In
   the BigInt setup the surrounding Rust trait impl is for `BigInt`, but several
   recursive calls are currently printed as
   `<Num as LinorderedEuclideanSemiringDivision>::divmod(...)`.  No such `Num`
   impl exists, and its `(Num, Num)` result is then passed where `(BigInt,
   BigInt)` is required.

   The generic `dispatch_divmod` wrapper followed by its `integer`
   specialization forces reconstruction of the BigInt trait impl; exporting the
   implementation constants keeps the recursive algorithm visible.  Together
   they reproduce the same wrong receiver while remaining independent of a
   particular machine-sized integer. *)

definition integer_divmod_pair :: "integer \<Rightarrow> integer \<Rightarrow> integer \<times> integer" where
  "integer_divmod_pair k l = (k div l, k mod l)"

definition dispatch_divmod ::
  "num \<Rightarrow> num \<Rightarrow> 'a::linordered_euclidean_semiring_division \<times> 'a" where
  "dispatch_divmod m n = divmod m n"

definition integer_instance_divmod :: "num \<Rightarrow> num \<Rightarrow> integer \<times> integer" where
  "integer_instance_divmod = dispatch_divmod"

export_code
  Code_Numeral.linordered_euclidean_semiring_division_integer_inst.divmod_integer
  Code_Numeral.divmod_integer integer_divmod_pair dispatch_divmod
  integer_instance_divmod in Rust

end
