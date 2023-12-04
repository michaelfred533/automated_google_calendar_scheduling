"""

"""

from __future__ import print_function # must be at beginning of file

# 3rd party imports

# python built-in imports
import copy
import datetime
from typing import List, Dict

# local imports
from create_schedule_package.event import Event, MemoryBlockEvent
from create_schedule_package import helper_functions
from create_schedule_package.topic_info import TopicInfo
from exceptions import * # imports all exception classes into current namespace, such that you don't have to call exceptions.MyError each time. This is usually a bad idea though, as names can overlap quickly in large projects
import get_calendar_data





# ----------------------------------------------------------------------------------------------------------------



def get_user_input() -> dict:
    """
    get user input for activities and what type of activities they are.
    whether to include free-recall sessions or not
    """
    class UserInputValidation:
        
        @staticmethod
        def get_time():
            
            while True:
                total_time = input("How many total hours do you want to spend learning tomorrow? ")
                
                try:
                    total_time = float(total_time)
                    if total_time >= 15: # time to study should be less than 15 hours
                        raise TooMuchStudyTimeError
                except ValueError:
                    print("Error: Please enter a number.")
                except TooMuchStudyTimeError:
                    print("Error: Please enter less than 15 hours.")
                except Exception:
                    print('Error: Something is wrong with the input information. Please try again.')
                
                else:
                    break
                
            total_time = total_time * 60
            return total_time
        
        @staticmethod
        def get_topics():
            
            while True:    
                topics = input("Please enter the activities you wish to schedule, seperated by a comma and space. eg. A, B, C: ")

                try:
                    if ", " not in topics:
                        raise MissingCommaError
                    topics = topics.split(", ")
                    if len(topics) >= 10:
                        raise TooManyTopicsError
                    if len(set(topics)) != len(topics):
                        raise DuplicateTopicsError
                
                except MissingCommaError:
                    print('Error: Please separate study activitys by a comma and space.')
                except TooManyTopicsError:
                    print('Error: You entered too many topics. Please enter less than 10 topics.')
                except DuplicateTopicsError:
                    print("Error: There are duplicates in your list. Please try again.")
                except Exception:
                    print('Error: Something is wrong with the input information. Please try again.')


                else:
                    break


            return topics
        
        @staticmethod
        def get_study_type_list(topics):

            while True:
                print(f"The activites you chose: {topics}.")
                study_type_list = input("Please enter the type for each activity (the current types are 'memory' and 'practice'). eg. memory, practice, practice: ")

                try:
                    if ", " not in study_type_list:
                        raise MissingCommaError
                    study_type_list = study_type_list.lower().split(", ")
                    if len(study_type_list) != len(topics):
                        raise LengthMismatchError
                    if not all(study_type == 'memory' or study_type == 'practice' for study_type in study_type_list):
                        raise IncorrectTypeError

                except MissingCommaError:
                    print("Error: Please enter each study type separated by a comma and space.")
                except LengthMismatchError:
                    print("Error: The length of the entered list does not match the length of the topics list.")
                except IncorrectTypeError:
                    print("Error: One or more of the types you entered does not match the supported types.")
                except Exception:
                    print('Error: Something is wrong with the input information. Please try again.')

                else: 
                    break

            return study_type_list
        
        @staticmethod
        def get_proportions(topics):
            while True:
                print(f"The activites you chose: {topics}.")
                proportions = input("Please input the proportion of your total time you'd like to spend for each activity in order separtated by a comma and space. eg. 0.5, 0.25, 0.25: ")
                
                try:
                    if ", " not in proportions:
                        raise MissingCommaError
    
                    proportions = [float(prop) for prop in proportions.split(", ")]
                    if len(proportions) != len(topics):
                        raise LengthMismatchError
                    if sum(proportions) != 1.0:
                        raise ProportionsDontAddToOneError
                except MissingCommaError:
                    print('Error: Please separate proportions by a comma and space.')
                except ValueError:
                    print('Error: Please enter numbers only.')
                except LengthMismatchError:
                    print('Error: The number of proportions does not match the number of topics entered.')
                except ProportionsDontAddToOneError:
                    print("Error: proportions do not add to 1: ", proportions)
                except Exception:
                    print('Error: Something is wrong with the input information. Please try again.')

                else:
                    break

            return proportions

    user_input_info = {}

    user_input_info['total_time'] = UserInputValidation.get_time()
    user_input_info['topics'] = UserInputValidation.get_topics()
    user_input_info['study_type_list'] = UserInputValidation.get_study_type_list(user_input_info['topics'])
    user_input_info['proportions'] = UserInputValidation.get_proportions(user_input_info['topics'])
    
    return user_input_info

