# Isabelle 2025 adapter syntax

Use code_printing for target (Rust). Return declaration body, imports, support files and root declarations; the controller assembles Rust_Program_Setup.thy.

Examples show syntax, not mandatory mappings:

    code_printing type_constructor bool \<rightharpoonup> (Rust) "bool"
      | constant True \<rightharpoonup> (Rust) "true"
    code_printing type_constructor Nat.nat \<rightharpoonup> (Rust) "u128"
    code_printing type_constructor List.list \<rightharpoonup> (Rust) "Vec<_>"

Underscores are argument holes. Escape literal identifier underscores: `my'_module::Type`. Call templates: `"!crate::Numbers::add'(_, _')"` has two holes; `"!crate::Numbers::inc'(_')"` has one. Plain Rust does not use this escaping.

Use typed surface constants when needed: `constant "plus :: nat \<Rightarrow> nat \<Rightarrow> nat"`. Graph IDs are not always valid Isar surface names; request source or inspect actual diagnostics rather than guessing overloaded names.

`code_printing code_module Numbers \<rightharpoonup> (Rust) \<open>...module body...\<close> for CONST1 CONST2` supplies support. Ordinary rust_files and rust_root are also available. Use cartouches, not obsolete {* *}.

HOL-Library.Code_Target_Nat and Code_Target_Int can change executable equations/constants. Isabelle feedback returns effective bindings and changed nodes. No override is needed for every helper. ML printers may not be simple templates; retain reported limits.

## Common instance-name trap

Do not write `constant zero_nat`, `one_nat`, `plus_nat`, `minus_nat` or `HOL.equal` with a bare unconstrained polymorphic type. These spellings have caused real loading failures. A Thingol-generated short name is not an Isar surface constant. Adding the same type annotation to an unknown name does not resolve it.

Use typed surface terms for overloaded operations. These forms are used by the existing Isabelle2Rust adapters (only syntax is reused, not their representation policy):

    constant "0 :: nat"
    constant "plus :: nat \<Rightarrow> _ \<Rightarrow> _"
    constant "minus :: nat \<Rightarrow> _ \<Rightarrow> _"
    constant "times :: nat \<Rightarrow> _ \<Rightarrow> _"
    constant "HOL.equal :: nat \<Rightarrow> _ \<Rightarrow> bool"

Alternatively, actual instance constants loaded in the current HOL context include `zero_nat_inst.zero_nat`, `one_nat_inst.one_nat`, `plus_nat_inst.plus_nat`, `minus_nat_inst.minus_nat` and `equal_nat_inst.equal_nat`. The qualification before the final dot matters. `HOL.equal_class.equal` names the class operation; a typed polymorphic term needs the `equal` sort, not unconstrained `'a`.

A small standalone syntax example (target helper/body chosen separately):

    code_printing
      constant "0 :: nat" \<rightharpoonup> (Rust) "!crate::numbers::zero'()"
    | constant "plus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
        (Rust) "!crate::numbers::add'(_, _')"

This does not select a numeric library. Implement `zero` and `add` for your selected representation. If Isabelle reports "Not a constant", change the invalid source selector using these forms or request the defining source; do not repeatedly submit the same short selector.
