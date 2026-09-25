# Jeremy's market structure visualization project

This section is written by a human (me)!

I've always wanted to make detailed visualizations of the broader economy, since I feel like it's hard to get an appreciation for the diversity of work and production that happens unless you're willing to look at very fine granularity, like NAICS 6-digit level. There are of course risks with insisting on such fine granularity, since data quality decays the further down you go, so I'd take these numbers with a grain of salt (the caveats should all be listed clearly on the page). Regardless I think the most interesting bit is just clicking into each sub-subindustry, seeing who the big companies are, and looking at trends/seeing if they square with your personal intuition. Because we have all probably interacted with many of these sectors before, if only through the products they create.

Anyway, in the future I hope to also add markups (notoriously difficult to measure of course) and trade statistics. Maybe I'll also look into what I can find about the demographics of the employee base within each sector.

## Tab 1: Does concentration eat the paycheck?

Interactive scatter of U.S. industries (899 six-digit NAICS) — product-market concentration
(Economic Census CR4/CR8/CR20/CR50, HHI) against labor's share of value added, with BLS labor-share
histories and QCEW 2026 Q1 employment / wages / geographic dispersion.

* `docs/` — static site (plain HTML/CSS/JS + D3 v7 from CDN). Serve with `python3 -m http.server -d docs`.
* `build_data.py` — rebuilds `docs/data/industries.json` from Census/BLS/QCEW raw files.
* `bundle.py` — emits a single self-contained `concentration_vs_labor_share.html`.
* `survey.md` — survey of prior visualizations and why this one differs.

### Labor share of value added

The default vertical variable is labor's share of value added. For manufacturing,
`EC2231BASIC` supplies exact 2022 Census payroll and value-added data for the available
six-digit industries. Where a NAICS group coincides with a BEA industry, the BEA value
is used directly. Elsewhere, the site estimates the share from 2022 BEA
compensation divided by value added for the finest mapped parent industry, multiplied
by the industry's payroll/revenue relative to that group's aggregate payroll/revenue.
This is equivalent to assuming intermediate inputs are the same share of revenue across
the group, and the estimate is capped at 100%. Where that assumption fails — for example,
in pass-through industries with tiny margins — the estimate can be far off. The second Y
option remains Census payroll divided by revenue, which is exact at the six-digit detail.
BEA compensation includes benefits, while Census payroll excludes them, so the two
measures are not strictly comparable.

### Employer names (caveat / TODO)

The "Well-known large employers" line in the detail panel comes from `top_employers.json`, a
hand-curated, indicative list — Census does not disclose which firms make up the top-4 share, and
QCEW has no firm identifiers. NAICS is assigned per establishment, so a multi-line firm can
legitimately appear in several industries. The list has **not** been systematically verified.

A possible cross-check against SEC EDGAR was prototyped (`edgar_top.py`, 12 largest industries;
`edgar_crosscheck.py`, all industries — unfinished) and tabled: map NAICS→SIC via the Census
concordance, pull 10-K filers and XBRL revenue per SIC, then flag curated names whose SIC points to a
different industry or large public filers missing from the list. Limits: SIC is coarser than
6-digit NAICS, revenue ≠ employment, and private firms cannot be checked at all.
