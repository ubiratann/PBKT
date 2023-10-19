#!/bin/python3.10

from __future__ import print_function

import os

from googleapiclient.http import MediaFileUpload
from google_apis import create_service
from datetime import datetime

FOLDER_MIME_TYPE   = os.environ.get('GOOGLE_DRIVE_FOLDER_MIME_TYPE', 'application/vnd.google-apps.folder')
XML_FILE_MIME_TYPE = os.environ.get('GOOGLE_DRIVE_XML_FILE_MIME_TYPE', 'text/xml')



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

    if not local_file_path and mime_type == XML_FILE_MIME_TYPE:
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
    
    create_if_not_exists(name=CURRENT_YEAR, drive=drive, parent_id=year_folder['id'], mime_type=XML_FILE_MIME_TYPE)

    # if not folder_exists:
    #     create_resource(drive, name=name, parent_id=PARENT_ID 'application/vnd.google-apps.folder')

if __name__=='__main__':
    main()