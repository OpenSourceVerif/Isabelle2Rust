theory Exception_Generic_Order_Test
  imports Rust_Base_Setup
begin

text \<open>
  A constant declared with code abort has no executable equations, but it still
  has a polymorphic Rust function signature. Its result-only type parameter
  requires explicit type arguments at calls. The exception declaration must
  use the same parameter order as ordinary function declarations and calls,
  even when that order differs from Thingol's list of sorted type variables.
  These roots cover concrete calls, a generic caller, and a delayed function
  value. Reaching the exception must still panic; constructing the function
  value or choosing another branch must not panic.
\<close>

definition missing_result :: "'a list \<Rightarrow> 'b option"
  where "missing_result xs = undefined"

declare [[code abort: missing_result]]

definition exception_concrete :: "bool list \<Rightarrow> unit option"
  where "exception_concrete xs = missing_result xs"

definition exception_generic :: "'a list \<Rightarrow> bool option"
  where "exception_generic xs = missing_result xs"

definition exception_delayed :: "bool \<Rightarrow> (unit list \<Rightarrow> bool option)"
  where "exception_delayed enabled =
    (if enabled then missing_result else (\<lambda>_. Some True))"

definition exception_safe :: "bool \<Rightarrow> bool option"
  where "exception_safe enabled = (if enabled then missing_result [()] else Some False)"

export_code exception_concrete exception_generic exception_delayed exception_safe
  in Rust module_name ExceptionGenerics

end
