theory search_Test
  imports Main "Rust.Rust_Setup"
begin

(* Cleaned for the Rust export suite: the original `search.thy` carried an
   incomplete/broken proof (a `then show ?case` with no statement, ~line 209)
   that stops the theory from elaborating before `export_code` is reached. All
   the proofs and `value` probes were dropped — they are neither exported nor
   depended on by an exported constant — leaving the four executable search
   functions, which export and compile cleanly. *)

fun liner_search_iter :: "'a \<Rightarrow> 'a list \<Rightarrow> nat \<Rightarrow> nat option" where
  "liner_search_iter _ [] _ = None"|
  "liner_search_iter x (x0 # xs) idx = (if x=x0 then (Some idx) else (liner_search_iter x xs (idx+1)))"

fun liner_search :: "'a \<Rightarrow> 'a list \<Rightarrow> nat option" where
  "liner_search a xs = liner_search_iter a xs 0"

function binary_search_iter :: "'a::ord \<Rightarrow> 'a list \<Rightarrow> int \<Rightarrow> int \<Rightarrow> nat option" where
  "binary_search_iter x xs l r = (if l \<le> r then
  (let mid=(l+r) div 2; mid_v=xs ! (nat mid) in
      (if mid_v=x
        then (Some (nat mid))
        else (if mid_v < x
              then (binary_search_iter x xs (mid+1) r)
              else (binary_search_iter x xs l (mid-1))))) else None)"
  by pat_completeness auto
termination apply (relation "measure (\<lambda> (x, xs, l, r). nat (r-l+1))")
    apply auto
  done

fun binary_search :: "'a::ord \<Rightarrow> 'a list \<Rightarrow> nat option" where
  bin_Nil: "binary_search _ [] = None"|
  bin_xs: "binary_search x xs = binary_search_iter x xs 0 ((int (length xs))-1)"

export_code liner_search_iter liner_search binary_search_iter binary_search in Rust

end
