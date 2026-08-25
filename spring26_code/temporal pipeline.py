import psycopg2
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# DATABASE CONNECTION
# ============================================================

DB_URL = "postgresql://selina04_mit_edu:ynoGrfDJ4hnEyXkqO0IGFw@livid-dibbler-6457.g8z.gcp-us-east1.cockroachlabs.cloud:26257/test?sslmode=require"

def execute_command(query, params=None, commit=False):
    connection = psycopg2.connect(DB_URL)
    cursor = connection.cursor()
    cursor.execute(query, params)
    if commit:
        connection.commit()
        val = None
    else:
        val = cursor.fetchall()
    cursor.close()
    connection.close()
    return val

# ============================================================
# NORMALIZATION AGAINST FULL DATASET
# ============================================================

def load_full_dataset_ranges():
    rows = execute_command("SELECT regulatory, patient_reach, clinical_citations FROM impact_scores")
    if not rows:
        raise RuntimeError("impact_scores table is empty — run pipeline_final.py first")
    reg_vals = [r[0] for r in rows if r[0] is not None]
    reach_vals = [r[1] for r in rows if r[1] is not None]
    clin_vals = [r[2] for r in rows if r[2] is not None]
    return {
        "reg_min": min(reg_vals), "reg_max": max(reg_vals),
        "reach_min": min(reach_vals), "reach_max": max(reach_vals),
        "clin_min": min(clin_vals), "clin_max": max(clin_vals),
    }

def normalize_value(value, min_val, max_val):
    if max_val == min_val:
        return 0.0
    result = (value - min_val) / (max_val - min_val) * 100
    return round(max(0.0, result), 1)

# ============================================================
# CLINICAL CITATIONS
# ============================================================

CITATION_WEIGHT = 0.25

CLINICAL_QUALIFIERS = frozenset({
    "therapy", "drug therapy", "therapeutic use", "surgery", "diagnosis",
    "prevention & control", "administration & dosage", "adverse effects",
    "rehabilitation", "nursing", "diet therapy", "radiotherapy", "transplantation",
})

CLINICAL_DESCRIPTORS = frozenset({
    "Clinical Trial", "Clinical Trials as Topic", "Randomized Controlled Trial",
    "Randomized Controlled Trials as Topic", "Controlled Clinical Trial",
    "Case Reports", "Treatment Outcome", "Double-Blind Method", "Follow-Up Studies",
    "Cohort Studies", "Prospective Studies", "Retrospective Studies",
    "Cross-Sectional Studies", "Clinical Protocols",
})

def is_clinical_paper(mesh_json_text):
    if not mesh_json_text or mesh_json_text in ("[]", "null", ""):
        return False
    try:
        entries = json.loads(mesh_json_text)
    except (json.JSONDecodeError, TypeError):
        return False
    has_humans = False
    has_clinical_signal = False
    for entry in entries:
        descriptor = entry.get("descriptor_name", "")
        qualifier = entry.get("qualifier_name") or ""
        if descriptor == "Humans":
            has_humans = True
        if qualifier.lower() in CLINICAL_QUALIFIERS:
            has_clinical_signal = True
        if descriptor in CLINICAL_DESCRIPTORS:
            has_clinical_signal = True
        if has_humans and has_clinical_signal:
            return True
    return False

def get_clinical_citation_score(researcher_oa_id, cutoff_year=2026):
    if not researcher_oa_id:
        return 0, 0, 0
    try:
        connection = psycopg2.connect(DB_URL)
        cursor = connection.cursor()
        cursor.execute(
        """SELECT mesh, cited_by_count
       FROM publications_new7
       WHERE researcher_id = %s
       AND publication_year <= %s
       AND publication_year >= 1990""",
        (researcher_oa_id, cutoff_year)
        )
        pub_count = 0
        total_citations = 0
        for mesh_text, cbc in cursor.fetchall():
            if is_clinical_paper(mesh_text):
                pub_count += 1
                try:
                    total_citations += int(cbc) if cbc else 0
                except (TypeError, ValueError):
                    pass
        cursor.close()
        connection.close()
        return pub_count, total_citations, total_citations * CITATION_WEIGHT
    except:
        return 0, 0, 0

# ============================================================
# TRIAL DATA
# ============================================================

def get_clinical_trials_new(researcher_id, cutoff_year=2026):
    return execute_command(
        f"""SELECT title, brief_title, start_date, id
            FROM clinical_trials_new7
            WHERE researcher_id = '{researcher_id}'
            AND (start_date IS NULL OR CAST(SUBSTRING(start_date, 1, 4) AS INT) <= {cutoff_year})"""
    )

