# ==========================================
# 1. IMPORTS
# ==========================================

import os
import json
import time
from typing import Any, Optional
from pathlib import Path
import csv

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

# ==========================================
# 4. INSERT TO SUPABASE
# ==========================================


def insert_commercialization(csv_path):
    """
    Inserts the commercialization csv into supabase
    """
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row['Name']
            company = row['Company']
            role = row['Role']
            source = row['Source']

            try:
                sql = """INSERT INTO commercialization (name, company, role, source) VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING"""
                execute(sql, (name, company, role, source))
                print(
                    f'Successfully uploaded {name} with role {role} from {company} to supabase!')
            except:
                print(
                    f'Failed to upload {name} with role {role} from company {company}')


def insert_leadership(csv_path):
    """
    Inserts a tier 4 csv into supabase
    """
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row['researcher_name']
            institution = row['institution']
            dimension = row['dimension']
            source = row['source']
            role = row['role']
            start = row['start_year']
            end = row['end_year']

            try:
                sql = """INSERT INTO leadership (researcher_name, institution, dimension, source, role, start_year, end_year)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING"""
                execute(sql, (name, institution, dimension,
                        source, role, start, end))
                print(
                    f'Successfully uploaded {name} with role {role} from {institution} to supabase!')
            except:
                conn.rollback()
                print(
                    f'Failed to upload {name} with role {role} from {institution}')


# ==========================================
# 5. MAIN
# ==========================================
csv_path = Path('Industry_Roles/Physician_Scientist_Industry_Roles.csv')
insert_commercialization(csv_path)
