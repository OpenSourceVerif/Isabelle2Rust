(* Exhaustive export isolation using the same frontend and serializers as
   export_code. A failing aggregate does not establish failure of its members:
   bisect only the failed language scopes until a group exports or one constant
   remains. The six serializers share each computed Thingol program. No target
   code is compiled or executed here. *)
local
  val output = Path.explode (getenv_strict "AFP_FULL_OUTPUT");
  val scope = split_lines (File.read (Path.explode (getenv_strict "AFP_FULL_SCOPE")))
    |> filter_out (fn s => s = "");
  val names = split_lines (File.read (Path.explode (getenv_strict "AFP_FULL_THEORIES")))
    |> filter_out (fn s => s = "") |> filter (is_some o Thy_Info.lookup_theory);
  val targets = ["Rust", "SML", "OCaml", "Haskell", "Scala", "Go"];
  val originals = map Thy_Info.get_theory names;
  val setups = map Thy_Info.get_theory ["Rust.Rust_BigInt_Setup", "Go.Go_Setup"];
  fun elem name props body = XML.Elem ((name, props), body);
  fun text name value = elem name [] [XML.Text value];
  fun capture f x =
    (case Exn.capture f x of
      Exn.Exn exn => if Exn.is_interrupt exn then Exn.reraise exn else Exn.Exn exn
    | result => result);
  (* A raw ML process has no Scala protocol peer. Use local filesystem
     operations rather than Isabelle_System's protocol-backed directory API. *)
  fun directory path =
    if File.is_dir path then ()
    else (directory (Path.dir path); OS.FileSys.mkDir (File.platform_path path));
  fun write path body =
    let
      val file = output + Path.explode path;
      val _ = directory (Path.dir file);
      val temporary = Path.ext "tmp" file;
      val _ = File.write temporary (XML.string_of body);
    in OS.FileSys.rename {old = File.platform_path temporary, new = File.platform_path file} end;
  fun constants cs = map (fn c => elem "constant" [("name", c)] []) cs;
  fun timed f x =
    let val start = Time.now (); val result = capture f x
    in (result, Time.toString (Time.- (Time.now (), start))) end;
  fun record context batch stage target cs result seconds extras =
    write ("attempts/" ^ context ^ "/" ^ batch ^ "/" ^ target ^ ".xml")
      (elem "attempt" [("context", context), ("batch", batch), ("stage", stage),
        ("target", target), ("seconds", seconds),
        ("status", case result of Exn.Res _ => "passed" | Exn.Exn _ => "failed")]
        (constants cs @ extras @
          (case result of Exn.Res _ => [] | Exn.Exn exn =>
            [text "error" (Runtime.exn_message exn)])));
  (* Keep full declaration types for error reports; names remain fully
     qualified, so locale constants, instances and generated constants retain
     their actual provenance rather than being inferred from a prefix. *)
  val _ = write "loaded.xml" (elem "loaded" [] (map (text "theory") names));
  val metadata_contexts = originals @ setups;
  fun declaration c =
    let
      val owner = get_first (fn thy => if Sign.declared_const thy c then SOME thy else NONE)
        metadata_contexts;
    in
      elem "constant" [("name", c)]
        (case owner of NONE => [] | SOME thy =>
          [text "type" (Syntax.string_of_typ (Proof_Context.init_global thy)
             (Sign.the_const_type thy c))])
    end;
  val _ = write "declarations.xml" (elem "declarations" [] (map declaration scope));
  val merged = capture (Context.begin_thy "AFP_Full_Export") (originals @ setups);
  (* Independent branches may carry conflicting code equations or instances.
     Fall back to maximal original theories and preserve each branch's later
     equations. This is separate evidence from a successful aggregate import. *)
  val contexts =
    (case merged of
      Exn.Res thy => [("merged", filter (Sign.declared_const thy) scope, Exn.Res thy)]
    | Exn.Exn exn =>
        let
          val _ = write "context-merge.xml" (elem "context_merge" [("status", "failed")]
            [text "error" (Runtime.exn_message exn)]);
          val maximal = filter_out (fn thy =>
            exists (fn other => Context.proper_subthy (thy, other)) originals) originals;
        in map_index (fn (i, thy) =>
          ("branch" ^ string_of_int (i + 1), filter (Sign.declared_const thy) scope,
           capture (Context.begin_thy ("AFP_Full_Branch_" ^ string_of_int (i + 1)))
             (thy :: setups))) maximal end);
  fun export context lthy batch cs languages =
    if null cs then ()
    else
      let
        val (front, seconds) = timed (Code_Thingol.consts_program lthy) cs;
        val _ = record context batch "frontend" "frontend" cs front seconds
          (map (text "language") languages);
        val failed =
          (case front of
            Exn.Exn _ => languages
          | Exn.Res program =>
              languages |> filter (fn target =>
                let
                  val prefix = Path.make [target, batch];
                  fun serialize () =
                    let
                      val exported =
                        Code_Target.export_code_for
                          (SOME ({physical = false}, (prefix, Position.none)))
                          target "" NONE [] program false (map Code_Symbol.Constant cs) lthy;
                      val key = "code/" ^ target ^ "/" ^ batch;
                      val files = Generated_Files.get_files (Proof_Context.theory_of exported)
                        |> filter (fn file =>
                          let val name = Path.implode (#path file)
                          in name = key orelse String.isPrefix (key ^ "/") name
                             orelse String.isPrefix (key ^ ".") name end);
                      val root = output + Path.basic "artifacts" + Path.basic context;
                      val _ = List.app (fn file =>
                        let val path = root + #path file
                        in directory (Path.dir path); Bytes.write path (#content file) end) files;
                    in map (fn file => text "file"
                      (Path.implode (Path.make ["artifacts", context] + #path file))) files end;
                  val (result, elapsed) = timed serialize ();
                  val _ = record context batch "target_preparation_or_serialization" target cs result elapsed
                    (case result of Exn.Res [] => [text "library_only" "true"]
                    | Exn.Res files => files | _ => []);
                in case result of Exn.Res _ => false | _ => true end));
      in
        (* Successful groups already cover every named constant and keep their
           complete artifacts. Only unresolved members need another frontend. *)
        if null failed orelse length cs = 1 then ()
        else
          let val (left, right) = chop (length cs div 2) cs
          in export context lthy (batch ^ "L") left failed;
             export context lthy (batch ^ "R") right failed end
      end;
  fun run_context (context, cs, result) =
    (case result of
      Exn.Exn exn => write ("attempts/" ^ context ^ "/loading.xml")
        (elem "context_loading" [("context", context), ("stage", "context_loading"),
          ("target", "context"), ("status", "failed")]
          (constants cs @ map (text "language") targets @
           [text "error" (Runtime.exn_message exn)]))
    | Exn.Res thy =>
        let
          val lthy = Named_Target.theory_init thy;
          val _ = write ("contexts/" ^ context ^ ".xml") (elem "context" []
            (map (text "theory") (map Context.theory_long_name (Theory.parents_of thy)) @ constants cs));
        in export context lthy "all" cs targets end);
  val _ = List.app run_context contexts;
in
  val _ = write "finished.xml" (elem "finished" [] []);
end;
