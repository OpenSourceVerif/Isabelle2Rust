open Step_test
open Yojson.Basic.Util

external monotonic_seconds : unit -> float = "i2r_monotonic_seconds"

type raw_case = {
  name : string;
  lp : int64 list;
  lr : int64 list;
  lm : int64 list;
  lc : int64 list;
  version : int64;
  fuel : int64;
  ipc : int64;
  index : int64;
  expected : int64;
}

type bench_case = {
  name : string;
  lp : Step_test.int list;
  lr : Step_test.int list;
  lm : Step_test.int list;
  lc : Step_test.int list;
  version : Step_test.int;
  fuel : Step_test.int;
  ipc : Step_test.int;
  index : Step_test.int;
  expected : Step_test.int;
}

let int64_of_hex_json json = json |> to_string |> Int64.of_string
let int64_list json = json |> to_list |> List.map int64_of_hex_json

let parse json : raw_case = {
  name = json |> member "dis" |> to_string;
  lp = json |> member "lp_std" |> int64_list;
  lr = json |> member "lr_std" |> int64_list;
  lm = json |> member "lm_std" |> int64_list;
  lc = json |> member "lc_std" |> int64_list;
  version = json |> member "v" |> int64_of_hex_json;
  fuel = json |> member "fuel" |> int64_of_hex_json;
  ipc = json |> member "ipc" |> int64_of_hex_json;
  index = json |> member "index" |> int64_of_hex_json;
  expected = json |> member "result_expected" |> int64_of_hex_json;
}

let prepare (case : raw_case) : bench_case = {
  name = case.name;
  lp = Step_test.int_list_of_standard_int_list case.lp;
  lr = Step_test.int_list_of_standard_int_list case.lr;
  lm = Step_test.int_list_of_standard_int_list case.lm;
  lc = Step_test.int_list_of_standard_int_list case.lc;
  version = Step_test.int_of_standard_int case.version;
  fuel = Step_test.int_of_standard_int case.fuel;
  ipc = Step_test.int_of_standard_int case.ipc;
  index = Step_test.int_of_standard_int case.index;
  expected = Step_test.int_of_standard_int case.expected;
}

let run case =
  Step_test.step_test case.lp case.lr case.lm case.lc case.version case.fuel
    case.ipc case.index case.expected

let () =
  let input = Sys.getenv "CROSS_JSON" in
  let cases =
    match Yojson.Basic.from_file input with
    | `List values -> List.map (fun value -> value |> parse |> prepare) values
    | _ -> failwith "SBPF-instruction input must be a JSON array"
  in
  if List.length cases <> 6000 then
    failwith "SBPF-instruction input must contain 6,000 vectors";
  let mode = match Sys.getenv_opt "SBPF_MEASURE" with Some value -> value | None -> "correctness" in
  if mode = "correctness" then begin
    let failures = List.filter (fun case -> not (run case)) cases in
    Printf.printf "RESULT benchmark=SBPF-instruction metric=correctness passed=%d failed=%d\n"
      (List.length cases - List.length failures) (List.length failures);
    List.iter (fun case -> Printf.eprintf "failed_case=%s\n" case.name) failures;
    if failures <> [] then failwith "OCaml SBPF-instruction validation failed"
  end else begin
    let repetitions =
      match Sys.getenv_opt "SUITE_REPETITIONS" with
      | Some value -> int_of_string value
      | None -> 1
    in
    if repetitions <= 0 then failwith "SUITE_REPETITIONS must be positive";
    let failures = ref 0 in
    let run_workload () =
      for _ = 1 to repetitions do
        List.iter
          (fun case -> if not (Sys.opaque_identity (run case)) then incr failures)
          cases
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
    if !failures <> 0 then failwith "timed OCaml SBPF-instruction validation failed";
    Printf.printf
      "RESULT benchmark=SBPF-instruction metric=%s process_id=%d cases=%d suite_repetitions=%d logical_units=%d elapsed_seconds=%.9f allocated_bytes=%.0f\n"
      mode (Unix.getpid ()) (List.length cases) repetitions
      (List.length cases * repetitions) elapsed allocated
  end
