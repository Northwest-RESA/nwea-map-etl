#Griffin Spalding County Schools
import glob
import io
import os
import zipfile
import pandas as pd
import psutil

import requests

from google.cloud import secretmanager, storage


gcp_project_id = 'gscs-data'
gcs_bucket = 'gscs-data-lake'


def get_secret():
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(
        {"name": f"projects/{gcp_project_id}/secrets/nwea-map-password/versions/latest"})
    
    return response.payload.data.decode("UTF-8")

def main(request):
    nwea_api_url = 'https://api.mapnwea.org/services/reporting/dex'
    nwea_username = 'data@gscs.org'
    nwea_password = get_secret()
    session = requests.Session()
    session.auth = (nwea_username, nwea_password)
    response = session.request('GET', nwea_api_url)

    if response.ok is False:
        response.raise_for_status()

    zip = zipfile.ZipFile(io.BytesIO(response.content))
    zip.extractall('/tmp')

    filename = 'ComboStudentAssessment.csv'

    first_row = pd.read_csv(f'/tmp/{filename}', nrows=1)
    if first_row.empty:
        term_name = 'No Data'
    else:
        term_name = first_row['TermName'].values[0]
    print(f'TermName = {term_name}')


    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    remote_path = f'assessment/nwea_map/active/{term_name}/'
    for csv_path in glob.glob('/tmp/*.csv'):
        blob = bucket.blob(remote_path + os.path.basename(csv_path))
        blob.upload_from_filename(csv_path)

    process = psutil.Process(os.getpid())
    print("Process MB used: ", end='')
    print(process.memory_info().rss / 1024 / 1024) # in MB

    return f'Uploaded CSV file(s) to GCS'
