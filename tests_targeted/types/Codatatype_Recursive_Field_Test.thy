theory Codatatype_Recursive_Field_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* A recursive codatatype field is represented by Box in Rust.  The tail of
   guarded_count is a conditional expression, so the generated constructor must
   wrap the complete `if` value as `Box::new(if ... { ... } else { ... })`; merely
   boxing ordinary applications in either branch leaves the constructor field at
   the wrong Rust type. *)
codatatype 'a guarded_stream =
  GCons (ghead: 'a) (gtail: "'a guarded_stream")

primcorec guarded_count :: "nat \<Rightarrow> nat guarded_stream" where
  "ghead (guarded_count n) = n"
| "gtail (guarded_count n) =
    (if n = 0 then guarded_count 1 else guarded_count (n - 1))"

(* Equality for a recursive datatype is compiled as nested matches because the
   tail pattern contains a boxed field.  Its generated field binders must remain
   distinct from both function parameters; otherwise the first head binder can
   shadow the second stream parameter before that parameter is matched. *)
definition guarded_equal ::
    "nat guarded_stream \<Rightarrow> nat guarded_stream \<Rightarrow> bool" where
  "guarded_equal xs ys \<longleftrightarrow> xs = ys"

export_code guarded_count guarded_equal in Rust

end
