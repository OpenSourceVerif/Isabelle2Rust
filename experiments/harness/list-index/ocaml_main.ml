let () =
  try
    while true do
      let fields = String.split_on_char ' ' (read_line ()) in
      match fields with
      | x :: xs ->
          let answer = Exported_reference.Reference.last_index_integer
            (List.map Z.of_string xs) (Z.of_string x) in
          print_endline (Z.to_string answer)
      | [] -> failwith "missing query"
    done
  with End_of_file -> ()
