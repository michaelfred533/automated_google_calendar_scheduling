"""

"""

from __future__ import print_function
import datetime
import os.path
import pandas as pd
import logging
import copy

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from apscheduler.schedulers.background import BackgroundScheduler

from google.oauth2 import service_account

import schedule


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# -------------------------------------------------------------------------

# service = schedule.access_calendar(SCOPES)


# logging.basicConfig(level = logging.DEBUG)

# start_date = str(datetime.date.today())
# end_date = str((datetime.date.today() + datetime.timedelta(days = 2)))
# logging.info(f"start date is {start_date}")
# logging.info(f"end date is {end_date}")
# events = schedule.get_events(service, start_date, end_date)
# print(len(events), events[0])

# ----------------------------------------------------------------------------------------------------------------

def get_user_input():
    """
    get user input for activities and what type of activities they are.
    whether to include free-recall sessions or not
    """

    # input list of activitys and proportion for each activity

    while True:
        total_time = input("How many total hours do you want to spend learning tomorrow? ")
        
        try:
            total_time = int(total_time)
        except ValueError:
            continue

        if len(str(total_time)) <= 2:
            break
        print("Wrong format. Please try again. The expected format is a 1-2 digit whole number.")
    
    while True:
        while True:    
            subjects = input("Please enter the activities you wish to schedule, seperated by a comma and space (A, B, C): ")
            subjects = subjects.split(", ")
            if len(set(subjects)) == len(subjects):
                break
            print("There are duplicates in your list. Please try again.")

        while True:
            memorize_or_not_list = input(f"The activites you chose: {subjects}. Please enter 'Y' or 'N' for each activity depending on if it involves memorization (Y, N, Y): ")
            memorize_or_not_list = memorize_or_not_list.lower().split(", ")
            if all(mem == "y" or mem == 'n' for mem in memorize_or_not_list) and (len(memorize_or_not_list) == len(subjects)):
                break
            print("ERROR: memorize_or_not_list in unexpected format: ", memorize_or_not_list, "Please try again. Make sure the length of the list matches the number of activites entered. You entered ", len(subjects), " subjects.") 

        while True:
            proportions = input("Please input the proportion of your total time you'd like to spend for each activity in order separtated by a comma and space: (.5, .25, .25): ")
            proportions = [float(prop) for prop in proportions.split(", ")]
            if sum(proportions) == 1.0:
                break
            print("ERROR: proportions do not add to 1: ", proportions, "Please try again")

        if len(subjects) == len(proportions):
            break
        
        print("ERROR: The number of activities and the number of proportions entered do not match. Please try again.")
        print("subjects length is ", len(subjects), "and proportions length is ", len(proportions))

    return total_time, subjects, proportions, memorize_or_not_list
    
    
def calc_times(total_time, subjects, proportions):

    #subjects, proportions = zip(*[(tup[0], tup[1]) for tup in subject_proportion_tuples])

    total_time = total_time * 60 # convert hours to minutes

    subject_time_tuples = []
    for sub, prop in zip(subjects, proportions):
        time = round((total_time * prop) / 15) * 15 # round time to nearest 15min multiple
        
        subject_time_tuples.append((sub, time))
    
    return subject_time_tuples

def separate(subject_time_tuples, memorize_or_not_list):

    subject_time_tuples_mem = []
    subject_time_tuples_nonmem = []
    for tup, mem in zip(subject_time_tuples, memorize_or_not_list):
        
        if mem == "n":
            subject_time_tuples_nonmem.append(tup)
        elif mem == "y":
            subject_time_tuples_mem.append(tup)
        else: print("mem in unexpected format: ", mem) # NOTE: this line should never fire because of the earlier check

    return subject_time_tuples_mem,  subject_time_tuples_nonmem 


def create_events(subject_time_tuples, is_mem = 0):
    """
    input: 
        
    
    output: events in 15m increments to schedule
    """
    
    all_events_list = []

    for tup in subject_time_tuples:
        print("current tup: ", tup)
        events = helper_calc_event(tup[0], tup[1], is_mem)
        all_events_list.extend([events]) 

    return all_events_list


def helper_calc_event(subject, time, is_mem = 0):
    """
    input: 
    time: amount of time to practice the subject
    subject: the activity to create calculate time-blocks
    
    output: events in 15m increments to schedule
    """
    ## TODO: combine these 2 events together into a block event of study + recall.
    ## for use in interleave function()
    if is_mem: 
        #print("is_mem YES: ", is_mem)
        #print("time and subject: ", time, subject)
        events = []
        time_copy = copy.copy(time)
        while time_copy > 0:
            if time_copy == 15:
                print('last 15m chunk, add to previous recall block')
                if events:
                    events[-1]['duration'] += 15
                    events[-1]['recall block'][0]['duration'] += 15
                elif not events:
                    event_study = {
                    'name' : (subject + " study"),
                    'duration' : time_copy,
                    }
                    events.append(event_study)
                time_copy = 0
            elif time_copy == 30: # if 30m remaining, insert only study time
                print('last 30m chunk:', time_copy)
                event_study = {
                    'name' : (subject + " study"),
                    'duration' : time_copy,
                    }
                events.append(event_study)
                time_copy = 0

            elif time_copy >= 45:
                print('time greater than 45:', time_copy)
                event_study = {
                    'name' : (subject + " study"),
                    'duration' : 30,
                    }
                event_recall = {
                    'name' : (subject + " recall"),
                    'duration' : 15,
                    }
                recall_block = {'recall block' : [event_study, event_recall], 'duration' : 45}
                events.append(recall_block)
                time_copy -= 45
            
        return events

