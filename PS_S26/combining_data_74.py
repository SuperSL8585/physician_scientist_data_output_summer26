import psycopg2
import requests
import json
import time
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# Note: Remember to change all table names for your needs
# ============================================================

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
# WEIGHTS
# ============================================================


WEIGHT_REGULATORY = 0.30
WEIGHT_PATIENT_REACH = 0.30
WEIGHT_CLINICAL_CITATIONS = 0.20
WEIGHT_GUIDELINE_CITATIONS = 0.20

# ============================================================
# CLINICAL CITATIONS (Katie's logic)
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


def get_clinical_citation_score(table_names, researcher_oa_ids, cutoff_year=2026):
    publication_table = table_names[0]
    if not researcher_oa_ids:
        return 0, 0, 0
    try:
        connection = psycopg2.connect(DB_URL)
        cursor = connection.cursor()
        pub_count = 0
        total_citations = 0

        for oa_id in researcher_oa_ids:
            cursor.execute(
                f"""SELECT mesh, cited_by_count
                FROM {publication_table}
                WHERE researcher_id = %s
                AND publication_year <= %s
                AND publication_year >= '1990'""",
                (oa_id, str(cutoff_year))
            )
            for mesh_text, cbc in cursor.fetchall():
                if is_clinical_paper(mesh_text):
                    pub_count += 1
                    try:
                        total_citations += int(cbc) if cbc else 0
                    except (TypeError, ValueError):
                        print("Error occured in mesh text block")
                        pass

        cursor.close()
        connection.close()
        weighted = total_citations * CITATION_WEIGHT
        return pub_count, total_citations, weighted, False
    except Exception as e:
        print('Error returnined on clinical citation score')
        # 4th value is True when error occurs
        return 0, 0, 0, True

# ============================================================
# GUIDELINE CITATIONS
# ============================================================


def get_guideline_count_for_doi(doi):
    """Check guideline cache first, then hit PubMed API if not cached."""
    clean_doi = doi.replace('https://doi.org/', '').strip()

    # check cache
    try:
        rows = execute_command(
            "SELECT guideline_count FROM guideline_cache WHERE doi = %s",
            (clean_doi,)
        )
        if rows:
            return rows[0][0]
    except:
        pass

    # hit PubMed API
    try:
        # step 1 — get PMID from DOI
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote(clean_doi)}[doi]&retmode=json&email=amsim@mit.edu'
        data = requests.get(url).json()
        ids = data.get('esearchresult', {}).get('idlist', [])
        if not ids:
            _cache_guideline(clean_doi, None, 0)
            return 0
        pmid = ids[0]
        time.sleep(0.1)

        # step 2 — get citing papers
        cite_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=pubmed&id={pmid}&linkname=pubmed_pubmed_citedin&retmode=json&email=amsim@mit.edu'
        cite_data = requests.get(cite_url).json()
        try:
            citing = cite_data['linksets'][0]['linksetdbs'][0]['links']
        except:
            _cache_guideline(clean_doi, pmid, 0)
            return 0

        if not citing:
            _cache_guideline(clean_doi, pmid, 0)
            return 0
        time.sleep(0.1)

        # step 3 — check for guidelines among citing papers
        ids_str = ','.join(citing[:100])
        fetch_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&rettype=xml&retmode=xml&email=amsim@mit.edu'
        xml = requests.get(fetch_url).text
        count = xml.count('Practice Guideline') + \
            xml.count('<PublicationType>Guideline')
        time.sleep(0.1)

        _cache_guideline(clean_doi, pmid, count)
        return count
    except:
        return 0


def _cache_guideline(doi, pmid, count):
    try:
        existing = execute_command(
            "SELECT 1 FROM guideline_cache WHERE doi = %s", (doi,)
        )
        if not existing:
            execute_command(
                "INSERT INTO guideline_cache (doi, pmid, guideline_count) VALUES (%s, %s, %s)",
                (doi, pmid, count),
                commit=True
            )
    except:
        pass


