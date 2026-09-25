"""Build site/data/industries.json from Economic Census concentration tables,
BLS Industry Productivity labor-share series and QCEW 2026Q1.

Run from /home/ubuntu/qcew.
"""
import json
import math
import os
import pandas as pd

OUT = "docs/data/industries.json"
# Hand-curated, indicative list of well-known large employers per 6-digit industry (not a Census product).
TOP_EMPLOYERS = json.load(open("top_employers.json")) if os.path.exists("top_employers.json") else {}

SECTOR_NAMES = {
    "11": "Agriculture", "21": "Mining & oil/gas", "22": "Utilities", "23": "Construction",
    "31-33": "Manufacturing", "42": "Wholesale trade", "44-45": "Retail trade",
    "48-49": "Transportation & warehousing", "51": "Information", "52": "Finance & insurance",
    "53": "Real estate & rental", "54": "Professional & technical services",
    "55": "Management of companies", "56": "Administrative & waste services",
    "61": "Educational services", "62": "Health care & social assistance",
    "71": "Arts, entertainment & recreation", "72": "Accommodation & food services",
    "81": "Other services",
}


def sector_of(code: str) -> str:
    two = code[:2]
    if two in ("31", "32", "33"):
        return "31-33"
    if two in ("44", "45"):
        return "44-45"
    if two in ("48", "49"):
        return "48-49"
    return two


