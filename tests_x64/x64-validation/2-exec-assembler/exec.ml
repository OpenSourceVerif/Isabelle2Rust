(*
eval $(opam env)
ocamlc -c x64_encode.ml
ocamlfind ocamlc -o exec -linkpkg x64_encode.cmo exec.ml
./exec
*)
open X64_encode

let ( let* ) o f =
  match o with
  | None   -> None
  | Some x -> f x

(*type instruction =
Paddq_rr of X64_encode.ireg * X64_encode.ireg |
Paddl_rr of X64_encode.ireg * X64_encode.ireg |
Psubl_rr of X64_encode.ireg * X64_encode.ireg | 
Psubq_rr of X64_encode.ireg * X64_encode.ireg *)

type token = string

let split_ws (s : string) : token list =
  let rec aux i acc =
    match String.index_from_opt s i ' ' with
    | None ->
        let t = String.sub s i (String.length s - i) in
        if t = "" then List.rev acc else List.rev (t :: acc)
    | Some j ->
        let t = String.sub s i (j - i) |> String.trim in
        let acc' = if t = "" then acc else t :: acc in
        aux (j + 1) acc'
  in aux 0 []

let parse_ireg = function
  | "RAX" -> Some X64_encode.RAX | "RBX" -> Some RBX | "RCX" -> Some RCX
  | "RDX" -> Some RDX | "RSI" -> Some RSI | "RDI" -> Some RDI
  | "RBP" -> Some RBP | "RSP" -> Some RSP
  | "R8"  -> Some R8  | "R9"  -> Some R9
  | "R10" -> Some R10 | "R11" -> Some R11
  | "R12" -> Some R12 | "R13" -> Some R13
  | "R14" -> Some R14 | "R15" -> Some R15
  | _     -> None

let parse_instruction (line : string) : X64_encode.instruction option =
  match split_ws line with
  | [opc; r1; r2] -> begin
      let* rd = parse_ireg r1 in
      let* rs = parse_ireg r2 in
      match opc with
      | "Paddq_rr" -> Some (X64_encode.Paddq_rr (rd, rs))
      | "Paddl_rr" -> Some (Paddl_rr (rd, rs))
      | "Psubq_rr" -> Some (Psubq_rr (rd, rs))
      | "Psubl_rr" -> Some (Psubl_rr (rd, rs))
      | _ -> None
    end
  | _ -> None



let exec_x64_encode () =

  let ic = open_in "../data/step1.in" in
  let oc = open_out "../data/step2.in" in

  try
  while true do
    (* 读取一行 *)
    let line = input_line ic in

    let line = String.trim line in
    if line <> "" then (
      match parse_instruction line with
        | None ->
            Printf.eprintf "Warning: cannot parse line: %s\n%!" line
        | Some ins -> begin
            Printf.fprintf oc "%s\n" line;

            match X64_encode.x64_encode ins with
            | None ->
                Printf.eprintf "Encode failed: %s\n%!" line
            | Some bytes ->
                List.iter
                  (fun w -> Printf.fprintf oc "0x%Lx" (X64_encode.myint_to_int64 (X64_encode.the_int
                    (len_bit0 (len_bit0 (len_bit0 len_num1))) w))
                  )
                  bytes;
                output_char oc '\n'
                  end 
      (*output_string oc line;
      output_char oc '\n'*)
    )
  done
with
| End_of_file -> 
    close_in ic;
    close_out oc;
    Printf.printf "File copy completed. Results written to ../0-data/step2.in\n"
| exn -> 
    close_in ic;
    close_out oc;
    Printf.eprintf "An error occurred: %s\n" (Printexc.to_string exn);
    raise exn

let () = exec_x64_encode ()