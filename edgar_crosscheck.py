#!/usr/bin/env python3
"""Cross-check curated employers against SEC filers for all six-digit industries."""

from __future__ import annotations

import csv
import difflib
import html
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = Path("/home/ubuntu/qcew")
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from edgar_top import (
    CURATED_JSON,
    EdgarTableParser,
    SecClient,
    latest_fact,
)


INDUSTRIES_TSV = BASE / "industries_6digit.tsv"
EMPLOYMENT_JSON = BASE / "docs/data/industries.json"
OUTPUT_JSON = BASE / "edgar_filers.json"
OUTPUT_MD = BASE / "edgar_flags.md"
CONCORDANCE_URL = "https://www.census.gov/naics/concordances/2002_NAICS_to_1987_SIC.xls"
SEC_SIC_URL = "https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list"
USER_AGENT = "jerzh research jeremy.q.zhou@gmail.com"
REVENUE_TAGS = (
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "InterestAndDividendIncomeOperating",
    "RevenuesNetOfInterestExpense",
)
RATE_LOCK = threading.Lock()
NEXT_REQUEST_AT = 0.0
CORPORATE_SUFFIXES = {
    "and",
    "co",
    "company",
    "corp",
    "corporation",
    "de",
    "inc",
    "incorporated",
    "limited",
    "llc",
    "ltd",
    "plc",
}


def download_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    with urlopen(request, timeout=60) as response:
        payload = response.read()
    if payload[:2] == b"\x1f\x8b":
        import gzip

        payload = gzip.decompress(payload)
    return payload


