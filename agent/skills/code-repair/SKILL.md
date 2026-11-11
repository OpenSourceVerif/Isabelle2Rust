---
name: code-repair
description: Diagnose and repair an existing Rust implementation, representation decision or test connector from concrete failed checks. Use after a failure, separately from first generation; the controller owns execution, budgets and acceptance.
---

# Repair an existing implementation

The original defect remains open until its own check passes. A malformed patch is an action error, not a replacement diagnosis. Current files and executed diffs override earlier assistant claims. Earlier semantic analyses may be wrong.

## Establish one falsifiable explanation

Start with the reproducer, actual output/diagnostic, expected source behavior and current affected function. For runtime/range errors inspect the isolated input and its bit widths before reasoning about an unreachable branch. A panic in a shared overflow helper identifies the symptom, not its caller. Trace the input through calls or request missing equations/callers. Do not diagnose from function names or a generic arithmetic convention.

State the implicated expression/interface and the supporting evidence. When evidence is sufficient, explain and patch in the same response; a separate diagnosis-only turn is not required. If evidence is missing, request the specific file/node/range. Do not re-read an entire graph to fix a known local signature mismatch.

## Make the actual edit

Return one coherent patch for that explanation, including affected callers or support functions. Follow edit_protocol when supplied: read and edit the same file IDs; the controller binds the response to the request snapshot, so a version echo is optional. Legacy requests without edit_protocol require base_code_version copied from code_version. Edits use exact unique old text. In source-v6 update ordinary support files, dependencies and realization records directly; no Isabelle printing setup is required. Avoid reprinting unchanged mappings/files. New files and intentional coherent redesigns remain possible.

Read repair_execution separately from the program defect. A rejected operation changed no files; address all retained action errors together. Unknown file, stale snapshot and non-unique old text require different corrections. During replace_files recovery, use the supplied complete current content and return the complete affected file. Actual applied diffs and subsequent checks decide progress, even when previous notes claim the repair is correct.

When edit_protocol advertises mapping removal, use remove_mapping:[source_id] to delete an erroneous realization. mapping merges entries, so leaving an entry out does not delete it. The original source/export coverage check still applies after removal.

Preserve the original source API, generic parameters, values and operation order. A compiler error is not authority to add clone, cast, stronger trait bounds or a different numeric convention. A note describing a fix without changing the responsible code does not repair it. A repeated rejected patch requires inspecting the supplied current text, not repeating the same intended edit.

## Verify the same defect

A compiler repair needs compilation and subsequent behavioral checks. A runtime repair needs the exact original reproducer and broader development checks. A support semantic repair needs source-grounded tests of that operation; unrelated business tests do not cover it. A representation revision needs coherent code and caller changes followed by compiler and behavior checks. Keep finite-range failure distinct from a valid output, and never shrink the input domain to erase the failure.

If a different error appears, distinguish progress from a new independent fault. Preserve the original issue and its completion condition. Only route to a connector when a concrete wrong argument, conversion or call in that connector explains the reproducer; a direct support-function test cannot be fixed by changing a connector it never calls.

## Domain knowledge on demand

For representations and mathematical operators read semantic-adaptation references and original equations. For borrowing, closure/interface errors or structural costs read the relevant rust-generation reference. First-generation design instructions are not the repair plan. Runtime measurements are not repair feedback.

## Program context

Use structured compiler locations, complete implicated Rust items, source correspondence and recent actual diffs. For a shared panic helper use executed caller evidence; request_diagnostics replays the original input with a debug backtrace. Repeated failures require new evidence or a changed explanation, and may justify a coherent larger function-group patch. Do not require the controller to know the root cause before allowing a repair.

Consult program_state.change_impact and stale decisions alongside the immutable issue. Request the original source entity with include_callers when a patch changes ownership, type bounds, numeric representation or support signatures. Coordinate the affected Rust callers and support in the same patch. Reconsider affected conditions rather than carrying over an earlier test result to changed code. A lexical impact hint may over-approximate; source equations and actual checks decide.
