(* Source extraction has no target serializer, printing setup or Thingol graph. *)
structure I2R_Source_Export =
struct
fun run (raw_names, (target, module_name)) lthy =
  let
    val thy = Proof_Context.theory_of lthy;
    val _ = if member (op =) ["Rust", "Rust_Agent"] target then ()
      else error "Source extraction expects a Rust export request";
    val names = map (Code.read_const thy) raw_names;
    fun emit file text = Export.export thy
      (Path.binding0 (Path.explode ("code/" ^ module_name ^ "/" ^ file))) [XML.Text text];
    fun theory_row t = I2R_Source_Model.obj [
      ("theory", I2R_Source_Model.quote (Context.theory_long_name t)),
      ("path", I2R_Source_Model.quote (File.platform_path
        (Resources.master_directory t + Path.basic (Context.theory_base_name t ^ ".thy"))))];
    val _ = emit "source-model.json" (I2R_Source_Model.export lthy names);
    val _ = emit "source-index.json" (I2R_Source_Model.obj
      [("theories", I2R_Source_Model.arr theory_row (Theory.nodes_of thy))]);
  in lthy end;
end;
val _ = Outer_Syntax.local_theory \<^command_keyword>\<open>i2r_export_source\<close>
  "export typed Isabelle facts for the agent-owned source graph"
  (Scan.repeat1 Parse.term -- (\<^keyword>\<open>in\<close> |-- Parse.name --
    Scan.optional (\<^keyword>\<open>module_name\<close> |-- Parse.name) "Candidate")
    >> I2R_Source_Export.run);
