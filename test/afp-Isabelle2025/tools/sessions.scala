/* Isabelle resolves session ownership and theory imports.  Keep entries with
   no executable code or source errors visible in the coverage manifest. */
import isabelle.*

object AFP_Sessions {
  def main(args: Array[String]): Unit = {

    val afp = Path.explode(sys.env("AFP_THYS")).canonical
    val base = afp.file.toPath
    val options = Options.init()
    val structure = Sessions.load_structure(options, dirs = List(afp))
    def entryOf(path: Path): Option[String] = {
      val p = path.canonical.file.toPath
      if (p.startsWith(base) && p != base) Some(base.relativize(p).getName(0).toString)
      else None
    }
    val names = structure.imports_topological_order.filter(n => entryOf(structure(n).dir).isDefined)
    val selected = structure.selection(Sessions.Selection(sessions = names))
    val deps = Sessions.deps(selected)
    val entries = names.groupBy(n => entryOf(structure(n).dir).get).map { case (entry, sessions) =>
      val theories = sessions.flatMap { session =>
        // Keep conditional sources visible even when their compiler is absent:
        // successful session builds can omit them without producing a heap theory.
        val theoryOptions = deps(session).used_theories.toMap
        deps(session).proper_session_theories.flatMap { node =>
          if (entryOf(node.path).contains(entry)) {
            Some(JSON.Object("name" -> node.theory,
              "path" -> base.resolve(entry).relativize(node.path.canonical.file.toPath).toString,
              "session" -> session,
              "conditions" -> theoryOptions.get(node).map(_.string("condition"))
                .toList.flatMap(_.split(",").toList).filter(_.nonEmpty)))
          } else None
        }
      }.distinct.sortBy(_("path").toString)
      val requirements = sessions.flatMap(n => structure(n).deps).filterNot(sessions.contains).distinct
      val entryDeps = requirements.flatMap(n => entryOf(structure(n).dir)).filterNot(_ == entry).distinct.sorted
      // Include stock Isabelle parents too: one failed HOL-Analysis build
      // must block its dependents instead of being retried for every AFP entry.
      val sessionRequirements = sessions.map(n =>
        n -> structure.imports_requirements(List(n)).filterNot(_ == n)).toMap
      entry -> JSON.Object("sessions" -> sessions, "dependencies" -> entryDeps,
        "required_sessions" -> structure.imports_requirements(sessions),
        "session_requirements" -> sessionRequirements,
        "theories" -> theories, "source_errors" -> sessions.flatMap(n => deps(n).errors))
    }
    File.write(Path.explode(sys.env("AFP_MANIFEST")), JSON.Format(JSON.Object(
      "entries" -> entries, "order" -> names.map(n => entryOf(structure(n).dir).get).distinct)))
  }
}
