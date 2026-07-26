theory Copy_Generic_RCall_Test
  imports Main "Rust.Rust_Base_Setup"
begin

datatype flag_pair =
  FlagPair bool bool

datatype flag_triple =
  FlagTriple bool bool bool

datatype color =
    Red
  | Green
  | Blue

datatype pixel =
  Pixel color color color

datatype nested_pair =
  NestedPair flag_pair color

datatype palette =
  Palette pixel pixel

datatype 'a copy_wrap =
  CopyWrap 'a

datatype ('a, 'b) copy_pair_wrap =
  CopyPairWrap 'a 'b

datatype 'a nested_copy_wrap =
  NestedCopyWrap "'a copy_wrap"

datatype copy_tree =
    CopyLeaf bool
  | CopyNode copy_tree copy_tree

fun flag_left :: "flag_pair \<Rightarrow> bool" where
  "flag_left (FlagPair x y) = x"

fun flag_right :: "flag_pair \<Rightarrow> bool" where
  "flag_right (FlagPair x y) = y"

fun flag_swap :: "flag_pair \<Rightarrow> flag_pair" where
  "flag_swap (FlagPair x y) = FlagPair y x"

fun flag_dup :: "flag_pair \<Rightarrow> flag_pair \<times> flag_pair" where
  "flag_dup x = (x, x)"

fun triple_first :: "flag_triple \<Rightarrow> bool" where
  "triple_first (FlagTriple x y z) = x"

fun triple_second :: "flag_triple \<Rightarrow> bool" where
  "triple_second (FlagTriple x y z) = y"

fun triple_rotate :: "flag_triple \<Rightarrow> flag_triple" where
  "triple_rotate (FlagTriple x y z) = FlagTriple y z x"

fun color_is_red :: "color \<Rightarrow> bool" where
  "color_is_red Red = True"
| "color_is_red Green = False"
| "color_is_red Blue = False"

fun color_dup :: "color \<Rightarrow> color \<times> color" where
  "color_dup c = (c, c)"

fun pixel_first :: "pixel \<Rightarrow> color" where
  "pixel_first (Pixel r g b) = r"

fun pixel_second :: "pixel \<Rightarrow> color" where
  "pixel_second (Pixel r g b) = g"

fun pixel_rotate :: "pixel \<Rightarrow> pixel" where
  "pixel_rotate (Pixel r g b) = Pixel g b r"

fun pixel_replace_first :: "pixel \<Rightarrow> color \<Rightarrow> pixel" where
  "pixel_replace_first (Pixel r g b) c = Pixel c g b"

fun nested_get_flag :: "nested_pair \<Rightarrow> flag_pair" where
  "nested_get_flag (NestedPair p c) = p"

fun nested_get_color :: "nested_pair \<Rightarrow> color" where
  "nested_get_color (NestedPair p c) = c"

fun nested_dup :: "nested_pair \<Rightarrow> nested_pair \<times> nested_pair" where
  "nested_dup x = (x, x)"

fun palette_first :: "palette \<Rightarrow> pixel" where
  "palette_first (Palette p q) = p"

fun palette_swap :: "palette \<Rightarrow> palette" where
  "palette_swap (Palette p q) = Palette q p"

fun wrap_unwrap :: "'a copy_wrap \<Rightarrow> 'a" where
  "wrap_unwrap (CopyWrap x) = x"

fun wrap_dup :: "'a copy_wrap \<Rightarrow> 'a copy_wrap \<times> 'a copy_wrap" where
  "wrap_dup x = (x, x)"

fun wrap_map_flag :: "flag_pair copy_wrap \<Rightarrow> flag_pair" where
  "wrap_map_flag (CopyWrap x) = x"

fun pair_wrap_first :: "('a, 'b) copy_pair_wrap \<Rightarrow> 'a" where
  "pair_wrap_first (CopyPairWrap x y) = x"

fun pair_wrap_swap :: "('a, 'b) copy_pair_wrap \<Rightarrow> ('b, 'a) copy_pair_wrap" where
  "pair_wrap_swap (CopyPairWrap x y) = CopyPairWrap y x"

fun pair_wrap_dup :: "('a, 'b) copy_pair_wrap \<Rightarrow> ('a, 'b) copy_pair_wrap \<times> ('a, 'b) copy_pair_wrap" where
  "pair_wrap_dup x = (x, x)"

fun nested_wrap_dup :: "'a nested_copy_wrap \<Rightarrow> 'a nested_copy_wrap \<times> 'a nested_copy_wrap" where
  "nested_wrap_dup x = (x, x)"

fun nested_wrap_unwrap_flag :: "flag_pair nested_copy_wrap \<Rightarrow> flag_pair" where
  "nested_wrap_unwrap_flag (NestedCopyWrap (CopyWrap x)) = x"

fun wrap_tree_dup :: "copy_tree copy_wrap \<Rightarrow> copy_tree copy_wrap \<times> copy_tree copy_wrap" where
  "wrap_tree_dup x = (x, x)"

fun mixed_pair_first :: "(flag_pair, copy_tree) copy_pair_wrap \<Rightarrow> flag_pair" where
  "mixed_pair_first (CopyPairWrap x t) = x"

fun mixed_pair_dup :: "(flag_pair, copy_tree) copy_pair_wrap \<Rightarrow> (flag_pair, copy_tree) copy_pair_wrap \<times> (flag_pair, copy_tree) copy_pair_wrap" where
  "mixed_pair_dup x = (x, x)"

fun value_dup :: "'a \<Rightarrow> 'a \<times> 'a" where
  "value_dup x = (x, x)"

fun tree_is_leaf :: "copy_tree \<Rightarrow> bool" where
  "tree_is_leaf (CopyLeaf b) = True"
| "tree_is_leaf (CopyNode l r) = False"

fun tree_dup :: "copy_tree \<Rightarrow> copy_tree \<times> copy_tree" where
  "tree_dup x = (x, x)"

(* R-Call tests: callers that delegate to Clone-bounded functions *)

(* Concrete caller: wrap_dup argument is Copy, R-Call should redirect to wrap_dup_copy *)
fun use_wrap_dup_flag :: "flag_pair copy_wrap \<Rightarrow> flag_pair copy_wrap \<times> flag_pair copy_wrap" where
  "use_wrap_dup_flag x = wrap_dup x"

(* Generic caller: when A is Copy, R-Call should redirect to wrap_dup_copy in the _copy specialization *)
fun use_wrap_dup_generic :: "'a copy_wrap \<Rightarrow> 'a copy_wrap \<times> 'a copy_wrap" where
  "use_wrap_dup_generic x = wrap_dup x"

(* Concrete caller for value_dup: FlagPair is Copy, R-Call should redirect *)
fun use_value_dup_flag :: "flag_pair \<Rightarrow> flag_pair \<times> flag_pair" where
  "use_value_dup_flag x = value_dup x"

export_code
  flag_left flag_right flag_swap flag_dup
  triple_first triple_second triple_rotate
  color_is_red color_dup
  pixel_first pixel_second pixel_rotate pixel_replace_first
  nested_get_flag nested_get_color nested_dup
  palette_first palette_swap
  wrap_unwrap wrap_dup wrap_map_flag
  pair_wrap_first pair_wrap_swap pair_wrap_dup
  nested_wrap_dup nested_wrap_unwrap_flag
  wrap_tree_dup mixed_pair_first mixed_pair_dup
  value_dup
  tree_is_leaf tree_dup
  use_wrap_dup_flag use_wrap_dup_generic use_value_dup_flag
  in Rust

end
