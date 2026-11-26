import copy
from datetime import datetime, timezone
import unittest

from core_semantics import (
    ContractError, canonical_path, check_approval, check_evidence,
    check_graph, check_packet, check_result,
)
from test_contracts import fixture


class SemanticTests(unittest.TestCase):
    def packet(self):
        return fixture("task-packet.valid.json")

    def pair(self):
        a = self.packet()
        b = copy.deepcopy(a)
        b["id"] = "task-2"
        b["agentRole"] = "backend-engineer"
        b["contract"]["ownership"] = [
            {"path": "src/api", "mode": "WRITE", "owner": "backend-engineer"}
        ]
        return a, b

    def test_independent(self):
        a, b = self.pair()
        self.assertEqual(check_graph([b, a]), ["task-1", "task-2"])

    def test_overlap(self):
        a, b = self.pair()
        b["contract"]["ownership"][0]["path"] = "SRC/UI/components"
        with self.assertRaises(ContractError):
            check_graph([a, b])

    def test_serialized_overlap(self):
        a, b = self.pair()
        b["contract"]["ownership"][0]["path"] = "src/ui"
        b["contract"]["dependencies"] = ["task-1"]
        self.assertEqual(check_graph([b, a]), ["task-1", "task-2"])

    def test_cycle(self):
        a, b = self.pair()
        a["contract"]["dependencies"] = ["task-2"]
        b["contract"]["dependencies"] = ["task-1"]
        with self.assertRaises(ContractError):
            check_graph([a, b])

    def test_missing_dependency(self):
        a = self.packet()
        a["contract"]["dependencies"] = ["missing"]
        with self.assertRaises(ContractError):
            check_graph([a])

    def test_duplicate_task(self):
        a = self.packet()
        with self.assertRaises(ContractError):
            check_graph([a, a])

    def test_mixed_runs(self):
        a, b = self.pair()
        b["runId"] = "other"
        with self.assertRaises(ContractError):
            check_graph([a, b])

    def test_parallel_unfrozen(self):
        a, b = self.pair()
        b["contract"]["freezeState"] = "unfrozen"
        with self.assertRaises(ContractError):
            check_graph([a, b])

    def test_false_freeze(self):
        with self.assertRaises(ContractError):
            check_packet(fixture("task-packet.false-freeze.json"))

    def test_read_write_conflict(self):
        a, b = self.pair()
        b["contract"]["ownership"][0].update(path="src/ui", mode="READ")
        with self.assertRaises(ContractError):
            check_graph([a, b])

    def test_unsafe_paths(self):
        for path in ("../x", "/x", "C:/x", "src//x", "src/../x", "src/*", "src/NUL.txt", "src/x."):
            with self.subTest(path=path), self.assertRaises(ContractError):
                canonical_path(path)

    def test_wrong_owner(self):
        a = self.packet()
        a["contract"]["ownership"][0]["owner"] = "other"
        with self.assertRaises(ContractError):
            check_packet(a)

    def test_evidence_mismatch(self):
        record = {"evidence": [{"id": "e1", "kind": "command", "status": "PASS", "exitCode": 1}], "findings": []}
        with self.assertRaises(ContractError):
            check_evidence(record)

    def test_missing_evidence(self):
        with self.assertRaises(ContractError):
            check_evidence({"evidence": [], "findings": [{"id": "f1", "evidenceIds": ["e1"]}]})

    def test_out_of_scope_write(self):
        a = self.packet()
        result = {"taskId": a["id"], "changedPaths": ["src/api/index.ts"], "readPaths": [],
                  "evidence": [], "findings": [], "status": "completed", "blockers": []}
        with self.assertRaises(ContractError):
            check_result(a, result)

    def test_approval_scope_expiry_actor(self):
        now = datetime(2026, 11, 26, tzinfo=timezone.utc)
        a = {"runId": "run-1", "actor": "maintainer", "decision": "approved",
             "scope": ["merge"], "expiresAt": "2026-11-27T00:00:00Z"}
        args = dict(run_id="run-1", action="merge", now=now, trusted_actors={"maintainer"})
        check_approval(a, **args)
        for change in ({"actor": "agent"}, {"scope": ["deploy"]}, {"runId": "other"},
                       {"expiresAt": "2026-11-26T00:00:00Z"}, {"decision": "pending"}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                check_approval({**a, **change}, **args)


if __name__ == "__main__":
    unittest.main()
