theory IntegratedNestedData_Test
  imports Main "Rust.Rust_Setup"
begin

datatype leaf_tag =
  Tag bool bool bool

datatype bool_expr =
    EValue leaf_tag
  | ENot bool_expr
  | EAnd bool_expr bool_expr
  | EIf bool bool_expr bool_expr

fun tag_any :: "leaf_tag \<Rightarrow> bool" where
  "tag_any (Tag x y z) = (x \<or> y \<or> z)"

fun tag_all :: "leaf_tag \<Rightarrow> bool" where
  "tag_all (Tag x y z) = (x \<and> y \<and> z)"

fun tag_flip :: "leaf_tag \<Rightarrow> leaf_tag" where
  "tag_flip (Tag x y z) = Tag (\<not> x) (\<not> y) (\<not> z)"

fun tag_rotate :: "leaf_tag \<Rightarrow> leaf_tag" where
  "tag_rotate (Tag x y z) = Tag y z x"

(* A four-constructor expression tree exercises uneven recursive branches. *)

fun expr_is_value :: "bool_expr \<Rightarrow> bool" where
  "expr_is_value (EValue _) = True"
| "expr_is_value _ = False"

fun expr_eval :: "bool_expr \<Rightarrow> bool" where
  "expr_eval (EValue t) = tag_any t"
| "expr_eval (ENot e) = (\<not> expr_eval e)"
| "expr_eval (EAnd l r) = (expr_eval l \<and> expr_eval r)"
| "expr_eval (EIf b l r) = (if b then expr_eval l else expr_eval r)"

fun expr_size :: "bool_expr \<Rightarrow> nat" where
  "expr_size (EValue _) = 1"
| "expr_size (ENot e) = Suc (expr_size e)"
| "expr_size (EAnd l r) = Suc (expr_size l + expr_size r)"
| "expr_size (EIf _ l r) = Suc (expr_size l + expr_size r)"

fun expr_depth :: "bool_expr \<Rightarrow> nat" where
  "expr_depth (EValue _) = 1"
| "expr_depth (ENot e) = Suc (expr_depth e)"
| "expr_depth (EAnd l r) = Suc (max (expr_depth l) (expr_depth r))"
| "expr_depth (EIf _ l r) = Suc (max (expr_depth l) (expr_depth r))"

fun expr_tag_count :: "bool_expr \<Rightarrow> nat" where
  "expr_tag_count (EValue _) = 1"
| "expr_tag_count (ENot e) = expr_tag_count e"
| "expr_tag_count (EAnd l r) = expr_tag_count l + expr_tag_count r"
| "expr_tag_count (EIf _ l r) = expr_tag_count l + expr_tag_count r"

fun expr_all_tags :: "bool_expr \<Rightarrow> bool" where
  "expr_all_tags (EValue t) = tag_all t"
| "expr_all_tags (ENot e) = expr_all_tags e"
| "expr_all_tags (EAnd l r) = (expr_all_tags l \<and> expr_all_tags r)"
| "expr_all_tags (EIf _ l r) = (expr_all_tags l \<and> expr_all_tags r)"

fun expr_flip_tags :: "bool_expr \<Rightarrow> bool_expr" where
  "expr_flip_tags (EValue t) = EValue (tag_flip t)"
| "expr_flip_tags (ENot e) = ENot (expr_flip_tags e)"
| "expr_flip_tags (EAnd l r) = EAnd (expr_flip_tags l) (expr_flip_tags r)"
| "expr_flip_tags (EIf b l r) = EIf b (expr_flip_tags l) (expr_flip_tags r)"

fun expr_mirror :: "bool_expr \<Rightarrow> bool_expr" where
  "expr_mirror (EValue t) = EValue t"
| "expr_mirror (ENot e) = ENot (expr_mirror e)"
| "expr_mirror (EAnd l r) = EAnd (expr_mirror r) (expr_mirror l)"
| "expr_mirror (EIf b l r) = EIf b (expr_mirror r) (expr_mirror l)"

