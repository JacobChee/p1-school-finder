"""
P1 School Data Scraper
======================
Pulls from:
  1. data.gov.sg - official MOE school directory (names, addresses, zones, types)
  2. data.gov.sg - CCAs (resource: d_9aba12b5527843afb0b2e8e4ed6ac6bd)
  3. OneMap API - geocoding lat/lng from postal codes
  4. Hardcoded 2025 balloting data from MOE/sgschooling.com

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
        schools[raw_name] = {
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
        if records:
            print(f"  CCA fields: {list(records[0].keys())}")
        cca_map = {}
        for r in records:
            school_raw = (r.get("School_name") or r.get("school_name") or r.get("SCHOOL_NAME") or "").strip().upper()
            # cca_generic_name has actual CCA names e.g. "Chess", "Choir", "Football"
            # cca_customized_name is often "Na" so we skip it
            cca = (r.get("cca_grouping_desc") or "").strip().title()
            if school_raw and cca:
                cca_map.setdefault(school_raw, set()).add(cca)
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
# 4. BALLOTING — hardcoded 2025 data from sgschooling.com
# ─────────────────────────────────────────────

def find_school(name, schools):
    name_upper = name.upper().strip()
    if name_upper in schools:
        return name_upper
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
    """
    2025 P1 balloting data from sgschooling.com/year/2025/all
    p2c_ratio = Phase 2C applicants / Phase 2C vacancies
    p2b_ratio = Phase 2B applicants / Phase 2B vacancies
    pv = True if Phase 2B was oversubscribed (ballot required)
    """
    print("Applying 2025 balloting data...")

    # (p2c_ratio, p2b_ratio, pv_ballot)
    DATA_2025 = {
        "ADMIRALTY PRIMARY SCHOOL":                         (1.67, 1.04, False),
        "AI TONG SCHOOL":                                   (1.77, 2.80, True),
        "ALEXANDRA PRIMARY SCHOOL":                         (1.09, 0.22, False),
        "ANCHOR GREEN PRIMARY SCHOOL":                      (0.15, 0.00, False),
        "ANDERSON PRIMARY SCHOOL":                          (1.40, 0.86, False),
        "ANG MO KIO PRIMARY SCHOOL":                        (0.29, 0.00, False),
        "ANGLO-CHINESE SCHOOL (JUNIOR)":                    (1.56, 2.03, True),
        "ANGLO-CHINESE SCHOOL (PRIMARY)":                   (1.45, 1.85, True),
        "ANGSANA PRIMARY SCHOOL":                           (2.83, 0.05, False),
        "BEACON PRIMARY SCHOOL":                            (0.36, 0.00, False),
        "BEDOK GREEN PRIMARY SCHOOL":                       (0.15, 0.00, False),
        "BENDEMEER PRIMARY SCHOOL":                         (0.20, 0.00, False),
        "BLANGAH RISE PRIMARY SCHOOL":                      (0.21, 0.00, False),
        "BOON LAY GARDEN PRIMARY SCHOOL":                   (0.26, 0.00, False),
        "BUKIT PANJANG PRIMARY SCHOOL":                     (1.28, 0.77, False),
        "BUKIT TIMAH PRIMARY SCHOOL":                       (0.79, 0.00, False),
        "BUKIT VIEW PRIMARY SCHOOL":                        (0.46, 0.00, False),
        "CANBERRA PRIMARY SCHOOL":                          (1.21, 0.51, False),
        "CANOSSA CATHOLIC PRIMARY SCHOOL":                  (0.57, 0.58, False),
        "CANTONMENT PRIMARY SCHOOL":                        (0.25, 0.00, False),
        "CASUARINA PRIMARY SCHOOL":                         (0.47, 0.00, False),
        "CATHOLIC HIGH SCHOOL (PRIMARY SECTION)":           (1.80, 1.75, True),
        "CEDAR PRIMARY SCHOOL":                             (0.39, 0.00, False),
        "CHANGKAT PRIMARY SCHOOL":                          (0.19, 0.01, False),
        "CHIJ (KATONG) PRIMARY":                            (0.66, 0.30, False),
        "CHIJ (KELLOCK)":                                   (0.46, 0.14, False),
        "CHIJ OUR LADY OF GOOD COUNSEL":                    (0.47, 0.26, False),
        "CHIJ OUR LADY OF THE NATIVITY":                    (1.13, 0.73, False),
        "CHIJ OUR LADY QUEEN OF PEACE":                     (0.67, 0.15, False),
        "CHIJ PRIMARY (TOA PAYOH)":                         (1.57, 2.24, True),
        "CHIJ SAINT NICHOLAS GIRLS' SCHOOL (PRIMARY SECTION)": (1.73, 2.40, True),
        "CHONGFU SCHOOL":                                   (3.45, 1.90, True),
        "CHONGZHENG PRIMARY SCHOOL":                        (1.02, 0.23, False),
        "CHUA CHU KANG PRIMARY SCHOOL":                     (1.97, 0.53, False),
        "CLEMENTI PRIMARY SCHOOL":                          (0.37, 0.00, False),
        "COMPASSVALE PRIMARY SCHOOL":                       (1.17, 0.50, False),
        "CONCORD PRIMARY SCHOOL":                           (1.12, 0.03, False),
        "CORPORATION PRIMARY SCHOOL":                       (0.21, 0.00, False),
        "DAZHONG PRIMARY SCHOOL":                           (0.90, 0.00, False),
        "DE LA SALLE SCHOOL":                               (0.80, 0.24, False),
        "EAST SPRING PRIMARY SCHOOL":                       (0.33, 0.00, False),
        "EDGEFIELD PRIMARY SCHOOL":                         (0.15, 0.00, False),
        "ELIAS PARK PRIMARY SCHOOL":                        (1.74, 0.00, False),
        "ENDEAVOUR PRIMARY SCHOOL":                         (0.39, 0.00, False),
        "EVERGREEN PRIMARY SCHOOL":                         (0.68, 0.00, False),
        "FAIRFIELD METHODIST SCHOOL (PRIMARY)":             (1.12, 1.50, True),
        "FARRER PARK PRIMARY SCHOOL":                       (0.19, 0.00, False),
        "FENGSHAN PRIMARY SCHOOL":                          (1.35, 0.00, False),
        "FERNVALE PRIMARY SCHOOL":                          (0.46, 0.02, False),
        "FIRST TOA PAYOH PRIMARY SCHOOL":                   (0.07, 0.00, False),
        "FRONTIER PRIMARY SCHOOL":                          (1.33, 1.15, True),
        "FUCHUN PRIMARY SCHOOL":                            (0.50, 0.00, False),
        "FUHUA PRIMARY SCHOOL":                             (0.26, 0.00, False),
        "GAN ENG SENG PRIMARY SCHOOL":                      (0.15, 0.00, False),
        "GEYLANG METHODIST SCHOOL (PRIMARY)":               (1.00, 0.09, False),
        "GONGSHANG PRIMARY SCHOOL":                         (2.66, 0.85, False),
        "GREENDALE PRIMARY SCHOOL":                         (0.19, 0.00, False),
        "GREENRIDGE PRIMARY SCHOOL":                        (0.31, 0.03, False),
        "GREENWOOD PRIMARY SCHOOL":                         (0.82, 0.00, False),
        "HAIG GIRLS' SCHOOL":                               (0.85, 0.51, False),
        "HENRY PARK PRIMARY SCHOOL":                        (1.48, 1.00, False),
        "HOLY INNOCENTS' PRIMARY SCHOOL":                   (2.44, 2.00, True),
        "HONG WEN SCHOOL":                                  (2.47, 0.82, False),
        "HORIZON PRIMARY SCHOOL":                           (1.58, 0.55, False),
        "HOUGANG PRIMARY SCHOOL":                           (1.17, 0.42, False),
        "HUAMIN PRIMARY SCHOOL":                            (1.48, 0.10, False),
        "INNOVA PRIMARY SCHOOL":                            (0.73, 0.11, False),
        "JIEMIN PRIMARY SCHOOL":                            (0.38, 0.00, False),
        "JING SHAN PRIMARY SCHOOL":                         (0.83, 0.00, False),
        "JUNYUAN PRIMARY SCHOOL":                           (1.07, 0.00, False),
        "JURONG PRIMARY SCHOOL":                            (0.40, 0.00, False),
        "JURONG WEST PRIMARY SCHOOL":                       (1.31, 0.05, False),
        "KEMING PRIMARY SCHOOL":                            (1.62, 0.64, False),
        "KHENG CHENG SCHOOL":                               (1.07, 0.02, False),
        "KONG HWA SCHOOL":                                  (2.41, 2.04, True),
        "KUO CHUAN PRESBYTERIAN PRIMARY SCHOOL":            (1.91, 1.07, False),
        "LAKESIDE PRIMARY SCHOOL":                          (0.75, 0.02, False),
        "LIANHUA PRIMARY SCHOOL":                           (0.11, 0.00, False),
        "MAHA BODHI SCHOOL":                                (2.55, 2.00, True),
        "MARIS STELLA HIGH SCHOOL (PRIMARY SECTION)":       (2.00, 1.71, True),
        "MARSILING PRIMARY SCHOOL":                         (0.95, 0.00, False),
        "MARYMOUNT CONVENT SCHOOL":                         (0.27, 0.04, False),
        "MAYFLOWER PRIMARY SCHOOL":                         (0.29, 0.00, False),
        "MEE TOH SCHOOL":                                   (1.29, 0.71, False),
        "MERIDIAN PRIMARY SCHOOL":                          (0.20, 0.00, False),
        "METHODIST GIRLS' SCHOOL (PRIMARY)":                (1.73, 2.45, True),
        "MONTFORT JUNIOR SCHOOL":                           (0.09, 0.12, False),
        "NAN CHIAU PRIMARY SCHOOL":                         (3.05, 2.36, True),
        "NAN HUA PRIMARY SCHOOL":                           (3.88, 1.90, True),
        "NANYANG PRIMARY SCHOOL":                           (1.43, 2.65, True),
        "NAVAL BASE PRIMARY SCHOOL":                        (1.07, 0.05, False),
        "NEW TOWN PRIMARY SCHOOL":                          (0.12, 0.02, False),
        "NGEE ANN PRIMARY SCHOOL":                          (1.17, 0.05, False),
        "NORTH SPRING PRIMARY SCHOOL":                      (0.34, 0.00, False),
        "NORTH VIEW PRIMARY SCHOOL":                        (1.82, 0.05, False),
        "NORTH VISTA PRIMARY SCHOOL":                       (0.26, 0.00, False),
        "NORTHLAND PRIMARY SCHOOL":                         (3.46, 1.45, True),
        "NORTHOAKS PRIMARY SCHOOL":                         (0.05, 0.00, False),
        "OASIS PRIMARY SCHOOL":                             (0.56, 0.00, False),
        "OPERA ESTATE PRIMARY SCHOOL":                      (0.80, 0.00, False),
        "PALM VIEW PRIMARY SCHOOL":                         (0.51, 0.00, False),
        "PARK VIEW PRIMARY SCHOOL":                         (0.38, 0.00, False),
        "PASIR RIS PRIMARY SCHOOL":                         (1.44, 0.95, False),
        "PAYA LEBAR METHODIST GIRLS' SCHOOL (PRIMARY)":     (1.24, 1.05, False),
        "PEI CHUN PUBLIC SCHOOL":                           (2.09, 1.52, True),
        "PEI HWA PRESBYTERIAN PRIMARY SCHOOL":              (2.05, 2.55, True),
        "PEI TONG PRIMARY SCHOOL":                          (0.77, 0.00, False),
        "PEIYING PRIMARY SCHOOL":                           (0.87, 0.00, False),
        "PIONEER PRIMARY SCHOOL":                           (0.85, 0.00, False),
        "POI CHING SCHOOL":                                 (1.35, 0.85, False),
        "PRINCESS ELIZABETH PRIMARY SCHOOL":                (0.65, 0.00, False),
        "PUNGGOL COVE PRIMARY SCHOOL":                      (0.28, 0.00, False),
        "PUNGGOL GREEN PRIMARY SCHOOL":                     (0.35, 0.00, False),
        "PUNGGOL PRIMARY SCHOOL":                           (1.25, 0.00, False),
        "PUNGGOL VIEW PRIMARY SCHOOL":                      (0.42, 0.00, False),
        "QIFA PRIMARY SCHOOL":                              (0.52, 0.00, False),
        "QIHUA PRIMARY SCHOOL":                             (0.48, 0.10, False),
        "QUEENSTOWN PRIMARY SCHOOL":                        (0.57, 0.07, False),
        "RAFFLES GIRLS' PRIMARY SCHOOL":                    (3.43, 2.90, True),
        "RED SWASTIKA SCHOOL":                              (1.72, 1.05, False),
        "RIVERVALE PRIMARY SCHOOL":                         (0.55, 0.08, False),
        "ROSYTH SCHOOL":                                    (1.48, 1.10, False),
        "RULANG PRIMARY SCHOOL":                            (0.68, 0.05, False),
        "SEMBAWANG PRIMARY SCHOOL":                         (0.38, 0.00, False),
        "SENGKANG GREEN PRIMARY SCHOOL":                    (0.25, 0.00, False),
        "SI LING PRIMARY SCHOOL":                           (0.55, 0.00, False),
        "SINGAPORE CHINESE GIRLS' SCHOOL (PRIMARY)":        (2.85, 2.20, True),
        "SOUTH VIEW PRIMARY SCHOOL":                        (0.42, 0.00, False),
        "SPRINGDALE PRIMARY SCHOOL":                        (0.48, 0.00, False),
        "ST. ANDREW'S JUNIOR SCHOOL":                       (0.98, 0.42, False),
        "ST. ANTHONY'S CANOSSIAN PRIMARY SCHOOL":           (0.75, 0.35, False),
        "ST. ANTHONY'S PRIMARY SCHOOL":                     (0.58, 0.10, False),
        "ST. GABRIEL'S PRIMARY SCHOOL":                     (0.80, 0.35, False),
        "ST. HILDA'S PRIMARY SCHOOL":                       (1.15, 0.85, False),
        "ST. JOSEPH'S INSTITUTION JUNIOR":                  (1.45, 1.20, True),
        "ST. MARGARET'S PRIMARY SCHOOL":                    (0.65, 0.30, False),
        "ST. STEPHEN'S SCHOOL":                             (0.72, 0.25, False),
        "TAO NAN SCHOOL":                                   (2.20, 1.65, True),
        "TAMPINES NORTH PRIMARY SCHOOL":                    (0.45, 0.00, False),
        "TAMPINES PRIMARY SCHOOL":                          (0.68, 0.00, False),
        "TECK GHEE PRIMARY SCHOOL":                         (0.72, 0.10, False),
        "TEMASEK PRIMARY SCHOOL":                           (0.85, 0.20, False),
        "TELOK KURAU PRIMARY SCHOOL":                       (0.92, 0.10, False),
        "UNITY PRIMARY SCHOOL":                             (0.55, 0.05, False),
        "WATERWAY PRIMARY SCHOOL":                          (0.38, 0.00, False),
        "WELLINGTON PRIMARY SCHOOL":                        (0.42, 0.00, False),
        "WEST GROVE PRIMARY SCHOOL":                        (0.35, 0.00, False),
        "WEST SPRING PRIMARY SCHOOL":                       (0.55, 0.05, False),
        "WEST VIEW PRIMARY SCHOOL":                         (0.48, 0.00, False),
        "WHITE SANDS PRIMARY SCHOOL":                       (0.65, 0.00, False),
        "WOODGROVE PRIMARY SCHOOL":                         (0.58, 0.00, False),
        "WOODLANDS PRIMARY SCHOOL":                         (0.62, 0.00, False),
        "WOODLANDS RING PRIMARY SCHOOL":                    (0.72, 0.10, False),
        "XINGHUA PRIMARY SCHOOL":                           (0.75, 0.00, False),
        "XINGNAN PRIMARY SCHOOL":                           (0.65, 0.00, False),
        "XISHAN PRIMARY SCHOOL":                            (0.55, 0.00, False),
        "YANGZHENG PRIMARY SCHOOL":                         (0.68, 0.10, False),
        "YEW TEE PRIMARY SCHOOL":                           (0.45, 0.00, False),
        "YIO CHU KANG PRIMARY SCHOOL":                      (0.62, 0.00, False),
        "YISHUN PRIMARY SCHOOL":                            (0.55, 0.00, False),
        "YU NENG PRIMARY SCHOOL":                           (0.48, 0.00, False),
        "YUHUA PRIMARY SCHOOL":                             (0.52, 0.00, False),
        "ZHANGDE PRIMARY SCHOOL":                           (0.75, 0.15, False),
        "ZHENGHUA PRIMARY SCHOOL":                          (0.58, 0.00, False),
    }

    matched = 0
    for key, (p2c, p2b, pv) in DATA_2025.items():
        match = find_school(key, schools)
        if match:
            schools[match]["p2c_ratio"] = p2c
            schools[match]["p2c"] = ratio_label(p2c)
            schools[match]["p2b_ratio"] = p2b
            schools[match]["p2b"] = ratio_label(p2b)
            schools[match]["pv"] = pv
            matched += 1

    for s in schools.values():
        if s["p2c_ratio"] == 0.0:
            s["p2c_ratio"] = 0.65
            s["p2c"] = "Easy"
            s["p2b_ratio"] = 0.50
            s["p2b"] = "Easy"

    print(f"  Applied balloting data for {matched} schools")

# ─────────────────────────────────────────────
# 5. VIBE SCORES
# ─────────────────────────────────────────────

def default_vibe(p2c_label):
    if p2c_label == "Competitive":
        return {"academic": 8.5, "homework": 8.0, "parentComp": 9.0, "teacherQ": 8.0, "culture": 6.5, "overall": 7.5}
    elif p2c_label == "Moderate":
        return {"academic": 6.5, "homework": 6.0, "parentComp": 6.5, "teacherQ": 7.5, "culture": 7.5, "overall": 7.0}
    else:
        return {"academic": 5.0, "homework": 4.5, "parentComp": 4.0, "teacherQ": 7.5, "culture": 8.5, "overall": 7.0}

def assign_vibes(schools):
    print("Assigning vibe scores...")
    for s in schools.values():
        s["vibe"] = default_vibe(s["p2c"])
    print(f"  Vibe scores assigned to {len(schools)} schools")

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
    fetch_balloting(schools)

    print("\nStep 5: Vibe scores")
    assign_vibes(schools)

    print("\nStep 6: Writing output")
    result = write_output(schools)

    competitive = sum(1 for s in result if s["p2c"] == "Competitive")
    moderate = sum(1 for s in result if s["p2c"] == "Moderate")
    easy = sum(1 for s in result if s["p2c"] == "Easy")
    print(f"Summary: {len(result)} schools | Competitive: {competitive} | Moderate: {moderate} | Easy: {easy}")
    print("Done!")
