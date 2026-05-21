# Evidence Model

Last reviewed: 2026-05-20

The workstation keeps three different knowledge layers:

- `references/generated/source-inventory.json`
  What official and local sources exist.
- `references/generated/source-facts.json`
  What the workstation has derived from those sources.
- `references/generated/source-evidence.json`
  Why the workstation believes those derived facts, including source key,
  locator, evidence type, stability, and rationale.
- `references/generated/official-live-worknets.json`
  The latest cached official online WorkNet snapshot, including resolution
  confidence and any live warnings from normalization.

## Usage rules

- Use `source-facts.json` when you need compact conclusions.
- Use `source-evidence.json` when you need to justify a conclusion or inspect
  how stable it is.
- Use `topic-dossiers.json` when you need operator-ready workflow framing.
- Use `coverage-audit.json` when you need to know whether a layer is merely
  available or actually high-confidence.

## Stability levels

- `high`
  Usually a normative spec, AIP, or whitepaper definition.
- `medium`
  Usually an official skill doc or official web surface that could evolve.
- `low`
  Usually editorial or guide-layer content that is useful but not normative.
