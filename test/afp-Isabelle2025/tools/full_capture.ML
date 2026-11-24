(* Record the actual outer outcome of an unchanged export request.  An
   interrupt may escape full_export.ML before its frontend attempt can be
   recorded.  Keep that distinction: this receipt reports evaluation of the
   original source, never a fabricated frontend or finished witness.  Release
   the captured result after writing so the process retains the same failure. *)
local
  val output = Path.explode (getenv_strict "AFP_FULL_OUTPUT");
  val source = Path.explode (getenv_strict "AFP_ORIGINAL_EXPORT_ML");
  val scope = split_lines (File.read (Path.explode (getenv_strict "AFP_FULL_SCOPE")))
    |> filter_out (fn name => name = "");
  val start = Time.now ();
  val result = Exn.capture (ML_Context.eval_file ML_Compiler.flags) source;
  val seconds = Time.toString (Time.- (Time.now (), start));
  fun elem name body = XML.Elem ((name, []), body);
  fun text name value = elem name [XML.Text value];
  val receipt = XML.Elem (("native_request_outcome",
      [("schema", "1"), ("origin", "original_full_export_outer_capture"),
       ("status", case result of Exn.Res _ => "returned" | Exn.Exn _ => "exception")]),
    map (fn name => XML.Elem (("constant", [("name", name)]), [])) scope @
    [text "original_script" (Path.implode source), text "seconds" seconds,
     text "original_finished_exists" (Bool.toString (File.exists (output + Path.basic "finished.xml")))] @
    (case result of Exn.Res _ => [] | Exn.Exn exn =>
      [text "exception_name" (General.exnName exn),
       text "exception_message" (Runtime.exn_message exn)]));
  val destination = output + Path.basic "native-request-outcome.xml";
  val temporary = Path.ext "tmp" destination;
  val _ = File.write temporary (XML.string_of receipt);
  val _ = OS.FileSys.rename
    {old = File.platform_path temporary, new = File.platform_path destination};
in
  val _ = Exn.release result;
end;