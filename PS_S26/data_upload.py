from medical_terms import MEDICAL_KEYWORDS
import psycopg2
import json
from pathlib import Path
import shutil
import csv
import pandas as pd
import requests

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


def file_opener(dataset_path, researcher_name):
    """
    Opens a json file, use * for all json files in the dataset path. Returns researcher name, cluster count, author data, and works data if exists
    """
    for file_path in dataset_path.glob(f'{researcher_name}.json'):
        with open(file_path, 'r', encoding='utf-8') as file:
            researcher_data = json.load(file)
            researcher_name = researcher_data['author_name']['name']
            cluster_count = researcher_data['author_name']['clusters_count']
            author_data = researcher_data.get('author_data', {})
            works_data = researcher_data.get('works_data', None)

            return researcher_name, cluster_count, author_data, works_data


def upload_to_cockroach_oa(researcher_name, oa_ids):
    """
    Uploads researcher into cockroach researchers_master_50 and researcher_oa_50 tables
    """
    execute_command(
        "INSERT INTO researchers_master_50 (researcher_name) VALUES (%s) ON CONFLICT DO NOTHING",
        (researcher_name,), commit=True
    )

    for oa_id in oa_ids:
        execute_command(
            "INSERT INTO researcher_oa_50 (researcher_name, oa_author_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (researcher_name, oa_id,), commit=True
        )

    print(
        f"Successfully uploaded {len(oa_ids)} valid IDs for {researcher_name}.")