#-------------------------------
    elif not is_mem: # technically this line is redundant. But helpful for testing
        #print("event is practice, not mem")
        #print("time and subject: ", time, subject)
        events = []
        time_copy = copy.copy(time)

        while time_copy > 0:

            if time_copy >= 60:
                print('time greater than 1 hour:', time_copy)
                event_practice = {
                    'name' : (subject + " practice"),
                    'duration' : 60,
                    }
                events.extend([event_practice])
                time_copy -= 60

            else:
                print('Last chunk under 1 hour: ', time_copy)
                event_practice = {
                    'name' : (subject + " practice"),
                    'duration' : time_copy,
                    }
                events.append(event_practice)
                time_copy = 0
        
        return events
        

def mix_lists(events_1, events_2):
    """
    
    """
    if len(events_1) >= len(events_2):
        events_long, events_short = events_1, events_2
    else:
        events_long, events_short = events_2, events_1 

    mixed_list = []
    for event_short, event_long in zip(events_short, events_long):
        mixed_list.extend([event_long, event_short])

    length_difference = len(events_long) - len(events_short)
    if length_difference > 0: 
        mixed_list.extend(events_long[-length_difference:])


    print('mixed list: ', mixed_list)
    return mixed_list


def interleave(events):
    """
    this function will actually be used to interleave nonmem and mem items 
    amongst themselves and then again to merge together
    """
    if len(events) > 2:
        print('ENTERING recursion: ', events[1:])
        print()
        interleaved_events = interleave(events[1:])
        events = [events[0], interleaved_events] # create new list with interleaved events and leftover events
    
    print('EXITING recursion')
    events_1, events_2 = events[0], events[1]
    #time_sum_1 = sum(item['duration'] for item in events_1 if 'duration' in item)
    #time_sum_2 = sum(item['duration'] for item in events_2 if 'duration' in item)


    #if time_sum_1 >= time_sum_2:
    if len(events_1) >= len(events_2):
        events_more, events_less = events_1, events_2
        #time_sum_more, time_sum_less = time_sum_1, time_sum_2
    else:
        events_more, events_less = events_2, events_1
        #time_sum_more, time_sum_less = time_sum_2, time_sum_1

    splits = round(len(events_more) / (len(events_less) + 1))
    if splits == 0:
        print('changing splits from 0 to 1..')
        splits = 1
    print('splits: ', splits)
    
    indexes = [ind for ind in range(splits, len(events_more)) if ind % splits == 0]
    if len(indexes) < len(events_less):
        print('indexes shorter than num of events: ', indexes, 'num events: ', len(events_less))
        indexes.append(len(events_more) + len(events_less) - 1)
    print("indexes: ", indexes)

    final_order = copy.copy(events_more)
    for ind, event, i in zip(indexes, events_less, range(len(indexes))):
        final_order.insert(ind + i, event)
    

    print('Interleave results: ', final_order)
    return final_order

# user_input -> calc_times -> separate -> create_events -> interleave

if __name__ == "__main__":
    #total_time, subjects, memorize_or_not_list = get_user_input()
    #print(total_time, subjects, memorize_or_not_list)
    
    # ADDED
    total_time, subjects, proportions, memorize_or_not_list = 5, ['A', 'B', 'X', 'Y', 'Z'], [.20, .20, .20, .20, .20], ['y', 'y', 'n', 'n', 'n'] 
    
    subject_time_tuples = calc_times(total_time, subjects, proportions)
    subject_time_tuples_mem,  subject_time_tuples_nonmem = separate(subject_time_tuples, memorize_or_not_list)

    events_mem = create_events(subject_time_tuples_mem, is_mem = 1)
    events_nonmem = create_events(subject_time_tuples_nonmem, 0)
    print("both event sets before interleaving: ")
    print(events_mem)
    print(events_nonmem)

    mixed_events = mix_lists(events_mem, events_nonmem)
    
    interleave(mixed_events)

    ## LEAVING OFF HERE: 
    # create tests for interleave() funciton - test with 3 or 5 subjects

"""
notes:

if you want to change how different mem subjects and non-mem subjects are dispursed, 
tweak the more/less logic flow in interleave() function 

"""








# def create_events():

#     # Define the event details
#     event = {
#         'summary': 'Sample Event',
#         'location': 'Sample Location',
#         'description': 'This is a sample event description.',
#         'start': {'dateTime': '2023-10-05T10:00:00', 'timeZone': "America/Los_Angeles"},
#         'end': {'dateTime': '2023-10-05T11:00:00', 'timeZone': "America/Los_Angeles"},
#     }
#     # Insert the event into the primary calendar
#     event = service.events().insert(calendarId='primary', body=event).execute()
#     print('Event created: %s' % (event.get('htmlLink')))


