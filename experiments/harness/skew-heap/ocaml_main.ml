open Exported_reference.Reference

let rec parse = function
  | "#" :: rest -> (Leaf, rest)
  | value :: rest ->
      let left, rest = parse rest in
      let right, rest = parse rest in
      (Node (left, Z.of_string value, right), rest)
  | [] -> failwith "tree token"

let rec encode tree tail = match tree with
  | Leaf -> "#" :: tail
  | Node (left, value, right) -> Z.to_string value :: encode left (encode right tail)

let () =
  try while true do
    let tokens = String.split_on_char ' ' (read_line ()) in
    let a, rest = parse tokens in
    let b, rest = parse rest in
    assert (rest = []);
    print_endline (String.concat " " (encode (merge_integer a b) []))
  done with End_of_file -> ()
