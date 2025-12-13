#!/usr/bin/env python
"""
helpers - Handles AfterScan projects configuration and metadata.

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "helpers"
__version__ = "1.0.2"
__data_version__ = "1.0"
__date__ = "2025-12-13"
__version_highlight__ = "WIP: Move custom_json_encoder to helpers.py"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import time
from collections import deque
import logging
import json
from datetime import datetime
from dataclasses import asdict
from job_manager import JobEntry
from configuration_manager import ProjectConfigEntry


# --- Static functions ---
# Define a function for
# identifying a Digit
def is_a_number(string):
    # Make a regular expression
    # for identifying a digit
    regex = '^[0-9]+$'
    # pass the regular expression
    # and the string in search() method
    if (re.search(regex, string)):
        return True
    else:
        return False


def empty_queue(q):
    while not q.empty():
        item = q.get()
        logging.debug(f"Emptying queue: Got {item[0]}")


# --- Utility classes ---
class FPSTracker:
    """
    A class to Calculate the number of processed frames per second.
    
    The methods (add_value and calculate_average) are instance methods 
    because they must access the instance's state (self.values).
    """

    def __init__(self):
        # Initialize the state (the values being tracked)
        self.time_list: list[time.time()] = []
        self.start_time = time.time()
        self.fps_value = -1


    def register_frame(self):
        """Adds a new value to the series."""
        frame_time = time.time()
        # Determine if we should start new count (last capture older than 5 seconds)
        if len(self.time_list) == 0 or self.time_list[-1] < frame_time - 12:
            self.start_time = frame_time
            self.time_list.clear()
            self.fps_value = -1
        # Add current time to list
        self.time_list.append(frame_time)
        # Remove entries older than one minute
        self.time_list.sort()
        while self.time_list[0] <= frame_time-60:
            self.time_list.remove(self.time_list[0])
        # Calculate current value, only if current count has been going for more than 10 seconds
        if frame_time - self.start_time > 60:  # no calculations needed, frames in list are all in the last 60 seconds
            self.fps_value = len(self.time_list)/60
        elif frame_time - self.start_time > 10:  # some  calculations needed if less than 60 sec
            self.fps_value = int((len(self.time_list) * 60) / (frame_time - self.start_time))/60

    def get_fps(self):
        return self.fps_value
    
    def reset(self):
        self.time_list.clear()
        self.start_time = time.ctime()
        self.fps_value = -1


class RollingAverage:
    """
    A class to Calculate the average of the last n values provided
    
    The methods (add_value and calculate_average) are instance methods 
    because they must access the instance's state (self.values).
    """
    def __init__(self, window_size):
        self.window_size = window_size
        self.window = deque(maxlen=window_size)
        self.sum = 0


    def add_value(self, value):
        # If the deque is full, subtract the element that will be dropped
        if len(self.window) == self.window_size:
            # Access the leftmost element before it's overwritten
            self.sum -= self.window[0]  # Peek at the oldest value
        self.window.append(value)  # Append new value, oldest is auto-removed by maxlen
        self.sum += value


    def get_average(self):
        if len(self.window) <= 0:  # Return averages as soon as possible
            return None
        return self.sum / len(self.window)


    def get_min(self):
        return min(self.window) if len(self.window) > 0 else 0


    def get_max(self):
        return max(self.window) if len(self.window) > 0 else 0


    def clear(self):
        self.window.clear()
        self.sum = 0


class CustomJsonEncoder(json.JSONEncoder):
    """
    A custom JSON Encoder that handles dataclasses and datetime objects 
    by automatically converting them to serializable dictionaries or strings.
    """
    def default(self, obj):
        # 1. Handle dataclasses (like JobEntry or ProjectConfigEntry)
        # Note: This automatically respects nested fields.
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        
        # 2. Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
            
        # 3. For all other types, use the default encoder behavior
        return super().default(obj)