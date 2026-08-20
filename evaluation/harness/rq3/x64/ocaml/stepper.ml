open X64_step_test
open Yojson.Basic.Util

external monotonic_seconds : unit -> float = "i2r_monotonic_seconds"

type raw_case = {
  name : string;
  mode : int64;
  bin : int64 list;
  cr : int64 list;
  ir : int64 list;
  mem : int64 list;
  compare : int;
  expected : int64 list;
}

type bench_case = {
  name : string;
  mode : X64_step_test.myint;
  bin : X64_step_test.myint list;
  cr : X64_step_test.myint list;
  ir : X64_step_test.myint list;
  mem : X64_step_test.myint list;
  compare : int;
  expected : int64 list;
}

let opcode_of ins =
  match String.split_on_char ' ' (String.trim ins) with
  | opcode :: _ -> opcode
  | [] -> ""

let cmp_or_test = function
  | "Ptestl_rr" | "Ptestl_ri" | "Ptestq_rr" | "Ptestq_ri"
  | "Pcmpl_rr" | "Pcmpl_ri" | "Pcmpq_rr" | "Pcmpq_ri" -> true
  | _ -> false

let int64_list json =
  json |> to_list |> List.map (fun value -> Int64.of_int (to_int value))

let string_int64_list json =
  json |> to_list |> List.map (fun value -> value |> to_string |> Int64.of_string)

let parse json : raw_case =
  let name = json |> member "ins" |> to_string in
  let cond = json |> member "cond" |> to_bool_option |> Option.value ~default:false in
  {
    name;
    mode = json |> member "mode" |> to_int |> Int64.of_int;
    bin = json |> member "bin" |> int64_list;
    cr = json |> member "cr" |> int64_list;
    ir = json |> member "ir" |> string_int64_list;
    mem = json |> member "mem" |> string_int64_list;
    compare = if not cond then 16 else if cmp_or_test (opcode_of name) then 20 else 21;
    expected = json |> member "expected" |> string_int64_list;
  }

let prepare (case : raw_case) : bench_case = {
  name = case.name;
  mode = X64_step_test.int64_to_myint case.mode;
  bin = X64_step_test.int64_list_to_myint_list case.bin;
  cr = X64_step_test.int64_list_to_myint_list case.cr;
  ir = X64_step_test.int64_list_to_myint_list case.ir;
  mem = X64_step_test.int64_list_to_myint_list case.mem;
  compare = case.compare;
  expected = case.expected;
}

let take n values =
  let rec loop n acc = function
    | _ when n = 0 -> List.rev acc
    | [] -> List.rev acc
    | value :: rest -> loop (n - 1) (value :: acc) rest
  in
  loop n [] values

let drop n values =
  let rec loop n = function
    | values when n = 0 -> values
    | [] -> []
    | _ :: rest -> loop (n - 1) rest
  in
  loop n values

let comparable count values =
  if count = 20 then take 18 values @ take 2 (drop 19 values)
  else take count values

let correct case =
  let actual = X64_step_test.x64_step_observe
      case.mode case.bin case.cr case.ir case.mem in
  let expected = comparable case.compare case.expected in
  let actual = comparable case.compare actual in
  match expected, actual with
  | first :: _, [] when first = Int64.minus_one -> true
  | _ -> expected = actual

let run case =
  X64_step_test.x64_step_benchmark case.mode case.bin case.cr case.ir case.mem

let () =
  let input = Sys.getenv "CROSS_JSON" in
  let cases =
    match Yojson.Basic.from_file input with
    | `List values -> List.map (fun value -> value |> parse |> prepare) values
    | _ -> failwith "x64-stepper input must be a JSON array"
  in
  if List.length cases <> 6000 then
    failwith "x64-stepper input must contain 6,000 vectors";
  let mode = match Sys.getenv_opt "X64_MEASURE" with
    | Some value -> value
    | None -> "correctness"
  in
  if mode = "correctness" then begin
    let failures = List.filter (fun case -> not (correct case)) cases in
    Printf.printf "RESULT benchmark=x64-stepper metric=correctness passed=%d failed=%d\n"
      (List.length cases - List.length failures) (List.length failures);
    List.iter (fun case -> Printf.eprintf "failed_case=%s\n" case.name) failures;
    if failures <> [] then failwith "OCaml x64-stepper validation failed"
  end else begin
    let repetitions = match Sys.getenv_opt "SUITE_REPETITIONS" with
      | Some value -> int_of_string value
      | None -> 1
    in
    if repetitions <= 0 then invalid_arg "SUITE_REPETITIONS must be positive";
    let run_workload () =
      for _ = 1 to repetitions do
        List.iter run cases
      done
    in
    let elapsed, allocated =
      if mode = "allocation" then begin
        let before_alloc = Gc.allocated_bytes () in
        run_workload ();
        (0., Gc.allocated_bytes () -. before_alloc)
      end else begin
        let started = monotonic_seconds () in
        run_workload ();
        (monotonic_seconds () -. started, 0.)
      end
    in
    Printf.printf
      "RESULT benchmark=x64-stepper metric=%s process_id=%d cases=%d suite_repetitions=%d logical_units=%d elapsed_seconds=%.9f allocated_bytes=%.0f\n"
      mode (Unix.getpid ()) (List.length cases) repetitions
      (List.length cases * repetitions) elapsed allocated
  end