def get_guideline_citation_score(table_names, researcher_oa_ids, cutoff_year=2026, limit=30):
    """Get total guideline citations for a researcher's top cited papers."""
    publication_table = table_names[0]
    if not researcher_oa_ids:
        return 0

    try:
        dois = []
        for oa_id in researcher_oa_ids:
            rows = execute_command(
                f"""SELECT doi FROM {publication_table}
                WHERE researcher_id = %s
                AND doi IS NOT NULL
                AND publication_year >= '1990'
                AND publication_year <= %s
                ORDER BY cited_by_count DESC
                LIMIT %s""",
                (oa_id, str(cutoff_year), limit)
            )
            dois.extend([row[0] for row in rows if row[0]])

    except:
        print('Error returned on guideline citations')
        # 2nd value is True when error occurs
        return 0, True

    total = 0
    for doi in dois:
        total += get_guideline_count_for_doi(doi)

    return total, False

# ============================================================
# TRIAL DATA — WITH DATABASE CACHING
# ============================================================


def get_clinical_trials_new(table_names, researcher_id, researcher_oa_ids=None, cutoff_year=2026):
    results = []
    clinical_table = table_names[1]

    # check by dim_id first
    if researcher_id:
        rows = execute_command(
            f"""SELECT title, brief_title, start_date, id
                FROM {clinical_table}
                WHERE researcher_id = '{researcher_id}'
                AND (start_date IS NULL OR CAST(SUBSTRING(start_date, 1, 4) AS INT) <= {cutoff_year})"""
        )
        results.extend(rows)

    # also check by oa_id as fallback
    if researcher_oa_ids:
        for oa_id in researcher_oa_ids:
            rows = execute_command(
                f"""SELECT title, brief_title, start_date, id
                    FROM {clinical_table}
                    WHERE researcher_id = '{oa_id}'
                    AND (start_date IS NULL OR CAST(SUBSTRING(start_date, 1, 4) AS INT) <= {cutoff_year})"""
            )
            results.extend(rows)

    # deduplicate by NCT ID
    seen = set()
    unique = []
    for r in results:
        if r[3] not in seen:
            seen.add(r[3])
            unique.append(r)

    return unique


def cache_trial_data(clinical_table, nct_id, phase, enrollment_count):
    try:
        execute_command(
            "UPDATE %s SET phase = %s, enrollment_count = %s WHERE id = %s",
            (clinical_table, phase, enrollment_count, nct_id),
            commit=True
        )
    except:
        pass


def get_trial_data_from_nct(table_names, nct_id):
    clinical_table = table_names[1]

    try:
        rows = execute_command(
            "SELECT phase, enrollment_count FROM %s WHERE id = %s",
            (clinical_table, nct_id,)
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

        interventions = data['protocolSection'].get(
            'armsInterventionsModule', {}).get('interventions', [])
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

        cache_trial_data(clinical_table, nct_id, phase, enrollment_count)
        return phase, enrollment_count, None, drugs
    except:
        return None, 0, None, []

# ============================================================
# FDA APPROVAL CHECK
# ============================================================


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
                    (drug_name, result['approval_type'], result['approval_date'],
                     result['approval_year'], result['sponsor']),
                    commit=True
                )
            else:
                execute_command(
                    "INSERT INTO fda_cache (drug_name, approval_type, approval_date, approval_year, sponsor) VALUES (%s, NULL, NULL, NULL, NULL)",
                    (drug_name,),
                    commit=True
                )
    except:
        pass

    return result

# ============================================================
# SCORING FUNCTIONS
# ============================================================


def score_regulatory_milestone(phase, fda_result=None, role="lead_pi", start_year=None):
    base_scores = {
        "full_approval_orig": 100, "full_approval_suppl": 60,
        "PHASE3": 40, "PHASE4": 40, "PHASE2": 20, "PHASE1": 10, "NA": 5,
    }
    role_modifiers = {"lead_pi": 1.0,
                      "co_investigator": 0.5, "contributing_author": 0.25}

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
        return 0, "No scoreable milestone"

    return round(base * modifier * time_decay, 2), "scored"


