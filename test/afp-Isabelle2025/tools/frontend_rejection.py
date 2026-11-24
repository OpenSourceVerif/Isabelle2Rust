"""Conservative classification of sealed Isabelle2025 strict-front-end errors."""
import re
import xml.etree.ElementTree as ET

VERSION = "Isabelle2025"
RULES = "strict-rejection-2025-v1"


def classify(failure):
    """Only typed, complete native exceptions at the strict call boundary.

    Never consume process logs, excerpts, context errors or Python exceptions.
    Patterns mirror code.ML, code_thingol.ML, type.ML and goal.ML in the
    frozen version. Unrecognized variants deliberately remain unresolved.
    """
    if (failure.get("phase") != "strict_frontend"
            or failure.get("version") != VERSION
            or failure.get("exception") not in {"ERROR", "TYPE", "THM"}):
        return None
    message = failure.get("message", "")
    kind = failure["exception"]
    if kind == "ERROR":
        patterns = (
            ("wellsortedness", r"Wellsortedness error(?:\n\((?:in code equation |with dependency ).+\))?:\nType .+ not of sort .+\n.+"),
            ("code_equation_pattern", r'(?:".+" is not a constructor, on left hand side of equation|Abstraction on left hand side of equation|Variable with application on left hand side of equation|Partially applied constant ".+" on left hand side of equation|Pattern not allowed here, but constant ".+" encountered on left hand side of equation|Duplicate variables on left hand side of equation), in theorem:\n.+'),
            ("wrong_equation_head", r"Wrong head of code equation,\nexpected constant .+\n.+"),
            ("abstraction_violation", r"Abstraction violation(?:\n\((?:in code equation |with dependency ).+\))?:\nconstant .+"),
            ("equation_type", r"Type error in application: (?:incompatible operand type|operator not of function type)\n\nOperator:.+\nOperand:.+"),
            ("equation_proof", r"Proof failed\.\n.+\nThe error\(s\) above occurred for the goal statement(?: \([^\n]*\))?:\n.+"),
            ("equation_tactic", r"Tactic failed(?:\nThe error\(s\) above occurred for the goal statement(?: \([^\n]*\))?:\n.+)?"),
        )
    elif kind == "TYPE":
        patterns = (("equation_type", r"(?:Type error in application|Type unification failed|Illegal type application)(?:\n|:).+"),)
    else:
        patterns = (("equation_proof", r"Proof failed\.\n.+"),)
    for reason, pattern in patterns:
        if re.fullmatch(pattern, message, re.DOTALL):
            return reason
    return None


def native_failure(root):
    """Validate the typed exception envelope, not just its human text."""
    nodes = root.findall("failure")
    if len(nodes) != 1:
        raise ValueError("Missing/duplicate native failure envelope")
    node = nodes[0]
    if (set(node.attrib) != {"phase", "version", "exception"}
            or len(node) != 2 or [n.tag for n in node] != ["message", "error"]
            or any(n.attrib or len(n) for n in node)
            or not node.findtext("message") or not node.findtext("error")):
        raise ValueError("Invalid native failure envelope")
    return dict(node.attrib, message=node.findtext("message"), error=node.findtext("error"))


def export_failure(path):
    root = ET.parse(path).getroot()
    if root.get("target") != "frontend" or root.get("stage") != "frontend":
        return None
    try:
        return classify(native_failure(root))
    except ValueError:
        return None
