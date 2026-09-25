"""Build site/data/industries.json from Economic Census concentration tables,
BLS Industry Productivity labor-share series and QCEW 2026Q1.

Run from /home/ubuntu/qcew.
"""
import json
import math
import pandas as pd

OUT = "site/data/industries.json"

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
    }
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
    industries.append(rec)

print("Industries out:", len(industries), pd.Series([r["level"] for r in industries]).value_counts().to_dict())
print("with 2017 match:", sum(r.get("cr4_2017") is not None for r in industries))
print("with BLS:", sum(r["bls"] is not None for r in industries), "exact:", sum(r["bls_code"] == r["code"] for r in industries))
print("with QCEW:", sum("qcew" in r for r in industries), "with geo:", sum("geo" in r for r in industries))

meta = {
    "sources": {
        "concentration": "U.S. Census Bureau, 2022 & 2017 Economic Census, EC2200SIZECONCEN / EC1700SIZECONCEN (share of sales/receipts by largest firms; HHI for manufacturing).",
        "payroll_share": "Same tables: annual payroll / sales, value of shipments or revenue.",
        "bls": "BLS Industry Productivity program (ip.data.1.AllData), labor share L03 or compensation/output, 1987-2023.",
        "qcew": "BLS QCEW 2026 Q1 single file (private ownership, national and county), released 2026-08-21.",
    }
}
with open(OUT, "w") as f:
    json.dump({"meta": meta, "industries": industries}, f, separators=(",", ":"))
print("wrote", OUT)
