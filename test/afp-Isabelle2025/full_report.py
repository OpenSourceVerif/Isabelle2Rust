#!/usr/bin/env python3
"""Generate four reports and exhaustive evidence catalogs for the AFP experiment.

Group failures remain diagnostics until their members have individual witnesses.
Preview reports are explicitly incomplete; final reports require an independent
completion audit matching the current experiment files.
"""
import argparse
import collections
import csv
import json
import os
from pathlib import Path
import re
import statistics
import xml.etree.ElementTree as ET

import afp_common as common
import full
import candidate_scope
import declaration_scope

CATEGORIES = (
    ("scan_coverage", "扫描回执覆盖验证", r"loaded theories do not cover|required session context",
     "原会话构建和声明检查可以均成功，但声明 XML 未覆盖扫描器要求的理论集合。此为候选发现证据验证失败，不能归为 HOL 证明失败或语言后端失败。"),
    ("dependency", "继承的扫描依赖阻塞", r"Blocked by:",
     "前置会话没有可接受的扫描回执，依赖条目没有执行自己的候选检查。阻塞不是该条目的导出失败；当前候选实验保留原始未知范围。"),
    ("infrastructure", "资源、工具或依赖",
     r"(?m)^(?:timeout|interrupted)$|host_restart|memory_limit|Run out of store|Interrupt_Breakdown|Unable to increase stack|out of memory|OutOfMemoryError|Java heap space|GC overhead limit|command not found|Protocol_Message",
     "资源或外部工具条件尚未满足，不能据此归因于 HOL 构造或目标打印规则；必须在阶段检查点处理。"),
    ("class_constraints", "代码类型类约束", r"Wellsortedness|No type arity|No type class|Missing.*arity",
     "Thingol 前端推导可执行代码的类型类字典时，依赖类型没有要求的实例。逻辑定义、量化和相等不自动给出 enum、equal 或 partial_term_of 的可执行实现。"),
    ("code_equations", "依赖缺少方程或目标实现", r"No code equations|Unimplemented constant",
     "目标准备先扣除该语言的 code_printing 实现，再检查剩余依赖。入口有方程不保证依赖闭包可执行；应结合六语言结果区分共享规格缺口与目标专用运行时适配。"),
    ("constructor_pattern", "方程模式与代码构造子", r"is not a constructor|Not a constructor",
     "代码证书要求左侧模式由当前表示的构造子组成。列表拼接、抽象表示和 nat 整数化后的 0/Suc 模式需要相应预处理；这发生在 Rust 文本打印之前。"),
    # Thingol also rejects an abstract constructor requested as a top-level
    # export. This interface check precedes every target serializer and has a
    # different diagnostic from an abstraction violation in a code equation.
    ("abstraction", "代码抽象类型接口", r"Abstraction violation|Cannot export abstract constructor",
     "代码抽象类型规定表示与抽象函数可出现的位置；越过接口的代码方程或直接导出抽象构造函数会被通用 Thingol 检查拒绝。"),
    ("context_merge", "独立理论上下文冲突", r"Clash of|Cannot merge|Duplicate.*instance|Duplicate.*definition",
     "独立分支可以各自有效，却不能把不同实例、定义或代码注册合并成同一理论。分支成功与整组导入冲突必须分别记录。"),
    ("name_interface", "常量名称或可见性", r"Inaccessible constant|Undefined constant|Not a constant|Unknown constant|No such constant",
     "常量必须在实际上下文中声明。内部全名与外层命令解析接口并非一回事；本轮直接使用实际 Const 全名并核验加载范围。"),
    ("term_or_proof", "预处理项构造或证明", r"Type error in application|Proof failed|Tactic failed|Failed to finish proof",
     "代码预处理会构造中间 HOL 项并证明重写等式。类型不一致或自动证明失败会阻止 Thingol 程序形成；具体规则须根据完整异常位置核查，不能只据此断定 AFP 定理错误。"),
    ("rust_trait", "Rust trait 或生命周期前提", r"E0277|E0310|trait bound|lifetime",
     "泛型 HOL 类约束需要一致的 Rust trait、父 trait 与 impl 前提。应对照生成类型、impl 和调用，区分实例覆盖不足与发射错误。"),
    ("rust_types", "Rust 类型或调用形状", r"E0308|E0614|E0618|mismatched types|cannot be dereferenced",
     "Rust 表达式、返回形状或参数分组与声明类型不一致；最后一条 rustc 诊断未必就是唯一根因。"),
    ("rust_ownership", "Rust 所有权或借用", r"E0382|E050[0-9]|borrow|moved value",
     "源语言值语义需要正确的移动、借用与克隆；两阶段实际编译结果分别统计。"),
    ("rust_syntax", "Rust 语法或宏适配",
     r"expected.*(?:token|expression|item)|format argument must be a string literal|expected one of",
     "表达式分组、语句位置或目标宏接口不满足 Rust 语法；后续派生诊断不应重复计为独立缺陷。"),
    ("module_cycle", "目标模块依赖环", r"module dependency cycle",
     "代码符号依赖被投影到目标模块后形成环；SML、OCaml、Go 的层次模块设施要求跨模块依赖无环。源理论命名空间分割也会制造这种环，显式共同模块名可以避免这类配置失败；它不证明 HOL 常量不可执行。"),
    ("ml_exception", "未覆盖的 ML 实现分支", r"exception (?:Match|Fail|Option|Empty|Bind|Subscript)|(?:Match|Fail|Option) raised",
     "完整异常位置和跨语言对照用于判断通用前端或具体 serializer 的未覆盖分支。"),
)


