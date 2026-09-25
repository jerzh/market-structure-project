# Does concentration eat the paycheck?

Interactive scatter of U.S. industries (899 six-digit NAICS) — product-market concentration
(Economic Census CR4/CR8/CR20/CR50, HHI) against labor's share of revenue, with BLS labor-share
histories and QCEW 2026 Q1 employment / wages / geographic dispersion.

* `site/` — static site (plain HTML/CSS/JS + D3 v7 from CDN). Serve with `python3 -m http.server -d site`.
* `build_data.py` — rebuilds `site/data/industries.json` from Census/BLS/QCEW raw files.
* `bundle.py` — emits a single self-contained `concentration_vs_labor_share.html`.
* `survey.md` — survey of prior visualizations and why this one differs.
