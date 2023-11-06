#!/bin/python3.10

from __future__ import print_function

import os, sys, getopt, logging

from datetime import datetime

from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

FOLDER_MIME_TYPE   = os.environ.get('GOOGLE_DRIVE_FOLDER_MIME_TYPE', 'application/vnd.google-apps.folder')
FILE_MIME_TYPE = os.environ.get('GOOGLE_DRIVE_BACKUP_FILE_MIME_TYPE', 'text/xml')

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
        print('Token created successfully!')
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
        print(f'{"Folder" if mime_type == FOLDER_MIME_TYPE else "File" } named: {name} not found in parent folder with id: {parent_id}')
 
    return resource

def create_resource(drive, name, parent_id, mime_type, local_file_path=None):
    file_metadata = {
        'name':name,
        'parents': [parent_id],
        'mimeType': mime_type
    }
    media_content = None
    if mime_type == FILE_MIME_TYPE:
        media_content = MediaFileUpload(local_file_path, mimetype=mime_type)

    try:
        resource = drive.files().create(
            body=file_metadata,
            media_body=media_content
        ).execute()
        print(f'{"Folder" if mime_type == FOLDER_MIME_TYPE else "File" }: {name} created!')
    except Exception as e:
        print(e)

    return resource

def create_if_not_exists(drive, name, parent_id, mime_type, local_file_path=None):
    resource = get_resource(drive=drive, name=name, parent_id=parent_id, mime_type=mime_type) 
    if not resource:
         resource = create_resource(drive=drive, name=name, parent_id=parent_id, mime_type=mime_type, local_file_path=local_file_path)
    return resource

def backup(target_file_path, root_folder_parent_id, drive):

    CURRENT_DAY   = datetime.now().day
    CURRENT_MONTH = datetime.now().month
    CURRENT_YEAR  = datetime.now().year
    
    year_folder  = create_if_not_exists(name=CURRENT_YEAR, drive=drive, parent_id=root_folder_parent_id, mime_type=FOLDER_MIME_TYPE)
    month_folder = create_if_not_exists(name=CURRENT_MONTH, drive=drive, parent_id=year_folder['id'], mime_type=FOLDER_MIME_TYPE)
    
    file_name=f'{CURRENT_DAY}-{CURRENT_MONTH}-{CURRENT_YEAR}-{target_file_path.split("/").pop()}'
    create_if_not_exists(name=file_name, drive=drive, parent_id=month_folder['id'], mime_type=FILE_MIME_TYPE, local_file_path=target_file_path)

def main(argv):

    API_NAME    ='drive'
    API_VERSION = 'v3'

    # If modifying these scopes, delete the file from tokens folder.
    DRIVE_SCOPES =  os.environ.get('GOOGLE_DRIVE_SCOPES', 'https://www.googleapis.com/auth/drive').split(',')

    PARENT_ID = os.environ.get('GOOGLE_DRIVE_PARENT_ID_FOLDER')

    CLIENT_SECRET_FILE = os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET_FILE', 'credentials.json')
    BACKUP_TARGET_FILE_PATH   = os.environ.get('BACKUP_TARGET_FILE_PATH', '/config')

    only_renew_token = False

    longopts=["help",
              "renew_token",
              "api_name=", 
              "api_version=", 
              "drive_scopes=", 
              "parent_id=", 
              "secret_file=",
              "file="]

    opts, args = getopt.getopt(args=argv, shortopts="hp:s:f:r", longopts=longopts)

    for opt, arg in opts:
        if opt in ('-h', '--help'): help()
        elif opt in ('-r', '--renew_token'): only_renew_token = True 
        else:
            if opt == '--api_name': API_NAME = arg
            if opt == '--api_version': API_VERSION = arg
            if opt == '--drive_scopes': DRIVE_SCOPES = arg.split(',')
            if opt in ('-p', '--parent_id'): PARENT_ID = arg
            if opt in ('-s', '--secret_file'): CLIENT_SECRET_FILE = arg
            if opt in ('-f', '--file'):  BACKUP_TARGET_FILE_PATH = arg

    drive = create_service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, DRIVE_SCOPES)

    if not only_renew_token:
        backup(BACKUP_TARGET_FILE_PATH, PARENT_ID, drive)

if __name__=='__main__':
    main(sys.argv[1:])