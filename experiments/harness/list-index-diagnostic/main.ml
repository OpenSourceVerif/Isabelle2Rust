let () =
  let op = Sys.argv.(1) and n = int_of_string Sys.argv.(2) and mode = Sys.argv.(3) in
  let offset = if Sys.argv.(4) = "large" then Z.shift_left Z.one 130 else Z.zero in
  let iterations = int_of_string Sys.argv.(5) in
  let xs = Array.init n (fun i -> Z.add offset (Z.of_int i)) in
  let q = match mode with "first" -> 0 | "last" -> n-1 | "absent" -> n+1 | _ -> failwith "mode" in
  let x = Z.add offset (Z.of_int q) and linked = Array.to_list xs in
  let expected = Z.of_int (if mode = "absent" then n else q) in
  let last = Exported_reference.Reference.last_index_integer in
  assert (Z.equal (last linked x) expected);
  let f = match op with
    | "ocaml_kernel" -> (fun () -> ignore (Sys.opaque_identity (last (Sys.opaque_identity linked) (Sys.opaque_identity x))))
    | "ocaml_e2e" -> (fun () -> ignore (Sys.opaque_identity (last (Array.to_list (Sys.opaque_identity xs)) (Sys.opaque_identity x))))
    | "ocaml_prepare_list" -> (fun () -> ignore (Sys.opaque_identity (Array.to_list (Sys.opaque_identity xs))))
    | _ -> failwith "op"
  in
  for _ = 1 to 10 do f () done;
  Gc.full_major ();
  let before = Gc.allocated_bytes () in
  let start = Unix.gettimeofday () in
  for _ = 1 to iterations do f () done;
  let elapsed = Unix.gettimeofday () -. start in
  let bytes = Gc.allocated_bytes () -. before in
  Printf.printf "%.0f %d %.3f\n" (elapsed *. 1e9) iterations (bytes /. float_of_int iterations)
