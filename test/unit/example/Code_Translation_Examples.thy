theory Code_Translation_Examples
  imports Main "Rust.Rust_Base_Setup"
begin

datatype 'a paper_list =
    PaperNil
  | PaperCons 'a "'a paper_list"

datatype ('a, 'b) phantom_box = PhantomBox 'a

definition make_pair :: "int \<Rightarrow> (int \<Rightarrow> int) \<times> int" where
  "make_pair y = ((\<lambda>x. x + y), y)"

definition offset_sum :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "offset_sum c = (\<lambda>x y. x + y + c)"

definition test_offset_sum :: "int \<Rightarrow> int \<Rightarrow> int" where
  "test_offset_sum x = (\<lambda>y. offset_sum 1 x y)"

fun singleton_list :: "'a paper_list \<Rightarrow> bool" where
  "singleton_list xs =
    (case xs of
       PaperCons _ PaperNil \<Rightarrow> True
     | _ \<Rightarrow> False)"

fun paper_length :: "'a paper_list \<Rightarrow> nat" where
  "paper_length PaperNil = 0"
| "paper_length (PaperCons _ xs) = Suc (paper_length xs)"

class paper_semigroup =
  fixes paper_plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+p" 65)

class paper_monoid = paper_semigroup +
  fixes paper_zero :: 'a

datatype paper_nat = PaperZero | PaperSuc paper_nat

instantiation paper_nat :: paper_semigroup
begin

fun paper_plus_paper_nat :: "paper_nat \<Rightarrow> paper_nat \<Rightarrow> paper_nat" where
  "PaperZero +p b = b"
| "PaperSuc a +p b = PaperSuc (a +p b)"

instance ..
end

instantiation paper_nat :: paper_monoid
begin

definition paper_zero_paper_nat :: paper_nat where
  "paper_zero = PaperZero"

instance ..
end

definition use_paper_plus :: "paper_nat \<Rightarrow> paper_nat \<Rightarrow> paper_nat" where
  "use_paper_plus x y = x +p y"

definition use_paper_zero :: paper_nat where
  "use_paper_zero = paper_zero"

definition generic_paper_plus :: "'a::paper_semigroup \<Rightarrow> 'a \<Rightarrow> 'a" where
  "generic_paper_plus x y = x +p y"

definition generic_paper_zero :: "'a::paper_monoid" where
  "generic_paper_zero = paper_zero"

export_code
  PhantomBox make_pair offset_sum test_offset_sum singleton_list paper_length
  use_paper_plus use_paper_zero generic_paper_plus generic_paper_zero
  in Rust

end
