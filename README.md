# Evidence Ledger

**Version:** 0.1  
**Status:** experimental

Evidence Ledger separates **observations, reports, documentary records, interpretations, inferences, and repeated claims** without collapsing them into one generic evidence bucket.

Its central rule is simple:

> **Evidence type is part of the evidence.**

A source can support a claim without being an observation. An inference can be reasonable without becoming a fact. A repeated claim can remain dependent on an earlier source instead of masquerading as independent corroboration.

## What it records

A ledger contains:

- research claims
- sources
- evidence entries
- evidence type
- whether an entry supports, contradicts, contextualizes, or remains unclear toward a claim
- independence status
- derivation links between evidence entries
- notes and source metadata

Evidence types:

- `observation`
- `firsthand-report`
- `secondhand-report`
- `documentary-record`
- `interpretation`
- `inference`
- `repetition`

Evidential directions:

- `supports`
- `contradicts`
- `context`
- `unclear`

Independence states:

- `independent`
- `dependent`
- `unknown`

None of these fields is an automatic truth score.

## Quick start

```bash
python evidence_ledger.py new ledger.json --title "North Reach warning"

python evidence_ledger.py claim ledger.json \
  "A warning note existed before the disappearance."

python evidence_ledger.py source ledger.json "1904 station log" \
  --kind primary --date 1904-11-03

python evidence_ledger.py entry ledger.json C001 \
  "The reviewed station log contains no warning note." \
  --type documentary-record \
  --stance contradicts \
  --independence independent \
  --source S001

python evidence_ledger.py entry ledger.json C001 \
  "A later folklore book repeats the warning-note story." \
  --type repetition \
  --stance supports \
  --independence dependent \
  --derived-from E002

python evidence_ledger.py audit ledger.json
python evidence_ledger.py render ledger.json -o report.md
python evidence_ledger.py matrix ledger.json -o matrix.md
python evidence_ledger.py mermaid ledger.json -o ledger.mmd
```

## Outputs

Evidence Ledger can produce:

- plain JSON
- a Markdown report
- a claim-by-evidence-type matrix
- a Mermaid provenance graph
- an audit report for missing or suspicious provenance structure

## Audit behavior

The audit is deliberately structural, not a fact checker.

It can flag things such as:

- an inference or interpretation with no recorded basis
- a repeated claim marked independent
- an entry with neither a source nor a derivation link

A flag does **not** mean the evidence is false. It means the ledger cannot currently see the bridge.

## Example

The fictional example in [`examples/demo.json`](examples/demo.json) shows several evidence classes touching the same claim without being flattened together.

See:

- [`examples/demo.md`](examples/demo.md)
- [`examples/demo.mmd`](examples/demo.mmd)

## What Evidence Ledger does not do

Evidence Ledger does not rank a firsthand report as automatically true.

It does not turn interpretation into observation.

It does not count dependent repetitions as independent corroboration.

It does not convert source age, evidence type, or quantity into a hidden credibility score.

It records the structure so a researcher can inspect what kind of support actually exists.

## Tests

```bash
python -m unittest discover -s tests -v
```

## License and reuse

**No reuse license has been granted.**

This public build is available for inspection and development by its maintainers. Do not assume that public visibility grants permission to copy, redistribute, modify, sell, incorporate, or relicense the code or documentation.

See [`COPYRIGHT.md`](COPYRIGHT.md).

## Working principle

A pile of statements is not yet an evidence structure.
