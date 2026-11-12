(* Native evidence only: no target serializer, compiler or execution. *)
local
  open AFP_Fixed;
  fun selection () =
    let
      val requested = names "theory" request;
      val loaded = filter (is_some o Thy_Info.lookup_theory) requested;
      val originals = map Thy_Info.get_theory loaded;
      val declarations = children "declaration" request;
      val merged = capture begin (loaded @ setups);
      val maximal = filter_out (fn thy =>
        exists (fn other => Context.proper_subthy (thy, other)) originals) originals;
      val parents = (case merged of Exn.Res _ => [loaded @ setups]
        | Exn.Exn _ => map (fn thy => Context.theory_long_name thy :: setups) maximal);
      fun describe parents =
        let
          val res = capture begin parents;
          fun owns thy node =
            let val c = attr "name" node in
              Sign.declared_const thy c andalso
              Name_Space.theory_name {long = true} (Sign.const_space thy) c = attr "owner" node
            end;
        in elem "context" [("status", case res of Exn.Res _ => "complete" | _ => "unresolved")]
          (map (fn p => elem "parent" [("name", p)] []) parents @
           (case res of Exn.Res thy => filter (owns thy) declarations | _ => []) @ error_body res)
        end;
    in write "selection.xml" (elem "selection" [("schema", "1")]
      (map (fn name => elem "loaded" [("name", name)] []) loaded @
       [elem "merge" [("status", case merged of Exn.Res _ => "complete" | _ => "failed")]
         (error_body merged)] @ map describe parents)) end;

  fun analysis () =
    let
      fun inspect () =
        let
          val thy = context ();
          val ctxt = Proof_Context.init_global thy;
          val declarations = children "declaration" request;
          val cs = map (attr "name") declarations;
          val _ = List.app (fn node =>
            if Sign.declared_const thy (attr "name" node) andalso
               Name_Space.theory_name {long = true} (Sign.const_space thy) (attr "name" node)
                 = attr "owner" node then ()
            else error "Declaration provenance changed") declarations;
          val roots = filter_out (Code.is_abstr thy) (sort_strings (distinct (op =) cs));
          (* Strict native generation: never use permissive NoStmt as evidence. *)
          val program = Code_Thingol.consts_program ctxt roots;
          val {eqngr, ...} = Code_Preproc.obtain false {ctxt = ctxt, consts = roots, terms = []};
          fun symbol sym = Code_Symbol.marker sym;
          fun equations c =
            let
              val eqns = Code_Preproc.cert eqngr c |> Code.equations_of_cert thy |> snd;
              fun is_projection ((args, _), _) = exists (is_some o fst) args;
              fun is_abstract ((_, (abs, _)), _) = is_some abs;
            in case eqns of NONE => "missing" | SOME [] => "empty"
              | SOME es => if exists is_abstract es then "abstract"
                else if exists is_projection es then "projection" else "ordinary" end;
          fun stmt_kind Code_Thingol.NoStmt = "none"
            | stmt_kind (Code_Thingol.Fun _) = "function"
            | stmt_kind (Code_Thingol.Datatype _) = "type"
            | stmt_kind (Code_Thingol.Datatypecons _) = "constructor"
            | stmt_kind (Code_Thingol.Class _) = "class"
            | stmt_kind (Code_Thingol.Classrel _) = "class_relation"
            | stmt_kind (Code_Thingol.Classparam _) = "class_parameter"
            | stmt_kind (Code_Thingol.Classinst _) = "instance";
          fun node (sym, (stmt, (_, successors))) =
            let
              val kind = stmt_kind stmt;
              val (facts, eqn) = (case sym of Code_Symbol.Constant c =>
                let
                  val structural = Code.is_constr thy c orelse Code.is_abstr thy c
                    orelse is_some (Axclass.class_of_param thy c);
                  val eqn = if structural then "structural" else equations c;
                  val belongs = (case stmt of Code_Thingol.Datatypecons tyco => tyco
                    | Code_Thingol.Classparam cls => cls | _ => "");
                in ([("name", c),
                     ("owner", Name_Space.theory_name {long = true} (Sign.const_space thy) c),
                     ("abstract_constructor", Bool.toString (Code.is_abstr thy c)),
                     ("structural_owner", belongs)], eqn) end
                | _ => ([], "structural"));
              val valid_equations =
                (kind = "none" andalso (eqn = "missing" orelse eqn = "empty")) orelse
                (kind = "function" andalso (eqn = "ordinary" orelse eqn = "abstract"
                  orelse eqn = "projection" orelse eqn = "empty")) orelse
                (kind <> "none" andalso kind <> "function" andalso eqn = "structural");
              val _ = if valid_equations then ()
                else error ("Inconsistent native equation/Thingol evidence for " ^ symbol sym);
            in elem "node" (("id", symbol sym) :: ("kind", kind) :: ("equations", eqn) :: facts)
              (map (fn dep => elem "edge" [("to", symbol dep)] [])
                (Code_Symbol.Graph.Keys.dest successors)) end;
          val nodes = Code_Symbol.Graph.fold (fn item => cons (node item)) program [];
          fun printing target =
            let val syms = Code_Symbol.symbols_of (Code_Target.get_printings ctxt target);
            in elem "target" [("name", target)]
              (map (fn sym => elem "printing" [("symbol", symbol sym)] [])
                (filter (fn sym => Code_Symbol.Graph.defined program sym) syms)) end;
          fun declaration node =
            elem "declaration"
              [("name", attr "name" node), ("source", attr "source" node),
               ("owner", attr "owner" node),
               ("abstract_constructor", Bool.toString (Code.is_abstr thy (attr "name" node)))] [];
        in map declaration declarations @ nodes @ map printing targets end;
      val res = capture inspect ();
    in write "analysis.xml" (elem "analysis"
      [("schema", "1"), ("context", attr "context" request),
       ("status", case res of Exn.Res _ => "complete" | _ => "unresolved")]
      (case res of Exn.Res body => body | _ => error_body res)) end;
in
  val _ = if attr "mode" request = "select" then selection () else analysis ();
end;
