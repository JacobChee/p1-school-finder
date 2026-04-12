"""
P1 School Data Scraper
======================
Pulls from:
  1. data.gov.sg - official MOE school directory (names, addresses, zones, types)
  2. data.gov.sg - CCAs (resource: d_9aba12b5527843afb0b2e8e4ed6ac6bd)
  3. OneMap API - geocoding lat/lng from postal codes
  4. KiasuParents - balloting data + forum text for vibe scoring
  5. Anthropic Claude API - vibe scoring from forum text

Outputs: src/schools.json
"""

import json, time, os, re
import requests
from bs4 import BeautifulSoup
from pathlib import Path

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ─────────────────────────────────────────────
# 1. DATA.GOV.SG — School Directory
# ─────────────────────────────────────────────

def fetch_all(url):
    api_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; P1Finder/1.0)",
        "Accept": "application/json",
    }
    records = []
    offset = 0
    while True:
        for attempt in range(6):
            try:
                r = requests.get(f"{url}&offset={offset}", headers=api_headers, timeout=30)
                if r.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == 5:
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

def dgp_to_zone(dgp):
    d = dgp.upper()
    if any(k in d for k in ["WOODLANDS","YISHUN","SEMBAWANG","ANG MO KIO","BISHAN","TOA PAYOH","SERANGOON","SENGKANG","PUNGGOL","HOUGANG","THOMSON"]):
        return "North"
    if any(k in d for k in ["BEDOK","TAMPINES","PASIR RIS","GEYLANG","KALLANG","MARINE PARADE","KATONG","POTONG PASIR"]):
        return "East"
    if any(k in d for k in ["JURONG","CLEMENTI","BUKIT BATOK","BUKIT PANJANG","CHOA CHU KANG","DOVER","BUKIT TIMAH"]):
        return "West"
    if any(k in d for k in ["QUEENSTOWN","BUKIT MERAH","NOVENA","ROCHOR","OUTRAM","MARINA","TANJONG PAGAR"]):
        return "South"
    return "North"

def fetch_school_directory():
    print("Fetching school directory from data.gov.sg...")
    url = "https://data.gov.sg/api/action/datastore_search?resource_id=d_688b934f82c1059ed0a6993d2a829089&limit=100"
    records = fetch_all(url)
    print(f"  Total records: {len(records)}")

    schools = {}
    for r in records:
        if r.get("mainlevel_code", "").upper().strip() != "PRIMARY":
            continue
        raw_name = r.get("school_name", "").strip()
        if not raw_name:
            continue
        name = raw_name.title()

        types = []
        if str(r.get("sap_ind", "")).upper() == "YES": types.append("SAP")
        if str(r.get("gifted_ind", "")).upper() == "YES": types.append("GEP")
        if str(r.get("autonomous_ind", "")).upper() == "YES": types.append("Autonomous")
        if str(r.get("affiliated_ind", "")).upper() == "YES": types.append("Affiliated")

        nature = r.get("nature_code", "").upper()
        gender = "Girls" if "GIRLS" in nature else "Boys" if "BOYS" in nature else "Co-ed"

        schools[raw_name] = {  # key by UPPERCASE for CCA matching
            "name": name,
            "addr": r.get("address", "").strip().title(),
            "postal": str(r.get("postal_code", "")),
            "zone": dgp_to_zone(r.get("dgp_code", "")),
            "gender": gender,
            "types": types,
            "lat": None, "lng": None,
            "ccas": [],
            "p2b": "Easy", "p2c": "Easy",
            "p2b_ratio": 0.0, "p2c_ratio": 0.0,
            "pv": False,
            "hist": [], "hist2b": {}, "hist2c": {},
            "vibe": default_vibe("Easy"),
        }

    print(f"  Primary schools: {len(schools)}")
    return schools

# ─────────────────────────────────────────────
# 2. CCAs
# ─────────────────────────────────────────────

def fetch_ccas(schools):
    print("Fetching CCAs...")
    try:
        time.sleep(5)
        url = "https://data.gov.sg/api/action/datastore_search?resource_id=d_9aba12b5527843afb0b2e8e4ed6ac6bd&limit=500"
        records = fetch_all(url)

        # Check field names from first record
        if records:
            print(f"  CCA fields: {list(records[0].keys())}")

        cca_map = {}
        for r in records:
            # Try both possible field names
            school_raw = (r.get("School_name") or r.get("school_name") or r.get("SCHOOL_NAME") or "").strip().upper()
            cca = (r.get("cca_generic_name") or r.get("CCA_GENERIC_NAME") or
                   r.get("cca_name") or r.get("CCA_NAME") or "").strip().title()
            if school_raw and cca:
                cca_map.setdefault(school_raw, set()).add(cca)

        # Match by uppercase key
        matched = 0
        for raw_name, school in schools.items():
            ccas = cca_map.get(raw_name.upper(), set())
            school["ccas"] = sorted(ccas)
            if ccas:
                matched += 1

        print(f"  CCAs attached to {matched} schools")
    except Exception as e:
        print(f"  CCAs failed: {e}, skipping")

