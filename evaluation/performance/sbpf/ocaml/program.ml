open Interp_test
open Yojson.Safe.Util

external monotonic_seconds : unit -> float = "i2r_monotonic_seconds"

type raw_case = {
  name : string;
  lp : int64 list;
  lm : int64 list;
  lc : int64 list;
  version : int64;
  fuel : int64;
  expected : int64;
  succeeds : bool;
}

type bench_case = {
  name : string;
  lp : Interp_test.int list;
  lm : Interp_test.int list;
  lc : Interp_test.int list;
  version : Interp_test.int;
  fuel : Interp_test.int;
  expected : Interp_test.int;
  succeeds : bool;
}

let int64_of_json = function
  | `Int value -> Int64.of_int value
  | `Intlit value -> Int64.of_string value
  | json -> failwith ("expected JSON integer, got " ^ Yojson.Safe.to_string json)

let int64_list json = json |> to_list |> List.map int64_of_json

let parse json : raw_case = {
  name = json |> member "dis" |> to_string;
  lp = json |> member "lp_std" |> int64_list;
  lm = json |> member "lm_std" |> int64_list;
  lc = json |> member "lc_std" |> int64_list;
  version = json |> member "v" |> int64_of_json;
  fuel = json |> member "fuel" |> int64_of_json;
  expected = json |> member "result_expected" |> int64_of_json;
  succeeds = json |> member "isok" |> to_bool;
}

let prepare (case : raw_case) : bench_case = {
  name = case.name;
  lp = Interp_test.int_list_of_standard_int_list case.lp;
  lm = Interp_test.int_list_of_standard_int_list case.lm;
  lc = Interp_test.int_list_of_standard_int_list case.lc;
  version = Interp_test.int_of_standard_int case.version;
  fuel = Interp_test.int_of_standard_int case.fuel;
  expected = Interp_test.int_of_standard_int case.expected;
  succeeds = case.succeeds;
}

let run case =
  Interp_test.bpf_interp_test case.lp case.lm case.lc case.version case.fuel
    case.expected case.succeeds

let () =
  let input = Sys.getenv "CROSS_JSON" in
  let cases =
    match Yojson.Safe.from_file input with
    | `List values -> List.map (fun value -> value |> parse |> prepare) values
    | _ -> failwith "SBPF-program input must be a JSON array"
  in
  if List.length cases <> 146 then failwith "SBPF-program input must contain 146 cases";
  let mode = match Sys.getenv_opt "SBPF_MEASURE" with Some value -> value | None -> "correctness" in
  if mode = "correctness" then begin
    let failures = List.filter (fun case -> not (run case)) cases in
    Printf.printf "RESULT benchmark=SBPF-program metric=correctness passed=%d failed=%d\n"
      (List.length cases - List.length failures) (List.length failures);
    List.iter (fun case -> Printf.eprintf "failed_case=%s\n" case.name) failures;
    if failures <> [] then failwith "OCaml SBPF-program validation failed"
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
    if !failures <> 0 then failwith "timed OCaml SBPF-program validation failed";
    Printf.printf
      "RESULT benchmark=SBPF-program metric=%s process_id=%d cases=%d suite_repetitions=%d logical_units=%d elapsed_seconds=%.9f allocated_bytes=%.0f\n"
      mode (Unix.getpid ()) (List.length cases) repetitions
      (List.length cases * repetitions) elapsed allocated
  end
