# Tableau workbook schema (vendored)

`twb_2026.3.0.xsd` is the official **Tableau Workbook Schema for version 2026.3**
(published 2026-10-30, source build 20263.26.1022.1645), copied unmodified from
<https://github.com/tableau/tableau-document-schemas> (`schemas/2026_3/`).
Copyright (c) 2024 Salesforce, Inc., licensed under the Apache License 2.0 (`LICENSE.txt`).

`scripts/validate_tableau_workbook.py` uses it to check the generated workbook's
structure. The schema imports two external namespaces without a file location
(`user:` attributes and `xml:base`); the validator supplies minimal stand-ins for
them at run time instead of editing this file.

Tableau's own note applies: passing the XSD is **syntactic** validation and does not
guarantee that a workbook opens; only opening it in Tableau proves that.