def initialize_topic_info(user_input_info: dict) -> List[TopicInfo]:
    def calculate_times_for_topics(user_input_info):

        study_times = []
        for prop in user_input_info['proportions']:
            time = round((user_input_info['total_time'] * prop) / 15) * 15 # round time to nearest 15min multiple
            study_times.append(time)

        return study_times
    
    study_times = calculate_times_for_topics(user_input_info)
    
    topic_info_objects = []
    for topic, type, prop, time in zip(user_input_info['topics'], user_input_info['study_type_list'], user_input_info['proportions'], study_times):        
        topic_info_objects.append(TopicInfo(topic, type, prop, time))

    return topic_info_objects


def group_topic_info_by_type(topic_info_objects: List[TopicInfo]) -> Dict[str, List[TopicInfo]]:

    topic_info_grouped_by_type_dict = {}
    for topic_info in topic_info_objects:
        if topic_info.study_type in topic_info_grouped_by_type_dict.keys():
            topic_info_grouped_by_type_dict[topic_info.study_type].append(topic_info)
        else:
            topic_info_grouped_by_type_dict[topic_info.study_type] = [topic_info]

    return topic_info_grouped_by_type_dict 

def build_events_for_all_topics(topic_info_grouped_by_type_dict: Dict[str, List[TopicInfo]]) -> None:
    """
    input: 
    output:
    """
    # NOTE: Could rewrite this code to support more than 2 types

    for topic_type in topic_info_grouped_by_type_dict.keys():
        if topic_type == 'memory':
            for topic_info in topic_info_grouped_by_type_dict['memory']:
                build_events_for_memory_topic(topic_info)
        elif topic_type == 'practice':
            for topic_info in topic_info_grouped_by_type_dict['practice']:
                build_events_for_practice_topic(topic_info)
        else:
            raise Exception        

def build_events_for_practice_topic(topic_info: TopicInfo) -> None:
    """
    input: 
    output: 
    """

    def add_practice_event(topic_info, practice_event_duration):

        event_practice = Event(topic_info.topic, practice_event_duration, topic_info.study_type)
        topic_info.events.extend([event_practice])
        topic_info.time_remaining -= practice_event_duration

    while topic_info.time_remaining > 0:

        if topic_info.time_remaining >= 90:
            add_practice_event(topic_info, 90)

        else:
            add_practice_event(topic_info, topic_info.time_remaining)
    
def build_events_for_memory_topic(topic_info: TopicInfo) -> None:
    
    def add_memory_block_event(topic_info, memory_block_duration):
            
        recall_duration = 15
        study_duration = memory_block_duration - recall_duration

        memory_block = MemoryBlockEvent(topic_info.topic, memory_block_duration, topic_info.study_type, study_duration, recall_duration)

        memory_block.recall_event.duration = recall_duration
        memory_block.study_event.duration = study_duration

        topic_info.events.append(memory_block)
        topic_info.time_remaining -= memory_block_duration    

    while topic_info.time_remaining > 0:

        if topic_info.time_remaining == 60:
            add_memory_block_event(topic_info, 60)
        
        else:
            memory_block_duration = min(45, topic_info.time_remaining)
            add_memory_block_event(topic_info, memory_block_duration) 
      


def create_list_of_all_events_to_schedule(topic_info_grouped_by_type_dict: Dict[str, List[TopicInfo]]) -> List[List[Event]]:
    
    list_of_each_topics_event_lists = []
    for study_type_list in topic_info_grouped_by_type_dict.values():
        for topic_info in study_type_list:
            list_of_each_topics_event_lists.append(topic_info.events)

    return list_of_each_topics_event_lists


def interleave(list_of_each_topics_event_lists: List[List[Event]]) -> List[Event]:
    """
    """

    def evenly_distribute_events_less_into_events_more(events):
        
        def calculate_number_of_times_to_split_events_more_list(events):
            splits = round(len(events['more']) / (len(events['less']) + 1))
            # ensures at least 1 split
            splits = max(splits, 1)
            print('splits: ', splits)

            return splits
        
        def find_indexes_to_insert_events_less_into_events_more_list(events, splits):

            def add_extra_index_at_end_of_list(events, indexes):
                final_index = len(events['more']) + len(events['less']) - 1
                indexes.append(final_index)

                return indexes
            
            indexes = [ind for ind in range(splits, len(events['more'])) if ind % splits == 0]
            if len(indexes) < len(events['less']):
                print('indexes shorter than num of events: ', indexes, 'num events: ', len(events['less']))
                add_extra_index_at_end_of_list(events, indexes)


            print("indexes: ", indexes)

            return indexes

        splits = calculate_number_of_times_to_split_events_more_list(events)

        indexes = find_indexes_to_insert_events_less_into_events_more_list(events, splits)

        events_in_final_order = copy.copy(events['more'])
        for ind, event, i in zip(indexes, events['less'], range(len(indexes))):
            events_in_final_order.insert(ind + i, event)

        return events_in_final_order
    

   
    if len(list_of_each_topics_event_lists) > 2:
        print('ENTERING recursion: ', list_of_each_topics_event_lists[1:])
        print()
        interleaved_events = interleave(list_of_each_topics_event_lists[1:])
        list_of_each_topics_event_lists = [list_of_each_topics_event_lists[0], interleaved_events] # create new list with interleaved events and leftover events

       
    print('EXITING recursion')

    events = {
        'more': list_of_each_topics_event_lists[1],
        'less' : list_of_each_topics_event_lists[0],
        }

    events_in_final_order = evenly_distribute_events_less_into_events_more(events)

    print('Interleave results: ')
    for event in events_in_final_order:
        print(event)

    return events_in_final_order

