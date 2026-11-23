import dotty.tools.dotc.Main;
import dotty.tools.dotc.interfaces.Diagnostic;
import dotty.tools.dotc.interfaces.SimpleReporter;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Compile one independent source tree at a time using the installed Scala compiler. */
public class ScalaCompileWorker {
    public static void main(String[] args) throws Exception {
        var input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        var reply = new PrintWriter(System.out, true, StandardCharsets.UTF_8);
        reply.println("ready");
        for (String line; (line = input.readLine()) != null; ) {
            var request = line.split("\t", -1);
            if (request.length != 3) {
                throw new IllegalArgumentException("Invalid Scala compile request");
            }
            try (var log = new PrintWriter(Files.newBufferedWriter(Path.of(request[2]),
                    StandardCharsets.UTF_8, StandardOpenOption.APPEND))) {
                SimpleReporter reporter = diagnostic -> {
                    String level = diagnostic.level() == Diagnostic.ERROR ? "error" : "diagnostic";
                    String location = diagnostic.position()
                        .map(pos -> "line " + (pos.line() + 1) + ", column " + (pos.column() + 1) + ": ")
                        .orElse("");
                    log.println(level + ": " + location + diagnostic.message());
                };
                var flags = new ArrayList<>(Arrays.asList(args).subList(1, args.length));
                flags.addAll(List.of("-classpath", args[0], "-d", request[1], request[0]));
                try {
                    var result = Main.process(flags.toArray(String[]::new), reporter, null);
                    log.flush();
                    reply.println(result.hasErrors() ? "1" : "0");
                } catch (RuntimeException | LinkageError error) {
                    error.printStackTrace(log);
                    log.flush();
                    reply.println("70");
                    return;
                }
            }
        }
    }
}
