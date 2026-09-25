#!/usr/bin/env python3
"""Build an SEC EDGAR comparison of large public companies by industry.

The resulting rankings are limited to companies listed by EDGAR under the
requested SICs.  They are not a complete market-cap or employment ranking.
"""

from __future__ import annotations

import html
import json
import gzip
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE = Path("/home/ubuntu/qcew")
OUTPUT_JSON = BASE / "edgar_top.json"
OUTPUT_MD = BASE / "edgar_compare.md"
CURATED_JSON = BASE / "top_employers.json"
USER_AGENT = "jerzh research jeremy.q.zhou@gmail.com"
MIN_REQUEST_INTERVAL = 1 / 8

NAICS = {
    "622110": ("General hospitals", ["8062"]),
    "722511": ("Full-service restaurants", ["5812"]),
    "722513": ("Limited-service restaurants", ["5812"]),
    "561320": ("Temporary help services", ["7363"]),
    "561330": ("Professional employer organizations", ["7363", "8742"]),
    "445110": ("Supermarkets", ["5411"]),
    "621111": ("Offices of physicians", ["8011"]),
    "455211": ("Warehouse clubs & supercenters", ["5331", "5399"]),
    "455219": ("Other general merchandise", ["5331", "5399"]),
    "522110": ("Commercial banking", ["6021", "6022"]),
    "621610": ("Home health care", ["8082"]),
    "624120": ("Services for elderly/disabled", ["8322"]),
}

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC", "PR", "VI", "GU", "AS", "MP",
}

REVENUE_TAGS = (
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "InterestAndDividendIncomeOperating",
)


@dataclass(frozen=True)
class Listing:
    cik: str
    name: str
    location: str
    sic: str


class EdgarTableParser(HTMLParser):
    """Extract company rows from the browse-edgar result table."""

    def __init__(self) -> None:
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.in_anchor = False
        self.row_cells: list[str] = []
        self.cell_parts: list[str] = []
        self.anchors: list[tuple[str, str]] = []
        self.anchor_parts: list[str] = []
        self.rows: list[tuple[list[str], str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "tr":
            self.in_row = True
            self.row_cells = []
            self.anchors = []
            self.anchor_parts = []
        elif self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []
        elif self.in_cell and tag == "a":
            self.in_anchor = True
            self.anchor_href = attrs_dict.get("href") or ""
            self.anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_anchor:
            self.anchor_parts.append(data)
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.in_anchor:
            self.in_anchor = False
            self.anchors.append((self.anchor_href, " ".join(self.anchor_parts).strip()))
        elif tag in {"td", "th"} and self.in_cell:
            text = " ".join("".join(self.cell_parts).split())
            self.row_cells.append(text)
            self.in_cell = False
            self.cell_parts = []
        elif tag == "tr" and self.in_row:
            if self.row_cells:
                for href, name in self.anchors:
                    if re.search(r"[?&]CIK=\d{1,10}", href, flags=re.I) and name:
                        self.rows.append((self.row_cells, href, name))
                        break
            self.in_row = False


class SecClient:
    def __init__(self) -> None:
        self.last_request = 0.0

    def get(self, url: str) -> bytes:
        delay = MIN_REQUEST_INTERVAL - (time.monotonic() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        request = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov" if "www.sec.gov" in url else "data.sec.gov",
        })
        for attempt in range(4):
            try:
                with urlopen(request, timeout=45) as response:
                    payload = response.read()
                    if payload[:2] == b"\x1f\x8b":
                        payload = gzip.decompress(payload)
                self.last_request = time.monotonic()
                return payload
            except HTTPError as exc:
                self.last_request = time.monotonic()
                if exc.code in {403, 429, 500, 502, 503, 504} and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except URLError:
                self.last_request = time.monotonic()
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise RuntimeError(f"unreachable request failure for {url}")


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(name)).strip()


def is_us_location(location: str) -> bool:
    """Return true when EDGAR supplies no location or a U.S. state/territory."""
    value = normalize_name(location).upper().replace(".", "")
    if not value:
        return True
    if value in US_STATES or value in {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}:
        return True
    # EDGAR sometimes gives "DE, US" or "NY, USA".
    pieces = [part.strip() for part in re.split(r"[,/;]", value) if part.strip()]
    return any(part in US_STATES or part in {"US", "USA", "UNITED STATES"} for part in pieces)