def score_patient_reach(phase, enrollment):
    if not enrollment:
        return 0
    benchmarks = {
        "PHASE1": (80, 10), "PHASE2": (300, 20), "PHASE3": (3000, 40),
        "PHASE4": (3000, 40), "NA": (5000, 15), "OBSERVATIONAL": (5000, 15)
    }
    max_e, base = benchmarks.get(phase, (5000, 15))
    return round(min(enrollment / max_e, 1.5) * base, 2)

# ============================================================
# MAIN SCORING FUNCTION
# ============================================================


def calculate_researcher_score(researcher_id, researcher_name, researcher_oa_ids, table_30, cutoff_year=2026):
    table_names = ['publications_sum26', 'clinical_trials_sum26']
    if table_30:
        table_names = ['publications_new7', 'clinical_trials_new7']

    trials = get_clinical_trials_new(
        table_names, researcher_id, researcher_oa_ids=researcher_oa_ids, cutoff_year=cutoff_year)
    print(f'Got clinical trials from {researcher_name}')

    total_regulatory_score = 0
    total_patient_reach_score = 0
    total_patients = 0
    fda_approvals_found = []

    for t in trials:
        title, brief_title, start_date, nct_id = t
        phase, enrollment, enrollment_type, drug_names = get_trial_data_from_nct(table_names,
                                                                                 nct_id)

        fda_result = None
        for drug_name in drug_names:
            fda_result = check_fda_approval(drug_name)
            if fda_result:
                fda_approvals_found.append(drug_name)
                break

        reg_score, _ = score_regulatory_milestone(
            phase=phase, fda_result=fda_result,
            role="lead_pi", start_year=start_date
        )
        patient_score = score_patient_reach(phase, enrollment)

        total_regulatory_score += reg_score
        total_patient_reach_score += patient_score
        total_patients += enrollment if enrollment else 0
    print(
        f'Scored regulatory for {researcher_name} with score {total_regulatory_score}')
    print(
        f'Scored patient reach for {researcher_name} with score {total_patient_reach_score}')

    clin_pub_count, clin_raw_citations, clin_weighted, failed_at_clinical = get_clinical_citation_score(
        table_names, researcher_oa_ids, cutoff_year=cutoff_year
    )
    print(
        f'Got clinical citation score for {researcher_name} with {clin_weighted}')

    guideline_score, failed_at_guideline = get_guideline_citation_score(
        table_names, researcher_oa_ids, cutoff_year=cutoff_year, limit=30
    )
    print(
        f'Got guideline citation score for {researcher_name} with {guideline_score}')

    if failed_at_clinical:
        print(f"{researcher_name} experienced an error at Clinical Citations")
    if failed_at_guideline:
        print(f"{researcher_name} experienced an error at Guideline Citations")

    return {
        "trial_count": len(trials),
        "regulatory": total_regulatory_score,
        "patient_reach": round(total_patient_reach_score, 2),
        "total_patients": total_patients,
        "clinical_citations_weighted": clin_weighted,
        "clinical_pub_count": clin_pub_count,
        "guideline_citations": guideline_score,
        "fda_approvals": fda_approvals_found,
        "commercial": 0,
    }

# ============================================================
# NORMALIZATION
# ============================================================


def normalize(scores, key):
    values = [s[key] for s in scores.values()]
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return {name: 0 for name in scores}
    return {name: round((s[key] - min_val) / (max_val - min_val) * 100, 2)
            for name, s in scores.items()}


# ============================================================
# MAIN
# ============================================================

