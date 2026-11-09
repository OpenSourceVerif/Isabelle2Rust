theory Diagnostic_Isolation_Test
  imports Main
begin

text \<open>
  Load the production backend against a diagnostic formatter with controlled
  failures. This theory intentionally imports Main, so its Rust target is local
  and the fault injection cannot change Rust_Base_Setup or other test theories.
  An observational exception must neither reject a valid export nor replace
  the actual Rust printer exception. Interrupts must still propagate.
\<close>

ML_file \<open>../../translate/code_debug_info.ML\<close>

ML \<open>
structure Diagnostic_Probe =
struct
  exception Printer_Failure;
  exception Formatter_Failure;
  exception Sink_Failure;
  val mode = Unsynchronized.ref "fail";
  val calls = Unsynchronized.ref 0;
end;
structure Original_Debug_Info = Code_Debug_Info;
structure Code_Debug_Info =
struct
  open Original_Debug_Info;
  fun print_debug_info_thingol_stmt stmt =
    (Diagnostic_Probe.calls := !Diagnostic_Probe.calls + 1;
     case !Diagnostic_Probe.mode of
       "fail" => raise Diagnostic_Probe.Formatter_Failure
     | "interrupt" => raise Exn.Interrupt_Break
     | "second" =>
         if !Diagnostic_Probe.calls > 1 then raise Diagnostic_Probe.Formatter_Failure
         else Original_Debug_Info.print_debug_info_thingol_stmt stmt
     | _ => Original_Debug_Info.print_debug_info_thingol_stmt stmt);
end;
\<close>

ML_file \<open>../../translate/code_rust.ML\<close>

code_printing
  type_constructor bool \<rightharpoonup> (Rust) "bool"
| constant True \<rightharpoonup> (Rust) "true"
| constant False \<rightharpoonup> (Rust) "false"

definition diagnostic_identity :: "bool \<Rightarrow> bool" where
  "diagnostic_identity b = b"
definition diagnostic_primitive :: "bool \<Rightarrow> bool" where
  "diagnostic_primitive b = b"
definition diagnostic_failure :: "bool \<Rightarrow> bool" where
  "diagnostic_failure b = diagnostic_primitive b"

setup \<open>
  Code_Target.set_printings (Code_Symbol.Constant
    (\<^const_name>\<open>diagnostic_primitive\<close>,
      [(Code_Rust.target, SOME (Code_Printer.complex_const_syntax
        (1, fn _ => fn _ => fn _ => fn _ => fn _ => fn _ =>
          raise Diagnostic_Probe.Printer_Failure)))]))
\<close>

ML \<open>
local
  val failed = Unsynchronized.ref ([]: string list);
  fun check label b = if b then () else failed := label :: !failed;
  fun produce c = Code_Target.produce_code \<^context> false [c]
    "Rust" "DiagnosticIsolation" NONE [];
  fun capture mode c =
    (Diagnostic_Probe.mode := mode; Diagnostic_Probe.calls := 0;
     Exn.capture produce c);
  val good = \<^const_name>\<open>diagnostic_identity\<close>;
  val bad = \<^const_name>\<open>diagnostic_failure\<close>;
  val _ = check "formatter failure before valid export"
    (case capture "fail" good of Exn.Res _ => !Diagnostic_Probe.calls > 0 | _ => false);
  val _ = check "formatter failure and original printer exception"
    (case capture "fail" bad of Exn.Exn Diagnostic_Probe.Printer_Failure => true | _ => false);
  val _ = check "crash report reuses the original diagnostic"
    (case capture "second" bad of
      Exn.Exn Diagnostic_Probe.Printer_Failure => !Diagnostic_Probe.calls = 1
    | _ => false);
  val _ = check "formatter interrupt is not swallowed"
    (case capture "interrupt" good of Exn.Exn Exn.Interrupt_Break => true | _ => false);

  (* Output handlers are restored even if the probe raises. Restrict faults to
     the backend's own messages, leaving unrelated Isabelle output untouched. *)
  fun with_failing_sink warning_sink f =
    let
      val sink = if warning_sink then Private_Output.warning_fn else Private_Output.tracing_fn;
      val original = !sink;
      val called = Unsynchronized.ref false;
      val prefix = if warning_sink then "RUST-STMT-CRASH" else "[Thingol]";
      val _ = sink := (fn ss =>
        if exists (String.isPrefix prefix) ss then
          (called := true; raise Diagnostic_Probe.Sink_Failure)
        else original ss);
      val result = Exn.capture f ();
      val _ = sink := original;
    in (Exn.release result, !called) end;
  val (success, trace_called) = with_failing_sink false (fn () => capture "normal" good);
  val _ = check "tracing sink failure"
    (trace_called andalso (case success of Exn.Res _ => true | _ => false));
  val (failure, warning_called) = with_failing_sink true (fn () => capture "normal" bad);
  val _ = check "warning sink preserves original printer exception"
    (warning_called andalso
      (case failure of Exn.Exn Diagnostic_Probe.Printer_Failure => true | _ => false));
  val _ = if null (!failed) then ()
    else error ("diagnostic isolation failures: " ^ commas (rev (!failed)));
in
  val _ = Diagnostic_Probe.mode := "fail";
  val _ = writeln "Diagnostic isolation: formatter/sink failures, original exception, and interrupt passed";
end
\<close>

text \<open>
  Compile a real exported crate while the formatter continues to fail.
  The resulting identity function is the ordinary Rust bool-to-bool function.
\<close>
export_code diagnostic_identity in Rust module_name DiagnosticIsolation

end
