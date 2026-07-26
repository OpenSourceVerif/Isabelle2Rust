theory Word_Rec_Arity_Test
  imports "HOL-Library.Word" "Rust.Rust_Base_Setup"
begin

(* hol-stress guidance test (Generate.thy: Word.rs `word_rec` --
   E0057/E0308 in a higher-order callback adapter).

   `word_rec` converts the natural recursion index to a word before invoking a
   two-argument step function.  The backend prints the adapter closure with two
   Rust arguments but then routes it through generated composition/application
   code that expects a unary function value, eventually calling a unary value
   with two arguments.  The Rust callback arity must remain consistent through
   `rec_nat`, `comp`, and the word conversion.

   Re-exporting the library primitive pins the exact core HOL construction that
   produces Word.rs:213 in the broad crate. *)

export_code word_rec in Rust

end
