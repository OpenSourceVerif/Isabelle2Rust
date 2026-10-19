(* Inspect actual loaded theories, never source-level definition keywords.
   Namespace provenance assigns locale/instance/generated constants to their
   defining theory even when their long names do not start with its basename.
   Code certificates include ordinary, abstract and projection equations. *)
local
  val names = split_lines (File.read (Path.explode (getenv "AFP_SCAN_THEORIES")))
    |> filter_out (fn s => s = "")
    |> filter (is_some o Thy_Info.lookup_theory);
  fun element name props body = XML.Elem ((name, props), body);
  fun failure name exn =
    element "error" [("name", name)] [XML.Text (Runtime.exn_message exn)];
  (* Code equations can be declared in a later theory than the constant.
     Prefer one read-only merge, retaining declaration provenance. Independent
     branches can instead have conflicting type instances, specifications or
     syntax registrations: each branch is valid without a joint import. Inspect
     their maximal loaded contexts separately in that case, preserving later
     equations along each branch and reporting why no global merge was possible.
     Ancestor contexts are omitted so superseded equations are not resurrected. *)
  val theories = map Thy_Info.get_theory names;
  val (contexts, diagnostics) =
    (case Exn.capture (Context.begin_thy "AFP_Executable_Candidates")
        (if null theories then [Thy_Info.get_theory "Pure"] else theories) of
      Exn.Res thy => ([thy], [])
    | Exn.Exn exn =>
        if Exn.is_interrupt exn then Exn.reraise exn
        else
          (filter_out (fn thy => exists (fn other => Context.proper_subthy (thy, other))
            theories) theories,
           [element "context_merge_error" [] [XML.Text (Runtime.exn_message exn)]]));
  fun inspect thy name =
    let
      val space = Sign.const_space thy;
      val ctxt = Proof_Context.init_global thy;
      (* Abbreviations share the namespace but are not logical constants and
         cannot carry code equations. Only genuine Const declarations qualify. *)
      val own = #constants (Consts.dest (Sign.consts_of thy))
        |> map_filter (fn (c, (_, NONE)) => SOME c | _ => NONE)
        |> filter (fn c => Name_Space.theory_name {long = true} space c = name)
        |> sort_strings;
      fun candidate c =
        let
          val result = Exn.capture (fn () =>
            Code.get_cert ctxt [] c |> Code.conclude_cert
            |> Code.equations_of_cert thy |> snd) ();
        in
          (case result of
            Exn.Res (SOME (_ :: _)) => [element "constant" [("name", c)] []]
          | Exn.Res _ => []
          (* A malformed certificate is still a candidate with code equations.
             Keep it available for a later exporter fix and report its error. *)
          | Exn.Exn exn =>
              if Exn.is_interrupt exn then Exn.reraise exn
              else [element "constant" [("name", c)] [], failure c exn])
        end;
    in element "theory" [("name", name)] (maps candidate own) end;
  fun safe_inspect thy name =
    (inspect thy name handle exn =>
      if Exn.is_interrupt exn then Exn.reraise exn else failure name exn);
  val body = maps (fn thy => map (safe_inspect thy) names) contexts @ diagnostics;
in
  val _ = File.write (Path.explode (getenv "AFP_SCAN_OUTPUT"))
    (XML.string_of (element "scan" [] body));
end;
