theory IntegratedList_Test
  imports Main "Rust.Rust_Base_Setup"
begin

datatype bit_cell =
  Bits bool bool

datatype 'a object_list =
    OEnd
  | OLink 'a "'a object_list"

fun bits_any :: "bit_cell \<Rightarrow> bool" where
  "bits_any (Bits x y) = (x \<or> y)"

fun bits_all :: "bit_cell \<Rightarrow> bool" where
  "bits_all (Bits x y) = (x \<and> y)"

fun bits_swap :: "bit_cell \<Rightarrow> bit_cell" where
  "bits_swap (Bits x y) = Bits y x"

(* Basic edge cases: empty, singleton, and recursive tails. *)

fun olist_is_empty :: "'a object_list \<Rightarrow> bool" where
  "olist_is_empty OEnd = True"
| "olist_is_empty (OLink _ _) = False"

fun olist_head :: "'a object_list \<Rightarrow> 'a option" where
  "olist_head OEnd = None"
| "olist_head (OLink x _) = Some x"

fun olist_last :: "'a object_list \<Rightarrow> 'a option" where
  "olist_last OEnd = None"
| "olist_last (OLink x OEnd) = Some x"
| "olist_last (OLink _ xs) = olist_last xs"

fun olist_length :: "'a object_list \<Rightarrow> nat" where
  "olist_length OEnd = 0"
| "olist_length (OLink _ xs) = Suc (olist_length xs)"

fun olist_any :: "bit_cell object_list \<Rightarrow> bool" where
  "olist_any OEnd = False"
| "olist_any (OLink x xs) = (bits_any x \<or> olist_any xs)"

fun olist_all :: "bit_cell object_list \<Rightarrow> bool" where
  "olist_all OEnd = True"
| "olist_all (OLink x xs) = (bits_all x \<and> olist_all xs)"

fun olist_count :: "bit_cell object_list \<Rightarrow> nat" where
  "olist_count OEnd = 0"
| "olist_count (OLink x xs) =
     (if bits_any x then Suc (olist_count xs) else olist_count xs)"

(* Recursive reconstruction and multi-parameter ownership. *)

fun olist_swap_bits :: "bit_cell object_list \<Rightarrow> bit_cell object_list" where
  "olist_swap_bits OEnd = OEnd"
| "olist_swap_bits (OLink x xs) = OLink (bits_swap x) (olist_swap_bits xs)"

fun olist_append :: "'a object_list \<Rightarrow> 'a object_list \<Rightarrow> 'a object_list" where
  "olist_append OEnd ys = ys"
| "olist_append (OLink x xs) ys = OLink x (olist_append xs ys)"

fun olist_reverse_acc :: "'a object_list \<Rightarrow> 'a object_list \<Rightarrow> 'a object_list" where
  "olist_reverse_acc OEnd acc = acc"
| "olist_reverse_acc (OLink x xs) acc = olist_reverse_acc xs (OLink x acc)"

definition olist_reverse :: "'a object_list \<Rightarrow> 'a object_list" where
  "olist_reverse xs = olist_reverse_acc xs OEnd"

fun olist_zip ::
  "'a object_list \<Rightarrow> 'b object_list \<Rightarrow> ('a \<times> 'b) object_list" where
  "olist_zip OEnd _ = OEnd"
| "olist_zip _ OEnd = OEnd"
| "olist_zip (OLink x xs) (OLink y ys) = OLink (x, y) (olist_zip xs ys)"

fun olist_unzip ::
  "('a \<times> 'b) object_list \<Rightarrow> 'a object_list \<times> 'b object_list" where
  "olist_unzip OEnd = (OEnd, OEnd)"
| "olist_unzip (OLink (x, y) ps) =
     (case olist_unzip ps of
        (xs, ys) \<Rightarrow> (OLink x xs, OLink y ys))"

fun olist_take_true :: "bit_cell object_list \<Rightarrow> bit_cell object_list" where
  "olist_take_true OEnd = OEnd"
| "olist_take_true (OLink x xs) =
     (if bits_any x then OLink x (olist_take_true xs) else OEnd)"

fun olist_filter_true :: "bit_cell object_list \<Rightarrow> bit_cell object_list" where
  "olist_filter_true OEnd = OEnd"
| "olist_filter_true (OLink x xs) =
     (if bits_any x then OLink x (olist_filter_true xs) else olist_filter_true xs)"

fun olist_partition ::
  "bit_cell object_list \<Rightarrow> bit_cell object_list \<times> bit_cell object_list" where
  "olist_partition OEnd = (OEnd, OEnd)"
| "olist_partition (OLink x xs) =
     (case olist_partition xs of
        (yes, no) \<Rightarrow>
          if bits_any x then (OLink x yes, no) else (yes, OLink x no))"

(* A wrapper makes the list part of a larger non-Copy value. *)

datatype bit_bucket =
  BitBucket "bit_cell object_list" bool

fun bucket_is_empty :: "bit_bucket \<Rightarrow> bool" where
  "bucket_is_empty (BitBucket xs _) = olist_is_empty xs"

fun bucket_any :: "bit_bucket \<Rightarrow> bool" where
  "bucket_any (BitBucket xs fallback) = (olist_any xs \<or> fallback)"

fun bucket_flip :: "bit_bucket \<Rightarrow> bit_bucket" where
  "bucket_flip (BitBucket xs fallback) =
     BitBucket (olist_swap_bits xs) (\<not> fallback)"

fun bucket_merge :: "bit_bucket \<Rightarrow> bit_bucket \<Rightarrow> bit_bucket" where
  "bucket_merge (BitBucket xs x) (BitBucket ys y) =
     BitBucket (olist_append xs ys) (x \<or> y)"

definition olist_query_pair :: "bit_cell object_list \<Rightarrow> bool \<times> nat" where
  "olist_query_pair xs = (olist_any xs, olist_length xs)"

definition olist_transform_chain ::
  "bit_cell object_list \<Rightarrow> bit_cell object_list" where
  "olist_transform_chain xs =
    (let ys = xs;
         ys = olist_swap_bits ys;
         ys = olist_reverse ys
     in ys)"

export_code
  bits_any bits_all bits_swap olist_is_empty olist_head olist_last olist_length
  olist_any olist_all olist_count olist_swap_bits olist_append olist_reverse_acc
  olist_reverse olist_zip olist_unzip olist_take_true olist_filter_true
  olist_partition bucket_is_empty bucket_any bucket_flip bucket_merge
  olist_query_pair olist_transform_chain
  in Rust

end
