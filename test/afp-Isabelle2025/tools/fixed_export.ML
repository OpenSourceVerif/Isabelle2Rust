(* Formal request: one frozen context and entry group, one strict frontend,
   reused by all six serializers. Failure never changes the request. *)
local
  open AFP_Fixed;
  val context_id = attr "context" request;
  val batch = attr "group" request;
  val cs = names "entry" request;
  val _ = if names "target" request = targets andalso attr "module" request = "AFP_Code"
    andalso not (null cs) andalso cs = sort_strings (distinct (op =) cs) then ()
    else error "Invalid fixed export request";
  fun record stage target result seconds extras =
    write ("attempts/" ^ context_id ^ "/" ^ batch ^ "/" ^ target ^ ".xml")
      (elem "attempt" [("context", context_id), ("batch", batch), ("stage", stage),
        ("target", target), ("seconds", seconds),
        ("status", case result of Exn.Res _ => "passed" | _ => "failed")]
        (map constant cs @ extras @ error_body result @
          (case result of Exn.Exn exn =>
            [failure (if stage = "frontend" then "strict_frontend" else stage) exn] | _ => [])));
  (* Keep the loaded-theory inventory even when context construction fails.
     The existing declaration audit uses it to distinguish independent source
     declarations with the same internal name. *)
  val _ = write "loaded.xml"
    (elem "loaded" [] (map (text "theory") (names "parent" request)));
  val (loaded, load_seconds) = timed context ();
  fun run thy =
    let
      val lthy = Named_Target.theory_init thy;
      val _ = write ("contexts/" ^ context_id ^ ".xml") (elem "context" []
        (map (text "theory") (names "parent" request) @ map constant cs));
      val _ = write "declarations.xml" (elem "declarations" []
        (map (fn c => elem "constant" [("name", c)]
          [text "type" (Syntax.string_of_typ lthy (Sign.the_const_type thy c))]) cs));
      (* consts_program restricts cached programs to exactly this group's full
         frontend closure before native target checking can see any nodes. *)
      val (front, seconds) = timed (Code_Thingol.consts_program lthy) cs;
      val _ = record "frontend" "frontend" front seconds (map (text "language") targets);
      fun serialize program target =
        let
          fun export () =
            let
              val prefix = Path.make [target, batch];
              val exported = Code_Target.export_code_for
                (SOME ({physical = false}, (prefix, Position.none)))
                target "AFP_Code" NONE [] program false (map Code_Symbol.Constant cs) lthy;
              val key = "code/" ^ target ^ "/" ^ batch;
              val files = Generated_Files.get_files (Proof_Context.theory_of exported)
                |> filter (fn file => let val name = Path.implode (#path file)
                  in name = key orelse String.isPrefix (key ^ "/") name
                     orelse String.isPrefix (key ^ ".") name end);
              val root = output + Path.basic "artifacts" + Path.basic context_id;
              val _ = List.app (fn file =>
                let val path = root + #path file
                in directory (Path.dir path); Bytes.write path (#content file) end) files;
            in map (fn file => text "file"
              (Path.implode (Path.make ["artifacts", context_id] + #path file))) files end;
          val (res, seconds) = timed export ();
        in record "target_preparation_or_serialization" target res seconds
          (case res of Exn.Res [] => [text "library_only" "true"] | Exn.Res files => files | _ => []) end;
    in case front of Exn.Res program => List.app (serialize program) targets | _ => () end;
  val _ = (case loaded of Exn.Res thy => run thy
    | _ => record "context_loading" "context" loaded load_seconds (map (text "language") targets));
in
  val _ = write "finished.xml" (elem "finished" [("group", batch), ("context", context_id)] []);
end;
