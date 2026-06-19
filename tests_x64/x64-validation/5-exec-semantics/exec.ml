open X64_step_test
open Yojson.Basic.Util

type test_case = {
  ins : string;
  mode: int64; 
  bin : int64 list;
  cr  : int64 list;
  ir  : int64 list;
  mem : int64 list;
  cond : bool; 
  rd  : int64;
  rs  : int64;
  expected : int64 list;
}

let green = "\027[32m"
let red = "\027[31m"
let reset = "\027[0m"
let count = ref 0
let passed = ref 0
let failed = ref 0

let string_of_i64_list lst =
  lst
  |> List.map (Printf.sprintf "0x%016Lx")
  |> String.concat "; "
  |> Printf.sprintf "[%s]"


let take n lst =
let rec aux acc n l =
  match l, n with
  | _, 0          -> List.rev acc
  | x :: xs, n    -> aux (x :: acc) (n - 1) xs
  | [], _         -> List.rev acc
in
aux [] n lst

let run_test_case test_case =
  let mode = X64_step_test.int64_to_myint test_case.mode in
  let lbin = X64_step_test.int64_list_to_myint_list test_case.bin in
  let lc   = X64_step_test.int64_list_to_myint_list test_case.cr in
  let lr   = X64_step_test.int64_list_to_myint_list test_case.ir in
  let lm   = X64_step_test.int64_list_to_myint_list test_case.mem in

  let actual   = X64_step_test.x64_step_test mode lbin lc lr lm in
  let slice_sz = if test_case.cond then 21 else 16 in
  let sliced_expected = take slice_sz test_case.expected in
  let sliced_actual   = take slice_sz actual in
  let ok =
    match sliced_expected, sliced_actual with
    | e1 :: _, [] when e1 = 0xffffffffffffffffL -> true
    | _ -> sliced_expected = sliced_actual
  in

  let color    = if ok then green else red in

  incr count;
  if ok then (
    incr passed;
    Printf.printf "%s%02d  %-40s true%s\n"
      color !count test_case.ins reset)
  else (
    incr failed;
    Printf.printf "%s%02d  %-40s false\n\
                   \  expected: %s\n\
                   \  actual  : %s%s\n"
      color !count test_case.ins
      (string_of_i64_list test_case.expected)
      (string_of_i64_list actual)
      reset
  )

let parse_test_case json =
  let get_list64 key =
    json |> member key |> to_list
         |> List.map (fun v -> Int64.of_int (to_int v)) in
  let get_int64 key =
    json |> member key |>  (fun v -> Int64.of_int (to_int v))
  in
  let parse_int64 s = Int64.of_string s in

  let ins = json |> member "ins" |> to_string in
  let bin = get_list64 "bin" in
  let mode = get_int64 "mode" in
  let cr = get_list64 "cr" in

  let ir = json |> member "ir" |> to_list |> List.map to_string in
  let ir = List.map parse_int64 ir in

  let mem = json |> member "mem" |> to_list |> List.map to_string in
  let mem = List.map parse_int64 mem in

  let cond = json |> member "cond" |> to_bool_option |> Option.value ~default:false in
  let rd = get_int64 "rd" in
  let rs = get_int64 "rs" in

  let expected = json |> member "expected" |> to_list |> List.map to_string in
  let expected = List.map parse_int64 expected in

  { ins; mode; bin; cr; ir; mem; cond; rd; rs; expected }

(*let parse_test_case1 json =
  let get_list64 key =
    json |> member key |> to_list
         |> List.map (fun v -> Int64.of_int (to_int v))
  in
  {
    ins = json |> member "ins" |> to_string;
    bin = get_list64 "bin";
    cr  = get_list64 "cr";
    ir  = get_list64 "ir";
    mem = get_list64 "mem";
    cond     = (json |> member "cond" |> to_bool_option |> Option.value ~default:false);
    expected = get_list64 "expected";
  }*)

let read_test_cases filename =
  let json = Yojson.Basic.from_file filename in
  match json with
  | `List test_list -> List.map parse_test_case test_list
  | _ -> failwith "Expected a JSON list at top level"

let () =
  let test_cases = read_test_cases "../0-data/step4.json" in
  List.iter run_test_case test_cases;

  Printf.printf "\nSummary: %s%d passed%s / %s%d failed%s\n\n"
  green !passed reset red !failed reset;

  if !failed = 0 then exit 0 else exit 1
