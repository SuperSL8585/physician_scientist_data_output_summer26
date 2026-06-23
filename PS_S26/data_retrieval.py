import psycopg2
import json
from pathlib import Path
import shutil

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


def get_oa_ids(researcher_name):
    """
    Retrieves the OA Ids from CockroachDB given a researcher name, returns the list of that researcher's oa ids
    """
    rows = execute_command(
        'SELECT oa_author_id FROM researcher_aliases_50 WHERE researcher_name = %s', (researcher_name))
    oa_ids = [row[0] for row in rows if row[0]]
    return oa_ids


def get_all_oa_ids():
    """
    Gets a list of all oa ids in the table
    """
    rows = execute_command('SELECT oa_author_id FROM researcher_aliases_50')
    oa_ids = [row[0] for row in rows if row[0]]
    return oa_ids


# MAIN
oa_ids = get_all_oa_ids()
print(oa_ids)
