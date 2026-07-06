theory Option_Test
  imports Main "Rust.Rust_Setup"
begin

datatype option = None | Some int | Rec option

fun get :: "option \<Rightarrow> int" where
  "get (Some x) = x"
| "get None = 0"
| "get (Rec op) = get op"

fun set :: "option \<Rightarrow> int \<Rightarrow> option" where
  "set (Some _) x = Some x"
| "set None x = Some x"
| "set (Rec op) x = Rec (set op x)"

export_code
  get set
  in Rust

end