researchers_50 = execute_command("""
    SELECT
    m.researcher_name,
    ARRAY_AGG(DISTINCT d.dim_author_id) as dim_ids,
    ARRAY_AGG(DISTINCT a.oa_author_id) as oa_ids
    FROM researchers_master_50 m
    LEFT JOIN researcher_dim_50 d ON m.researcher_name = d.researcher_name
    LEFT JOIN researcher_oa_50 a ON m.researcher_name = a.researcher_name
    GROUP BY m.researcher_name;
""")
researchers_30 = execute_command("""
    SELECT r.first_m_last_name, r.unique_dim_id, r.unique_oa_id
    FROM researchers_new7 r
    WHERE r.first_m_last_name IN (
        'Jasmohan Bajaj', 'Peter Crompton', 'Juan Wisnivesky',
        'Beth Kirkpatrick', 'Wonder Drake', 'Maximilian Diehn',
        'Shyamasundaran Kottilil', 'Vineet Arora', 'Jeffrey Curtis',
        'Aaron Cypess', 'Aida Habtezion', 'Karl Bilimoria',
        'Reshma Jagsi', 'Alessia Fornoni', 'Bernhard Kühn',
        'Keith Choate', 'Catherine Blish', 'Sarat Chandarlapaty',
        'Robert Baloh', 'Alexander Krupnick', 'Ash Alizadeh',
        'Rasheed Gbadegesin', 'Andrew Auerbach', 'Conrad Weihl',
        'Agata Smogorzewska', 'Anna Greka', 'Soumya Raychaudhuri',
        'Trever Bivona', 'Margaret Feeney', 'Euan Ashley'
    )
    AND r.unique_oa_id IS NOT NULL
""")

all_researchers = researchers_50 + researchers_30


print(f"Running pipeline on {len(all_researchers)} researchers...\n")

scores = {}


def process_researcher(r):
    table_30 = False
    name, dim_id, oa_ids = r
    if r in researchers_30:
        table_30 = True
        oa_ids = [oa_ids]
    print(f"Processing: {name}...")
    dim_id = dim_id[0]
    return name, calculate_researcher_score(dim_id, name, oa_ids, table_30)


with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(process_researcher, r)               : r for r in all_researchers}
    for future in as_completed(futures):
        name, result = future.result()
        scores[name] = result

# normalize all four dimensions
reg_norm = normalize(scores, "regulatory")
reach_norm = normalize(scores, "patient_reach")
clin_norm = normalize(scores, "clinical_citations_weighted")
guideline_norm = normalize(scores, "guideline_citations")

# compute final scores
final_scores = {}
for name in scores:
    total = round(
        (reg_norm[name] * WEIGHT_REGULATORY) +
        (reach_norm[name] * WEIGHT_PATIENT_REACH) +
        (clin_norm[name] * WEIGHT_CLINICAL_CITATIONS) +
        (guideline_norm[name] * WEIGHT_GUIDELINE_CITATIONS), 2)
    final_scores[name] = total

print("\n=== FINAL SCORES (normalized) ===")
print(f"{'Researcher':<30} {'Trials':>6} {'Reg':>8} {'PatReach':>10} {'ClinCit':>10} {'Guideline':>10} {'TOTAL':>8}")
print("-" * 85)
for name, total in sorted(final_scores.items(), key=lambda x: x[1], reverse=True):
    s = scores[name]
    print(f"{name:<30} {s['trial_count']:>6} {reg_norm[name]:>8.1f} {reach_norm[name]:>10.1f} {clin_norm[name]:>10.1f} {guideline_norm[name]:>10.1f} {total:>8.2f}")

# save to database
print("\nSaving scores to database...")
for name in scores:
    s = scores[name]
    execute_command(
        """INSERT INTO impact_scores_74
           (researcher_name, regulatory, patient_reach, clinical_citations, real_world_score)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (researcher_name) DO UPDATE SET
           regulatory = EXCLUDED.regulatory,
           patient_reach = EXCLUDED.patient_reach,
           clinical_citations = EXCLUDED.clinical_citations,
           real_world_score = EXCLUDED.real_world_score,
           run_date = now()""",
        (name, s['regulatory'], s['patient_reach'],
         s['clinical_citations_weighted'], final_scores[name]),
        commit=True
    )
    print(f"{name} is saved into Cockroach!")
print("Scores saved.")