def parse_listing_page(payload: bytes, sic: str) -> list[Listing]:
    parser = EdgarTableParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    listings: list[Listing] = []
    for cells, href, anchor_name in parser.rows:
        match = re.search(r"[?&]CIK=(\d{1,10})", href, flags=re.I)
        if not match or not anchor_name:
            continue
        # The browse-edgar table is CIK, company, state/country, ... .
        location = cells[2] if len(cells) > 2 else ""
        if not is_us_location(location):
            continue
        cik = match.group(1).zfill(10)
        company_name = cells[1] if len(cells) > 1 else anchor_name
        listings.append(Listing(cik, normalize_name(company_name), normalize_name(location), sic))
    return listings


def list_sic_companies(client: SecClient, sic: str) -> list[Listing]:
    all_rows: list[Listing] = []
    start = 0
    while True:
        url = (
            "https://www.sec.gov/cgi-bin/browse-edgar"
            f"?action=getcompany&SIC={sic}&type=10-K&dateb=&owner=include"
            f"&count=100&start={start}"
        )
        page_rows = parse_listing_page(client.get(url), sic)
        print(f"SIC {sic}: page start={start}, {len(page_rows)} U.S. rows", file=sys.stderr)
        if not page_rows:
            break
        all_rows.extend(page_rows)
        start += 100
    unique: dict[str, Listing] = {}
    for row in all_rows:
        unique.setdefault(row.cik, row)
    return list(unique.values())


def latest_fact(units: dict[str, list[dict[str, Any]]], unit_preference: str | None = None) -> tuple[int | float | None, int | None]:
    candidates: list[dict[str, Any]] = []
    for unit, entries in units.items():
        if unit_preference and unit != unit_preference:
            continue
        for entry in entries:
            if entry.get("form") == "10-K" and isinstance(entry.get("fy"), int) and entry["fy"] >= 2022:
                if "val" in entry:
                    candidates.append(entry)
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: (x.get("fy", 0), x.get("filed", ""), x.get("end", "")), reverse=True)
    value = candidates[0]["val"]
    if isinstance(value, (int, float)):
        return value, candidates[0]["fy"]
    return None, None


def extract_companyfacts(payload: bytes) -> dict[str, Any] | None:
    facts = json.loads(payload)
    namespaces = facts.get("facts", {})
    dei = namespaces.get("dei", {}).get("EntityNumberOfEmployees", {})
    # EntityNumberOfEmployees is inconsistently unit-typed across filings
    # (and is absent from many otherwise valid companyfacts payloads).
    employees, employee_fy = latest_fact(dei.get("units", {}))

    revenue = None
    revenue_fy = None
    for tag in REVENUE_TAGS:
        us_gaap_tag = namespaces.get("us-gaap", {}).get(tag)
        if not us_gaap_tag:
            continue
        candidate, candidate_fy = latest_fact(us_gaap_tag.get("units", {}))
        if candidate is not None and (revenue_fy is None or (candidate_fy or 0) > revenue_fy):
            revenue, revenue_fy = candidate, candidate_fy
    # A company with no 10-K facts is intentionally excluded.  A company
    # with facts but no target metric is also not rankable for this output.
    if employees is None and revenue is None:
        return None
    fy = max(x for x in (employee_fy, revenue_fy) if x is not None)
    return {
        "employees": int(employees) if employees is not None else None,
        "revenue": float(revenue) if revenue is not None else None,
        "fy": fy,
        "employee_fy": employee_fy,
        "revenue_fy": revenue_fy,
    }


def companyfacts_for_listing(client: SecClient, listing: Listing) -> dict[str, Any] | None:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{listing.cik}.json"
    try:
        return extract_companyfacts(client.get(url))
    except (HTTPError, URLError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"skip CIK {listing.cik} ({listing.name}): {exc}", file=sys.stderr)
        return None


