"""quick test of invariant checks"""
from pathlib import Path
from ashwam_monitor.io.loader import load_parser_outputs, load_journals_as_dict
from ashwam_monitor.invariants.runner import run_invariant_checks

outputs, errors = load_parser_outputs(Path("data/parser_outputs_day1.jsonl"))
print(f"loaded {len(outputs)} outputs, {len(errors)} errors")

journals = load_journals_as_dict(Path("data/journals.jsonl"))
print(f"loaded {len(journals)} journals")

report = run_invariant_checks(outputs, journals)

print(f"\n=== INVARIANT REPORT ===")
print(f"Schema validity: {report.schema_validity_rate:.1%}")
print(f"Evidence validity: {report.evidence_validity_rate:.1%}")
print(f"Hallucination rate: {report.hallucination_rate:.1%}")
print(f"Contradiction rate: {report.contradiction_rate:.1%}")
print(f"\nAlerts ({len(report.alerts)}):")
for a in report.alerts:
    print(f"  {a}")
print(f"\nViolations: {len(report.violations)}")