def get_trial_data_from_nct(nct_id):
    try:
        rows = execute_command(
            "SELECT phase, enrollment_count FROM clinical_trials_new7 WHERE id = %s",
            (nct_id,)
        )
        if rows and rows[0][0] is not None and rows[0][1] is not None:
            return rows[0][0], rows[0][1], "CACHED", []
    except:
        pass

    try:
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
        response = requests.get(url)
        data = response.json()
        design = data['protocolSection'].get('designModule', {})
        phases = design.get('phases', [])
        enrollment = design.get('enrollmentInfo', {})
        phase = phases[0] if phases else None
        enrollment_count = enrollment.get('count', 0)

        interventions = data['protocolSection'].get('armsInterventionsModule', {}).get('interventions', [])
        exclude_patterns = {
            'placebo', 'vehicle', 'control', 'saline', 'sham',
            'standard care', 'usual care', 'regimen', 'agonist',
            'antagonist', 'inhibitor', 'receptor', 'probiotic'
        }
        drugs = []
        for i in interventions:
            if i.get('type') == 'DRUG':
                name = i.get('name', '').strip()
                if ';' in name:
                    for part in name.split(';'):
                        part = part.strip()
                        if part and len(part) <= 40:
                            if not any(word in part.lower() for word in exclude_patterns):
                                drugs.append(part)
                    continue
                if len(name) > 40:
                    continue
                if any(word in name.lower() for word in exclude_patterns):
                    continue
                drugs.append(name)

        return phase, enrollment_count, None, drugs
    except:
        return None, 0, None, []

def check_fda_approval(drug_name):
    if not drug_name:
        return None

    try:
        rows = execute_command(
            "SELECT approval_type, approval_date, approval_year, sponsor FROM fda_cache WHERE drug_name = %s",
            (drug_name,)
        )
        if rows:
            if rows[0][0] is None:
                return None
            return {
                'drug': drug_name,
                'approval_type': rows[0][0],
                'approval_date': rows[0][1],
                'approval_year': rows[0][2],
                'sponsor': rows[0][3]
            }
    except:
        pass

    result = None
    url = f'https://api.fda.gov/drug/drugsfda.json?search=openfda.brand_name:{drug_name}&limit=5'
    response = requests.get(url)
    if response.status_code != 200 or 'results' not in response.json():
        url = f'https://api.fda.gov/drug/drugsfda.json?search=openfda.generic_name:{drug_name}&limit=5'
        response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if 'results' in data:
            for r in data['results']:
                for submission in r.get('submissions', []):
                    if submission.get('submission_status') == 'AP':
                        date = submission.get('submission_status_date', '')
                        result = {
                            'drug': drug_name,
                            'approval_type': submission.get('submission_type'),
                            'approval_date': date,
                            'approval_year': int(date[:4]) if date else None,
                            'sponsor': r.get('sponsor_name')
                        }
                        break
                if result:
                    break

    try:
        existing = execute_command(
            "SELECT 1 FROM fda_cache WHERE drug_name = %s", (drug_name,)
        )
        if not existing:
            if result:
                execute_command(
                    "INSERT INTO fda_cache (drug_name, approval_type, approval_date, approval_year, sponsor) VALUES (%s, %s, %s, %s, %s)",
                    (drug_name, result['approval_type'], result['approval_date'], result['approval_year'], result['sponsor']),
                    commit=True
                )
            else:
                execute_command(
                    "INSERT INTO fda_cache (drug_name, approval_type, approval_date, approval_year, sponsor) VALUES (%s, NULL, NULL, NULL, NULL)",
                    (drug_name,),
                    commit=True
                )
    except Exception as e:
        pass

    return result

# ============================================================
# SCORING
# ============================================================

def score_regulatory_milestone(phase, fda_result=None, role="lead_pi", start_year=None):
    base_scores = {
        "full_approval_orig": 100, "full_approval_suppl": 60,
        "PHASE3": 40, "PHASE4": 40, "PHASE2": 20, "PHASE1": 10, "NA": 5,
    }
    role_modifiers = {"lead_pi": 1.0, "co_investigator": 0.5, "contributing_author": 0.25}

    years_ago = (2026 - int(str(start_year)[:4])) if start_year else 5
    time_decay = 1.0 if years_ago <= 5 else (0.75 if years_ago <= 10 else 0.5)
    modifier = role_modifiers.get(role, 1.0)

    if fda_result:
        base = base_scores["full_approval_orig"] if fda_result['approval_type'] == 'ORIG' else base_scores["full_approval_suppl"]
        if fda_result['approval_year']:
            ya = 2026 - fda_result['approval_year']
            time_decay = 1.0 if ya <= 5 else (0.75 if ya <= 10 else 0.5)
    elif phase in base_scores:
        base = base_scores[phase]
    else:
        return 0

    return round(base * modifier * time_decay, 2)

def score_patient_reach(phase, enrollment):
    if not enrollment:
        return 0
    benchmarks = {
        "PHASE1": (80, 10), "PHASE2": (300, 20), "PHASE3": (3000, 40),
        "PHASE4": (3000, 40), "NA": (5000, 15), "OBSERVATIONAL": (5000, 15)
    }
    max_e, base = benchmarks.get(phase, (5000, 15))
    return round(min(enrollment / max_e, 1.5) * base, 2)

WEIGHT_REGULATORY = 0.35
WEIGHT_PATIENT_REACH = 0.35
WEIGHT_CLINICAL_CITATIONS = 0.30

