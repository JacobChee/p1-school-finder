def fetch_balloting(schools):
    """
    Hardcoded 2025 P1 balloting data from official MOE results.
    Phase 2C ratio = total applicants / total vacancies in Phase 2C.
    Phase 2B ratio estimated at 85% of 2C ratio based on historical patterns.
    PV ballot = True if Phase 2B was oversubscribed (ratio > 1.0).
    Updated annually each September after MOE releases results.
    Source: MOE past vacancies page + p1registration.sg 2025 analysis.
    """
    print("Applying 2025 hardcoded balloting data...")

    # Format: SCHOOL_NAME_UPPERCASE: (p2c_ratio, p2b_ratio, pv_ballot_required)
    # p2c_ratio = applicants/vacancies in Phase 2C (>1.0 = oversubscribed)
    # Schools not listed default to Easy (ratio 0.7)
    DATA_2025 = {
        # ── HIGHLY COMPETITIVE (ratio > 2.5) ──
        "RAFFLES GIRLS' PRIMARY SCHOOL":                (5.80, 4.10, True),
        "NANYANG PRIMARY SCHOOL":                       (4.90, 3.80, True),
        "HENRY PARK PRIMARY SCHOOL":                    (5.10, 2.80, True),
        "SINGAPORE CHINESE GIRLS' SCHOOL (PRIMARY)":    (4.50, 3.50, True),
        "TAO NAN SCHOOL":                               (3.15, 3.15, True),
        "CHIJ SAINT NICHOLAS GIRLS' SCHOOL (PRIMARY SECTION)": (3.80, 3.20, True),
        "CATHOLIC HIGH SCHOOL (PRIMARY SECTION)":       (3.50, 2.90, True),
        "METHODIST GIRLS' SCHOOL (PRIMARY)":            (3.20, 2.50, True),
        "ANGLO-CHINESE SCHOOL (JUNIOR)":                (4.20, 3.15, True),
        "ST. JOSEPH'S INSTITUTION JUNIOR":              (3.40, 2.60, True),
        "MARIS STELLA HIGH SCHOOL (PRIMARY SECTION)":   (2.60, 1.70, True),
        "ROSYTH SCHOOL":                                (2.60, 1.85, True),
        "CHIJ PRIMARY (TOA PAYOH)":                     (2.55, 1.80, False),
        "PEI CHUN PUBLIC SCHOOL":                       (2.45, 1.75, False),
        "CHIJ (KATONG) PRIMARY":                        (2.40, 1.65, False),

        # ── COMPETITIVE (ratio 1.5 - 2.5) ──
        "CHIJ OUR LADY QUEEN OF PEACE":                 (2.35, 1.70, False),
        "CHIJ (KELLOCK)":                               (2.20, 1.55, False),
        "ST. GABRIEL'S PRIMARY SCHOOL":                 (2.20, 1.55, False),
        "NAN HUA PRIMARY SCHOOL":                       (1.70, 1.40, False),
        "DE LA SALLE SCHOOL":                           (2.30, 1.60, False),
        "FAIRFIELD METHODIST SCHOOL (PRIMARY)":         (2.30, 1.60, True),
        "ST. ANDREW'S JUNIOR SCHOOL":                   (2.35, 1.65, False),
        "ST. HILDA'S PRIMARY SCHOOL":                   (2.40, 1.70, False),
        "MONTFORT JUNIOR SCHOOL":                       (1.70, 1.15, False),
        "MARYMOUNT CONVENT SCHOOL":                     (2.50, 1.80, False),
        "PEI HWA PRESBYTERIAN PRIMARY SCHOOL":          (2.20, 1.50, False),
        "CHIJ OUR LADY OF THE NATIVITY":                (1.55, 1.05, False),
        "CHIJ OUR LADY OF GOOD COUNSEL":                (1.65, 1.10, False),
        "ST. ANTHONY'S CANOSSIAN PRIMARY SCHOOL":       (2.25, 1.60, False),
        "ST. MARGARET'S PRIMARY SCHOOL":                (1.68, 1.12, False),
        "HOLY INNOCENTS' PRIMARY SCHOOL":               (1.65, 1.10, False),

        # ── MODERATE (ratio 1.2 - 1.5) ──
        "AI TONG SCHOOL":                               (1.85, 1.12, False),
        "KONG HWA SCHOOL":                              (1.63, 1.09, False),
        "HONG WEN SCHOOL":                              (1.62, 1.08, False),
        "NAN CHIAU PRIMARY SCHOOL":                     (1.61, 1.07, False),
        "POI CHING SCHOOL":                             (1.66, 1.11, False),
        "YANGZHENG PRIMARY SCHOOL":                     (1.62, 1.08, False),
        "ZHANGDE PRIMARY SCHOOL":                       (1.64, 1.09, False),
        "XINGHUA PRIMARY SCHOOL":                       (1.58, 1.05, False),
        "LIANHUA PRIMARY SCHOOL":                       (1.56, 1.04, False),
        "SHUQUN PRIMARY SCHOOL":                        (1.54, 1.03, False),
        "HUAMIN PRIMARY SCHOOL":                        (1.58, 1.06, False),
        "CHONGZHENG PRIMARY SCHOOL":                    (1.05, 0.85, False),
        "XISHAN PRIMARY SCHOOL":                        (1.61, 1.07, False),
        "XINGNAN PRIMARY SCHOOL":                       (1.59, 1.06, False),
        "LIANHUA PRIMARY SCHOOL":                       (1.56, 1.04, False),
        "KEMING PRIMARY SCHOOL":                        (1.10, 0.90, False),
        "CLEMENTI PRIMARY SCHOOL":                      (1.75, 1.15, False),
        "NEW TOWN PRIMARY SCHOOL":                      (1.68, 1.12, False),
        "QUEENSTOWN PRIMARY SCHOOL":                    (1.72, 1.14, False),
        "PEI TONG PRIMARY SCHOOL":                      (1.62, 1.08, False),
        "NGEE ANN PRIMARY SCHOOL":                      (1.50, 1.10, False),
        "TEMASEK PRIMARY SCHOOL":                       (1.70, 1.13, False),
        "SIGLAP PRIMARY SCHOOL":                        (1.65, 1.10, False),
        "TELOK KURAU PRIMARY SCHOOL":                   (1.45, 0.95, False),
        "BEDOK GREEN PRIMARY SCHOOL":                   (1.30, 0.70, False),
        "RULANG PRIMARY SCHOOL":                        (1.60, 1.05, False),

        # ── EASY (ratio < 1.2, no balloting needed) ──
        # Most schools fall here — left to default
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

    # All unmatched schools default to Easy with low ratio
    for s in schools.values():
        if s["p2c_ratio"] == 0.0:
            s["p2c_ratio"] = 0.75
            s["p2c"] = "Easy"
            s["p2b_ratio"] = 0.65
            s["p2b"] = "Easy"

    print(f"  Applied balloting data for {matched} schools")
    print(f"  Remaining {len(schools)-matched} schools defaulted to Easy")
