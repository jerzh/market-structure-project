# Survey: U.S. labor share vs. market concentration visualizations

## Scope and verification notes

This is a landscape survey rather than a replication of any one paper. “Labor
share” is not uniform across sources: it can mean payroll/value added,
compensation/value added, compensation/GDP, or labor compensation as a share of
the total dollar cost of output. “Concentration” can mean a sales CR4/CR8/CR20,
HHI, a top-firm share, or (for labor markets) an employment/wage HHI. Those
measures should not be silently substituted for one another.

* **Fetched** means I fetched the linked page, API metadata, or data file during
  this survey.
* **Search-verified** means a web search returned the cited page and the
  relevant description, but a full page fetch was not possible (typically a
  large PDF or a blocked raw-download endpoint).
* Dates and coverage below describe the cited source, not necessarily the
  latest vintage.

## Notable examples

### 1. Autor, Dorn, Katz, Patterson & Van Reenen — *The Fall of the Labor
Share and the Rise of Superstar Firms*

* **URL:** [QJE article](https://doi.org/10.1093/qje/qjaa004) (Fetched);
  [NBER working paper 23396](https://www.nber.org/system/files/working_papers/w23396/w23396.pdf)
  (Search-verified).
* **What is plotted:** Static figures relate rising within-industry sales
  concentration to falling labor share. Concentration is sales CR4 and CR20
  (with HHI robustness); labor share is payroll/value added in the broad
  Economic Census analysis, with payroll/sales and a broader compensation
  measure in manufacturing. The paper also shows sales and employment shares
  of the largest firms and reallocation decompositions.
* **Data and granularity:** U.S. Economic Census establishment/firm microdata,
  generally 1982–2016 in the QJE version (earlier working-paper figures often
  end in 2012), six large sectors, and time-consistent four-digit industries
  (the related paper reports 676 industries, 388 manufacturing).
* **Interaction:** Static PDF/article figures; no public point-level interactive
  explorer.
* **Shortcomings:** Census microdata are confidential, so users cannot freely
  reproduce or drill into every point. Census years are five years apart;
  industry concordance is nontrivial; imports and foreign producers require
  special treatment; coverage is not a complete annual all-sector panel. It is
  the clearest direct precedent, but not a public, animated data product.

### 2. De Loecker & Eeckhout — *The Rise of Market Power and the
Macroeconomic Implications*

* **URL:** [QJE article](https://doi.org/10.1093/qje/qjz041) (Fetched);
  [NBER working paper 23687](https://www.nber.org/papers/w23687)
  (Search-verified).
* **What is plotted:** Time series and distributions of firm markups and
  profits, including the upper-tail/aggregate markup rise from the early
  1980s through 2016. Labor share is discussed as a macro implication, but the
  main figures are not a labor-share-by-industry versus concentration scatter.
  Markup is a price/marginal-cost concept, not CR4 or HHI.
* **Data and granularity:** Publicly traded U.S. firms in Compustat,
  approximately 1955–2016, with firm and industry aggregations; private firms
  are not comprehensively observed.
* **Interaction:** Static paper figures.
* **Shortcomings:** Markups are not concentration ratios, and the sample
  excludes most private firms. The paper does not provide a public interactive
  that links each industry's markup path to a labor-share path or to Census
  concentration ratios.

### 3. Grullon, Larkin & Michaely — *Are U.S. Industries Becoming More
Concentrated?*

* **URL:** [Review of Finance article](https://doi.org/10.1093/rof/rfz007)
  (Search-verified); [author PDF](https://www.stern.nyu.edu/sites/default/files/assets/documents/Michaely%2C%20Roni%20-%20Are%20US%20Industries%20Becoming%20More%20Concentrated.pdf)
  (Search-verified).
* **What is plotted:** HHI, top-four firm share, and related concentration
  measures, alongside profit margins, M&A outcomes, and stock returns. The
  labor-share question is background/context rather than a consistently
  plotted second axis.
* **Data and granularity:** CRSP/Compustat merged data, publicly traded
  U.S.-incorporated firms, roughly 1972–2014, with industry-level panels and
  robustness checks involving alternative concentration measures and private
  firms.
* **Interaction:** Static paper figures.
* **Shortcomings:** Public-firm coverage and industry definitions can make
  concentration differ from Economic Census measures; market shares are not
  necessarily the same universe as Census sales shares. No public interactive
  joins the paper's concentration series to BLS/BEA labor shares.

### 4. Barkai — *Declining Labor and Capital Shares*

* **URL:** [Journal of Finance article](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12909)
  (Search-verified); [Stanford paper PDF](https://www.gsb.stanford.edu/sites/gsb/files/jmp_simcha-barkai_updated.pdf)
  (Search-verified).
* **What is plotted:** Static time series for labor, capital, and pure-profit
  shares in the U.S. nonfinancial corporate sector. Industry evidence links
  increases in concentration with declines in labor share, but the headline
  visual is not an interactive industry scatter.
* **Data and granularity:** National accounts and firm/industry data, mainly
  nonfinancial corporations over the roughly 1980–2014/30-year period studied.
  Capital costs are constructed from required returns and capital stocks; labor
  share is compensation relative to gross value added.
* **Interaction:** Static paper figures.
* **Shortcomings:** Aggregate sector framing and constructed capital costs make
  it difficult to map directly onto a Census CR4/HHI series. It does not offer
  an open, point-level industry explorer or geographic detail.

### 5. Gutiérrez & Philippon — *From Good to Bad Concentration?*

* **URL:** [NBER working paper 25983 (PDF)](https://www.nber.org/system/files/working_papers/w25983/revisions/w25983.rev0.pdf)
  (Search-verified); [author copy](https://pages.stern.nyu.edu/~tphilipp/papers/CGP_NBER_WP.pdf)
  (Search-verified).
* **What is plotted:** Figure 1 is a compact four-panel static dashboard:
  cumulative change in sales CR8, profit rate, labor share, and net investment.
  Labor share is compensation of employees divided by gross value added.
  Concentration is an industry sales-weighted CR8.
* **Data and granularity:** Economic Census concentration (SIC-4 before 1992,
  NAICS-6 after 1997, consistently defined industries where possible),
  FRED/BEA national-account series, and industry data; concentration comparisons
  cover the past roughly 40 years, with Census observations every five years.
* **Interaction:** Static PDF figures.
* **Shortcomings:** The labor-share panel is aggregate rather than a directly
  linked point for every industry and year. Different industry coding systems
  and an imputed 1992–1997 change complicate a clean time animation. No
  geographic or establishment-level layer is offered.

### 6. Sinclair — *The Monopolists Are Winning*

* **URL:** [Interactive visualization](https://sinclairtarget.com/concentration/)
  (Fetched/search-verified); [D3 source repository](https://github.com/sinclairtarget/the-monopolists-are-winning-interactive)
  (Search-verified).
* **What is plotted:** Interactive scatter/bubble views of Census sales CR4:
  baseline-versus-later concentration for NAICS sectors and then more detailed
  industries. Bubble area represents industry revenue; tooltips and filtering
  reveal industries moving toward greater concentration.
* **Data and granularity:** U.S. Economic Census, principally 2002 and 2012,
  12 NAICS sectors and drill-down industry data. It uses top-four sales shares,
  not labor share or HHI.
* **Interaction:** Yes—D3 interactive scatter/bubbles and drill-down.
* **Shortcomings:** It is the strongest interaction precedent for concentration
  but has no labor-share variable, only a small number of Census years, an older
  data vintage, and no QCEW wages, establishments, or maps. Its comparison
  design emphasizes two endpoints rather than animated industry trajectories.

### 7. Open Markets Institute — *America's Concentration Crisis*

* **URL:** [Interactive report](https://concentrationcrisis.openmarketsinstitute.org/)
  (Fetched/search-verified); [publication page](https://www.openmarketsinstitute.org/publications/americas-concentration-crisis)
  (Search-verified).
* **What is plotted:** Industry- and market-specific concentration charts,
  often top-firm or top-parent-company shares, with consumer-facing examples
  such as health care and branded products. It is about concentration and
  monopoly power, not labor share.
* **Data and granularity:** IBISWorld data purchased by Open Markets, with
  selected national and regional markets and varying industry/market
  definitions; the report dates to 2018–2019.
* **Interaction:** Interactive web report with chart navigation; not a general
  downloadable time-series explorer.
* **Shortcomings:** Licensed/private source, heterogeneous market definitions,
  weak reproducibility, and no harmonized labor-share series. It is useful for
  communicating market structure but not for a NAICS-consistent CR4-versus-
  labor-share panel.

### 8. Federal Reserve Bank of St. Louis — *Declining Labor Share and U.S.
Industries*

* **URL:** [FRED blog post](https://www.stlouisfed.org/on-the-economy/2019/december/declining-labor-share-us-industries)
  (Search-verified); related [FRED post](https://fredblog.stlouisfed.org/2019/08/capitals-gain-is-lately-labours-loss/)
  (Search-verified).
* **What is plotted:** Aggregate employee compensation/GDP and an industry
  decomposition for eight major industries. The post emphasizes compensation
  of employees as a fraction of industry value added and compares snapshots
  beginning in 1987, with later years.
* **Data and granularity:** BEA industry/national accounts, broad major
  industries, roughly 1987 onward for the decomposition.
* **Interaction:** Blog charts use FRED-style interactive graphing in places,
  but the article's industry comparison is principally a static explanatory
  graphic.
* **Shortcomings:** No product-market concentration variable, no NAICS
  four-/six-digit view, and no linked firm or geographic layer. It is a useful
  labor-share precedent but cannot answer whether the industries with the
  largest CR4 increases had the largest labor-share declines.

### 9. New York Times — *“Superstar Firms” May Have Shrunk Workers' Share of
Income*

* **URL:** [NYT article](https://www.nytimes.com/2017/03/08/business/economy/labor-share-economic-output.html)
  (Search-verified).
* **What is plotted:** A journalistic explanation of the Autor et al. result,
  pairing the falling worker share with examples of large firms and industry
  concentration. Related NYT concentration graphics (including the later
  top-two market-share chart) compare early-2000s versus current top-company
  shares across categorical industries.
* **Data and granularity:** Draws on Autor et al. and Census-style industry
  concentration; selected industries and endpoints rather than a complete
  NAICS panel.
* **Interaction:** Mostly static/explanatory graphics; the article is
  publisher-controlled and may be paywalled.
* **Shortcomings:** Limited reproducibility and point-level data access; no
  downloadable labor-share-by-industry and concentration-by-industry join;
  selected examples can overemphasize famous markets.

### 10. Our World in Data — Labor share of GDP

* **URL:** [OWID Grapher](https://ourworldindata.org/grapher/labor-share-of-gdp?tab=chart)
  (Fetched).
* **What is plotted:** Interactive country/region time series of labor share
  of GDP, percent of output paid as compensation plus the labor component of
  self-employment.
* **Data and granularity:** ILO modelled estimates via the UN SDG dataset,
  country/region aggregate, 2004–2025 in the fetched page.
* **Interaction:** Yes—time-series, country selection, download/embed controls.
* **Shortcomings:** No U.S. industry/NAICS detail and no product-market
  concentration measure. Its self-employment adjustment is conceptually
  different from BLS industry labor share or Economic Census payroll/value
  added, so it should not be mixed without documentation.

### 11. BLS Industry Productivity Viewer

* **URL:** [Industry Productivity Viewer](https://data.bls.gov/apps/industry-productivity-viewer/home.htm)
  (Fetched/search-verified); [BLS Industry Productivity documentation](https://www.bls.gov/help/one_screen/ip.htm)
  (Search-verified).
* **What is plotted:** Interactive annual charts can select labor share
  (percent), labor compensation, hours, output, labor productivity, and total
  factor productivity. It supports comparisons among industries.
* **Data and granularity:** BLS Industry Productivity series for selected
  2-, 3-, 4-, 5-, and 6-digit NAICS industries; annual measures generally from
  1987 onward. The viewer advertises a full downloadable XLSX dataset.
* **Interaction:** Yes—measure, industry, and duration selectors plus chart
  creation.
* **Shortcomings:** No Economic Census CR4/CR20/HHI layer, no firm identities,
  no QCEW geography, and industry availability varies. TFP coverage is much
  narrower than the labor-share coverage (not all NAICS industries).

### 12. Census Economic Census concentration tables and data.census.gov

* **URLs:** [2017 API group: `EC1700SIZECONCEN`](https://api.census.gov/data/2017/ecnsize/groups/EC1700SIZECONCEN.html)
  (Fetched); [2022 API group: `EC2200SIZECONCEN`](https://api.census.gov/data/2022/ecnsize/groups/EC2200SIZECONCEN.html)
  (Fetched); [2017 Census table](https://data.census.gov/table/ECNSIZE2017.EC1700SIZECONCEN)
  (Search-verified); [2022 Census table](https://data.census.gov/table/ECNSIZE2022.EC2200SIZECONCEN)
  (Search-verified); [2022 FTP directory](https://www2.census.gov/programs-surveys/economic-census/data/2022/sector00/)
  (Fetched).
* **What is plotted/available:** Tables expose concentration-ratio records
  identified by `CONCENFI`/`CONCENFI_LABEL`, the largest-firm sales/revenue
  percentage `VAL_PCT`, and HHI `HHI` (plus flags such as `HHI_F` and
  `VAL_PCT_F`). `data.census.gov` supports table and chart views and
  downloads.
* **Data and granularity:** U.S. Economic Census 2017 and 2022, 2- through
  6-digit NAICS for most in-scope sectors; the fetched table notes say
  agriculture (11) and management of companies (55) are exceptions. The
  universe is payroll establishments/firms in the covered sectors. “Sector
  00” is a multi-sector presentation, not a real NAICS sector.
* **Interaction:** data.census.gov is interactive; FTP files are static
  downloads; API metadata is machine-readable.
* **Shortcomings:** It contains no labor-share series. Census concentration is
  released only in Economic Census vintages, not annually. NAICS revisions
  complicate comparisons. Suppression/imputation flags matter. The Census API
  **data requests currently require an API key** (a no-key request fetched in
  this survey returned “Missing Key”), while group metadata endpoints and FTP
  ZIP files are downloadable without an API key. Thus the data are public, but
  “public API without a key” is no longer a safe assumption.

## Public datasets for a new product

### (a) Labor share by industry

#### BLS Industry Productivity (best direct match for annual NAICS panels)

* Landing page: [BLS Industry Productivity](https://www.bls.gov/productivity/)
  and [viewer](https://data.bls.gov/apps/industry-productivity-viewer/home.htm).
* Raw-series documentation: [`ip.txt`](https://download.bls.gov/pub/time.series/ip/ip.txt);
  series definitions: [`ip.series`](https://download.bls.gov/pub/time.series/ip/ip.series);
  measure definitions: [`ip.measure`](https://download.bls.gov/pub/time.series/ip/ip.measure).
* Exact measure identifier **verified in the fetched/search-returned
  `ip.measure` listing:** `L03` = “Labor share (Percentage)”; `L02` =
  “Labor compensation (Millions of current dollars)”. The BLS series
  schema includes `sector_code`, seven-character padded `industry_code`,
  `measure_code`, `duration_code`, and `area_code`.
* Representative exact series **fetched and verified on FRED, sourced from
  BLS Industry Productivity:** `IPUEN33411L030000000`, “Labor Share for
  Manufacturing: Computer and Peripheral Equipment Manufacturing (NAICS
  33411) in the United States”; annual, percent, not seasonally adjusted.
  FRED page: https://fred.stlouisfed.org/series/IPUEN33411L030000000.
* BLS documentation says annual industry productivity data cover selected
  2- through 6-digit NAICS industries from 1987 forward. Labor share is
  particularly usable because the viewer directly exposes it; however,
  coverage is “selected industries,” not every NAICS code.
* BLS total factor productivity tables are complementary, not a universal
  substitute: the documentation says TFP is available for a much smaller
  set, including 86 four-digit manufacturing industries, air transportation,
  and line-haul railroads. Use TFP/cost-share tables when the analysis needs
  productivity decomposition, but use the IP `L03` series for the broadest
  labor-share panel.

#### BEA GDP by Industry (best accounting cross-check)

* Landing page: [BEA GDP by Industry](https://bea.gov/data/gdp/gdp-industry);
  [interactive tables](https://apps.bea.gov/iTable/iTable.cfm?isuri=&reqid=150&step=2);
  [table guide](https://www.bea.gov/resources/guide-interactive-gdp-industry-accounts-tables).
* Exact dataset/table identifiers **verified in the fetched BEA guide and API
  documentation:** dataset `GDPbyIndustry`; `TableID=1` “Value Added by
  Industry”; `TableID=6` “Components of Value Added by Industry”; and
  `TableID=7` “Components of Value Added by Industry as a Percentage of Value
  Added.” The guide defines compensation of employees, gross operating
  surplus, taxes, and value added.
* A conventional BEA labor share is compensation of employees / value added.
  BEA is conceptually preferable when the denominator must be value added and
  compensation should include wages, salaries, and supplements, but industry
  detail, revisions, and current/real-dollar choices must be documented.
* The BEA API generally requires a BEA key; iTable and downloadable tables
  are public. This differs from Census FTP access.

### (b) Concentration by NAICS

#### Census Economic Census

* Exact table IDs **verified by fetched Census metadata/table pages:** 
  `EC1700SIZECONCEN` (2017) and `EC2200SIZECONCEN` (2022), both in dataset
  `ECNSIZE` for “Selected Sectors: Concentration of Largest Firms for the
  U.S.”
* Exact fields **verified in the fetched group JSON/HTML:** `CONCENFI`,
  `CONCENFI_LABEL`, `VAL_PCT`, `HHI`, `HHI_F`, and `VAL_PCT_F`; NAICS fields
  are `NAICS2017`/`NAICS2017_LABEL` and `NAICS2022`/`NAICS2022_LABEL`,
  respectively.
* Download options: the 2017 FTP ZIP
  `https://www2.census.gov/programs-surveys/economic-census/data/2017/sector00/EC1700SIZECONCEN.zip`
  was downloaded successfully without a key; the 2022 equivalent is listed
  in the fetched FTP directory at
  `https://www2.census.gov/programs-surveys/economic-census/data/2022/sector00/EC2200SIZECONCEN.zip`.
  The Census dissemination page confirms FTP downloads are the complete
  table route. API metadata is keyless; API data calls now require a key.
* Concentration-ratio codes should be read from `CONCENFI_LABEL` rather than
  hard-coded assumptions about which top-firm ranks are present. The
  `VAL_PCT` field is explicitly the largest-firm sales/shipments/revenue
  percentage; `HHI` is explicitly the sales/shipments/revenue HHI.

#### QCEW as the geographic/labor-market companion

* [QCEW downloadable data](https://www.bls.gov/cew/downloadable-data-files.htm)
  and [CSV slices](https://www.bls.gov/cew/additional-resources/open-data/csv-data-slices.htm)
  were search-verified. NAICS files are available from 1990 onward (with
  reconstructed early years), and QCEW publishes establishments, employment,
  wages, and related measures by industry and geography.
* QCEW does **not** directly provide product-market firm sales CR4/HHI.
  It can add annual wages, establishment counts, employment, and geographic
  dispersion to a Census concentration/labor-share product. With EIN-based
  records where permitted, researchers can also construct labor-market
  employment or wage HHI; see the BLS
  [QCEW labor-market concentration article](https://www.bls.gov/opub/mlr/2024/article/measuring-labor-market-concentration-using-the-qcew.htm)
  (search-verified).

## What appears to be missing

No public visualization found in this survey combines all of the following in
one reproducible interface:

1. Census product-market concentration (CR4/CR8/CR20 and/or HHI);
2. BLS `L03` or BEA compensation/value-added labor share;
3. consistent NAICS crosswalks across Census vintages;
4. an industry-level scatter with point labels, sector filters, and time
   animation; and
5. QCEW wages, establishment counts, employment, and geographic dispersion.

The most promising design is therefore a **sector/industry small-multiple and
scatter explorer**:

* x-axis: concentration level or change (CR4/CR8/HHI), with a switch for
  sales-weighted versus unweighted aggregation;
* y-axis: BLS labor share (`L03`) or BEA compensation/value added;
* animation: Census years (with explicit NAICS concordance and missing-year
  treatment), plus an optional annual BLS/BEA labor-share trace between Census
  concentration observations;
* point size: industry value added, sales, employment, or QCEW establishments;
* color/filter: NAICS sector, industry depth, manufacturing/services, and
  Census suppression/imputation flags;
* linked side panel: QCEW annual wages, average weekly wage, establishments,
  employment, and maps of geographic concentration;
* separate toggle for **product-market HHI** versus **labor-market employment/
  wage HHI** so users do not confuse seller concentration with monopsony;
* optional import-adjusted concentration for manufacturing, with clear notes
  that imports are not firm-resolved in the Census measure.

Important methodological guardrails are to label the denominator (sales,
value added, GDP, or total production cost), preserve the difference between
payroll and total compensation, expose Census flags/suppression, and avoid
implying causality from a descriptive scatter. The interaction should make
vintage gaps and changing NAICS definitions visible rather than interpolating
them away.

## Fetch record (selected authoritative checks)

* Fetched: Autor QJE landing page, Sinclair visualization, Open Markets
  visualization, BLS viewer, FRED representative BLS series,
  Census 2017/2022 concentration group metadata, Census 2022 FTP directory,
  OWID Grapher, and the Federal Reserve concentration note.
* Fetched/downloaded: 2017
  `EC1700SIZECONCEN.zip` FTP file (ZIP containing `EC1700SIZECONCEN.dat`).
* Search-verified or cited from search snippets: raw BLS `ip.measure`/`ip.series`
  definitions (the raw endpoint returned HTTP 403 to this environment),
  BEA API table mapping, the academic PDFs, and the QCEW documentation pages.
* Direct Census API data requests for 2017 and 2022, without a key, returned
  the official “Missing Key” page. This is why the report distinguishes
  keyless metadata/FTP access from API data access.