fun expr_collect_tags :: "bool_expr \<Rightarrow> leaf_tag list" where
  "expr_collect_tags (EValue t) = [t]"
| "expr_collect_tags (ENot e) = expr_collect_tags e"
| "expr_collect_tags (EAnd l r) = expr_collect_tags l @ expr_collect_tags r"
| "expr_collect_tags (EIf _ l r) = expr_collect_tags l @ expr_collect_tags r"

fun expr_same_shape :: "bool_expr \<Rightarrow> bool_expr \<Rightarrow> bool" where
  "expr_same_shape (EValue _) (EValue _) = True"
| "expr_same_shape (ENot x) (ENot y) = expr_same_shape x y"
| "expr_same_shape (EAnd l r) (EAnd l' r') =
     (expr_same_shape l l' \<and> expr_same_shape r r')"
| "expr_same_shape (EIf _ l r) (EIf _ l' r') =
     (expr_same_shape l l' \<and> expr_same_shape r r')"
| "expr_same_shape _ _ = False"

definition expr_choose :: "bool \<Rightarrow> bool_expr \<Rightarrow> bool_expr \<Rightarrow> bool_expr" where
  "expr_choose b l r = (if b then l else r)"

definition expr_query_pair :: "bool_expr \<Rightarrow> bool \<times> nat" where
  "expr_query_pair e = (expr_eval e, expr_depth e)"

definition expr_transform_chain :: "bool_expr \<Rightarrow> bool_expr" where
  "expr_transform_chain e =
    (let x = e;
         x = expr_flip_tags x;
         x = expr_mirror x
     in x)"

(* The wrapper combines a recursive tree, a recursive list, and a Copy flag. *)

datatype expr_bundle =
  ExprBundle bool_expr "bool_expr list" bool

fun expr_list_eval :: "bool_expr list \<Rightarrow> bool list" where
  "expr_list_eval [] = []"
| "expr_list_eval (x # xs) = expr_eval x # expr_list_eval xs"

fun expr_list_size :: "bool_expr list \<Rightarrow> nat" where
  "expr_list_size [] = 0"
| "expr_list_size (x # xs) = expr_size x + expr_list_size xs"

fun expr_list_flip :: "bool_expr list \<Rightarrow> bool_expr list" where
  "expr_list_flip [] = []"
| "expr_list_flip (x # xs) = expr_flip_tags x # expr_list_flip xs"

fun bundle_flag :: "expr_bundle \<Rightarrow> bool" where
  "bundle_flag (ExprBundle _ _ b) = b"

fun bundle_size :: "expr_bundle \<Rightarrow> nat" where
  "bundle_size (ExprBundle focus rest _) = expr_size focus + expr_list_size rest"

fun bundle_eval :: "expr_bundle \<Rightarrow> bool \<times> bool list" where
  "bundle_eval (ExprBundle focus rest _) = (expr_eval focus, expr_list_eval rest)"

fun bundle_flip :: "expr_bundle \<Rightarrow> expr_bundle" where
  "bundle_flip (ExprBundle focus rest b) =
     ExprBundle (expr_flip_tags focus) (expr_list_flip rest) (\<not> b)"

definition bundle_query_pair :: "expr_bundle \<Rightarrow> bool \<times> nat" where
  "bundle_query_pair b = (bundle_flag b, bundle_size b)"

export_code
  tag_any tag_all tag_flip tag_rotate expr_is_value expr_eval expr_size
  expr_depth expr_tag_count expr_all_tags expr_flip_tags expr_mirror
  expr_collect_tags expr_same_shape expr_choose expr_query_pair
  expr_transform_chain expr_list_eval expr_list_size expr_list_flip bundle_flag
  bundle_size bundle_eval bundle_flip bundle_query_pair
  in Rust

end
