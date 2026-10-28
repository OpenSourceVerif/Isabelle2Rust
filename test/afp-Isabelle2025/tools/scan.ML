(* Frozen discovery records real declarations before any code preprocessing.
   Executability is a later diagnostic: target-only mappings, constructors,
   aborting functions and declarations without equations must remain visible.
   Each original theory is inspected in its own namespace; equation additions
   in a descendant cannot change whether that declaration exists. *)
local
  fun element name props body = XML.Elem ((name, props), body);
  fun catalogue () =
    let
      val requested = split_lines
        (File.read (Path.explode (getenv_strict "AFP_SCAN_THEORIES")))
        |> filter_out (fn name => name = "") |> distinct (op =);
      val names = filter (is_some o Thy_Info.lookup_theory) requested;
      val theories = map Thy_Info.get_theory names;
      val maximal = filter_out (fn thy =>
        exists (fn other => Context.proper_subthy (thy, other)) theories) theories;
      fun own thy name =
        #constants (Consts.dest (Sign.consts_of thy))
        |> filter (fn (c, _) =>
          Name_Space.theory_name {long = true} (Sign.const_space thy) c = name)
        |> sort_by #1;
      fun declaration name (c, (_, abbreviation)) =
        element (if is_none abbreviation then "constant" else "abbreviation")
          [("name", c), ("owner", name)] [];
      fun inspect (name, thy) =
        let val declarations = own thy name in
          element "theory"
            [("name", name), ("context", name),
             ("declared", string_of_int (length declarations))]
            (map (declaration name) declarations)
        end;
      fun context thy =
        element "context" [("name", Context.theory_long_name thy)]
          (map_filter (fn (name, original) =>
            if Context.subthy (original, thy)
            then SOME (element "covers" [("theory", name)] []) else NONE)
            (names ~~ theories));
      val body =
        map (fn name => element "requested" [("name", name)] []) requested @
        map (fn name => element "loaded" [("name", name)] []) names @
        map context maximal @ map inspect (names ~~ theories);
    in
      File.write (Path.explode (getenv_strict "AFP_SCAN_OUTPUT"))
        (XML.string_of (element "scan"
          [("schema", "2"), ("policy", "owned-constants-v1"),
           ("method", "declaration-catalogue-v1"),
           ("unit", getenv_strict "AFP_SCAN_UNIT")] body))
    end;

(* Inspect actual loaded theories, never source-level definition keywords.
   Namespace provenance assigns locale/instance/generated constants to their
   defining theory even when their long names do not start with its basename.
   Code certificates include ordinary, abstract and projection equations. *)
fun certificate_probe () =
let
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
      (* Registered code equations are normalized with the code generator's
         preprocessor simpset, not the ordinary HOL simp rules. The latter can
         rewrite constructor patterns into non-constructors or expand logical
         definitions unrelated to code generation. map_pre exposes the existing
         simpset to an identity callback; its returned persistent theory value
         is discarded, so no declaration or equation is changed. *)
      val pre = Unsynchronized.ref (NONE : simpset option);
      val _ = Code_Preproc.map_pre (fn current =>
        (pre := SOME (simpset_of current); current)) thy;
      val ctxt = put_simpset (the (!pre)) (Proof_Context.init_global thy);
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
  (* Preserve interrupts and full diagnostics without an unrestricted ML
     handler: theory-context compilation checks catch-all handlers strictly. *)
  fun safe_inspect thy name =
    (case Exn.capture (inspect thy) name of
      Exn.Res result => result
    | Exn.Exn exn =>
        if Exn.is_interrupt exn then Exn.reraise exn else failure name exn);
  val body = maps (fn thy => map (safe_inspect thy) names) contexts @ diagnostics;
in
  File.write (Path.explode (getenv "AFP_SCAN_OUTPUT"))
    (XML.string_of (element "scan" [("certificate_context", "code_preprocessing_simpset")] body))
end;

in
  val _ =
    if getenv "AFP_SCAN_POLICY" = "owned-constants-v1"
    then catalogue ()
    else certificate_probe ();
end;
