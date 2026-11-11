(* Read the workspace backend in memory. Preserve its literals, function-type
   printer and reserved names; replace only the serializer registration.
   Execute the original base setup's Isar declarations in this agent theory.
   No original repository file is changed or copied. *)
val _ = Theory.setup (fn thy =>
  let
    val root = Resources.master_directory thy + Path.explode "../../translate";
    fun eval_text text thy = Context.theory_map
      (ML_Context.exec (fn () => ML_Context.eval_source ML_Compiler.flags (Input.string text))) thy;
    val backend = File.read (root + Path.basic "code_rust.ML");
    val needle = "serializer = serializer_rust";
    val parts = String.fields (fn c => c = #"\n") backend;
    val matches = filter (String.isSubstring needle) parts;
    val _ = if length matches = 1 then ()
      else error "Rust serializer bridge expected exactly one registration hook";
    val thy1 = thy
      |> eval_text (File.read (root + Path.basic "code_debug_info.ML"))
      |> eval_text (String.concatWith "\n" (map (fn line => if String.isSubstring needle line
          then "    (target, {serializer = I2R_Adapter_Export.serializer, literals = literals_rust," else line) parts));
    val source = File.read (root + Path.explode "Rust_Base_Setup.thy");
    val commands = Outer_Syntax.parse_text thy1 (K thy1) Position.none source
      |> filter_out (fn tr => member (op =) ["theory", "end"] (Toplevel.name_of tr));
    val thy2 = fold (Toplevel.command_exception false) commands (Toplevel.make_state (SOME thy1))
      |> Toplevel.theory_of;
  in Code_Target.add_derived_target ("Rust_Agent", [("Rust", I)]) thy2 end);