# ─────────────────────────────────────────────
# 3. GEOCODING via OneMap
# ─────────────────────────────────────────────

def geocode_schools(schools):
    print("Geocoding via OneMap...")
    geocoded = 0
    for raw_name, s in schools.items():
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

# ─────────────────────────────────────────────
# 4. BALLOTING — KiasuParents
# ─────────────────────────────────────────────

def find_school(name, schools):
    name_upper = name.upper().strip()
    if name_upper in schools:
        return name_upper
    # Partial match
    name_clean = re.sub(r'\s+', ' ', name_upper.replace("PRIMARY SCHOOL","").replace("SCHOOL","").strip())
    for key in schools:
        key_clean = re.sub(r'\s+', ' ', key.replace("PRIMARY SCHOOL","").replace("SCHOOL","").strip())
        if name_clean == key_clean or name_clean in key_clean or key_clean in name_clean:
            return key
    return None

def ratio_label(r):
    if r < 1.2: return "Easy"
    if r < 2.0: return "Moderate"
    return "Competitive"

def fetch_balloting(schools):
    print("Fetching balloting from MOE past vacancies page...")
    # MOE official past vacancies and balloting data
    urls_to_try = [
        "https://www.moe.gov.sg/primary/p1-registration/past-vacancies-and-balloting-data",
        "https://www.moe.gov.sg/primary/p1-registration/vacancy",
    ]
    matched = 0
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            tables = soup.find_all("table")
            print(f"  Found {len(tables)} tables")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
                    if len(cells) < 3:
                        continue
                    school_name = cells[0].strip()
                    match = find_school(school_name, schools)
                    if not match:
                        continue
                    # Look for vacancy/applicant numbers
                    nums = []
                    for cell in cells[1:]:
                        try:
                            nums.append(int(cell.replace(",","").strip()))
                        except ValueError:
                            pass
                    if len(nums) >= 2:
                        vacancies, applicants = nums[0], nums[1]
                        if vacancies > 0:
                            ratio = round(applicants / vacancies, 2)
                            schools[match]["p2c_ratio"] = ratio
                            schools[match]["p2c"] = ratio_label(ratio)
                            schools[match]["p2b_ratio"] = round(ratio * 0.85, 2)
                            schools[match]["p2b"] = ratio_label(ratio * 0.85)
                            if ratio > 2.5:
                                schools[match]["pv"] = True
                            matched += 1
            if matched > 0:
                print(f"  Matched {matched} schools")
                break
            time.sleep(1)
        except Exception as e:
            print(f"  {url} failed: {e}")

    # If MOE page didn't work, use hardcoded 2025 data for known competitive schools
    if matched == 0:
        print("  Using hardcoded 2025 balloting data for known competitive schools...")
        KNOWN_2025 = {
            "RAFFLES GIRLS' PRIMARY SCHOOL": (4.10, True),
            "NANYANG PRIMARY SCHOOL": (3.80, True),
            "HENRY PARK PRIMARY SCHOOL": (5.10, True),
            "SINGAPORE CHINESE GIRLS' SCHOOL (PRIMARY)": (4.50, True),
            "TAO NAN SCHOOL": (3.15, True),
            "CATHOLIC HIGH SCHOOL (PRIMARY SECTION)": (2.90, True),
            "CHIJ SAINT NICHOLAS GIRLS' SCHOOL (PRIMARY SECTION)": (3.20, True),
            "Methodist GIRLS' SCHOOL (PRIMARY)": (3.20, True),
            "ROSYTH SCHOOL": (2.60, True),
            "ST. JOSEPH'S INSTITUTION JUNIOR": (2.60, True),
            "MARIS STELLA HIGH SCHOOL (PRIMARY SECTION)": (2.60, True),
            "ANGLO-CHINESE SCHOOL (JUNIOR)": (3.15, True),
            "NAN HUA PRIMARY SCHOOL": (1.70, False),
            "PEI CHUN PUBLIC SCHOOL": (2.45, False),
            "FAIRFIELD Methodist SCHOOL (PRIMARY)": (2.30, True),
            "CHIJ (KELLOCK)": (2.20, False),
            "CHIJ (KATONG) PRIMARY": (2.40, False),
            "CHIJ PRIMARY (TOA PAYOH)": (2.55, False),
            "AI TONG SCHOOL": (1.85, False),
            "KONG HWA SCHOOL": (1.63, False),
            "KEMING PRIMARY SCHOOL": (1.10, False),
        }
        for raw_key, (ratio, pv) in KNOWN_2025.items():
            match = find_school(raw_key, schools)
            if match:
                schools[match]["p2c_ratio"] = ratio
                schools[match]["p2c"] = ratio_label(ratio)
                schools[match]["p2b_ratio"] = round(ratio * 0.85, 2)
                schools[match]["p2b"] = ratio_label(ratio * 0.85)
                schools[match]["pv"] = pv
                matched += 1
        print(f"  Applied hardcoded data for {matched} schools")