def get_todays_calendar() -> List[dict]:
    
    start_date = str(datetime.date.today())
    end_date = str((datetime.date.today() + datetime.timedelta(days = 1)))

    service = get_calendar_data.access_calendar()
    events = get_calendar_data.get_events(service, start_date, end_date)
    print('from todays calendar: ', events, '\n')

    return events

def add_start_and_end_times_for_events(new_events_list: List[Event]) -> None:
   
    def add_start_end_duration_to_existing_events(existing_events):
        for event in existing_events:
            event['start_time'] = helper_functions.create_timezone_datetime_object('T' + str(event['start']['dateTime'][11:19]))
            event['end_time'] = helper_functions.create_timezone_datetime_object('T' + str(event['end']['dateTime'][11:19]))
            event['duration'] = (event['end_time'] - event['start_time']).total_seconds() / 60
    
    def find_non_overlaping_time(existing_events, proposed_new_event_time):
        def update_start_and_end_times(proposed_new_event_time):
            proposed_new_event_time['start'] = existing_event['end_time']
            proposed_new_event_time['end'] = proposed_new_event_time['start'] + datetime.timedelta(minutes = new_event.duration)
            print('updated start time: ', proposed_new_event_time['start'])
            return proposed_new_event_time
        
        for existing_event in existing_events:
            if proposed_new_event_time['start'] < existing_event['end_time'] and proposed_new_event_time['end'] > existing_event['start_time']:
                print('overlap found! proposed start: ', proposed_new_event_time['start'], 'existing event start: ', existing_event['start_time'])
                proposed_new_event_time = update_start_and_end_times(proposed_new_event_time)

        return proposed_new_event_time

    proposed_new_event_time = {
        'start': helper_functions.create_timezone_datetime_object('T09:00:00'),
        'end': None
    }
    
    existing_events = get_todays_calendar()
    add_start_end_duration_to_existing_events(existing_events)
    
    schedule = []
    for new_event in new_events_list:
        
        proposed_new_event_time['end'] = proposed_new_event_time['start'] + datetime.timedelta(minutes = new_event.duration)  
        proposed_new_event_time = find_non_overlaping_time(existing_events, proposed_new_event_time)            
        
        new_event.set_start_and_end_times(proposed_new_event_time)
        schedule.append(new_event)
        
        proposed_new_event_time['start'] = proposed_new_event_time['end']


def add_events_to_google_calendar(events_in_final_order: List[Event]) -> None:    

    for event in events_in_final_order:
        event.create_google_calendar_event()
        


def skip_unnecessary_steps(topic_info_objects: List[TopicInfo]) -> List[Event]:
    events_in_final_order = topic_info_objects[0].events

    return events_in_final_order

def run_program(user_input_info: Dict) -> None:
    topic_info_objects = initialize_topic_info(user_input_info)
    topic_info_grouped_by_type_dict = group_topic_info_by_type(topic_info_objects)
    build_events_for_all_topics(topic_info_grouped_by_type_dict)

    number_of_different_topics = len(topic_info_grouped_by_type_dict.keys())
    if  number_of_different_topics == 1:
        print('only 1 topic')
        events_in_final_order = skip_unnecessary_steps(topic_info_objects)
    else:
        list_of_each_topics_event_lists = create_list_of_all_events_to_schedule(topic_info_grouped_by_type_dict)
        sorted_list_of_each_topics_event_lists = sorted(list_of_each_topics_event_lists, key = len, reverse=True)
        events_in_final_order = interleave(sorted_list_of_each_topics_event_lists)
    
    add_start_and_end_times_for_events(events_in_final_order)
    add_events_to_google_calendar(events_in_final_order)

if __name__ == "__main__":

    user_input_info = get_user_input()
    run_program(user_input_info)

    # NOTE: Could distribute by type AND topic, right now only by topic
    # MAYBE - not sure if this is interleaving or just task-switching

