"""
P1 School Data Scraper
======================
Pulls from:
  1. data.gov.sg - official MOE school directory (names, addresses, lat/lng, zones, types, CCAs)
  2. elite.com.sg - Phase 2B/2C balloting data (HTML table, no JS rendering needed)

Outputs: src/schools.json
"""

import json
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# ─────────────────────────────────────────────
# 1. DATA.GOV.SG — Official MOE School Directory
# ─────────────────────────────────────────────

def fetch_all(url):
    records = []
    offset = 0
    while True:
        r = requests.get(f"{url}&offset={offset}", timeout=20)
        r.raise_for_status()
        result = r.json()["result"]
        batch = result["records"]
        records.extend(batch)
        print(f"  Fetched {len(records)}/{result['total']}")
        if len(records) >= result["total"]:
            break
        offset += len(batch)
        time.sleep(0.5)
    return records

def fetch_school_directory():
    print("Fetching school directory from data.gov.sg...")
    url = "https://data.gov.sg/api/action/datastore_search?resource_id=d_688b934f82c1059ed0a6993d2a829089&limit=100"
    records = fetch_all(url)
    schools = {}
    for r in records:
        if r.get("mainlevel_code", "").upper() != "PRIMARY":
            continue
        name = r.get("school_name", "").strip().title()
        if not name:
            continue

        # Zone
        dgp = r.get("dgp_code", "").upper()
        zone = dgp_to_zone(dgp)

        # Gender
        nature = r.get("nature_code", "").upper()
        if "GIRLS" in nature:
            gender = "Girls"
        elif "BOYS" in nature:
            gender = "Boys"
        else:
            gender = "Co-ed"

        # Types
        types = []
        if str(r.get("sap_ind", "")).upper() == "YES":
            types.append("SAP")
        if str(r.get("gifted_ind", "")).upper() == "YES":
            types.append("GEP")
        if str(r.get("autonomous_ind", "")).upper() == "YES":
            types.append("Autonomous")
        if str(r.get("affiliated_ind", "")).upper() == "YES":
            types.append("Affiliated")

        # Coordinates
        try:
            lat = float(r["latitude"])
            lng = float(r["longitude"])
        except (KeyError, ValueError, TypeError):
            lat, lng = None, None

        schools[name] = {
            "name": name,
            "addr": r.get("address", "").strip().title(),
            "postal": str(r.get("postal_code", "")),
            "zone": zone,
            "gender": gender,
            "types": types,
            "lat": lat,
            "lng": lng,
            "ccas": [],
            "p2b": "Easy",
            "p2c": "Easy",
            "p2b_ratio": 0.0,
            "p2c_ratio": 0.0,
            "pv": False,
            "hist": [],
            "hist2b": {},
            "hist2c": {},
            "vibe": default_vibe("Easy"),
        }

    print(f"  Found {len(schools)} primary schools")
    return schools

def dgp_to_zone(dgp):
    north = ["WOODLANDS", "YISHUN", "SEMBAWANG", "ANG MO KIO", "BISHAN",
             "TOA PAYOH", "SERANGOON", "SENGKANG", "PUNGGOL", "HOUGANG",
             "THOMSON", "ANG MO KIO"]
    south = ["QUEENSTOWN", "BUKIT MERAH", "NOVENA", "ROCHOR", "OUTRAM",
              "MARINA", "DOWNTOWN", "TANJONG PAGAR"]
    east  = ["BEDOK", "TAMPINES", "PASIR RIS", "GEYLANG", "KALLANG",
              "MARINE PARADE", "KATONG", "POTONG PASIR"]
    west  = ["JURONG", "CLEMENTI", "BUKIT BATOK", "BUKIT PANJANG",
              "CHOA CHU KANG", "DOVER", "BUKIT TIMAH"]
    dgp_upper = dgp.upper()
    for kw in north:
        if kw in dgp_upper: return "North"
    for kw in south:
        if kw in dgp_upper: return "South"
    for kw in east:
        if kw in dgp_upper: return "East"
    for kw in west:
        if kw in dgp_upper: return "West"
    return "North"

def fetch_ccas(schools):
    print("Fetching CCAs from data.gov.sg...")
    url = "https://data.gov.sg/api/action/datastore_search?resource_id=d_cf4229e5cefe9a8bec60571a29ca6d31&limit=500"
    records = fetch_all(url)
    cca_map = {}
    for r in records:
        name = r.get("school_name", "").strip().title()
        cca = r.get("cca_generic_name", "").strip().title()
        if name and cca:
            cca_map.setdefault(name, set()).add(cca)
    for name, school in schools.items():
        school["ccas"] = sorted(cca_map.get(name, []))
    matched = sum(1 for s in schools.values() if s["ccas"])
    print(f"  Attached CCAs to {matched} schools")

# ─────────────────────────────────────────────
# 2. ELITE.COM.SG — Balloting Data
# ─────────────────────────────────────────────

