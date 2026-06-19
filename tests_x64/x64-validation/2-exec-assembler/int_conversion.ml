let i64_MIN
  = (Neg (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
     (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
     (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))));;

let rec num_to_int64 (n: num) : int64 =
  match n with
  | One -> 1L
  | Bit0 m -> Int64.mul 2L (num_to_int64 m)
  | Bit1 m -> Int64.add (Int64.mul 2L (num_to_int64 m)) 1L     

let myint_to_int64 (mi: myint) : int64 =
  match mi with
  | Zero_int -> 0L
  | Pos n -> num_to_int64 n
  | Neg n -> Int64.neg (num_to_int64 n)

let rec num_of_int64 (n: int64) =
  if n = 1L then One
  else if Int64.rem n 2L = 0L then Bit0 (num_of_int64 (Int64.div n 2L))
  else Bit1 (num_of_int64 (Int64.div n 2L))


let int64_to_myint (n: int64) =
  if n = 0L then Zero_int
  else if n > 0L then  Pos (num_of_int64 (n))
  else if n = 0x8000000000000000L then i64_MIN
  else Neg (num_of_int64 (Int64.sub 0L n))


let int64_list_to_myint_list lst =
  List.map int64_to_myint lst


  let parse_ireg = function
  | "RAX" -> Some RAX | "RBX" -> Some RBX | "RCX" -> Some RCX
  | "RDX" -> Some RDX | "RSI" -> Some RSI | "RDI" -> Some RDI
  | "RBP" -> Some RBP | "RSP" -> Some RSP
  | "R8"  -> Some R8  | "R9"  -> Some R9
  | "R10" -> Some R10 | "R11" -> Some R11
  | "R12" -> Some R12 | "R13" -> Some R13
  | "R14" -> Some R14 | "R15" -> Some R15
  | _     -> None

let parse_instruction (line : string) : instruction option =
  match split_ws line with
  | [opc; r1; r2] -> begin
      let* rd = parse_ireg r1 in
      let* rs = parse_ireg r2 in
      match opc with
      | "Paddq_rr" -> Some (Paddq_rr (rd, rs))
      | "Paddl_rr" -> Some (Paddl_rr (rd, rs))
      | "Psubq_rr" -> Some (Psubq_rr (rd, rs))
      | "Psubl_rr" -> Some (Psubl_rr (rd, rs))
      | _ -> None
    end
  | _ -> None



let exec_x64_encode () =

  let ic = open_in "../data/assembly.in" in
  let oc = open_out "../data/binary.in" in

  try
  while true do
    let line = input_line ic in

    let line = String.trim line in
    if line <> "" then (
      match parse_instruction line with
        | None ->
            Printf.eprintf "Warning: cannot parse line: %s\n%!" line
        | Some ins -> begin
            Printf.fprintf oc "%s\n" line;

            match x64_encode ins with
            | None ->
                Printf.eprintf "Encode failed: %s\n%!" line
            | Some bytes ->
                List.iter
                  (fun w -> Printf.fprintf oc "%Ld " (myint_to_int64 (the_int
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
    Printf.printf "File copy completed. Results written to ../0-data/binary.in\n"
| exn -> 
    close_in ic;
    close_out oc;
    Printf.eprintf "An error occurred: %s\n" (Printexc.to_string exn);
    raise exn

let () = exec_x64_encode ()