def category(message):
    for key, label, pattern, explanation in CATEGORIES:
        if re.search(pattern, message, re.IGNORECASE):
            return key, label, explanation
    return "other", "其他错误（待逐例解释）", "根据完整日志中的 HOL 对象、失败位置和代码生成前提逐例核查；证据不足时不指定责任。"


def md(value):
    return str(value).replace("|", r"\|").replace("\n", " ").replace("\r", "")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(map(md, headers)) + " |",
                      "| " + " | ".join("---" for _ in headers) + " |"]
                     + ["| " + " | ".join(map(md, row)) + " |" for row in rows])


def write_csv(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def link(report_dir, path, label="完整证据"):
    target = Path(path)
    if not target.is_absolute():
        target = common.PROJECT / target
    return "[" + label + "](<" + os.path.relpath(target, report_dir) + ">)"


def failure_events(base, data, result):
    """Stream complete exception bodies with immutable original evidence."""
    message_index = common.read_json(base / "scan-messages/index.json", {})
    # Auxiliary prerequisites have their own logs even when they precede all
    # candidate attempts. Retain their failures alongside the scan phase.
    prerequisite_root = base / "prerequisites"
    for path in sorted(prerequisite_root.glob("**/result.json")):
        check = common.read_json(path, {})
        if check.get("status") not in {"passed", None}:
            yield {"entry": "@prerequisite/" + path.relative_to(prerequisite_root).parts[0],
                   "phase": "scan", "stage": "prerequisite", "status": check["status"],
                   "constants": [], "target": None, "error": full.log_text(check),
                   "historical": "history" in path.relative_to(prerequisite_root).parts,
                   "evidence": [check["log"]] if check.get("log") else [common.relative(path)]}
    # Host interruption can occur before an entry has a result row. Its
    # recovery observation and partial original logs remain historical evidence.
    for path in sorted((base / "recovery").glob("*/result.json")):
        check = common.read_json(path, {})
        if check.get("status") not in {"passed", None}:
            yield {"entry": check.get("entry", "@execution"), "phase": check.get("phase", "scan"),
                   "stage": "process_interruption", "status": check["status"], "constants": [],
                   "target": None, "historical": True, "error": full.log_text(check),
                   "evidence": [check["log"], *check.get("evidence", [])]}
    for entry in data["order"]:
        record = result["entries"][entry]
        scan = record["scan"]
        inherited_messages = candidate_scope.messages(base, scan)
        documents = {}
        for phase in ("loading", "inspections"):
            for check in scan.get(phase, []):
                if check["status"] in {"passed", "blocked", "blocked_dependency"}:
                    continue
                messages = [message_index.get(s) or inherited_messages.get(s, {})
                            for s in check.get("failed_sessions", [])]
                usable = [x for x in messages if x.get("status") == "passed" and x.get("origin_verified")
                          and x.get("receipt_index_verified", True)]
                evidence = [x["command"]["log"] for x in usable]
                if check.get("log"):
                    evidence.insert(0, check["log"])
                yield {"entry": entry, "phase": "scan", "stage": phase, "status": check["status"],
                       "session": check.get("session"), "constants": [], "target": None,
                       "full_message_available": len(usable) == len(messages),
                       "evidence": evidence,
                       "error": "\n".join((common.PROJECT / p).read_text(errors="replace")
                                         for p in evidence if (common.PROJECT / p).is_file())}
        for kind in ("certificate_errors", "context_merge_errors", "errors"):
            for diagnostic in scan.get(kind, []):
                value = diagnostic if isinstance(diagnostic, dict) else {"message": diagnostic}
                evidence = value.get("detail")
                path = common.PROJECT / evidence if evidence else None
                message = value.get("message", "")
                complete = not value.get("truncated")
                if path and path.is_file():
                    if path not in documents:
                        documents[path] = ET.parse(path).getroot()
                    tag = "context_merge_error" if kind == "context_merge_errors" else "error"
                    matches = [n.text or "" for n in documents[path].iter(tag)
                               if not value.get("name") or n.attrib.get("name") == value["name"]]
                    exact = [m for m in matches if m.startswith(message)]
                    if exact or matches:
                        message = "\n\n".join(exact or matches)
                        complete = True
                yield {"entry": entry, "phase": "scan", "stage": kind, "status": "failed",
                       "constants": [value["name"]] if value.get("name") else [], "target": None,
                       "error": message, "full_message_available": complete,
                       # A complete legacy exception can outlive its temporary XML.
                       "message_source": "scan_xml" if path and path.is_file() else "result_record",
                       "evidence": [evidence] if path and path.is_file()
                       else [common.relative(base / "results.json")]}
        # A scanner can reject otherwise successful native commands because
        # their XML context coverage is incomplete. Keep that receipt error.
        for path, receipt in candidate_scope.receipts(base, scan):
            if receipt.get("error"):
                yield {"entry": entry, "phase": "scan", "stage": "receipt_validation",
                       "status": "failed", "constants": [], "target": None,
                       "error": receipt["error"], "full_message_available": True,
                       "inherited": True, "evidence": [common.relative(path)]}
        if scan["status"] == "blocked":
            dependencies = candidate_scope.dependencies(base, scan)
            yield {"entry": entry, "phase": "scan", "stage": "dependency", "status": "blocked",
                   "constants": [], "target": None, "error": "Blocked by: " + ", ".join(dependencies),
                   "evidence": [common.relative(base / "results.json")]}
        # Earlier configuration attempts remain in the failure catalog even
        # after their candidate cells have been replaced by fresh results.
        stages = [(True, value) for value in record.get("full_export_history", [])]
        stages.append((False, record.get("full_export", {})))
        for historical, stage in stages:
            for run in stage.get("runs", []):
                if run["command"]["status"] != "passed":
                    yield {"entry": entry, "phase": "export", "stage": "process",
                           "status": run["command"]["status"], "constants": [], "target": None,
                           "historical": historical, "error": full.log_text(run["command"]), "evidence": [run["command"]["log"]]}
                for attempt in run["attempts"]:
                    if attempt["status"] != "failed":
                        continue
                    message = ET.parse(common.PROJECT / attempt["evidence"]).getroot().findtext("error", "")
                    yield {"entry": entry, "phase": "export", "stage": attempt["stage"], "status": "failed",
                           "historical": historical, "target": attempt["target"], "constants": attempt["constants"], "error": message,
                           "evidence": [attempt["evidence"], run["command"]["log"]],
                           "group_diagnostic": len(attempt["constants"]) > 1 and attempt["stage"] != "context_loading"}
        compilations = [(True, value) for value in record.get("full_compile_history", [])]
        compilations.append((False, record.get("full_compile", {})))
        for historical, inventory in compilations:
            for manifest, compiled in inventory.items():
                for phase in ("stage1_compile", "optimization", "stage2_compile"):
                    value = compiled.get(phase, {})
                    checks = ([value] if value else []) if phase == "optimization" else value.get("checks", [])
                    for check in checks:
                        if check["status"] == "passed":
                            continue
                        yield {"entry": entry, "phase": "compile", "stage": phase, "status": check["status"],
                               "historical": historical, "manifest": manifest, "target": "Rust", "constants": [],
                               "error": full.log_text(check), "evidence": [check["log"]]}


def candidate_rows(data, result, exports):
    for entry in data["order"]:
        stage = result["entries"][entry].get("full_export", {})
        owners = collections.defaultdict(list)
        for path, names in exports[entry].items():
            for name in names:
                owners[name].append(path)
        for name in common.candidates(exports[entry]):
            row = {"entry": entry, "constant": name, "theories": ";".join(sorted(owners[name]))}
            for target in full.TARGETS:
                value = stage.get("candidates", {}).get(name, {}).get(target, {})
                row[target] = value.get("status", "pending")
                row[target + "_evidence"] = ";".join(value.get("evidence", []))
            yield row


def compile_rows(data, result):
    for entry in data["order"]:
        record = result["entries"][entry]
        for manifest in full.rust_manifests(record):
            value = record.get("full_compile", {}).get(manifest, {})
            yield {"entry": entry, "manifest": manifest, "stage2": value.get("stage2", ""),
                   **{p: value.get(p, {}).get("status", "not_run")
                      for p in ("stage1_compile", "optimization", "stage2_compile")}}


def performance(result):
    """Only identical scopes with six successful serializers form comparisons."""
    matched = {t: [] for t in full.TARGETS}
    front = []
    counts = collections.Counter()
    for record in result["entries"].values():
        for run in record.get("full_export", {}).get("runs", []):
            groups = collections.defaultdict(dict)
            for attempt in run["attempts"]:
                groups[(attempt.get("context"), attempt.get("batch"))][attempt.get("target")] = attempt
                counts[(attempt.get("target"), attempt["status"])] += 1
            for attempts in groups.values():
                if all(t in attempts and attempts[t]["status"] == "passed" for t in full.TARGETS):
                    if len({tuple(attempts[t]["constants"]) for t in full.TARGETS}) != 1:
                        raise ValueError("Mismatched serializer comparison scope")
                    for target in full.TARGETS:
                        matched[target].append(float(attempts[target]["seconds"]))
                    if attempts.get("frontend", {}).get("status") == "passed":
                        front.append(float(attempts["frontend"]["seconds"]))
    return {"matched_successful_scopes": len(matched["Rust"]), "shared_frontend_seconds": sum(front),
            "languages": {t: {"samples": len(times), "total_seconds": sum(times),
                             "median_seconds": statistics.median(times) if times else None,
                             "all_passed_attempts": counts[(t, "passed")],
                             "all_failed_attempts": counts[(t, "failed")]}
                          for t, times in matched.items()}}


def case_context(report, entry, names, result, exports):
    """Show actual declaration types and original source provenance for cases."""
    types = {}
    for run in result["entries"][entry].get("full_export", {}).get("runs", []):
        file = common.PROJECT / run["directory"] / "declarations.xml"
        if file.is_file():
            for node in ET.parse(file).getroot().findall("constant"):
                if node.attrib["name"] in names:
                    types[node.attrib["name"]] = node.findtext("type", "")
    rows = []
    afp = Path(result.get("environment", {}).get("afp_root", common.PROJECT / "temp/afp-Isabelle2025"))
    for name in names[:5]:
        owners = [path for path, cs in exports[entry].items() if name in cs]
        sources = "、".join(link(report, afp / "thys" / entry / path, path) for path in owners)
        rows.append([name, types.get(name, "见完整证书/异常上下文"), sources])
    return table(["请求常量", "实际 HOL 类型", "定义理论"], rows) + "\n\n" if rows else ""


def build_report(base, data, result, exports, verified=False):
    report = base / "report"
    report.mkdir(parents=True, exist_ok=True)
    boundary = common.read_json(base / "candidate-baseline.json", {})
    current_candidates = boundary.get("mode") == "current_candidates"
    status = ("当前候选的后续导出与编译审计已通过" if current_candidates else "完成审计已通过") if verified else "实验进行中；本报告不是最终交付"
    header = status + "。数据时间：" + result.get("updated", "未完成首次补扫") + "。\n\n"
    if current_candidates:
        header += ("本轮以选定的当前候选快照为前提，不补跑候选扫描。扫描状态沿用输入："
                   + json.dumps(boundary.get("scan_counts", {}), ensure_ascii=False)
                   + "；扫描完整性没有被宣称为通过。输入、摘要和 922 个会话回执见 "
                   + link(report, base / "candidate-baseline.json", "候选范围契约")
                   + "。全部 893 条目继续出现在统计中。\n\n")
    entries = []
    for entry in data["order"]:
        record = result["entries"][entry]
        stage = record.get("full_export", {})
        entries.append({"entry": entry, "scan": record["scan"]["status"],
                        "scanned_theories": len(record["scan"].get("theories", [])),
                        "expected_theories": len(data["entries"][entry]["theories"]),
                        "candidates": len(common.candidates(exports[entry])),
                        **{t: stage.get("languages", {}).get(t, "pending") for t in full.TARGETS}})
    write_csv(report / "entries.csv", list(entries[0]), entries)
    fields = ["entry", "constant", "theories"] + [k for t in full.TARGETS for k in (t, t + "_evidence")]
    write_csv(report / "candidates.csv", fields, candidate_rows(data, result, exports))
    # Declaration identities include the source path; repeated internal names
    # retain separate branch evidence while candidates.csv remains deduplicated.
    declaration_counts = {target: collections.Counter() for target in full.TARGETS}
    def declarations():
        for entry in data["order"]:
            for row in declaration_scope.rows(entry, data["entries"][entry],
                                              result["entries"][entry], exports[entry]):
                for target in full.TARGETS:
                    declaration_counts[target][row[target]] += 1
                yield row
    declaration_fields = ["entry", "theory", "constant", "context_evidence"] + fields[3:]
    write_csv(report / "declarations.csv", declaration_fields, declarations())
    crates = list(compile_rows(data, result))
    write_csv(report / "compilation.csv",
              ["entry", "manifest", "stage2", "stage1_compile", "optimization", "stage2_compile"], crates)
    counts = {"scan": dict(collections.Counter(row["scan"] for row in entries))}
    for target in full.TARGETS:
        counts[target] = dict(collections.Counter(row[target] for row in entries))
    for phase in ("stage1_compile", "optimization", "stage2_compile"):
        counts[phase] = dict(collections.Counter(row[phase] for row in crates))
    cells = {t: collections.Counter() for t in full.TARGETS}
    for row in candidate_rows(data, result, exports):
        for target in full.TARGETS:
            cells[target][row[target]] += 1
    errors = collections.Counter()
    examples = collections.defaultdict(list)
    missing = 0
    events = 0
    historical = 0
    historical_errors = collections.Counter()
    with (report / "failures.jsonl").open("w") as stream:
        for event in failure_events(base, data, result):
            key, label, explanation = category(event["status"] + "\n" + event["error"])
            event.update(category=key, category_label=label, error_sha256=full.digest(event["error"].encode()))
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            events += 1
            historical += bool(event.get("historical"))
            event_key = (event["phase"], key, event.get("target") or "", event["status"])
            errors[event_key] += 1
            if event.get("historical"):
                historical_errors[event_key] += 1
            missing += event.get("full_message_available") is False
            if len(examples[(event["phase"], key)]) < 3:
                examples[(event["phase"], key)].append(event)
    timings = performance(result)
    summary = {"generated": common.timestamp(), "completion_verified": verified, "entry_count": len(entries),
               "candidate_references": sum(r["candidates"] for r in entries),
               "source_declarations": sum(declaration_counts[full.TARGETS[0]].values()),
               "declaration_statuses": {target: dict(counts) for target, counts in declaration_counts.items()},
               "distinct_candidates": len({c for scope in exports.values() for c in common.candidates(scope)}),
               "owned_theories": sum(r["expected_theories"] for r in entries),
               "scanned_theories": sum(r["scanned_theories"] for r in entries), "phase_counts": counts,
               "candidate_statuses": {t: dict(v) for t, v in cells.items()}, "rust_crates": len(crates),
               "failure_events": events, "historical_failure_events": historical,
               "current_failure_events": events - historical,
               "missing_full_messages": missing, "performance": timings,
               "input_sha256": full.inputs(base),
               "experiment_scope": "current_candidates" if current_candidates else "full_scan",
               "inherited_scan_complete": boundary.get("scan_complete") if current_candidates else None,
               "inherited_scan_counts": boundary.get("scan_counts", {})}
    common.write_json(report / "summary.json", summary)
    error_rows = [{"phase": p, "category": c, "target": t, "status": s, "events": n,
                   "current_events": n - historical_errors[(p, c, t, s)],
                   "historical_events": historical_errors[(p, c, t, s)]}
                  for (p, c, t, s), n in sorted(errors.items())]
    write_csv(report / "failure-categories.csv", ["phase", "category", "target", "status", "events", "current_events", "historical_events"], error_rows)
    overview = [
        "# AFP 全量导出总体报告\n\n", header,
        f"本轮范围为 {len(entries)} 个 AFP 条目、{summary['owned_theories']} 个所属理论。",
        f"当前已检查 {summary['scanned_theories']} 个理论，保留 {summary['distinct_candidates']} 个不同内部全名字串",
        f"（按条目计 {summary['candidate_references']} 个候选引用）。所有条目均在 entries.csv 中占一行。"
        "不同条目中的同名声明只在名字串统计中合并；各条目独立保留候选结果与证据。"
        f"按来源理论计 {summary['source_declarations']} 个声明身份，见 declarations.csv。\n\n",
        "## 方法与口径\n\n",
        ("候选来自选定快照的全部自有常量声明，包括自动生成的辅助常量和仅有逻辑意义的定义；"
         "发现阶段没有以代码方程或可执行性筛选。已知扫描失败与未知范围原样保留。"
         if current_candidates else
         "扫描保留有代码方程及证书异常的候选；异常不代表可执行性证明。复用完整扫描，"
         "不限时补扫不完整内容，并补取旧临时文件清理后缺失的完整证书诊断。"),
        "每个常量组构造一次 Thingol 程序，供该组待处理的目标共用。整组失败继续拆分；",
        "单常量失败或必需上下文加载失败才形成候选失败证据。成功组的完整源码全部保留。"
        "进程存储耗尽时，保留原始尝试并在新进程中缩小初始常量组；"
        "六语言仍共享同组前端。无法继续拆分的资源失败保持未决并阻断阶段检查点。\n\n",
        "每个 Rust 成功导出 crate 分别进行 Stage-1 编译、既有优化器转换和 Stage-2 编译。",
        "即使 Stage-1 失败，仍尝试优化与 Stage-2；没有执行生成程序或测试运行时行为。\n\n",
        "SML 是官方 ML 目标。Go 使用 AFP 2025 的 Go_Setup，其 code_go.ML 与",
        " isabelle-go-codegen 的 08b4c92 版本逐字节相同；AFP 适配理论另有整数按位映射。",
        "Rust 数值 profile 为 Rust_BigInt_Setup；这些设置合并为六语言共用的上下文。"
        "六目标使用共同显式模块名 AFP_Code，以避免源命名空间划分制造模块依赖环；"
        "旧配置尝试单列为历史证据。\n\n",
        "## 全条目导出状态\n\n",
        table(["目标", "全部候选成功", "部分成功", "全部失败", "阻断", "完整扫描为空", "待执行"],
              [[t] + [counts[t].get(s, 0) for s in
                      ("passed", "partial", "failed", "blocked", "no_candidates", "pending")]
               for t in full.TARGETS]),
        "\n\n完整扫描为空与扫描受阻没有混为一类。整组失败尝试数不是候选失败数；",
        "候选表中的成功表示同名查询至少存在一个可导出上下文。"
        "逐声明表另按来源理论筛选实际上下文，同名的独立声明不互相代替；"
        "context_evidence 记录加载及父理论证据，六语言证据保持原始完整 batch。\n\n",
        "## 同作用域性能对比\n\n",
        f"六目标全部成功、请求常量相同的作用域有 {timings['matched_successful_scopes']} 个；",
        f"共用前端墙钟时间为 {timings['shared_frontend_seconds']:.3f} 秒。\n\n",
        table(["目标", "样本数", "准备与序列化总秒数", "中位秒数"],
              [[t, v["samples"], f"{v['total_seconds']:.3f}",
                "" if v["median_seconds"] is None else f"{v['median_seconds']:.3f}"]
               for t, v in timings["languages"].items()]),
        "\n\n目标计时包含目标投影、适配与打印；共享前端另计。固定顺序为 Rust、SML、",
        "OCaml、Haskell、Scala、Go，保留毫秒分辨率与缓存顺序效应。失败快速路径和不同",
        "拆分范围没有混入成功吞吐量。此处比较生成耗时，不比较程序运行速度。\n\n",
        "## 交付文件\n\n",
        "- [扫描细节](scan-failures.md)、[导出细节](export-failures.md)、[编译细节](compile-failures.md)。\n",
        "- [全条目表](entries.csv)、[全候选及六语言证据](candidates.csv)、[逐来源声明表](declarations.csv)。\n",
        "- [全部 Rust crate 编译表](compilation.csv)。\n",
        "- [完整失败正文及原始证据索引](failures.jsonl)、[分类统计](failure-categories.csv)、[机器统计](summary.json)。\n\n",
        "成功源码保存在本实验目录的 exports；Stage-2 源码保存在 rust-stage2。",
        "本轮新尝试的异常 XML、进程日志及补取的扫描会话数据库均保留。",
        "复用的未截断证书正文可直接取自 results.json 原记录，目录注明 message_source；",
        f"失败事件目录包含 {historical} 个已归档的执行或前置构建尝试（historical=true）；",
        "当前是否受阻由阶段检查点判定，历史故障不会因修复而删除。旧 baseline/report 仅作历史来源，",
        "不计作本轮最终结果。\n"]
    (report / "README.md").write_text("".join(overview))
    for phase, filename, title in (
            ("scan", "scan-failures.md", "候选扫描失败与诊断"),
            ("export", "export-failures.md", "六语言导出错误"),
            ("compile", "compile-failures.md", "Rust 两阶段编译错误")):
        parts = ["# " + title + "\n\n", header,
                 "按实际失败/阻断事件计数，保留重复上下文、递归拆分和已归档的执行尝试。",
                 "historical=true 的事件属于先前尝试，不代表当前检查点仍失败。",
                 "候选失败率使用 candidates.csv 的单常量证据；条目状态分母见 entries.csv。\n\n",
                 table(["类别", "目标", "状态", "当前事件", "历史事件"],
                       [[r["category"], r["target"], r["status"], r["current_events"], r["historical_events"]]
                        for r in error_rows if r["phase"] == phase]),
                 "\n\n完整异常正文及原始日志位置见 [failures.jsonl](failures.jsonl)。\n\n"]
        if phase == "compile":
            parts.extend(["## 全部 crate 的两阶段状态\n\n",
                          table(["阶段", "状态", "crate 数"], [[p, s, n]
                                for p in ("stage1_compile", "optimization", "stage2_compile")
                                for s, n in sorted(counts[p].items())]),
                          "\n\n优化失败造成的 Stage-2 阻断单列，没有伪称 Rust 编译失败。\n\n"])
        for (event_phase, key), cases in sorted(examples.items()):
            if event_phase != phase:
                continue
            label, explanation = category(cases[0]["status"] + "\n" + cases[0]["error"])[1:]
            parts.extend(["## " + label + "\n\n", explanation + "\n\n"])
            for event in cases:
                evidence = "、".join(link(report, p) for p in event["evidence"])
                suffix = "（历史尝试）" if event.get("historical") else ""
                parts.extend(["### " + event["entry"] + " / " + event["stage"] + suffix + "\n\n",
                              "目标：" + str(event.get("target") or "通用设施") + "。" + evidence + "。\n\n"])
                if event["constants"]:
                    parts.append(case_context(report, event["entry"], event["constants"], result, exports))
                # Full messages live in the catalog and original witness;
                # report excerpts only help readers locate representative cases.
                parts.append("\n".join("> " + line for line in event["error"][:1800].splitlines()) + "\n\n")
        (report / filename).write_text("".join(parts))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=common.HERE / "full")
    parser.add_argument("--preview", action="store_true",
                        help="render explicitly incomplete progress reports without taking the writer lock")
    args = parser.parse_args()
    base = args.output_dir.resolve()
    if args.preview:
        data, result, exports = full.load(base)
        summary = build_report(base, data, result, exports)
    else:
        with common.experiment_lock():
            data, result, exports = full.load(base)
            audit = common.read_json(base / "data-audit.json", {})
            if not audit.get("passed") or audit.get("input_sha256") != full.inputs(base):
                raise ValueError("A current independent completion audit is required for final reports")
            summary = build_report(base, data, result, exports, verified=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