def num(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- Economic Census
def load_ec(path, naics_col, year):
    df = pd.read_csv(path, sep="|", dtype=str, keep_default_na=False)
    df.columns = [c.lstrip("#") for c in df.columns]
    df = df[(df["TYPOP"] == "00") & (df["GEOTYPE"] == "01")]
    rows = {}
    for code, g in df.groupby(naics_col):
        code = code.strip()
        if code in ("00", ""):
            continue
        rec = {"year": year}
        g = g.set_index("CONCENFI")
        if "001" not in g.index:
            continue
        a = g.loc["001"]
        rec["label"] = a[f"{naics_col}_LABEL" if year == 2022 else f"{naics_col}_TTL"]
        rec["firms"] = num(a["FIRM"])
        rec["estabs"] = num(a["ESTAB"])
        rec["revenue"] = num(a["RCPTOT"])  # $1,000
        rec["payroll"] = num(a["PAYANN"])  # $1,000
        rec["emp"] = num(a["EMP"])
        rec["payroll_share"] = (
            100 * rec["payroll"] / rec["revenue"] if rec["payroll"] and rec["revenue"] else None
        )
        for k, cf in (("cr4", "604"), ("cr8", "608"), ("cr20", "620"), ("cr50", "650")):
            rec[k] = num(g.loc[cf]["VAL_PCT"]) if cf in g.index else None
        rec["hhi"] = num(g.loc["650"]["HHI"]) if "650" in g.index and g.loc["650"]["HHI"] not in ("", "0") else None
        rec["flag"] = (a["RCPTOT_F"] or a["PAYANN_F"] or (g.loc["604"]["VAL_PCT_F"] if "604" in g.index else "")) or None
        rows[code] = rec
    return rows


ec22 = load_ec("ec2022/EC2200SIZECONCEN.dat", "NAICS2022", 2022)
ec17 = load_ec("ec2017/EC1700SIZECONCEN.dat", "NAICS2017", 2017)
print("EC 2022 codes:", len(ec22), " EC 2017 codes:", len(ec17))


def load_census_value_added(path):
    df = pd.read_csv(path, sep="|", dtype=str, keep_default_na=False)
    df.columns = [c.lstrip("#") for c in df.columns]
    df = df[
        (df["GEO_ID"] == "0100000US")
        & df["INDLEVEL"].isin({"3", "4", "5", "6"})
    ]
    rows = {}
    for _, row in df.iterrows():
        payroll = num(row["PAYANN"])
        value_added = num(row["VALADD"])
        if value_added is None or value_added <= 0 or payroll is None:
            continue
        rows[row["NAICS2022"].strip()] = round(100 * payroll / value_added, 1)
    return rows


census_va = load_census_value_added("ec2231/EC2231BASIC.dat")
print("Census value-added labor-share rows:", len(census_va), " six-digit:", sum(len(k) == 6 for k in census_va))


def load_bea_value_added(path):
    raw = pd.read_excel(path, sheet_name="TVA113-A", header=None)
    years = [int(raw.iloc[7, col]) for col in range(3, raw.shape[1]) if num(raw.iloc[7, col]) is not None]
    series = {}
    component_names = {
        "Compensation of employees",
        "Taxes on production and imports less subsidies",
        "Gross operating surplus",
    }
    for row in range(8, len(raw) - 3):
        title = str(raw.iloc[row, 1]).strip() if pd.notna(raw.iloc[row, 1]) else ""
        if not title or title in component_names:
            continue
        if [str(raw.iloc[row + offset, 1]).strip() for offset in range(1, 4)] != [
            "Compensation of employees",
            "Taxes on production and imports less subsidies",
            "Gross operating surplus",
        ]:
            continue
        value_added = [num(raw.iloc[row, col]) for col in range(3, 3 + len(years))]
        compensation = [num(raw.iloc[row + 1, col]) for col in range(3, 3 + len(years))]
        shares = [
            round(100 * comp / value, 1) if comp is not None and value not in (None, 0) else None
            for value, comp in zip(value_added, compensation)
        ]
        series[title] = {"years": years, "values": shares}
    return series


bea_va = load_bea_value_added("bea/gdp/ValueAdded.xlsx")
BEA_NAICS_MAP = {
    key: value for key, value in json.load(open("bea_naics_map.json")).items() if not key.startswith("_")
}
missing_bea_titles = sorted(set(BEA_NAICS_MAP.values()) - set(bea_va))
if missing_bea_titles:
    raise RuntimeError(f"BEA titles not found in TVA113-A: {missing_bea_titles}")


def bea_lookup(code):
    for prefix in sorted(BEA_NAICS_MAP, key=len, reverse=True):
        if code == prefix or code.startswith(prefix):
            title = BEA_NAICS_MAP[prefix]
            return title, bea_va[title]
    return None, None


print("BEA value-added industries:", len(bea_va), " mapped titles:", len(set(BEA_NAICS_MAP.values())))


six_digit_codes = {
    code for code in ec22
    if len(code) == 6 and code.isdigit()
}
bea_exact_codes = set()
for code, title in BEA_NAICS_MAP.items():
    descendants = {
        child for child in six_digit_codes
        if (sector_of(child) == code if "-" in code else child.startswith(code))
    }
    mapped_to_title = {
        child for child in six_digit_codes
        if bea_lookup(child)[0] == title
    }
    if descendants == mapped_to_title:
        bea_exact_codes.add(code)
print("BEA exact group codes:", len(bea_exact_codes), sorted(bea_exact_codes))


bea_parent_totals = {}
for code, e in ec22.items():
    if len(code) != 6 or not code.isdigit() or e["cr4"] is None or e["payroll_share"] is None:
        continue
    bea_title, _ = bea_lookup(code)
    if bea_title is None or e["payroll"] is None or e["revenue"] is None:
        continue
    totals = bea_parent_totals.setdefault(bea_title, [0.0, 0.0])
    totals[0] += e["payroll"]
    totals[1] += e["revenue"]
bea_parent_ratio = {
    title: payroll / revenue
    for title, (payroll, revenue) in bea_parent_totals.items()
    if revenue > 0
}
print("BEA parent payroll/revenue ratios:", len(bea_parent_ratio))

# ---------------------------------------------------------------- BLS Industry Productivity
series = pd.read_csv("ip.series", sep="\t", dtype=str)
series.columns = [c.strip() for c in series.columns]
series = series[(series["duration_code"] == "0") & (series["area_code"] == "000000")]
series["series_id"] = series["series_id"].str.strip()
series["naics"] = series["industry_code"].str[1:].str.rstrip("_")
data = pd.read_csv("ip.data.1.AllData", sep="\t", dtype=str)
data.columns = [c.strip() for c in data.columns]
data["series_id"] = data["series_id"].str.strip()
data["value"] = pd.to_numeric(data["value"].str.strip(), errors="coerce")
data = data.merge(series[["series_id", "naics", "measure_code"]], on="series_id")
data = data[data["measure_code"].isin(["L03", "L02", "T30", "T39"])]
piv = data.pivot_table(index=["naics", "year"], columns="measure_code", values="value").reset_index()
for m in ("L03", "L02", "T30", "T39"):
    if m not in piv.columns:
        piv[m] = float("nan")

bls = {}
for naics, g in piv.groupby("naics"):
    g = g.sort_values("year")
    if g["L03"].notna().any():
        vals = g[["year", "L03"]].dropna()
        kind = "BLS labor share (compensation / value of production)"
    elif g["L02"].notna().any() and g["T39"].notna().any():
        vals = g.assign(v=100 * g["L02"] / g["T39"])[["year", "v"]].dropna()
        kind = "BLS compensation / value added"
    elif g["L02"].notna().any() and g["T30"].notna().any():
        vals = g.assign(v=100 * g["L02"] / g["T30"])[["year", "v"]].dropna()
        kind = "BLS compensation / sectoral output"
    else:
        continue
    bls[naics] = {"kind": kind, "years": [int(y) for y in vals.iloc[:, 0]], "values": [round(float(v), 1) for v in vals.iloc[:, 1]]}
print("BLS labor-share series:", len(bls))


def bls_lookup(code):
    for n in range(len(code), 1, -1):
        c = code[:n]
        if c in bls:
            return c, bls[c]
    return None, None


# ---------------------------------------------------------------- QCEW 2026 Q1 (national, private)
q = pd.read_csv("qcew_national_private_2026q1.csv", dtype={"industry_code": str, "agglvl_code": str, "disclosure_code": str})
q["industry_code"] = q["industry_code"].str.strip()
qcew = {}
for _, r in q.iterrows():
    qcew[r["industry_code"]] = {
        "emp": num(r["month3_emplvl"]),
        "estabs": num(r["qtrly_estabs"]),
        "avg_wkly_wage": num(r["avg_wkly_wage"]),
        "emp_yoy": num(r["oty_month3_emplvl_pct_chg"]),
        "wage_yoy": num(r["oty_avg_wkly_wage_pct_chg"]),
        "estab_yoy": num(r["oty_qtrly_estabs_pct_chg"]),
    }

# Geographic concentration of employment across counties (6-digit where disclosed, else 4-digit).
c = pd.read_csv("qcew_county_private_2026q1.csv", dtype={"industry_code": str, "agglvl_code": str, "area_fips": str, "disclosure_code": str})
c = c[(c["disclosure_code"] != "N") & (c["month3_emplvl"] > 0)]
c = c[~c["area_fips"].str.endswith("999")]  # drop "unknown/statewide" pseudo-counties
areas = pd.read_csv("area_titles.csv", dtype=str).drop_duplicates("area_fips").set_index("area_fips")["area_title"].to_dict()
geo = {}
for code, g in c.groupby("industry_code"):
    code = code.strip()
    nat = qcew.get(code, {}).get("emp")
    if not nat:
        continue
    tot = g["month3_emplvl"].sum()
    coverage = tot / nat
    if coverage < 0.7:  # too much suppressed to say anything about geography
        continue
    sh = g["month3_emplvl"] / nat
    top = g.sort_values("month3_emplvl", ascending=False).head(1)
    geo[code] = {
        "geo_hhi": round(float((sh ** 2).sum() * 10000)),
        "counties": int(len(g)),
        "coverage": round(float(coverage * 100)),
        "top_county_share": round(float(sh.max() * 100), 1),
        "top_county": areas.get(top["area_fips"].iloc[0], top["area_fips"].iloc[0]),
    }
print("Geo HHI industries:", len(geo), pd.Series([len(k) for k in geo]).value_counts().to_dict())

# ---------------------------------------------------------------- Assemble
industries = []
for code, e in ec22.items():
    if e["cr4"] is None or e["payroll_share"] is None:
        continue
    prev = ec17.get(code)
    bcode, b = bls_lookup(code)
    bea_title, bea = bea_lookup(code)
    census_share = census_va.get(code) if sector_of(code) == "31-33" else None
    if census_share is not None:
        va_share = census_share
        va_source = "census"
    elif bea is not None:
        parent_share = bea["values"][bea["years"].index(2022)] if 2022 in bea["years"] else None
        parent_ratio = bea_parent_ratio.get(bea_title)
        record_ratio = e["payroll"] / e["revenue"] if e["payroll"] is not None and e["revenue"] else None
        if parent_share is not None and code in bea_exact_codes:
            va_share = parent_share
            va_source = "bea"
        elif parent_share is not None and parent_ratio is None:
            scaled_share = parent_share
            va_capped = scaled_share > 100
            va_share = min(100, scaled_share)
            va_source = "bea_scaled"
        elif parent_share is not None and parent_ratio and record_ratio is not None:
            scaled_share = parent_share * record_ratio / parent_ratio
            va_capped = scaled_share > 100
            va_share = min(100, scaled_share)
            va_source = "bea_scaled"
        else:
            va_share = None
            va_source = None
    else:
        va_share = None
        va_source = None
    rec = {
        "code": code,
        "level": 2 if "-" in code else len(code),
        "label": e["label"],
        "sector": sector_of(code),
        "sector_name": SECTOR_NAMES.get(sector_of(code), sector_of(code)),
        "cr4": e["cr4"], "cr8": e["cr8"], "cr20": e["cr20"], "cr50": e["cr50"], "hhi": e["hhi"],
        "payroll_share": round(e["payroll_share"], 1),
        "revenue_musd": round(e["revenue"] / 1000) if e["revenue"] else None,
        "payroll_musd": round(e["payroll"] / 1000) if e["payroll"] else None,
        "emp": e["emp"], "firms": e["firms"], "estabs": e["estabs"],
        "rev_per_emp_k": round(e["revenue"] / e["emp"]) if e["emp"] else None,
        "pay_per_emp_k": round(e["payroll"] / e["emp"], 1) if e["emp"] else None,
        "flag": e["flag"],
        "cr4_2017": prev["cr4"] if prev else None,
        "payroll_share_2017": round(prev["payroll_share"], 1) if prev and prev["payroll_share"] else None,
        "firms_2017": prev["firms"] if prev else None,
        "bls_code": bcode,
        "bls": b,
        "va_share": va_share,
        "va_source": va_source,
    }
    if va_source == "bea":
        rec["va_bea_industry"] = bea_title
        rec["bea_series"] = bea
        rec["va_share"] = round(va_share, 1)
    elif va_source == "bea_scaled":
        rec["va_bea_industry"] = bea_title
        rec["va_bea_parent_share"] = parent_share
        rec["bea_series"] = bea
        if va_capped:
            rec["va_capped"] = True
        rec["va_share"] = round(va_share, 1)
    if rec["cr4_2017"] is not None:
        rec["cr4_chg"] = round(rec["cr4"] - rec["cr4_2017"], 1)
    if rec["payroll_share_2017"] is not None:
        rec["payroll_share_chg"] = round(rec["payroll_share"] - rec["payroll_share_2017"], 1)
    qc = qcew.get(code)
    if qc:
        rec["qcew"] = qc
    g = geo.get(code) or (geo.get(code[:4]) if len(code) >= 4 else None)
    if g:
        rec["geo"] = dict(g, code=code if code in geo else code[:4])
    if code in TOP_EMPLOYERS:
        rec["top_employers"] = TOP_EMPLOYERS[code]
    industries.append(rec)

six_digit = [r for r in industries if r["level"] == 6]
for rec in industries:
    if rec["level"] >= 6:
        continue
    if "-" in rec["code"]:
        children = [child for child in six_digit if sector_of(child["code"]) == rec["code"]]
    else:
        children = [child for child in six_digit if child["code"].startswith(rec["code"])]
    children.sort(key=lambda child: child.get("emp") or 0, reverse=True)
    names = []
    for rank in range(4):
        for child in children:
            child_names = child.get("top_employers") or []
            if rank < len(child_names) and child_names[rank] not in names:
                names.append(child_names[rank])
                if len(names) == 4:
                    break
        if len(names) == 4:
            break
    rec["top_employers"] = names
    rec["top_employers_derived"] = True

print("Industries out:", len(industries), pd.Series([r["level"] for r in industries]).value_counts().to_dict())
print("with 2017 match:", sum(r.get("cr4_2017") is not None for r in industries))
print("with BLS:", sum(r["bls"] is not None for r in industries), "exact:", sum(r["bls_code"] == r["code"] for r in industries))
print("with QCEW:", sum("qcew" in r for r in industries), "with geo:", sum("geo" in r for r in industries))
scaled_va = [r["va_share"] for r in industries if r["va_source"] == "bea_scaled"]
print(
    "scaled BEA value-added labor share:",
    "min", round(min(scaled_va), 1),
    "median", round(float(pd.Series(scaled_va).median()), 1),
    "max", round(max(scaled_va), 1),
    "capped", sum(r.get("va_capped") is True for r in industries),
)
print(
    "value-added labor share:",
    "census exact", sum(r["va_source"] == "census" for r in industries),
    "bea", sum(r["va_source"] == "bea" for r in industries),
    "bea_scaled", sum(r["va_source"] == "bea_scaled" for r in industries),
    "null", sum(r["va_source"] is None for r in industries),
)

meta = {
    "sources": {
        "concentration": "U.S. Census Bureau, 2022 & 2017 Economic Census, EC2200SIZECONCEN / EC1700SIZECONCEN (share of sales/receipts by largest firms; HHI for manufacturing).",
        "payroll_share": "Same tables: annual payroll / sales, value of shipments or revenue.",
        "value_added": "U.S. Census Bureau, 2022 Economic Census EC2231BASIC value added and annual payroll (exact for manufacturing 6-digit industries); elsewhere an estimate based on BEA GDP by Industry TVA113-A (1997–2024), scaled by each industry's payroll/revenue relative to its mapped BEA group's aggregate ratio and capped at 100%.",
        "bls": "BLS Industry Productivity program (ip.data.1.AllData), labor share L03 or compensation/output, 1987-2023.",
        "qcew": "BLS QCEW 2026 Q1 single file (private ownership, national and county), released 2026-08-21.",
        "top_employers": "Curated list of well-known large employers per industry (top_employers.json); indicative only, not from Census or BLS.",
    }
}
with open(OUT, "w") as f:
    json.dump({"meta": meta, "industries": industries}, f, separators=(",", ":"))
print("wrote", OUT)
