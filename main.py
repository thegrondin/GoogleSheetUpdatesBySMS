from __future__ import print_function

import getopt
import os.path
import os
import sys
import threading

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from twilio.rest import Client
from tinydb import TinyDB, Query

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

SAMPLE_SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
SAMPLE_RANGE_NAME = os.environ.get('SPREADSHEET_RANGE')

db = TinyDB('./db.json')
phones_db = TinyDB('./phones.json')


def send_sms(msg, to):
    message = client.messages.create(
        messaging_service_sid=os.environ.get('TWILIO_MESSAGING_SERVICE_SID'),
        body=msg,
        to=to
    )

    print(message.sid)


def get_spreadsheet(service):
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])

    new_data = []

    for row in values:
        db_row = Query()
        if not db.search(db_row.title == str(row[0])):
            db.insert({'title': str(row[0])})
            new_data.append(row[0])

    if new_data:
        for phone in phones_db.all():
            send_sms(f"Hello ! The Google Sheet was updated ({', '.join(new_data)})",
                     str(phone.get('number')))

    threading.Timer(10, get_spreadsheet, (service,)).start()


def add_phone(number):
    db_row = Query()
    if not db.search(db_row.title == str(number)):
        phones_db.insert({'number': f'+{number}'})


def start_sms_sheets_process():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    get_spreadsheet(service)

    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:

        print('Name, Major:')
        for row in values:
            # Print columns A and E, which correspond to indices 0 and 4.
            print('%s' % (row[0]))


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "a:", ["add-phone="])
    except getopt.GetoptError:
        print('googlesheetupdateSMS.py -a 1234568901')
        sys.exit(2)

    if opts:
        for opt, arg in opts:
            if opt in ('-a', '--add-phone'):
                add_phone(arg)
        return

    start_sms_sheets_process()


if __name__ == "__main__":
   main(sys.argv[1:])