from __future__ import print_function
import os.path

import socket
socket.setdefaulttimeout(60) 


from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import csv
import sys
import base64
import json
import time
import os
from pyasn1.type.univ import Null
import requests
from configparser import ConfigParser
import time
import datetime

while 2>1:

    ###################### Main Sequence ########################

    #begin timer
    t0=time.time()

    #reads the config file to import settings
    config = ConfigParser()
    config.read('config.ini')

    #reads the PerformanceSelection file for requested performance metrics and associated points
    with open('GraphIDs.csv', 'r', encoding='utf-8-sig') as csvfile:
        reading_raw = list(csv.reader(csvfile))


    ##### Obtaining Token#####


    #reads the client_id and client_secret from the config file to generate the token for the GET command

    client_id = config.get('main', 'client id')
    client_secret = config.get('main', 'client secret')

    url = 'https://api.buildingos.com/o/token/'
    data = {"grant_type": "client_credentials"}

    creds = base64.b64encode("{}:{}".format(client_id,client_secret).encode())
    headers = {'Authorization': 'Basic ' + creds.decode('UTF-8'), 'Content-Type': 'application/x-www-form-urlencoded'}

    r = requests.post(url, headers=headers, data=data)

    access_token = r.json()["access_token"]

    ##### Data Request #####

    headers = {'Authorization': 'Bearer '+access_token}

    payload={'resolution':'live'}
    #this payload can be used for user editable time ranges of data
    #payload={'resolution':'live','start':'2021-05-01T08:45:00-04:00','end':'2021-05-24T08:45:00-04:00'}

    #starts timer to see how efficiently points are being pulled
    t0=time.time()
    total_points=1
    url_temp=[]
    url=[]
    input_var_temp=[]
    n=1
    while n<len(reading_raw):
        #creates the lists of all of the UUIDs to pull data for
        m=4
        input_var_GET_raw=[]    
        while m<len(reading_raw[n]):
            input_var_GET_raw.append(reading_raw[n][m])
            m+=1
            
        input_var_GET=list(filter(None, input_var_GET_raw))
        input_var_temp.append([reading_raw[n][0],reading_raw[n][1],reading_raw[n][2],reading_raw[n][3],reading_raw[n][4],reading_raw[n][5],reading_raw[n][6],reading_raw[n][7],reading_raw[n][8],reading_raw[n][9]])
        n+=1

    input_var=[]    
    n=0
    while n<len(input_var_temp):
        input_var.append(list(filter(None,input_var_temp[n])))
        n+=1

    url='https://api.buildingos.com/meters/data?'

    uuid_temp=[]
    x=0
    y=6
    while x<len(input_var):
        while y<len(input_var[x]):

            uuid_temp.append(input_var[x][y])
            
            y+=1
            
        x+=1
        y=6

    uuid_temp_short=[]
    for i in uuid_temp:
        if i not in uuid_temp_short:
            uuid_temp_short.append(i)

    x=0   
    url_count=0 
    while x<len(uuid_temp_short):
            if url_count==0:
                url=url+'uuid='+uuid_temp_short[x]
            else:
                url=url+'&uuid='+uuid_temp_short[x]
            
            url_count=+1
            x+=1

    r=requests.get(url, params=payload, headers=headers, verify=False)

    data=r.json()

    time.sleep(1)

    print(url)

    reading_out=[]
    reading_out_temp=[]
    a=0
    b=6
    c=0
    while a <len(input_var):
        if len(input_var[a]) > 6:
            while b<len(input_var[a]):
                char=input_var[a][b]

                if len(reading_out_temp)==0:
                    reading_out_temp.append([input_var[a][0],input_var[a][1],input_var[a][2],input_var[a][4],input_var[a][5],
                    data['data'][char]['data'][len(data['data'][char]['data'])-1]['localtime'],
                    data['data'][char]['data'][len(data['data'][char]['data'])-1]['value']])
                else:
                    reading_out_temp[len(reading_out_temp)-1].append(data['data'][char]['data'][len(data['data'][char]['data'])-1]['localtime'])
                    reading_out_temp[len(reading_out_temp)-1].append(data['data'][char]['data'][len(data['data'][char]['data'])-1]['value'])

                b+=1

        a+=1
        b=6
        reading_out.append(reading_out_temp[0])
        reading_out_temp=[]




    t1= time.time()
    print(t1-t0)
    print((t1-t0)/len(url))


    sheet_count=0

    while sheet_count <len(reading_out):


        ################################## GOOGLE SHEETS SECTION #############################################################

        #sets the name of the spreadsheet and the range of values to work within
        spreadsheetId = reading_out[sheet_count][0]
        rangeId = reading_out[sheet_count][1]
        sheetID = reading_out[sheet_count][2]

        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

        credentials = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        # if os.path.exists('token.json'):
        #     creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        #pulls in the authentication json
        #os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:\\Users\\irykjn\\Desktop\\BuildingOS Calcs\\BuildingOS Graphing\\token.json"
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getcwd()+"\\token.json"

        service = build('sheets', 'v4', credentials=credentials)

        #reads teh data currently in the spreadsheet
        result=service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId,
        range=rangeId,
        ).execute()

        existing_values=[]
        #pulls down all existing data
        existing_values=result.get('values',[])



        #checks to see if the latest data point is new or not
        #if not new, skip
        #if new, run checks and append
        last_time_stamp = existing_values[len(existing_values)-1][2]

        print('\nGraph {} of {}'.format(sheet_count+1,len(reading_out)))
        now = datetime.datetime.now()
        print("Current date and time : ")
        print(now.strftime("%Y-%m-%d %H:%M:%S"))

        if last_time_stamp ==reading_out[sheet_count][5]:
            print('No new data')
        else:
            #checks to see if data can be appended freely or needs to be culled and then appended
            print('Updating graph')
            if len(existing_values)>int(input_var[sheet_count][3])-1:
                
                print("\nRemoving row from sheet {} in spreadsheet {}".format(sheetID,spreadsheetId))

                spreadsheet_data = [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheetID,
                                "dimension": "ROWS",
                                "startIndex": 0,
                                "endIndex": 1
                            }
                        }
                    }
                ]

                update_spreadsheet_data = {"requests": spreadsheet_data}

                service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheetId,
                body=update_spreadsheet_data,
                ).execute()

            #appends the new data into the spreadsheet
            # x=0
            # values=[]
            # while x<len(reading_out[sheet_count-1]):
            #     values_temp = reading_out[sheet_count-1][x]
            #     del values_temp[0:2]
            #     values.append(values_temp)
            #     x+=1

            values_temp=[]
            values=[]
            
            values_temp = reading_out[sheet_count].copy()
            del values_temp[0:3]
            values.append(values_temp)
            



            resource = {
            "majorDimension": "ROWS",
            "values": values
            }


            service.spreadsheets().values().append(
            spreadsheetId=spreadsheetId,
            range=rangeId,
            body=resource,
            valueInputOption="USER_ENTERED"
            ).execute()

        sheet_count+=1

    t1=time.time()

    total_time=t1-t0

    print("\nWaiting {} seconds until next update.".format(900-total_time))
    time.sleep(900-total_time)
