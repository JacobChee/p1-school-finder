"""
P1 School Data Scraper
======================
Pulls from:
  1. data.gov.sg - official MOE school directory (names, addresses, zones, types)
  2. data.gov.sg - CCAs (resource: d_9aba12b5527843afb0b2e8e4ed6ac6bd)
  3. OneMap API - geocoding lat/lng from postal codes
  4. p1registration.sg - Phase 2B/2C balloting data (2025)

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
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; P1Finder/1.0; +https://p1-school-finder.vercel.app)",
        "Accept": "application/json",
    }
    records = []
    offset = 0
    retries = 5
    while True:
        for attempt in range(retries):
            try:
                r = requests.get(f"{url}&offset={offset}", headers=headers, timeout=30)
                if r.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise
                time.sleep(5)
        try:
            data = r.json()
            result = data["result"]
            batch = result["records"]
        except (KeyError, ValueError) as e:
            print(f"  Unexpected response: {e}, retrying after 30s...")
            time.sleep(30)
            continue
        records.extend(batch)
        print(f"  Fetched {len(records)}/{result['total']}")
        if len(records) >= result["total"]:
            break
        offset += len(batch)
        time.sleep(3)
    return records

def fetch_school_directory():
    print("Fetching school directory from data.gov.sg...")
    url = "https://data.gov.sg/api/action/datastore_search?resource_id=d_688b934f82c1059ed0a6993d2a829089&limit=100"
    records = fetch_all(url)
    print(f"  Total records fetched: {len(records)}")
    if records:
        sample = records[0]
        print(f"  Sample keys: {list(sample.keys())[:8]}")
        print(f"  Sample mainlevel_code: {sample.get('mainlevel_code', 'NOT FOUND')}")
        print(f"  Sample school_name: {sample.get('school_name', 'NOT FOUND')}")
    schools = {}
    primary_count = 0
    for r in records:
        level = r.get("mainlevel_code", "").upper().strip()
        if level != "PRIMARY":
            continue
        primary_count += 1
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

    print(f"  Primary records found: {primary_count}")
    print(f"  Schools with valid data: {len(schools)}")
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
    # Try multiple known resource IDs for CCAs
    url = "https://data.gov.sg/api/action/datastore_search?resource_id=d_9aba12b5527843afb0b2e8e4ed6ac6bd&limit=500"
    print(f"  Using CCA resource: d_9aba12b5527843afb0b2e8e4ed6ac6bd")
    try:
        time.sleep(5)  # extra pause before second API call
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
    except Exception as e:
        print(f"  CCAs fetch failed ({e}), skipping — will use empty lists")

# ─────────────────────────────────────────────
# 2. ELITE.COM.SG — Balloting Data
# ─────────────────────────────────────────────

def fetch_balloting(schools):
    print("Fetching balloting data from p1registration.sg...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    urls = {
        "p2b": "https://www.p1registration.sg/2025/07/10/p1-registration-phase-2b-results-2025-balloting-analysis/",
        "p2c": "https://www.p1registration.sg/2025/07/10/p1-registration-phase-2c-results-2025-balloting-analysis/",
    }

    for phase_key, url in urls.items():
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            tables = soup.find_all("table")
            print(f"  {phase_key}: found {len(tables)} tables")
            matched = 0
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
                    if len(cells) < 2:
                        continue
                    school_name = cells[0].strip().title()
                    # Find numeric ratio in cells
                    for cell in cells[1:]:
                        try:
                            val = float(cell.replace(",","").replace("%","").strip())
                            if 0.1 < val < 20:
                                match = find_school(school_name, schools)
                                if match:
                                    schools[match][f"{phase_key}_ratio"] = round(val, 2)
                                    schools[match][phase_key] = ratio_label(val)
                                    if phase_key == "p2b" and val > 1.0:
                                        schools[match]["pv"] = True
                                    matched += 1
                                break
                        except ValueError:
                            continue
            print(f"  {phase_key}: matched {matched} schools")

            # Also try MOE past vacancies page as fallback
            if matched == 0:
                print(f"  Trying MOE past vacancies page...")
                moe_url = "https://www.moe.gov.sg/primary/p1-registration/past-vacancies-and-balloting-data"
                try:
                    mr = requests.get(moe_url, headers=headers, timeout=20)
                    ms = BeautifulSoup(mr.text, "lxml")
                    for tbl in ms.find_all("table"):
                        rows = tbl.find_all("tr")
                        for row in rows[1:]:
                            cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
                            if len(cells) < 3:
                                continue
                            school_name = cells[0].strip().title()
                            match = find_school(school_name, schools)
                            if match:
                                try:
                                    vacancies = int(cells[1].replace(",",""))
                                    applicants = int(cells[2].replace(",",""))
                                    ratio = round(applicants/vacancies, 2) if vacancies > 0 else 0
                                    schools[match][f"{phase_key}_ratio"] = ratio
                                    schools[match][phase_key] = ratio_label(ratio)
                                    matched += 1
                                except (ValueError, ZeroDivisionError):
                                    pass
                    print(f"  MOE fallback: matched {matched} schools")
                except Exception as e:
                    print(f"  MOE fallback failed: {e}")

            time.sleep(2)
        except Exception as e:
            print(f"  {phase_key} failed: {e}")

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
# 3. HISTORICAL DATA — p1registration.sg
# ─────────────────────────────────────────────

def fetch_history(schools):
    print("Fetching historical balloting data from p1registration.sg...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    years = [2022, 2023, 2024, 2025]

    for year in years:
        for phase, phase_key in [("2B", "hist2b"), ("2C", "hist2c")]:
            slug = "phase-2b" if phase == "2B" else "phase-2c"
            url = f"https://www.p1registration.sg/{year}/07/10/p1-registration-{slug}-results-{year}-balloting-analysis/"
            try:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "lxml")
                for table in soup.find_all("table"):
                    rows = table.find_all("tr")
                    for row in rows[1:]:
                        cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
                        if len(cells) < 2:
                            continue
                        school_name = cells[0].strip().title()
                        for cell in cells[1:]:
                            try:
                                val = float(cell.replace(",","").replace("%","").strip())
                                if 0.1 < val < 20:
                                    match = find_school(school_name, schools)
                                    if match:
                                        schools[match][phase_key][str(year)] = round(val, 2)
                                    break
                            except ValueError:
                                continue
                time.sleep(1)
            except Exception as e:
                print(f"  {year} Phase {phase} failed: {e}")

    # Build simple hist list for backward compat
    for s in schools.values():
        hist2c = s.get("hist2c", {})
        s["hist"] = [hist2c.get(str(y), s["p2c_ratio"]) for y in [2023, 2024, 2025]]

    print("  Historical data attached")

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

def geocode_schools(schools):
    """Use OneMap API to get lat/lng from postal code"""
    print("Geocoding schools via OneMap...")
    geocoded = 0
    for name, s in schools.items():
        if s.get("lat") and s.get("lng"):
            continue
        postal = s.get("postal", "")
        if not postal:
            continue
        try:
            r = requests.get(
                f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={postal}&returnGeom=Y&getAddrDetails=Y&pageNum=1",
                timeout=10
            )
            data = r.json()
            if data.get("results"):
                s["lat"] = float(data["results"][0]["LATITUDE"])
                s["lng"] = float(data["results"][0]["LONGITUDE"])
                geocoded += 1
            time.sleep(0.3)
        except Exception:
            pass
    print(f"  Geocoded {geocoded} schools")

def write_output(schools):
    valid = [s for s in schools.values() if s.get("lat") and s.get("lng")]
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

    print("\nStep 5: Geocoding")
    geocode_schools(schools)

    print("\nStep 6: Vibe scores")
    assign_vibes(schools)

    print("\nStep 7: Writing output")
    result = write_output(schools)

    # Summary
    competitive = sum(1 for s in result if s["p2c"] == "Competitive")
    moderate = sum(1 for s in result if s["p2c"] == "Moderate")
    easy = sum(1 for s in result if s["p2c"] == "Easy")
    print(f"\nSummary: {len(result)} schools | Competitive: {competitive} | Moderate: {moderate} | Easy: {easy}")
    print("Done!")
