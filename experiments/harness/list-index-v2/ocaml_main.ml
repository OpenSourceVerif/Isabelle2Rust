let evaluate xs x = Exported_reference.Reference.last_index_integer (Array.to_list xs) x

let bench () =
  let n = int_of_string Sys.argv.(2) in
  let mode = Sys.argv.(3) in
  let iterations = int_of_string Sys.argv.(4) in
  let xs = Array.init n Z.of_int in
  let q = match mode with "first" -> 0 | "last" -> n-1 | "absent" -> n+1 | _ -> failwith "mode" in
  let x = Z.of_int q in
  let expected = Z.of_int (if mode = "absent" then n else q) in
  for _ = 1 to 10 do assert (Z.equal (evaluate xs x) expected) done;
  Gc.full_major ();
  let start = Unix.gettimeofday () in
  let result = ref Z.zero in
  for _ = 1 to iterations do
    result := Sys.opaque_identity (evaluate (Sys.opaque_identity xs) (Sys.opaque_identity x))
  done;
  let nanos = (Unix.gettimeofday () -. start) *. 1e9 in
  assert (Z.equal !result expected);
  Printf.printf "%.0f %d %s\n" nanos iterations (Z.to_string !result)

let () =
  if Array.length Sys.argv > 1 && Sys.argv.(1) = "--bench" then bench () else
  try while true do
    match String.split_on_char ' ' (read_line ()) with
    | x :: xs -> print_endline (Z.to_string (evaluate (Array.of_list (List.map Z.of_string xs)) (Z.of_string x)))
    | [] -> failwith "query"
  done with End_of_file -> ()
