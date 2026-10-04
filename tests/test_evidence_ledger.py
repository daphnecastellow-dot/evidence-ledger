import tempfile
import unittest
from pathlib import Path

from evidence_ledger import (
    LedgerError,
    add_claim,
    add_entry,
    add_source,
    audit,
    load,
    new_project,
    render_markdown,
    render_matrix,
    render_mermaid,
    save,
)


class EvidenceLedgerTests(unittest.TestCase):
    def test_type_stance_and_independence_are_separate(self):
        data = new_project("Ledger")
        cid = add_claim(data, "The signal occurred.")
        sid = add_source(data, "Harbor log", "primary", "1904-11-03")
        eid = add_entry(
            data, cid, "The log records three rings.", "documentary-record",
            "supports", "independent", [sid],
        )
        entry = data["entries"][0]
        self.assertEqual(eid, "E001")
        self.assertEqual(entry["type"], "documentary-record")
        self.assertEqual(entry["stance"], "supports")
        self.assertEqual(entry["independence"], "independent")

    def test_repetition_can_preserve_dependency(self):
        data = new_project("Dependency")
        cid = add_claim(data, "A warning note existed.")
        original = add_entry(
            data, cid, "A 1978 book reports a warning note.", "secondhand-report",
            "supports", "unknown",
        )
        repeat = add_entry(
            data, cid, "A later article repeats the warning-note story.", "repetition",
            "supports", "dependent", derived_from=[original],
        )
        self.assertEqual(data["entries"][1]["derived_from"], [original])
        self.assertEqual(data["entries"][1]["id"], repeat)

    def test_audit_flags_missing_bridges_without_declaring_falsehood(self):
        data = new_project("Audit")
        cid = add_claim(data, "Weather caused the event.")
        add_entry(
            data, cid, "Therefore the storm caused the disappearance.", "inference",
            "supports", "unknown",
        )
        findings = audit(data)
        self.assertTrue(any("no recorded evidence basis" in item for item in findings))

    def test_rejects_unknown_derivation(self):
        data = new_project("Bad")
        cid = add_claim(data, "Claim")
        with self.assertRaises(LedgerError):
            add_entry(
                data, cid, "Derived statement", "interpretation", "supports",
                "dependent", derived_from=["E999"],
            )

    def test_round_trip_and_renderers(self):
        data = new_project("Render")
        cid = add_claim(data, "The bell rang.")
        sid = add_source(data, "Station log", "primary")
        add_entry(
            data, cid, "The log records a bell.", "documentary-record",
            "supports", "independent", [sid],
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.json"
            save(path, data)
            loaded = load(path)
        self.assertIn("documentary-record", render_markdown(loaded))
        self.assertIn("C001", render_matrix(loaded))
        self.assertIn("source for", render_mermaid(loaded))


if __name__ == "__main__":
    unittest.main()