def calculate_score_at_cutoff(researcher_id, researcher_oa_id, cutoff_year, ranges):
    trials = get_clinical_trials_new(researcher_id, cutoff_year=cutoff_year)

    total_reg = 0
    total_reach = 0

    for t in trials:
        title, brief_title, start_date, nct_id = t
        phase, enrollment, _, drug_names = get_trial_data_from_nct(nct_id)

        fda_result = None
        for drug_name in drug_names:
            fda_result = check_fda_approval(drug_name)
            if fda_result:
                break

        total_reg += score_regulatory_milestone(phase=phase, fda_result=fda_result, start_year=start_date)
        total_reach += score_patient_reach(phase, enrollment)

    _, _, clin_weighted = get_clinical_citation_score(researcher_oa_id, cutoff_year=cutoff_year)

    reg_norm = normalize_value(total_reg, ranges["reg_min"], ranges["reg_max"])
    reach_norm = normalize_value(total_reach, ranges["reach_min"], ranges["reach_max"])
    clin_norm = normalize_value(clin_weighted, ranges["clin_min"], ranges["clin_max"])

    return round(
        (reg_norm * WEIGHT_REGULATORY) +
        (reach_norm * WEIGHT_PATIENT_REACH) +
        (clin_norm * WEIGHT_CLINICAL_CITATIONS)
    , 2)

# ============================================================
# MAIN
# ============================================================

print("Loading normalization ranges from full dataset...")
ranges = load_full_dataset_ranges()
print(f"  Reg range: {ranges['reg_min']} - {ranges['reg_max']}")
print(f"  Reach range: {ranges['reach_min']} - {ranges['reach_max']}")
print(f"  ClinCit range: {ranges['clin_min']} - {ranges['clin_max']}")

career_starts = {
    "Jeffrey Curtis":     1991,
    "Beth Kirkpatrick":   1995,
    "Alexander Krupnick": 1996,
    "Ash Alizadeh":       1998,
    "Peter Crompton":     1998,
    "Jasmohan Bajaj":     1999,
    "Juan Wisnivesky":    1999,
}

# career year blocks — up to 35 years
YEAR_BLOCKS = [5, 10, 15, 20, 25, 30, 35]

researchers = execute_command("""
    SELECT r.first_m_last_name, r.unique_dim_id, r.unique_oa_id
    FROM researchers_new7 r
    WHERE r.first_m_last_name IN (
        'Jeffrey Curtis', 'Beth Kirkpatrick', 'Alexander Krupnick',
        'Ash Alizadeh', 'Peter Crompton', 'Jasmohan Bajaj', 'Juan Wisnivesky'
    )
    AND r.unique_dim_id IS NOT NULL
""")

researcher_map = {r[0]: (r[1], r[2]) for r in researchers}

def process_researcher_temporal(name):
    start_year = career_starts[name]
    dim_id, oa_id = researcher_map[name]
    print(f"  Processing {name}...")
    scores = []
    # score at each 5-year block
    for years_in in YEAR_BLOCKS:
        cutoff = start_year + years_in
        if cutoff > 2026:
            scores.append(None)  # not reached yet
        else:
            scores.append(calculate_score_at_cutoff(dim_id, oa_id, cutoff, ranges))
    # current score
    scores.append(calculate_score_at_cutoff(dim_id, oa_id, 2026, ranges))
    return name, scores

print("\nCollecting temporal scores...")
raw = {}
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(process_researcher_temporal, name): name
               for name in career_starts if name in researcher_map}
    for future in as_completed(futures):
        name, scores = future.result()
        raw[name] = scores

def fmt(val):
    if val is None:
        return "     —"
    return f"{val:>6.1f}"

print("\n=== TEMPORAL ANALYSIS (normalized against full 30 researcher dataset) ===")
print("Note: — means researcher has not yet reached that career stage.")
print("Note: 2020-2022 scores may reflect COVID-related activity spikes.")
print()

header = f"{'Researcher':<25} {'Start':>6}"
for yr in YEAR_BLOCKS:
    header += f" {'Yr'+str(yr):>6}"
header += f" {'Current':>7}"
print(header)
print("-" * 95)

for name, start_year in sorted(career_starts.items(), key=lambda x: x[1]):
    if name not in raw:
        continue
    s = raw[name]
    row = f"{name:<25} {start_year:>6}"
    for i, val in enumerate(s[:-1]):  # all blocks except current
        row += f" {fmt(val)}"
    row += f" {s[-1]:>7.1f}"  # current
    print(row)

print("\nFor Google Sheets — copy table below (dashes for incomplete years):")
print()
sheet_header = "Researcher,Start," + ",".join([f"Yr {yr}" for yr in YEAR_BLOCKS]) + ",Current"
print(sheet_header)
for name, start_year in sorted(career_starts.items(), key=lambda x: x[1]):
    if name not in raw:
        continue
    s = raw[name]
    row_vals = []
    for val in s[:-1]:
        row_vals.append("—" if val is None else str(val))
    row_vals.append(str(s[-1]))
    print(f"{name},{start_year}," + ",".join(row_vals))

print("\nDone.")