def fetch_balloting(schools):
    print("Fetching balloting data from elite.com.sg...")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; P1Finder/1.0)"}

    for phase, phase_key in [("2B", "p2b"), ("2C", "p2c")]:
        url = f"https://elite.com.sg/primary-schools?phase={phase}"
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            table = soup.find("table")
            if not table:
                print(f"  No table found for Phase {phase}")
                continue

            rows = table.find_all("tr")[1:]  # skip header
            matched = 0
            for row in rows:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) < 4:
                    continue
                school_name = cells[0].strip().title()
                try:
                    vacancies = int(cells[1].replace(",", "").replace("-", "0"))
                    applicants = int(cells[2].replace(",", "").replace("-", "0"))
                    ratio = round(applicants / vacancies, 2) if vacancies > 0 else 0.0
                except (ValueError, ZeroDivisionError):
                    ratio = 0.0

                # Fuzzy match school name
                match = find_school(school_name, schools)
                if match:
                    schools[match][f"{phase_key}_ratio"] = ratio
                    schools[match][phase_key] = ratio_label(ratio)
                    if phase_key == "p2b" and ratio > 2.5:
                        schools[match]["pv"] = True
                    matched += 1

            print(f"  Phase {phase}: matched {matched} schools")
            time.sleep(1)

        except Exception as e:
            print(f"  Phase {phase} scrape failed: {e}")

def find_school(name, schools):
    if name in schools:
        return name
    name_lower = name.lower()
    for key in schools:
        if key.lower() == name_lower:
            return key
    # Partial match
    name_clean = name_lower.replace(" primary school", "").replace(" school", "").strip()
    for key in schools:
        key_clean = key.lower().replace(" primary school", "").replace(" school", "").strip()
        if name_clean == key_clean or name_clean in key_clean or key_clean in name_clean:
            return key
    return None

def ratio_label(r):
    if r < 1.2: return "Easy"
    if r < 2.0: return "Moderate"
    return "Competitive"

# ─────────────────────────────────────────────
# 3. HISTORICAL DATA — elite.com.sg years
# ─────────────────────────────────────────────

def fetch_history(schools):
    print("Fetching historical balloting data...")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; P1Finder/1.0)"}
    years = [2021, 2022, 2023, 2024, 2025]

    for year in years:
        for phase, phase_key in [("2B", "hist2b"), ("2C", "hist2c")]:
            url = f"https://elite.com.sg/primary-schools?phase={phase}&year={year}"
            try:
                r = requests.get(url, headers=headers, timeout=20)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                table = soup.find("table")
                if not table:
                    continue
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cells = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cells) < 3:
                        continue
                    school_name = cells[0].strip().title()
                    try:
                        vacancies = int(cells[1].replace(",", "").replace("-", "0"))
                        applicants = int(cells[2].replace(",", "").replace("-", "0"))
                        ratio = round(applicants / vacancies, 2) if vacancies > 0 else 0.0
                    except (ValueError, ZeroDivisionError):
                        ratio = 0.0
                    match = find_school(school_name, schools)
                    if match:
                        schools[match][phase_key][str(year)] = ratio
                time.sleep(0.5)
            except Exception as e:
                print(f"  {year} Phase {phase} failed: {e}")
                time.sleep(1)

    # Also build simple hist list [2023, 2024, 2025] for backward compat
    for s in schools.values():
        hist2c = s.get("hist2c", {})
        s["hist"] = [hist2c.get(str(y), s["p2c_ratio"]) for y in [2023, 2024, 2025]]

    print("  Historical data attached")

# ─────────────────────────────────────────────
# 4. VIBE SCORES — estimated from competitiveness
# ─────────────────────────────────────────────

def default_vibe(p2c_label):
    if p2c_label == "Competitive":
        return {"academic": 8.5, "homework": 8.0, "parentComp": 9.0, "teacherQ": 8.0, "culture": 6.5, "overall": 7.5}
    elif p2c_label == "Moderate":
        return {"academic": 6.5, "homework": 6.0, "parentComp": 6.5, "teacherQ": 7.5, "culture": 7.5, "overall": 7.0}
    else:
        return {"academic": 5.0, "homework": 4.5, "parentComp": 4.0, "teacherQ": 7.5, "culture": 8.5, "overall": 7.0}

def assign_vibes(schools):
    for s in schools.values():
        s["vibe"] = default_vibe(s["p2c"])

# ─────────────────────────────────────────────
# 5. OUTPUT
# ─────────────────────────────────────────────

def write_output(schools):
    valid = [s for s in schools.values() if s["lat"] and s["lng"]]
    valid.sort(key=lambda s: s["name"])
    out_path = Path("src/schools.json")
    out_path.write_text(json.dumps(valid, indent=2, ensure_ascii=False))
    print(f"\nWrote {len(valid)} schools to {out_path}")
    return valid

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== P1 School Data Scraper ===\n")

    print("Step 1: School directory")
    schools = fetch_school_directory()

    print("\nStep 2: CCAs")
    fetch_ccas(schools)

    print("\nStep 3: Balloting ratios")
    fetch_balloting(schools)

    print("\nStep 4: Historical data")
    fetch_history(schools)

    print("\nStep 5: Vibe scores")
    assign_vibes(schools)

    print("\nStep 6: Writing output")
    result = write_output(schools)

    # Summary
    competitive = sum(1 for s in result if s["p2c"] == "Competitive")
    moderate = sum(1 for s in result if s["p2c"] == "Moderate")
    easy = sum(1 for s in result if s["p2c"] == "Easy")
    print(f"\nSummary: {len(result)} schools | Competitive: {competitive} | Moderate: {moderate} | Easy: {easy}")
    print("Done!")
