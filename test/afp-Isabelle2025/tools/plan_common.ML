(* Read-only context reconstruction shared by analysis and fixed export. *)
structure AFP_Fixed =
struct
  val output = Path.explode (getenv_strict "AFP_FULL_OUTPUT");
  val request = XML.parse (File.read (output + Path.basic "request.xml"));
  val targets = ["Rust", "SML", "OCaml", "Haskell", "Scala", "Go"];
  val setups = ["Rust.Rust_BigInt_Setup", "Go.Go_Setup"];
  fun elem name props body = XML.Elem ((name, props), body);
  fun text name value = elem name [] [XML.Text value];
  fun attr name (XML.Elem ((_, props), _)) = the_default "" (Properties.get props name)
    | attr _ _ = "";
  fun children name (XML.Elem (_, body)) =
        filter (fn XML.Elem ((tag, _), _) => tag = name | _ => false) body
    | children _ _ = [];
  fun names name node = map (attr "name") (children name node);
  fun capture f x =
    (case Exn.capture f x of Exn.Exn exn =>
      if Exn.is_interrupt exn then Exn.reraise exn else Exn.Exn exn | res => res);
  fun directory path =
    if File.is_dir path then ()
    else (directory (Path.dir path); OS.FileSys.mkDir (File.platform_path path));
  fun write name node =
    let
      val path = output + Path.explode name;
      val _ = directory (Path.dir path);
      val tmp = Path.ext "tmp" path;
      val _ = File.write tmp (XML.string_of node);
    in OS.FileSys.rename {old = File.platform_path tmp, new = File.platform_path path} end;
  fun constant name = elem "constant" [("name", name)] [];
  fun begin parents = Context.begin_thy "AFP_Fixed_Context" (map Thy_Info.get_theory parents);
  fun context () = begin (names "parent" request);
  fun timed f x =
    let val start = Time.now (); val res = capture f x
    in (res, Time.toString (Time.- (Time.now (), start))) end;
  (* Raw exception payload is separate from the complete rendered exception.
     Only this strict-call envelope is eligible for rejection classification. *)
  fun failure phase exn =
    let
      fun payload (ERROR msg) = ("ERROR", msg)
        | payload (TYPE (msg, _, _)) = ("TYPE", msg)
        | payload (THM (msg, _, _)) = ("THM", msg)
        | payload other = ("OTHER", Runtime.exn_message other);
      val (kind, msg) = payload exn;
    in elem "failure" [("phase", phase), ("version", "Isabelle2025"), ("exception", kind)]
      [text "message" (XML.content_of (YXML.parse_body msg)), text "error" (Runtime.exn_message exn)] end;
  fun error_body (Exn.Exn exn) = [text "error" (Runtime.exn_message exn)]
    | error_body _ = [];
end;