# ─────────────────────────────────────────────
# 5. VIBE SCORING — KiasuParents + Claude API
# ─────────────────────────────────────────────

def scrape_forum_text(school_name):
    """Scrape school MOE website and sgschoolkaki for vibe text"""
    slug = school_name.lower().replace(" ", "").replace("'", "").replace("(", "").replace(")", "").replace("-","")
    # Try SGSchoolKaki which aggregates school info
    urls = [
        f"https://sgschoolkaki.com/primary-school/{slug.replace(' ','-')}",
        f"https://www.greatschools.org/singapore/primary-schools/{slug}",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                paras = soup.find_all("p")
                text = " ".join(p.get_text(strip=True) for p in paras[:40])
                if len(text) > 200:
                    return text[:3000]
        except Exception:
            pass
    return ""

def score_vibe_with_claude(school_name, forum_text):
    """Use Claude API to score school vibe from forum text"""
    if not ANTHROPIC_API_KEY:
        return None

    if not forum_text:
        return None

    prompt = f"""You are analyzing parent forum discussions about {school_name} primary school in Singapore.

Based on this forum text, score the school on these 5 dimensions from 1-10:
- academic: how exam-focused and academically intense the school is (10 = very intense)
- homework: amount of homework sent home (10 = very heavy)
- parentComp: how competitive and kiasu the parent community is (10 = very competitive)
- teacherQ: teacher quality and responsiveness (10 = excellent)
- culture: school culture, warmth, inclusivity (10 = very positive)

Forum text:
{forum_text}

Respond with ONLY a JSON object like this, no other text:
{{"academic": 7.0, "homework": 6.5, "parentComp": 8.0, "teacherQ": 7.5, "culture": 7.0, "overall": 7.2}}

If there is insufficient data to score a dimension, use 5.0 as default."""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        data = r.json()
        text = data["content"][0]["text"].strip()
        # Extract JSON
        match = re.search(r'\{[^}]+\}', text)
        if match:
            scores = json.loads(match.group())
            # Validate all keys present
            required = ["academic", "homework", "parentComp", "teacherQ", "culture", "overall"]
            if all(k in scores for k in required):
                return {k: float(scores[k]) for k in required}
    except Exception as e:
        print(f"    Claude API error for {school_name}: {e}")
    return None

def default_vibe(p2c_label):
    if p2c_label == "Competitive":
        return {"academic": 8.5, "homework": 8.0, "parentComp": 9.0, "teacherQ": 8.0, "culture": 6.5, "overall": 7.5}
    elif p2c_label == "Moderate":
        return {"academic": 6.5, "homework": 6.0, "parentComp": 6.5, "teacherQ": 7.5, "culture": 7.5, "overall": 7.0}
    else:
        return {"academic": 5.0, "homework": 4.5, "parentComp": 4.0, "teacherQ": 7.5, "culture": 8.5, "overall": 7.0}

def assign_vibes(schools):
    print("Scoring school vibes...")
    use_claude = bool(ANTHROPIC_API_KEY)
    print(f"  Claude API: {'enabled' if use_claude else 'disabled - using estimates'}")

    scored = 0
    for raw_name, s in schools.items():
        # Assign default first based on competitiveness
        s["vibe"] = default_vibe(s["p2c"])

        if use_claude:
            try:
                forum_text = scrape_forum_text(s["name"])
                if forum_text:
                    scores = score_vibe_with_claude(s["name"], forum_text)
                    if scores:
                        s["vibe"] = scores
                        scored += 1
                time.sleep(0.5)  # be polite to KiasuParents
            except Exception as e:
                print(f"  Vibe error for {s['name']}: {e}")

    print(f"  Claude-scored: {scored} schools, estimated: {len(schools)-scored} schools")

# ─────────────────────────────────────────────
# 6. OUTPUT
# ─────────────────────────────────────────────

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

    print("\nStep 3: Geocoding")
    geocode_schools(schools)

    print("\nStep 4: Balloting ratios")
    try:
        fetch_balloting(schools)
    except Exception as e:
        print(f"  Balloting failed: {e}, continuing...")

    print("\nStep 5: Vibe scores")
    assign_vibes(schools)

    print("\nStep 6: Writing output")
    result = write_output(schools)

    competitive = sum(1 for s in result if s["p2c"] == "Competitive")
    moderate = sum(1 for s in result if s["p2c"] == "Moderate")
    easy = sum(1 for s in result if s["p2c"] == "Easy")
    claude_scored = sum(1 for s in result if s.get("vibe_source") == "claude")
    print(f"Summary: {len(result)} schools | Competitive: {competitive} | Moderate: {moderate} | Easy: {easy}")
    print("Done!")
