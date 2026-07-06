# Targeted Test Migration Map

This file records source-to-suite mapping for tests migrated from `tests_targeted` into `test/targeted`.

## `cases/Case_Suite_Test.thy`

- `tests_targeted/cases/Case_Bool_Test.thy` -> `test/targeted/cases/Case_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/cases/Case_Default_Test.thy` -> `test/targeted/cases/Case_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/cases/Case_Length1_Test.thy` -> `test/targeted/cases/Case_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/cases/Case_Length2_Test.thy` -> `test/targeted/cases/Case_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/cases/Case_Option_Test.thy` -> `test/targeted/cases/Case_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/cases/Case_Poly_Test.thy` -> `test/targeted/cases/Case_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/cases/Partial_Match_Test.thy` -> `test/targeted/cases/Case_Suite_Test.thy` (`2` exported definitions)

## `lets/Let_Suite_Test.thy`

- `tests_targeted/lets/Let_Binding_Test.thy` -> `test/targeted/lets/Let_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/lets/Let_Case_Test.thy` -> `test/targeted/lets/Let_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/lets/Let_Nested_Test.thy` -> `test/targeted/lets/Let_Suite_Test.thy` (`1` exported definitions)

## `constructors/Constructor_Suite_Test.thy`

- `tests_targeted/constructors/Cons_As_Value_Test.thy` -> `test/targeted/constructors/Constructor_Suite_Test.thy` (`2` exported definitions)
- `tests_targeted/constructors/Cons_Mono_Test.thy` -> `test/targeted/constructors/Constructor_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/constructors/Cons_Poly_Test.thy` -> `test/targeted/constructors/Constructor_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/constructors/Result_Test.thy` -> `test/targeted/constructors/Constructor_Suite_Test.thy` (`7` exported definitions)

## `lists/List_Suite_Test.thy`

- `tests_targeted/lists/List_Cons_Test.thy` -> `test/targeted/lists/List_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/lists/List_Test.thy` -> `test/targeted/lists/List_Suite_Test.thy` (`1` exported definitions)

## `abstraction/Abstraction_Basic_Suite_Test.thy`

- `tests_targeted/abstraction/Abs_Addn_Test.thy` -> `test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/abstraction/Abs_Capture_Multi_Test.thy` -> `test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/abstraction/Abs_Capture_Test.thy` -> `test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/abstraction/Abs_Inc_Test.thy` -> `test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/abstraction/Abs_Nested_Test.thy` -> `test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/abstraction/Abs_No_Capture_Test.thy` -> `test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/abstraction/Abs_Poly_Test.thy` -> `test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/abstraction/Closure_Boxing_Test.thy` -> `test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy` (`3` exported definitions)

## `abstraction/Abstraction_Unsaturated_Suite_Test.thy`

- `tests_targeted/abstraction/Unsaturated_Test.thy` -> `test/targeted/abstraction/Abstraction_Unsaturated_Suite_Test.thy` (`1` exported definitions)

## `functions/Function_General_Suite_Test.thy`

