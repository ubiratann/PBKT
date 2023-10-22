#!/bin/python3.10

from __future__ import print_function

import os

from datetime import datetime

from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

FOLDER_MIME_TYPE   = os.environ.get('GOOGLE_DRIVE_FOLDER_MIME_TYPE', 'application/vnd.google-apps.folder')
BACKUP_FILE_MIME_TYPE = os.environ.get('GOOGLE_DRIVE_BACKUP_FILE_MIME_TYPE', 'text/xml')

def create_service(client_secret_file, api_name, api_version, *scopes, prefix=''):
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    
    creds = None
    working_dir = os.getcwd()
    token_dir = 'tokens'
    token_file = f'token_{API_SERVICE_NAME}_{API_VERSION}{prefix}.json'

    if not os.path.exists(os.path.join(working_dir, token_dir)):
        os.mkdir(os.path.join(working_dir, token_dir))

    if os.path.exists(os.path.join(working_dir, token_dir, token_file)):
        creds = Credentials.from_authorized_user_file(os.path.join(working_dir, token_dir, token_file), SCOPES)


    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(os.path.join(working_dir, token_dir, token_file), 'w') as token:
            token.write(creds.to_json())

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=creds, static_discovery=False)
        print(API_SERVICE_NAME, API_VERSION, 'service created successfully')
        return service
    except Exception as e:
        print(e)
        print(f'Failed to create service instance for {API_SERVICE_NAME}')
        os.remove(os.path.join(working_dir, token_dir, token_file))
        return None

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime(year, month, day, hour, minute, 0).isoformat() + 'Z'
    return dt

def get_resource(name, drive, mime_type, parent_id):
    
    resource = None
    
    results = drive.files().list(
            q=f"'{parent_id}' in parents and name='{name}' and mimeType='{mime_type}'",
            fields='files(id, name)')
    
    try: 
        results = results.execute()
        resource = results.get('files', [])[0]
    except:
        print('Resource {name}, not found in parent with id {parent_id}')
 
    return resource

def create_resource(drive, name, parent_id, mime_type, local_file_path=None):
    file_metadata = {
        'name':name,
        'parents': [parent_id]
    }

    if not local_file_path and mime_type == BACKUP_FILE_MIME_TYPE:
        local_file_path = name

    media_content = MediaFileUpload(local_file_path, mimetype=mime_type)

    try:
        resource = drive.files().create(
            body=file_metadata,
            media_body=media_content
        ).execute()
    except Exception as e:
        print(e)

    return resource

def create_if_not_exists(drive, name, parent_id, mime_type):
    resource = get_resource(drive=drive, name=name, parent_id=parent_id) 
    if not resource:
         create_resource(drive=drive,name=name,parent_id=parent_id,mime_type=mime_type)

def main():

    API_NAME    ='drive'
    API_VERSION = 'v3'

    CLIENT_SECRET_FILE = os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET_FILE', 'credentials.json') 
    
    CURRENT_DAY   = datetime.now().day
    CURRENT_MONTH = datetime.now().month
    CURRENT_YEAR  = datetime.now().year

    PARENT_ID = os.environ.get('GOOGLE_DRIVE_PARENT_ID_FOLDER')

    # If modifying these scopes, delete the file from tokens folder.
    SCOPES = ['https://www.googleapis.com/auth/drive']

    drive = create_service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

    year_folder = create_if_not_exists(name=CURRENT_YEAR, drive=drive, parent_id=PARENT_ID, mime_type=FOLDER_MIME_TYPE)
    
    create_if_not_exists(name=CURRENT_YEAR, drive=drive, parent_id=year_folder['id'], mime_type=BACKUP_FILE_MIME_TYPE)

    # if not folder_exists:
    #     create_resource(drive, name=name, parent_id=PARENT_ID 'application/vnd.google-apps.folder')

if __name__=='__main__':
    main()