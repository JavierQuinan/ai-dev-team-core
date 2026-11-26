"""Candidate contract tests; not runtime enforcement or provider evidence."""
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/candidate-v0.1.json").read_text(encoding="utf-8"))


def validator(name):
    return Draft202012Validator(
        {**SCHEMA, "$ref": f"#/$defs/{name}"},
        format_checker=FormatChecker(),
    )


def fixture(name):
    return json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))


def check_freeze(packet):
    contract = packet["contract"]
    if contract["freezeState"] == "frozen" and contract["unresolvedDecisions"]:
        raise ValueError("unresolved material decision")


class ContractTests(unittest.TestCase):
    def test_schema_is_valid(self):
        Draft202012Validator.check_schema(SCHEMA)

    def test_valid_packet(self):
        packet = fixture("task-packet.valid.json")
        validator("TaskPacket").validate(packet)
        check_freeze(packet)

    def test_false_freeze(self):
        packet = fixture("task-packet.false-freeze.json")
        validator("TaskPacket").validate(packet)
        with self.assertRaises(ValueError):
            check_freeze(packet)

    def test_unknown_field(self):
        packet = fixture("task-packet.valid.json")
        packet["unexpected"] = True
        self.assertFalse(validator("TaskPacket").is_valid(packet))

    def test_negative_budget(self):
        packet = fixture("task-packet.valid.json")
        packet["tokenBudget"] = -1
        self.assertFalse(validator("TaskPacket").is_valid(packet))

    def test_incompatible_version(self):
        packet = fixture("task-packet.valid.json")
        packet["schemaVersion"] = "2.0.0"
        self.assertFalse(validator("TaskPacket").is_valid(packet))


if __name__ == "__main__":
    unittest.main()