def rank_companies(client: SecClient, listings_by_sic: dict[str, list[Listing]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    all_listings: dict[str, dict[str, Listing]] = defaultdict(dict)
    for sic, listings in listings_by_sic.items():
        for listing in listings:
            all_listings[sic][listing.cik] = listing
    facts_cache: dict[str, dict[str, Any] | None] = {}
    listing_cache: dict[str, Listing] = {}
    for sic_listings in all_listings.values():
        for listing in sic_listings.values():
            listing_cache[listing.cik] = listing
            if listing.cik not in facts_cache:
                facts_cache[listing.cik] = companyfacts_for_listing(client, listing)

    results: dict[str, list[dict[str, Any]]] = {}
    employee_counts: dict[str, int] = {}
    for naics_code, (_, sics) in NAICS.items():
        by_cik: dict[str, dict[str, Any]] = {}
        all_ciks: set[str] = set()
        for sic in sics:
            for listing in listings_by_sic.get(sic, []):
                all_ciks.add(listing.cik)
                facts = facts_cache.get(listing.cik)
                if facts is None:
                    continue
                item = by_cik.setdefault(listing.cik, {
                    "name": listing.name,
                    "cik": listing.cik,
                    "sic": set(),
                    "employees": facts["employees"],
                    "revenue": facts["revenue"],
                    "fy": facts["fy"],
                })
                item["sic"].add(sic)
        employee_counts[naics_code] = sum(1 for item in by_cik.values() if item["employees"] is not None)
        ranked = sorted(
            by_cik.values(),
            key=lambda item: (
                item["employees"] is not None,
                item["employees"] if item["employees"] is not None else -1,
                item["revenue"] if item["revenue"] is not None else -1,
            ),
            reverse=True,
        )
        output_rows: list[dict[str, Any]] = []
        for item in ranked[:6]:
            output_rows.append({
                "name": item["name"],
                "cik": item["cik"],
                "sic": ",".join(sorted(item["sic"])),
                "employees": item["employees"],
                "revenue": item["revenue"],
                "fy": item["fy"],
            })
        results[naics_code] = output_rows
    return results, employee_counts


def compact_number(value: int | float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(int(value))


def money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.0f}"


def write_markdown(results: dict[str, list[dict[str, Any]]], employee_counts: dict[str, int], listings_by_sic: dict[str, list[Listing]]) -> None:
    curated = json.loads(CURATED_JSON.read_text())
    lines = [
        "# SEC EDGAR public-company comparison",
        "",
        "Indicative comparison built from SEC EDGAR `10-K` SIC listings and XBRL company facts. "
        "Companies are ranked by latest available fiscal-year employee count (FY ≥ 2022), "
        "then by revenue when employee count is unavailable. This is not an authoritative "
        "market-share or total-employment ranking.",
        "",
        "| NAICS | Industry | Curated employers | EDGAR top 6 (employees) | Public companies found | With employee count |",
        "|---|---|---|---|---:|---:|",
    ]
    for code, (label, sics) in NAICS.items():
        edgar_names = []
        for item in results.get(code, []):
            edgar_names.append(f"{item['name']} ({compact_number(item['employees'])})")
        found = len({listing.cik for sic in sics for listing in listings_by_sic.get(sic, [])})
        curated_names = "; ".join(curated.get(code, []))
        lines.append(
            f"| {code} | {label} | {curated_names} | "
            f"{'; '.join(edgar_names) or 'No rankable 10-K facts'} | {found} | "
            f"{employee_counts.get(code, 0)} |"
        )
    lines.extend([
        "",
        "## Notes",
        "",
        "- SIC 5812 is shared by full-service restaurants (722511) and limited-service restaurants (722513); "
        "EDGAR SIC listings cannot separate these two NAICS industries, so they receive the same underlying "
        "public-company universe and may have the same ranking.",
        "- SIC 7363 is shared by temporary help services (561320) and one of the SICs used for professional "
        "employer organizations (561330); SIC 8742 is also included for 561330.",
        "- SIC 5331 and 5399 are used for both general-merchandise NAICS industries as specified; EDGAR cannot "
        "reliably distinguish warehouse clubs/supercenters from other general merchandise.",
        "- A company is retained when the EDGAR listing does not provide a location, or when its listed location "
        "is a U.S. state/territory. Foreign locations are filtered out when supplied.",
        "- Employee and revenue values are the latest qualifying `10-K` facts with fiscal year ≥ 2022. "
        "Revenue is selected from the requested XBRL tags, in priority order, subject to the latest fiscal year.",
    ])
    OUTPUT_MD.write_text("\n".join(lines) + "\n")


def main() -> None:
    client = SecClient()
    listings_by_sic: dict[str, list[Listing]] = {}
    unique_sics = sorted({sic for _, sics in NAICS.values() for sic in sics})
    for sic in unique_sics:
        listings_by_sic[sic] = list_sic_companies(client, sic)
        print(f"SIC {sic}: {len(listings_by_sic[sic])} unique U.S. companies", file=sys.stderr)
    results, employee_counts = rank_companies(client, listings_by_sic)
    OUTPUT_JSON.write_text(json.dumps(results, indent=2) + "\n")
    write_markdown(results, employee_counts, listings_by_sic)
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
