from __future__ import print_function
import datetime
import os.path
import pandas as pd
from difflib import SequenceMatcher

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from apscheduler.schedulers.background import BackgroundScheduler


scheduler = BackgroundScheduler()

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_events(start_date, end_date):
    """
    Calls the Google Calendar API and pulls all the events in the calendar from within the date-range specified.

    Inputs: start date and end date to pull events from
    Outputs: list of calendar event items
    """
    print("Getting events...")

    # 1) Define the time period to collect data from --------------------

    start_date = (
        datetime.datetime.strptime(str(start_date), "%Y-%m-%d").isoformat() + "Z"
    )  # 'Z' indicates UTC time
    end_date = (
        datetime.datetime.strptime(str(end_date), "%Y-%m-%d").isoformat() + "Z"
    )  # 'Z' indicates UTC time
    # datetime.datetime.utcnow()

    # events = fetch_events(start_date, end_date)

    # 2) Gather credentials / log in --------------------------

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        # Refresh creds if they are expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        # Have user login to get creds
        else:
            flow = (
                InstalledAppFlow.from_client_secrets_file(  # construct instance of flow
                    "credentials.json", SCOPES
                )
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build(
        "calendar", "v3", credentials=creds
    )  # Creates the resource for interacting with the calendar api

    # 3) Gather events from the Google Calendar API -------------------------------

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_date,
            timeMax=end_date,
            singleEvents=True,
            maxResults=2500,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        print("No events found.")
    print(type(events))
    print(events[:10])
    return events


def extract_event_data(events):
    """
    Extract data from each event. Records the time spent on each activity within and across days.

    Input:
        events - List of event items pulled from Google Calendar
    Outputs:
        events_for_all_days_dict - a dictionary that contains the duration of each event for each day
        total_event_times_dict - a dictionary that contains a running total of the time spent of each activity
    """

    # 1) Gather data on each event --------------------

    events_for_all_days_dict = {}
    total_event_times_dict = {}

    # print(event['summary'], event_start_date)
    ## BUG: Default value for maxResults in list() above is 250, I set it to 2500 instead.
    for i, event in enumerate(events):
        # Extract the date and time of the start and the end of the event
        event_start_date = datetime.datetime.strptime(
            event["start"]["dateTime"], "%Y-%m-%dT%H:%M:%S%z"
        )
        event_end_date = datetime.datetime.strptime(
            event["end"]["dateTime"], "%Y-%m-%dT%H:%M:%S%z"
        )

        # Account for user-error in entry of event names: Strip leading and trailing spaces, and convert to lowercase.
        event_name = event["summary"].strip().lower()

        # Account for spelling errors by matching very closely related strings (eg. "reponding" and "responding")
        for name in total_event_times_dict.keys():
            ratio = SequenceMatcher(None, event_name, name).ratio()
            if (ratio != 1) & (ratio > 0.9):
                event_name = name

        current_day = event_start_date.date()

        # Define starting variables for the first iteration though the for-loop
        if i == 0:
            previous_day = event_start_date.date()
            events_for_current_day_dict = {}

        # Every time the iteration reaches a new day, save values for the previous day and create new variables for next day
        if previous_day != current_day:
            events_for_all_days_dict[str(previous_day)] = events_for_current_day_dict
            events_for_current_day_dict = {}
            previous_day = current_day

        event_duration = (
            event_end_date - event_start_date
        ).total_seconds() / 60  # Event duration in minutes

        # Add events to events_for_current_day_dicts to keep track of time spent for each day
        if event_name in events_for_current_day_dict.keys():
            events_for_current_day_dict[event_name] += event_duration
        else:
            events_for_current_day_dict[event_name] = event_duration

        # Add events separately to total_event_times_dict to track total time spent on each event over the entire data collection period
        if event_name in total_event_times_dict.keys():
            total_event_times_dict[event_name] += event_duration
        else:
            total_event_times_dict[event_name] = event_duration

        # Save the events from the last day
        if i == len(events) - 1:
            events_for_all_days_dict[str(previous_day)] = events_for_current_day_dict

    return events_for_all_days_dict, total_event_times_dict
    # -------------------- Save event data in a csv file to be uploaded to Tableau --------------------


def save_to_csv(events_for_all_days_dict, total_event_times_dict):
    # 1) Create empty lists for each activity
    set_of_all_events = set()
    convert_to_csv_dict = {"Days": []}
    for day in events_for_all_days_dict.keys():
        convert_to_csv_dict["Days"].append(day)
        for event in events_for_all_days_dict[day]:
            set_of_all_events.add(event)
            if (
                "(" + event + ")" + " - time spent for each day"
                not in convert_to_csv_dict.keys()
            ):
                convert_to_csv_dict[
                    "(" + event + ")" + " - time spent for each day"
                ] = []

    # 2) Record the time spent on each activity for each day, or record 0 if the activity was not perfermed
    for day in convert_to_csv_dict["Days"]:
        for event in list(set_of_all_events):
            if event in events_for_all_days_dict[day]:
                convert_to_csv_dict[
                    "(" + event + ")" + " - time spent for each day"
                ].append(events_for_all_days_dict[day][event])
            else:
                convert_to_csv_dict[
                    "(" + event + ")" + " - time spent for each day"
                ].append(0)

    # print('convert_to_csv_dict', convert_to_csv_dict)

    # 3) Create data columns for the event names and the total time spent on each activity

    (
        convert_to_csv_dict[" Total time spent on each event"],
        convert_to_csv_dict["event Names"],
    ) = ([], [])

    for event in total_event_times_dict.keys():
        convert_to_csv_dict[" Total time spent on each event"].append(
            total_event_times_dict[event]
        )
        convert_to_csv_dict["event Names"].append(event)

    # The following 2 lines avoid the 'not equal length' error by filling in the remaining elements with nulls since our data columns differ in length.
    df = pd.DataFrame.from_dict(convert_to_csv_dict, orient="index")
    df = (
        df.transpose()
    )  # Transpose returns data to a normal format recognized by Tableau
    # print('df', df)
    df.to_csv("ScheduleData.csv")


if __name__ == "__main__":
    events = get_events("2022-07-01", "2022-09-01")
    events_for_all_days_dict, total_event_times_dict = extract_event_data(events)
    save_to_csv(events_for_all_days_dict, total_event_times_dict)
    print("...finished")


## NOTES ---------------

# Add KPIs, need Measure, Tager, Frequency, Source (this tool)
