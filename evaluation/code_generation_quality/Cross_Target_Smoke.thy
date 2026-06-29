theory Cross_Target_Smoke
  imports
    "../../tests_targeted/abstraction/Abs_Capture_Test"
    "../../tests_targeted/types/Type_Nested_Rec_Test"
    "../../tests_targeted/classes/Class_Superclass_Test"
    "../../tests_targeted/fpp/4_ds_algo/Sorting/Quicksort_Test"
    "Go.Go_Setup"
begin

export_code
  Abs_Capture_Test.make_pair
  Type_Nested_Rec_Test.wrap
  Type_Nested_Rec_Test.is_leaf
  Class_Superclass_Test.add12
  Quicksort_Test.quicksort
in SML module_name Cross_Target_Smoke

export_code
  Abs_Capture_Test.make_pair
  Type_Nested_Rec_Test.wrap
  Type_Nested_Rec_Test.is_leaf
  Class_Superclass_Test.add12
  Quicksort_Test.quicksort
in OCaml module_name Cross_Target_Smoke

export_code
  Abs_Capture_Test.make_pair
  Type_Nested_Rec_Test.wrap
  Type_Nested_Rec_Test.is_leaf
  Class_Superclass_Test.add12
  Quicksort_Test.quicksort
in Haskell module_name Cross_Target_Smoke

export_code
  Abs_Capture_Test.make_pair
  Type_Nested_Rec_Test.wrap
  Type_Nested_Rec_Test.is_leaf
  Class_Superclass_Test.add12
  Quicksort_Test.quicksort
in Scala module_name Cross_Target_Smoke

export_code
  Abs_Capture_Test.make_pair
  Type_Nested_Rec_Test.wrap
  Type_Nested_Rec_Test.is_leaf
  Class_Superclass_Test.add12
  Quicksort_Test.quicksort
in Go module_name Cross_Target_Smoke

export_code
  Abs_Capture_Test.make_pair
  Type_Nested_Rec_Test.wrap
  Type_Nested_Rec_Test.is_leaf
  Class_Superclass_Test.add12
  Quicksort_Test.quicksort
checking SML OCaml? Haskell? Scala? Go

end