def parse_concordance() -> list[dict[str, str]]:
    """Convert the Census legacy XLS concordance to CSV using xls2csv."""
    payload = download_bytes(CONCORDANCE_URL)
    with tempfile.TemporaryDirectory(prefix="naics-concordance-") as temp_dir:
        xls_path = Path(temp_dir) / "concordance.xls"
        xls_path.write_bytes(payload)
        result = subprocess.run(
            ["xls2csv", str(xls_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    rows = list(csv.DictReader(result.stdout.splitlines()))
    normalized: list[dict[str, str]] = []
    for row in rows:
        naics = re.sub(r"\D", "", str(row.get("2002 NAICS") or ""))
        sic = re.sub(r"\D", "", str(row.get("SIC") or ""))
        if len(naics) >= 4 and sic:
            normalized.append({"naics": naics.zfill(6), "sic": sic.zfill(4)})
    if not normalized:
        raise RuntimeError("Census concordance contained no parseable NAICS/SIC rows")
    return normalized


class SicTableParser(HTMLParser):
    """Extract the first cell from rows in the SEC SIC list table."""

    def __init__(self) -> None:
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.cells: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.in_row = True
            self.cells = []
        elif self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_cell:
            self.cells.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.cells:
                self.rows.append(self.cells)
            self.in_row = False


def parse_sec_sic_list(payload: bytes) -> set[str]:
    parser = SicTableParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    sics = {
        cells[0].zfill(4)
        for cells in parser.rows
        if cells and re.fullmatch(r"\d{1,4}", cells[0])
    }
    if not sics:
        raise RuntimeError("SEC SIC list contained no parseable SIC codes")
    return sics


def sec_get(client: SecClient, url: str, attempts: int = 6) -> bytes:
    global NEXT_REQUEST_AT
    for attempt in range(attempts):
        try:
            with RATE_LOCK:
                delay = NEXT_REQUEST_AT - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                NEXT_REQUEST_AT = max(NEXT_REQUEST_AT, time.monotonic()) + 1 / 8
            return client.get(url)
        except Exception as exc:
            if isinstance(exc, HTTPError) and exc.code == 404:
                raise
            if attempt + 1 == attempts:
                raise
            delay = min(30, 2**attempt)
            print(
                f"SEC request retry {attempt + 1}/{attempts - 1} after {exc}: "
                f"sleeping {delay}s",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError("unreachable SEC request failure")


def nearest_sec_sic(raw_sic: str, sec_sics: set[str]) -> str | None:
    if raw_sic in sec_sics:
        return raw_sic
    prefix = raw_sic.zfill(4)[:3]
    candidates = [sic for sic in sec_sics if sic[:3] == prefix]
    if not candidates:
        return None
    return min(candidates, key=lambda sic: abs(int(sic) - int(raw_sic)))


def read_industries() -> dict[str, str]:
    industries: dict[str, str] = {}
    with INDUSTRIES_TSV.open(encoding="utf-8") as handle:
        for line in handle:
            code, label = line.rstrip("\n").split("\t", 1)
            industries[code] = label
    if len(industries) != 899:
        raise RuntimeError(f"expected 899 six-digit industries, found {len(industries)}")
    return industries


def build_mappings(
    industries: dict[str, str],
    concordance: list[dict[str, str]],
    sec_sics: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    by_naics: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    for row in concordance:
        by_naics[row["naics"]].add(row["sic"])
        reverse[row["sic"]].add(row["naics"][:3])

    mappings: dict[str, dict[str, Any]] = {}
    for code in industries:
        candidates: set[str] = set()
        level = "none"
        for prefix, candidate_level in ((code, "exact"), (code[:5], "five-digit"), (code[:4], "four-digit")):
            candidates = set()
            for source_naics, sics in by_naics.items():
                if source_naics.startswith(prefix):
                    candidates.update(sics)
            if candidates:
                level = candidate_level
                break
        mapped_sics: set[str] = set()
        for raw_sic in sorted(candidates):
            mapped = nearest_sec_sic(raw_sic, sec_sics)
            if mapped is not None:
                mapped_sics.add(mapped)
        mappings[code] = {
            "match_level": level,
            "source_sics": sorted(candidates),
            "sics": sorted(mapped_sics),
        }
    return mappings, reverse


def list_sic_companies_all(client: SecClient, sic: str) -> list[dict[str, str]]:
    """List all EDGAR rows, including foreign rows that may have 10-K facts."""
    rows: list[dict[str, str]] = []
    start = 0
    while True:
        url = (
            "https://www.sec.gov/cgi-bin/browse-edgar"
            f"?action=getcompany&SIC={sic.lstrip('0')}&type=10-K&dateb=&owner=include"
            f"&count=100&start={start}"
        )
        payload = sec_get(client, url)
        parser = EdgarTableParser()
        parser.feed(payload.decode("utf-8", errors="replace"))
        page: list[dict[str, str]] = []
        for cells, href, anchor_name in parser.rows:
            match = re.search(r"[?&]CIK=(\d{1,10})", href, flags=re.I)
            if not match:
                continue
            location = cells[2] if len(cells) > 2 else ""
            name = cells[1] if len(cells) > 1 else anchor_name
            page.append({
                "cik": match.group(1).zfill(10),
                "name": " ".join(name.split()),
                "location": " ".join(location.split()),
                "sic": sic,
            })
        print(f"SIC {sic}: page start={start}, {len(page)} rows", file=sys.stderr, flush=True)
        if not page:
            break
        rows.extend(page)
        start += 100
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        unique.setdefault(row["cik"], row)
    return list(unique.values())


def filer_facts(client: SecClient, listing: dict[str, str]) -> dict[str, Any] | None:
    cik = listing["cik"]
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    try:
        facts = json.loads(sec_get(client, url))
    except Exception as exc:
        print(f"CIK {cik}: companyfacts unavailable ({exc})", file=sys.stderr, flush=True)
        return None
    namespaces = facts.get("facts", {})
    revenue: int | float | None = None
    revenue_fy: int | None = None
    for tag in REVENUE_TAGS:
        fact = namespaces.get("us-gaap", {}).get(tag)
        if not fact:
            continue
        value, fy = latest_fact(fact.get("units", {}))
        if value is not None and (revenue_fy is None or (fy or 0) > revenue_fy):
            revenue, revenue_fy = value, fy
    if revenue is None:
        return None
    dei = namespaces.get("dei", {}).get("EntityNumberOfEmployees", {})
    employees, employee_fy = latest_fact(dei.get("units", {}))
    return {
        "name": listing["name"],
        "cik": cik,
        "location": listing.get("location", ""),
        "sic": listing["sic"],
        "employees": int(employees) if employees is not None else None,
        "revenue": float(revenue),
        "fy": max(x for x in (revenue_fy, employee_fy) if x is not None),
        "revenue_fy": revenue_fy,
        "employee_fy": employee_fy,
    }


def normalize_name(name: str) -> str:
    value = re.sub(r"\([^)]*\)", " ", html.unescape(name).lower())
    value = re.sub(r"[/&.,'’+\-]", " ", value)
    value = re.sub(r"[^a-z0-9 ]", " ", value)
    tokens = [token for token in value.split() if token not in CORPORATE_SUFFIXES]
    return " ".join(tokens)


def names_match(left: str, right: str) -> tuple[bool, float]:
    left_norm = normalize_name(left)
    right_norm = normalize_name(right)
    if not left_norm or not right_norm:
        return False, 0.0
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    containment = (
        left_tokens <= right_tokens or right_tokens <= left_tokens
    ) and min(len(left_tokens), len(right_tokens)) >= 1
    ratio = difflib.SequenceMatcher(None, left_norm, right_norm).ratio()
    return containment or ratio >= 0.85, ratio


def load_cache() -> dict[str, Any]:
    if not OUTPUT_JSON.exists():
        return {"filers": {}}
    try:
        value = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("filers"), dict):
            return value
    except (OSError, json.JSONDecodeError):
        pass
    return {"filers": {}}


def cache_filings(
    client: SecClient,
    mappings: dict[str, dict[str, Any]],
    cache: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    filers: dict[str, list[dict[str, Any]]] = {
        str(sic): rows for sic, rows in cache.get("filers", {}).items()
    }
    in_progress: dict[str, dict[str, Any]] = {
        str(sic): value for sic, value in cache.get("in_progress", {}).items()
    }
    used_sics = sorted({sic for mapping in mappings.values() for sic in mapping["sics"]})
    for index, sic in enumerate(used_sics, start=1):
        if sic in filers:
            print(f"[{index}/{len(used_sics)}] SIC {sic}: using cache ({len(filers[sic])})", file=sys.stderr, flush=True)
            continue
        progress = in_progress.get(sic)
        if progress:
            listings = progress["listings"]
            usable = progress.get("usable", [])
            processed = int(progress.get("processed", 0))
            print(
                f"SIC {sic}: resuming facts {processed}/{len(listings)}, "
                f"usable={len(usable)}",
                file=sys.stderr,
                flush=True,
            )
        else:
            listings = list_sic_companies_all(client, sic)
            usable = []
            processed = 0
            in_progress[sic] = {
                "listings": listings,
                "usable": usable,
                "processed": processed,
            }
            cache["in_progress"] = in_progress
            OUTPUT_JSON.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        pending = listings[processed:]
        worker_local = threading.local()

        def fetch_fact(listing: dict[str, str]) -> dict[str, Any] | None:
            if not hasattr(worker_local, "client"):
                worker_local.client = SecClient()
            return filer_facts(worker_local.client, listing)

        with ThreadPoolExecutor(max_workers=8) as executor:
            facts = executor.map(fetch_fact, pending)
            for listing_index, fact in enumerate(facts, start=processed + 1):
                if fact is not None:
                    usable.append(fact)
                in_progress[sic]["processed"] = listing_index
                in_progress[sic]["usable"] = usable
                if listing_index % 100 == 0:
                    print(
                        f"SIC {sic}: facts {listing_index}/{len(listings)}, usable={len(usable)}",
                        file=sys.stderr,
                        flush=True,
                    )
                    cache["in_progress"] = in_progress
                    OUTPUT_JSON.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        filers[sic] = usable
        in_progress.pop(sic, None)
        cache["filers"] = filers
        cache["in_progress"] = in_progress
        cache["meta"] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "sics_completed": index,
            "sics_used": len(used_sics),
        }
        OUTPUT_JSON.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[{index}/{len(used_sics)}] SIC {sic}: cached {len(usable)} usable filers", file=sys.stderr, flush=True)
    return filers


def best_filer_match(name: str, all_filers: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates: list[tuple[float, float, dict[str, Any]]] = []
    for filer in all_filers:
        matched, ratio = names_match(name, filer["name"])
        if matched:
            candidates.append((ratio, filer.get("revenue") or 0.0, filer))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def money_billions(value: float | None) -> str:
    return f"${value / 1_000_000_000:.1f}B" if value is not None else "n/a"


def load_employment() -> dict[str, float]:
    payload = json.loads(EMPLOYMENT_JSON.read_text(encoding="utf-8"))
    return {
        row["code"]: float(row.get("emp") or 0)
        for row in payload["industries"]
        if row.get("level") == 6
    }


def make_report(
    industries: dict[str, str],
    curated: dict[str, list[str]],
    mappings: dict[str, dict[str, Any]],
    reverse: dict[str, set[str]],
    filers: dict[str, list[dict[str, Any]]],
) -> tuple[str, dict[str, int]]:
    all_filers = [filer for rows in filers.values() for filer in rows]
    employment = load_employment()
    flagged: list[dict[str, Any]] = []
    mismatch_count = missing_count = both_count = 0
    for code, label in industries.items():
        mapping = mappings[code]
        mapped_sics = set(mapping["sics"])
        names = curated.get(code, [])
        matched: list[tuple[str, dict[str, Any] | None]] = [
            (name, best_filer_match(name, all_filers)) for name in names
        ]
        mismatch_items: list[tuple[str, dict[str, Any]]] = []
        matched_revenues: list[float] = []
        curated_ciks: set[str] = set()
        for name, filer in matched:
            if filer is None:
                continue
            if filer["sic"] in mapped_sics:
                curated_ciks.add(filer["cik"])
                if filer.get("revenue") is not None:
                    matched_revenues.append(float(filer["revenue"]))
            elif code[:3] not in reverse.get(filer["sic"], set()):
                mismatch_items.append((name, filer))
        candidates = [
            filer
            for sic in mapped_sics
            for filer in filers.get(sic, [])
            if filer.get("revenue") is not None
        ]
        threshold = max(matched_revenues) if matched_revenues else 5_000_000_000
        missing = [
            filer
            for filer in candidates
            if float(filer["revenue"]) > threshold and filer["cik"] not in curated_ciks
        ]
        missing.sort(key=lambda filer: float(filer["revenue"]), reverse=True)
        missing = missing[:3]
        if mismatch_items:
            mismatch_count += 1
        if missing:
            missing_count += 1
        if mismatch_items and missing:
            both_count += 1
        if mismatch_items or missing:
            flagged.append({
                "code": code,
                "label": label,
                "sics": sorted(mapped_sics),
                "curated": names,
                "matched": matched,
                "mismatch": mismatch_items,
                "missing": missing,
                "employment": employment.get(code, 0),
            })
    flagged.sort(key=lambda row: row["employment"], reverse=True)

    exact = sum(mapping["match_level"] == "exact" for mapping in mappings.values())
    five = sum(mapping["match_level"] == "five-digit" for mapping in mappings.values())
    four = sum(mapping["match_level"] == "four-digit" for mapping in mappings.values())
    used_sics = {sic for mapping in mappings.values() for sic in mapping["sics"]}
    stats = {
        "exact": exact,
        "five_digit": five,
        "four_digit": four,
        "sics": len(used_sics),
        "filers": len({filer["cik"] for filer in all_filers}),
        "mismatch": mismatch_count,
        "missing": missing_count,
        "both": both_count,
    }
    lines = [
        "# EDGAR cross-check of curated employers",
        "",
        "The curated employer list is indicative and not an authoritative ranking. "
        "SEC SIC assignments are broad and may not correspond exactly to six-digit NAICS.",
        "",
        "## Summary",
        "",
        f"- Industries mapped at exact level: **{exact}**",
        f"- Industries mapped at five-digit level: **{five}**",
        f"- Industries mapped at four-digit level: **{four}**",
        f"- SEC SICs used: **{len(used_sics)}**",
        f"- Usable filers pulled: **{stats['filers']}**",
        f"- Industries flagged for mismatch: **{mismatch_count}**",
        f"- Industries flagged for missing large filers: **{missing_count}**",
        f"- Industries flagged for both: **{both_count}**",
        "",
        "## Flagged industries",
        "",
        "| NAICS | Industry | SEC SICs | Curated names / matches | Top missing filers |",
        "|---|---|---|---|---|",
    ]
    for row in flagged:
        curated_parts: list[str] = []
        mismatches = {name: filer for name, filer in row["mismatch"]}
        for name, filer in row["matched"]:
            if name in mismatches:
                curated_parts.append(f"✗ {name} (SIC {mismatches[name]['sic']})")
            elif filer is not None and filer["sic"] in row["sics"]:
                curated_parts.append(f"✓ {name}")
            else:
                curated_parts.append(name)
        missing_text = "<br>".join(
            f"{filer['name']} ({money_billions(filer.get('revenue'))})"
            for filer in row["missing"]
        ) or "—"
        lines.append(
            f"| {row['code']} | {row['label']} | {', '.join(row['sics']) or '—'} | "
            f"{'<br>'.join(curated_parts)} | {missing_text} |"
        )
    lines.extend([
        "",
        f"_Flagged industries are sorted by six-digit industry employment descending "
        f"({len(flagged)} rows)._",
        "",
    ])
    return "\n".join(lines), stats


def main() -> None:
    industries = read_industries()
    curated = json.loads(CURATED_JSON.read_text(encoding="utf-8"))
    cache = load_cache()
    mappings: dict[str, dict[str, Any]]
    reverse: dict[str, set[str]]
    cached_mappings = cache.get("sic_mappings")
    cached_reverse = cache.get("reverse_sic_naics")
    if cached_mappings and cached_reverse:
        mappings = cached_mappings
        reverse = {sic: set(prefixes) for sic, prefixes in cached_reverse.items()}
    else:
        concordance = parse_concordance()
        client = SecClient()
        sec_sics = parse_sec_sic_list(sec_get(client, SEC_SIC_URL))
        mappings, reverse = build_mappings(industries, concordance, sec_sics)
        cache["sic_mappings"] = mappings
        cache["reverse_sic_naics"] = {
            sic: sorted(prefixes) for sic, prefixes in reverse.items()
        }
        OUTPUT_JSON.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    client = SecClient()
    filers = cache_filings(client, mappings, cache)
    cache["sic_mappings"] = mappings
    cache["reverse_sic_naics"] = {
        sic: sorted(prefixes) for sic, prefixes in reverse.items()
    }
    cache["meta"] = {
        **cache.get("meta", {}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filers_pulled": len({filer["cik"] for rows in filers.values() for filer in rows}),
    }
    OUTPUT_JSON.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report, stats = make_report(industries, curated, mappings, reverse, filers)
    OUTPUT_MD.write_text(report, encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
