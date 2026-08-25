# ==========================================
# 1. IMPORTS
# ==========================================

import os
import json
import time
from typing import Any, Optional
from pathlib import Path
import csv
import requests

import pandas as pd
import psycopg2
from psycopg2.extras import Json
import dimcli

from dotenv import load_dotenv

# ==========================================
# 2. ENVIRONMENT
# ==========================================

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

required_variables = {
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}

missing = [
    name
    for name, value in required_variables.items()
    if not value
]

if missing:
    raise ValueError(
        f"Missing environment variables: {', '.join(missing)}"
    )

print("✓ Environment variables loaded")


# ==========================================
# 3. CONNECT TO SUPABASE
# ==========================================

conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    sslmode="prefer",
)

conn.autocommit = False

with conn.cursor() as cur:
    cur.execute("SELECT current_database(), current_user;")
    database_name, database_user = cur.fetchone()

print("✓ Connected to Supabase PostgreSQL")
print("Database:", database_name)
print("User:", database_user)


def fetch_one(sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()


def execute_returning_id(sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)

        row = cur.fetchone()

        if row is None:
            raise RuntimeError(
                "Expected INSERT/UPDATE to return an ID."
            )

        return row[0]


def fetch_all(sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_drugs_data_from_nct(nct_id):
    try:
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
        response = requests.get(url)
        data = response.json()
        design = data['protocolSection'].get('designModule', {})
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
        return drugs
    except:
        return []


def check_fda_approval(drug_name):
    if not drug_name:
        return None

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
    return result


# ==========================================
# 5. MAIN
# ==========================================
id_query = """
SELECT researcher_id FROM researcher
"""
researcher_ids = fetch_all(id_query)
headers = ['nct_id', 'drug_name', 'approval_type',
           'approval_date', 'approval_year', 'sponsor']
with open('fda_results.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(headers)


for (researcher_id,) in researcher_ids:
    trial_query = """
    SELECT c.nct_id FROM researcher_clinical_trial r JOIN clinical_trial c ON r.clinical_trial_id = c.clinical_trial_id
    WHERE r.researcher_id = %s
    """
    trial_ids = fetch_all(trial_query, (researcher_id,))
    drugs = []
    results_dict = {}
    for (trial_id,) in trial_ids:
        new_drugs = get_drugs_data_from_nct(trial_id)
        for drug in new_drugs:
            result = check_fda_approval(drug)
            results_dict[drug] = result

        with open('fda_results.csv', 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for drug_name, result in results_dict.items():
                if result is None:
                    continue
                row = [trial_id, result['drug'], result['approval_type'],
                       result['approval_date'], result['approval_year'], result['sponsor']]
                writer.writerow(row)
                print(f'Successfully wrote {result["drug"]} into csv')
        print(f'Successfully wrote all approvals for id: {trial_id}')
