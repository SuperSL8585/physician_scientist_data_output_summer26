import psycopg2
import csv
from pathlib import Path
import ast


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


def oa_upload_to_cockroach(researcher_name, oa_ids):
    """
    Uploads researcher into cockroach researchers_master_50 and researcher_aliases_50 tables
    """
    execute_command(
        "INSERT INTO researchers_master_50 (researcher_name) VALUES (%s) ON CONFLICT DO NOTHING",
        (researcher_name,), commit=True
    )
    print(f"Starting Upload of {researcher_name}")

    for oa_id in oa_ids:
        execute_command(
            "INSERT INTO researcher_aliases_50 (researcher_name, oa_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (researcher_name, oa_id,), commit=True
        )
        print(f"Uploading {oa_id} for {researcher_name}...")

    print(
        f"\nSuccessfully ingested {len(oa_ids)} valid IDs for {researcher_name}.\n")


def researcher_oa_upload(dataset_path):
    """
    Takes the path to a dataset containing names and ids and adds them to CockroachDB
    """
    with open(dataset_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            try:
                oa_ids = ast.literal_eval(row['ID'])

                if isinstance(oa_ids, list):
                    oa_upload_to_cockroach(row['Name'], oa_ids)
                else:
                    # Fallback case if it's just a raw single ID string
                    oa_upload_to_cockroach(row['Name'], [str(oa_ids).strip()])

            except (ValueError, SyntaxError) as e:
                print(
                    f"Skipping row for {row['Name']} due to parsing error: {e}")

# MAIN


source_file = Path('openAlex_Ids_50_name_maniti.csv')
researcher_oa_upload(source_file)
