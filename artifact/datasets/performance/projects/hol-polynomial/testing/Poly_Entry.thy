theory Poly_Entry imports "HOL-Computational_Algebra.Polynomial" "Rust.Rust_Base_Setup" begin
definition poly_entry :: "int poly => int => int" where "poly_entry p x = poly p x"
lemma original_binding: "poly_entry p x = poly p x" by (simp add: poly_entry_def)
end
