# HSN data sources

- `cbic_hsn_8digit.json` — 12,604 Indian 8-digit HSN tariff lines (CBIC). Taken from the
  `hsn-code-package` npm package v3.0.0 (ISC licence, github.com/karthi-21/HSN-Code-Package),
  file `data/hsn_codes.json`. Leading zeros are dropped in that file (e.g. `1011010` = `01011010`).
- `wco_hs.csv`, `wco_sections.csv` — WCO Harmonized System 2/4/6-digit names, from
  github.com/datasets/harmonized-system (ODC Public Domain Dedication).

`supplier_finder.py` combines them into `docs/tools/supplier-finder/hsn.json` at build time.
