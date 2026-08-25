# Uploads a csv with dimension information to cockroach

import psycopg2
import csv
from pathlib import Path

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


def tier4_upload_to_cockroach(csv_path):
    """
    Uploads a csv containing tier 4 information onto cockroach
    """

    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            name = row['Name']
            institution = row['Institution']
            role = row['Role']
            type = row['Leadership Type']
            start = row['Start Year']
            end = row['End Year']
            source = row['Source']

            execute_command('INSERT INTO tier4_74 (researcher_name, institution, role, dimension, start_year, end_year, source)'
                            'VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING', (name, institution, role, type, start, end, source,), commit=True)

            print(
                f'Successfully uploaded {name} with role {role} from {institution} to Cockroach')


def commercialization_upload_to_cockroach(csv_path):
    """
    Uploads commericalization csv to cockroach containing name, company, role, and source
    """

    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            name = row['Name']
            company = row['Company']
            role = row['Role']
            source = row['Source']
            execute_command('INSERT INTO commercialization_74 (name, company, role, source)'
                            'VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING', (name, company, role, source,), commit=True)
            print(
                f'Successfully uploaded {name} with role {role} at {company} to Cockroach')


csv_path = Path(
    'Industry_Roles/Physician_Scientist_Industry_Roles_Batch9.csv')

commercialization_upload_to_cockroach(csv_path)