def upload_to_cockroack_dim(dataset_path):
    """
    Uploads disambiguated dim ids from a csv file assuming researcher names were already uploaded
    """
    with open(dataset_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)

        for row in csv_reader:
            name = row['name']
            dim_id = row['disambiguated_id']
            execute_command('INSERT INTO researcher_dim_50 (researcher_name, dim_author_id) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                            (name, dim_id,), commit=True)
            print(f'Successfully uploaded id: {dim_id} for {name}')


def insert_specialties(csv_name):
    """
    Obtains the specialties of physician scientists in the researchers_master_50 table and inserts them to Cockroach
    """
    df = pd.read_csv(csv_name, encoding='latin1')
    rows = execute_command("SELECT researcher_name FROM researchers_master_50")
    researcher_names = [row[0] for row in rows if row[0]]
    specialties = {}
    no_match = []
    mult_matches = []
    df_first = df['first_name']
    df_last = df['last_name']
    for researcher in researcher_names:
        researcher_name = researcher
        split_names = researcher.split()
        first_name = split_names[0]
        last_name = split_names[1]
        match = df[(df_first == first_name) & (df_last == last_name)]

        if match.empty:
            no_match.append(researcher_name)

        else:
            specialties = match['original specialization'].tolist()
            if len(specialties) == 1:
                execute_command(
                    "UPDATE researchers_master_50 SET specialty = %s WHERE researcher_name = %s",
                    (specialties[0], researcher_name),
                    commit=True
                )
                print(f'{researcher_name} has {specialties[0]} uploaded')
            elif specialties[0] == []:
                no_match.append(researcher_name)
            else:
                mult_matches.append(researcher_name)
    return no_match, mult_matches


def insert_h_index(researchers):
    """
    Queries a researcher's h index from open alex and inserts the h index into cockroach
    researchers: a list of researcher names to query
    """
    def get_oa_data(oa_id):
        query_id = f'https://api.openalex.org/authors/{oa_id}'

        try:
            response = requests.get(query_id)

            if response.status_code == 200:
                data = response.json()
                stats = data.get('summary_stats', {})
                h_index = stats.get('h_index', 0)
                return h_index

        except:
            print(f'Error quering for {researcher}')

    def find_best_oa(oa_list):
        best_h = 0
        for id in oa_list:
            try:
                id_h = get_oa_data(id)
                if id_h > best_h:
                    best_h = id_h
            except:
                pass
        return best_h

    for researcher in researchers:
        oa_ids_rows = execute_command(
            "SELECT oa_author_id FROM researcher_oa_50 WHERE researcher_name = %s", (researcher,))
        oa_ids = [row[0] for row in oa_ids_rows if row[0]]
        if len(oa_ids) == 1:
            h_index = get_oa_data(oa_ids[0])
        else:
            h_index = find_best_oa(oa_ids)

        execute_command("UPDATE researchers_master_50 SET h_index = %s WHERE researcher_name = %s",
                        (int(h_index), researcher),
                        commit=True)
        print(f'{researcher} successfully uploaded with h-index {h_index}')


def researcher_upload_single_cluster(dataset_path, needs_manual_check):
    """
    Uploads researchers to CockroachDB only if they have 1 cluster.
    Returns researchers that have multiple clusters for future reference.
    """
    for file_path in dataset_path.glob('*.json'):
        with open(file_path, 'r', encoding='utf-8') as file:
            oa_ids = []
            researcher_data = json.load(file)
            researcher_name = researcher_data['author_name']['name']
            cluster_count = researcher_data['author_name']['clusters_count']
            author_data = researcher_data.get('author_data', {})
            if cluster_count < 2:
                for cluster_key, cluster_info in author_data.items():
                    oa_ids.extend(cluster_info['ids'])

                upload_to_cockroach_oa(researcher_name, oa_ids)

            else:
                needs_manual_check.append(researcher_name)
                print(
                    f"Need to check {cluster_count} clusters for {researcher_name}")

    return needs_manual_check


def move_scientists(unfinished_scientists, source_dir, target_dir):
    """
    Moves completed scientists to a different directory
    unfinished_scientists: List of the names of all unfinished scientists
    source_dir: source folder
    target_dir: target folder
    """
    if unfinished_scientists:
        for file_path in source_dir.iterdir():
            if file_path.stem not in unfinished_scientists:
                shutil.move(str(file_path), str(target_dir / file_path.name))
                print(f"Moved {file_path.stem} to target")
    else:
        rows = execute_command(
            'SELECT researcher_name FROM researchers_master_50')
        finished_scientists = [row[0] for row in rows if row[0]]
        for file_path in source_dir.iterdir():
            if file_path.stem in finished_scientists:
                shutil.move(str(file_path), str(target_dir / file_path.name))
                print(f"Moved {file_path.stem} to target")


def filter_clusters_by_works(dataset_path):
    """
    Some files have works_data, filters the ones that do and uses medical keywords to filter or review them
    """
    for file_path in dataset_path.glob('*.json'):
        with open(file_path, 'r', encoding='utf-8') as file:
            approved_clusters = set()
            review_clusters = set()
            oa_ids = []
            researcher_data = json.load(file)
            researcher_name = researcher_data['author_name']['name']
            author_data = researcher_data.get('author_data', {})
            works_data = researcher_data.get('works_data', None)
            try:
                if works_data:
                    for works_key, works_info in works_data.items():
                        if works_info['title'] and works_info['gold_person_id'] not in approved_clusters:
                            for word in works_info['title'].split():
                                word = word.lower()
                                if word in MEDICAL_KEYWORDS:
                                    approved_clusters.add(
                                        works_info['gold_person_id']
                                    )
                                    print(
                                        f"For {researcher_name}, approved cluster {works_info['gold_person_id']}")
                for cluster in author_data.keys():
                    if cluster not in approved_clusters:
                        review_clusters.add(cluster)
                        print(
                            f"For {researcher_name}, review cluster {works_info['gold_person_id']}")

                write_filter_results(
                    researcher_name, approved_clusters, review_clusters)

            except:
                pass


def write_filter_results(name, approved_clusters, review_clusters):
    with open("filtered_clusters.txt", "a") as file:
        file.write(f"{name}")
        if approved_clusters:
            file.write("approved_clusters = ")
            for item in approved_clusters:
                file.write(f"{item}, ")
        print("\n")
        if review_clusters:
            file.write("review_clusters = ")
            for item in review_clusters:
                file.write(f"{item}, ")
        print("\n")


def researcher_upload_by_cluster_set(dataset_path, researcher_name, cluster_set):
    """
    Uploads researchers by the cluster given. A cluster set is a set of clusters that have been identified to be associated with a researcher.
    """
    researcher_name, cluster_count, author_data, works_data = file_opener(
        dataset_path, researcher_name)
    for cluster_key, cluster_info in author_data.items():
        oa_ids = []
        if cluster_key in cluster_set:
            oa_ids.extend(cluster_info['ids'])
            upload_to_cockroach_oa(researcher_name, oa_ids)


def input_clusters_for_upload(dataset_path):
    """
    Prompts user for researcher name and a set of clusters for upload

    Input in the following format:
    First Prompt: First_name Last_name (Ex. Alex Kopin)
    Second Prompt: Cluster name you want to use, has 2 forms (Ex. A5082620506 or tap_william_0)
    """
    continuing = True
    while continuing:
        try:
            researcher_name = input(
                'Researcher you want to upload with capitalized first and last name: ')
            cluster_set = '{' + input(
                'Set of clusters you want to upload for given researcher: ') + '}'
            cluster_set = set(cluster_set[1:-1].split(", "))
            researcher_upload_by_cluster_set(
                dataset_path, researcher_name, cluster_set)
        except:
            print('Please give a valid researcher and/or cluster set')
        answer = input('Continue to next researcher? (y/n): ')
        if answer == 'y':
            continuing = True
        else:
            continuing = False


# =================================
# MAIN
# =================================

# ----------------------------------
# 1. Setup Source and target folders
# ----------------------------------
source_dir = Path('unfied_dataset')
# target_dir = Path('uploaded_scientists')

# ----------------------------------
# 2. Quick Upload for researchers with single clusters
# ----------------------------------
# needs_manual_check = researcher_upload_single_cluster(source_dir, [])
# print('\nPlease check:')
# for name in needs_manual_check:
#     print(name)
# move_scientists(needs_manual_check, source_dir, target_dir)

# ----------------------------------
# 3. Upload for other researchers by picking clusters
# ----------------------------------
# input_clusters_for_upload(source_dir)
# move_scientists(False, source_dir, target_dir)

# ----------------------------------
# 4. Upload for dimensions ids
# ----------------------------------
# upload_to_cockroack_dim(source_dir)

# ----------------------------------
# 5. Inserting specialties
# ----------------------------------
# no_match, mult_matches = insert_specialties('original_names.csv')
# print(f'The following scientists have no match: {no_match}')
# print(f'The following scientists have multiple matches: {mult_matches}')

# ----------------------------------
# 6. Inserting h-index for analysis
# ----------------------------------
name_rows = execute_command(
    "SELECT researcher_name FROM researchers_master_50")
names = [row[0] for row in name_rows if row[0]]
insert_h_index(names)
