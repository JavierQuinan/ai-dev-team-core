"""Deterministic candidate semantics; inputs must first pass wire schema validation.

This module checks declarations, not filesystem isolation or actor identity.
Callers must enforce authorization and actual write boundaries independently.
"""
from datetime import datetime
from pathlib import PurePosixPath
import re
import unicodedata


class ContractError(ValueError):
    """A candidate contract violates a semantic invariant."""


def canonical_path(value):
    # Restrictive portable path subset; no glob, traversal, drive or UNC aliases.
    if not isinstance(value, str) or not value or value.startswith("/") or re.search(r'[\\:*?"<>|\x00-\x1f]', value):
        raise ContractError("unsafe repository path")
    parts = value.split("/")
    if any(p in ("", ".", "..") or p.endswith((" ", ".")) for p in parts):
        raise ContractError("noncanonical repository path")
    if any(p.casefold() == ".git" for p in parts):
        raise ContractError("repository metadata is outside task ownership")
    if any(p.split(".")[0].casefold() in {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))} for p in parts):
        raise ContractError("reserved repository path")
    return tuple(unicodedata.normalize("NFC", p).casefold() for p in PurePosixPath(value).parts)


def exact_path(value):
    """Validate portable syntax, but preserve spelling for declared access scope."""
    canonical_path(value)
    return tuple(value.split("/"))


def overlaps(a, b):
    return a[:len(b)] == b or b[:len(a)] == a


def check_packet(packet):
    c = packet["contract"]
    if c["freezeState"] == "frozen" and c["unresolvedDecisions"]:
        raise ContractError("unresolved material decision")
    for entry in c["ownership"]:
        canonical_path(entry["path"])
        if entry["owner"] != packet["agentRole"]:
            raise ContractError("ownership must identify assigned role")


def check_graph(packets):
    """Return deterministic topological order; reject unordered access conflicts."""
    if not packets:
        raise ContractError("empty task graph")
    by_id = {p["id"]: p for p in packets}
    if len(by_id) != len(packets):
        raise ContractError("duplicate task id")
    if len({p["runId"] for p in packets}) > 1:
        raise ContractError("mixed runs")
    ancestors = {}
    remaining = set(by_id)
    order = []
    for p in packets:
        check_packet(p)
        if not set(p["contract"]["dependencies"]) <= by_id.keys():
            raise ContractError("unknown dependency")
    while remaining:
        ready = sorted(i for i in remaining if set(by_id[i]["contract"]["dependencies"]) <= ancestors.keys())
        if not ready:
            raise ContractError("dependency cycle")
        for i in ready:
            deps = by_id[i]["contract"]["dependencies"]
            ancestors[i] = set(deps).union(*(ancestors[d] for d in deps))
            order.append(i)
            remaining.remove(i)
    for pos, i in enumerate(order):
        for j in order[pos + 1:]:
            if i in ancestors[j] or j in ancestors[i]:
                continue
            a, b = by_id[i]["contract"], by_id[j]["contract"]
            for x in a["ownership"]:
                for y in b["ownership"]:
                    if "WRITE" in (x["mode"], y["mode"]) and overlaps(canonical_path(x["path"]), canonical_path(y["path"])):
                        raise ContractError(f"unordered access conflict: {i}, {j}")
            if any(e["mode"] == "WRITE" for e in a["ownership"]) and any(e["mode"] == "WRITE" for e in b["ownership"]):
                if any(c["freezeState"] != "frozen" for c in (a, b)):
                    raise ContractError("parallel writers require frozen contracts")
    return order


def check_result(packet, result):
    if packet["id"] != result["taskId"]:
        raise ContractError("result task mismatch")
    writes = [exact_path(e["path"]) for e in packet["contract"]["ownership"] if e["mode"] == "WRITE"]
    reads = [exact_path(e["path"]) for e in packet["contract"]["ownership"]]
    for paths, allowed in ((result["changedPaths"], writes), (result["readPaths"], reads)):
        for path in paths:
            p = exact_path(path)
            if not any(p[:len(root)] == root for root in allowed):
                raise ContractError("reported path outside declared ownership")
    check_evidence(result)
    if result["status"] == "completed" and result["blockers"]:
        raise ContractError("completed result contains unresolved blockers")


def check_evidence(record):
    evidence = {e["id"]: e for e in record["evidence"]}
    if len(evidence) != len(record["evidence"]):
        raise ContractError("duplicate evidence id")
    for e in evidence.values():
        if e["kind"] == "command" and e["status"] in ("PASS", "FAIL"):
            if "exitCode" not in e or (e["exitCode"] == 0) != (e["status"] == "PASS"):
                raise ContractError("command evidence contradicts exit status")
    seen = set()
    for f in record["findings"]:
        if f["id"] in seen:
            raise ContractError("duplicate finding id")
        seen.add(f["id"])
        if not set(f["evidenceIds"]) <= evidence.keys():
            raise ContractError("missing finding evidence")


def check_approval(approval, *, run_id, action, now, trusted_actors):
    """Check scope and expiry only; trusted actors must come from authenticated policy."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ContractError("timezone-aware clock required")
    expiry = datetime.fromisoformat(approval["expiresAt"].replace("Z", "+00:00"))
    if expiry.tzinfo is None or expiry.utcoffset() is None:
        raise ContractError("timezone-aware expiry required")
    if (approval["runId"] != run_id or approval["decision"] != "approved"
            or approval["actor"] not in trusted_actors or action not in approval["scope"]
            or expiry <= now):
        raise ContractError("approval not valid for requested action")