- `tests_targeted/functions/Fun_Upd_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/functions/Func_Add_Int3_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/functions/Func_Add_Int_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/functions/Func_Add_Nat_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/functions/Func_Max_Case_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/functions/Func_Max_If_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/functions/Infix_Prec_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`3` exported definitions)
- `tests_targeted/functions/Module_Collision_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/functions/Mut_Ref_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/functions/Return_Poly_Test.thy` -> `test/targeted/functions/Function_General_Suite_Test.thy` (`1` exported definitions)

## `functions/Function_High_Level_Suite_Test.thy`

- `tests_targeted/functions/High_Level_Mapping_Test.thy` -> `test/targeted/functions/Function_High_Level_Suite_Test.thy` (`6` exported definitions)

## `functions/Function_High_Level_Peano_Suite_Test.thy`

- `tests_targeted/functions/High_Level_Mapping_Peano_Test.thy` -> `test/targeted/functions/Function_High_Level_Peano_Suite_Test.thy` (`4` exported definitions)

## `types/Type_Set_Pair_Suite_Test.thy`

- `tests_targeted/types/Set_Pair_Test.thy` -> `test/targeted/types/Type_Set_Pair_Suite_Test.thy` (`1` exported definitions)

## `types/Type_Simple_Suite_Test.thy`

- `tests_targeted/types/Type_Func_Mono_Test.thy` -> `test/targeted/types/Type_Simple_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/types/Type_Func_Poly_Test.thy` -> `test/targeted/types/Type_Simple_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/types/Type_Pair_Test.thy` -> `test/targeted/types/Type_Simple_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/types/Type_Record_Test.thy` -> `test/targeted/types/Type_Simple_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/types/Type_Tuple_Test.thy` -> `test/targeted/types/Type_Simple_Suite_Test.thy` (`8` exported definitions)

## `types/Type_Phantom_Suite_Test.thy`

- `tests_targeted/types/Phantom_Multi_Test.thy` -> `test/targeted/types/Type_Phantom_Suite_Test.thy` (`3` exported definitions)
- `tests_targeted/types/Phantom_Param_Test.thy` -> `test/targeted/types/Type_Phantom_Suite_Test.thy` (`2` exported definitions)

## `types/Type_Recursive_Suite_Test.thy`

- `tests_targeted/types/Type_Nested_Rec_Test.thy` -> `test/targeted/types/Type_Recursive_Suite_Test.thy` (`2` exported definitions)

## `types/Type_Codatatype_Suite_Test.thy`

- `tests_targeted/types/Codatatype_Shape_Test.thy` -> `test/targeted/types/Type_Codatatype_Suite_Test.thy` (`3` exported definitions)

## `types/Type_BigInt_Suite_Test.thy`

- `tests_targeted/types/Nat_BigInt_Test.thy` -> `test/targeted/types/Type_BigInt_Suite_Test.thy` (`6` exported definitions)

## `records/Record_Option_Suite_Test.thy`

- `tests_targeted/records/Rec_Get_Test.thy` -> `test/targeted/records/Record_Option_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/records/Rec_Set_Test.thy` -> `test/targeted/records/Record_Option_Suite_Test.thy` (`1` exported definitions)

## `records/Record_Mutual_Suite_Test.thy`

- `tests_targeted/records/Rec_Mut_Test.thy` -> `test/targeted/records/Record_Mutual_Suite_Test.thy` (`1` exported definitions)
## `classes/Class_Misc_Suite_Test.thy`

- `tests_targeted/classes/Class_Multi_Method_Test.thy` -> `test/targeted/classes/Class_Misc_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/classes/Class_No_Ins2_Test.thy` -> `test/targeted/classes/Class_Misc_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/classes/Class_Superclass_Test.thy` -> `test/targeted/classes/Class_Misc_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/classes/Equal_Inst_Test.thy` -> `test/targeted/classes/Class_Misc_Suite_Test.thy` (`2` exported definitions)
- `tests_targeted/classes/Equal_Pair_Test.thy` -> `test/targeted/classes/Class_Misc_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/classes/Int_Zero_Inst_Test.thy` -> `test/targeted/classes/Class_Misc_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/classes/Itself_Dispatch_Test.thy` -> `test/targeted/classes/Class_Misc_Suite_Test.thy` (`2` exported definitions)
- `tests_targeted/classes/Trait_Cross_Module_Test.thy` -> `test/targeted/classes/Class_Misc_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Inc_No_Instance_Suite_Test.thy`

- `tests_targeted/classes/Class_No_Ins_Test.thy` -> `test/targeted/classes/Class_Inc_No_Instance_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Inc_Instance_Suite_Test.thy`

- `tests_targeted/classes/Instance_Nat_Test.thy` -> `test/targeted/classes/Class_Inc_Instance_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Inc_Poly_Suite_Test.thy`

- `tests_targeted/classes/Class_Poly_Test.thy` -> `test/targeted/classes/Class_Inc_Poly_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Inst_Mono_Dispatch_Suite_Test.thy`

- `tests_targeted/classes/Inst_Mono_Dispatch_Test.thy` -> `test/targeted/classes/Class_Inst_Mono_Dispatch_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Semigroup_Base_Suite_Test.thy`

- `tests_targeted/classes/Semigroup_Test.thy` -> `test/targeted/classes/Class_Semigroup_Base_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Semigroup_Nat_Suite_Test.thy`

- `tests_targeted/classes/Semigroup_Nat_Test.thy` -> `test/targeted/classes/Class_Semigroup_Nat_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Semigroup_Nat2_Suite_Test.thy`

- `tests_targeted/classes/Semigroup_Nat2_Test.thy` -> `test/targeted/classes/Class_Semigroup_Nat2_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Semigroup_Nat3_Suite_Test.thy`

- `tests_targeted/classes/Semigroup_Nat3_Test.thy` -> `test/targeted/classes/Class_Semigroup_Nat3_Suite_Test.thy` (`1` exported definitions)

## `classes/Class_Semigroup_Option_Suite_Test.thy`

- `tests_targeted/classes/Semigroup_Option_Test.thy` -> `test/targeted/classes/Class_Semigroup_Option_Suite_Test.thy` (`1` exported definitions)

## `optimization/Optimization_Borrow_Suite_Test.thy`

- `tests_targeted/optimization/borrow/Borrow_CopyField_Own_Test.thy` -> `test/targeted/optimization/Optimization_Borrow_Suite_Test.thy` (`4` exported definitions)
- `tests_targeted/optimization/borrow/Borrow_Move_Demand_Test.thy` -> `test/targeted/optimization/Optimization_Borrow_Suite_Test.thy` (`6` exported definitions)
- `tests_targeted/optimization/borrow/Borrow_Paper_Example_Test.thy` -> `test/targeted/optimization/Optimization_Borrow_Suite_Test.thy` (`3` exported definitions)
- `tests_targeted/optimization/borrow/Borrow_Per_Param_Test.thy` -> `test/targeted/optimization/Optimization_Borrow_Suite_Test.thy` (`5` exported definitions)
- `tests_targeted/optimization/borrow/Borrow_Tree_Generic_Test.thy` -> `test/targeted/optimization/Optimization_Borrow_Suite_Test.thy` (`6` exported definitions)

## `optimization/Optimization_Copy_Basic_Suite_Test.thy`

- `tests_targeted/optimization/copy/Copy_Bool_Fields_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Basic_Suite_Test.thy` (`3` exported definitions)
- `tests_targeted/optimization/copy/Copy_Generic_Bound_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Basic_Suite_Test.thy` (`2` exported definitions)
- `tests_targeted/optimization/copy/Copy_Nat_NonCopy_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Basic_Suite_Test.thy` (`9` exported definitions)
- `tests_targeted/optimization/copy/Copy_Nested_Types_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Basic_Suite_Test.thy` (`4` exported definitions)
- `tests_targeted/optimization/copy/Copy_Recursive_NonCopy_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Basic_Suite_Test.thy` (`8` exported definitions)

## `optimization/Optimization_Copy_Generic_RCall_Suite_Test.thy`

- `tests_targeted/optimization/copy/Copy_Generic_RCall_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Generic_RCall_Suite_Test.thy` (`35` exported definitions)

## `optimization/Optimization_Copy_Borrow_Suite_Test.thy`

- `tests_targeted/optimization/copy_borrow/Count_True_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Borrow_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/optimization/copy_borrow/List_Ops_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Borrow_Suite_Test.thy` (`7` exported definitions)
- `tests_targeted/optimization/copy_borrow/Tree_Query_Test.thy` -> `test/targeted/optimization/Optimization_Copy_Borrow_Suite_Test.thy` (`9` exported definitions)

## `optimization/Optimization_Mut_Suite_Test.thy`

- `tests_targeted/optimization/mut/Mut_Chain_Test.thy` -> `test/targeted/optimization/Optimization_Mut_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/optimization/mut/Mut_Chain_Unit_Test.thy` -> `test/targeted/optimization/Optimization_Mut_Suite_Test.thy` (`4` exported definitions)
- `tests_targeted/optimization/mut/Mut_Generic_Wrapper_Test.thy` -> `test/targeted/optimization/Optimization_Mut_Suite_Test.thy` (`5` exported definitions)
- `tests_targeted/optimization/mut/Mut_Last_Use_Test.thy` -> `test/targeted/optimization/Optimization_Mut_Suite_Test.thy` (`4` exported definitions)
- `tests_targeted/optimization/mut/Mut_Nat_Test.thy` -> `test/targeted/optimization/Optimization_Mut_Suite_Test.thy` (`1` exported definitions)
- `tests_targeted/optimization/mut/Mut_Tree_Complex_Test.thy` -> `test/targeted/optimization/Optimization_Mut_Suite_Test.thy` (`6` exported definitions)

