#!/usr/bin/env python
"""
AfterScan - Basic post-processing for scanned R8/S8 films

This utility is intended to handle the basic post-processing after film
scanning is completed.

Actions performed by this tool include:
- Stabilization
- Cropping
- Video generation

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "AfterScan"
__version__ = "1.30.23"
__data_version__ = "1.0"
__date__ = "2025-11-21"
__version_highlight__ = "Improve stabilization process, specially in extreme cases"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

import tkinter.messagebox
from tkinter import DISABLED, NORMAL, LEFT, RIGHT, TOP, BOTTOM, N, W, E, NW, NS, EW, RAISED, SUNKEN, END, VERTICAL, HORIZONTAL
from tkinter import Toplevel, Label, Button, Frame, LabelFrame, Canvas, Text, Scrollbar, Scale, Entry, Radiobutton, Listbox
from tkinter import Tk, IntVar, StringVar, OptionMenu

#from tkinter import *

#import tkinter.font as tkfont

from PIL import ImageTk, Image, ImageDraw, ImageFont

import os
import time
import subprocess as sp
import json
from datetime import datetime
import logging
import sys
import getopt
import cv2
import numpy as np
from glob import glob
import platform
import re
import shutil
from enum import Enum
import textwrap
import random
import threading
import queue
from matplotlib import font_manager
from tooltip import Tooltips
from rolling_average import RollingAverage
import hashlib
import uuid
import base64
from collections import deque
import webbrowser

try:
    import requests
    requests_loaded = True
except ImportError:
    requests_loaded = False

from define_rectangle import DefineRectangle

# Check for temporalDenoise in OpenCV at startup
HAS_TEMPORAL_DENOISE = hasattr(cv2, 'temporalDenoising')

# Frame vars
first_absolute_frame = 0
last_absolute_frame = 0
frame_scale_refresh_done = True
frame_scale_refresh_pending = False
frames_to_encode = 0
from_frame = 0
to_frame = 0
CurrentFrame = 0
StartFrame = 0
ReferenceFrame = 0
frame_selected = 0
global work_image, base_image, original_image
# FPS calculation (taken from ALT-Scann8)
FPS_LastMinuteFrameTimes = list()
FPS_StartTime = time.ctime()
FPS_CalculatedValue = -1
denoise_window_size = 3
temp_denoise_frame_deque = deque(maxlen=denoise_window_size)

# Configuration & support file vars
script_dir = os.path.dirname(os.path.realpath(__file__))

general_config_filename = os.path.join(script_dir, "AfterScan.json")
project_settings_filename = os.path.join(script_dir, "AfterScan-projects.json")
project_settings_backup_filename = os.path.join(script_dir, "AfterScan-projects.json.bak")
project_config_basename = "AfterScan-project.json"
project_config_filename = ""
project_config_from_file = True
project_name = "No Project"
default_job_list_filename_legacy = os.path.join(script_dir, "AfterScan_job_list.json")
default_job_list_filename = os.path.join(script_dir, "AfterScan.joblist.json")
JobListFilename = default_job_list_filename
job_list_hash = None    # To determine if job list has changed since loaded
temp_dir = os.path.join(script_dir, "temp")
if not os.path.exists(temp_dir):
    os.mkdir(temp_dir)
logs_dir = os.path.join(script_dir, "Logs")
if not os.path.exists(logs_dir):
    os.mkdir(logs_dir)
copy_templates_from_temp = False
resources_dir = os.path.join(script_dir, "Resources")
if not os.path.exists(resources_dir):
    os.mkdir(resources_dir)
    copy_templates_from_temp = True
# Soundtrack
soundtrack_file_path = os.path.join(script_dir, "projector-loop.mp3")
if os.path.isfile(soundtrack_file_path):
    sound_file_available = True
else:
    sound_file_available = False

template_list = None
hole_template_filename_r8 = os.path.join(script_dir, "Pattern.R8.jpg")
hole_template_filename_s8 = os.path.join(script_dir, "Pattern.S8.jpg")
hole_template_filename_custom = os.path.join(script_dir, "Pattern.custom.jpg")
hole_template_filename_corner = os.path.join(script_dir, "Pattern_Corner_TR.jpg")
hole_template_filename_bw = os.path.join(script_dir, "Pattern_BW.jpg")
hole_template_filename_wb = os.path.join(script_dir, "Pattern_WB.jpg")
hole_template_filename = hole_template_filename_s8
files_to_delete = []
EXPECTED_HASHES = {
    'Pattern.S8.jpg': 'dc4b94a14ef3d3dad3fe9d5708b4f2702bed44be2a3ed0aef63e8405301b3562', # new, smaller
    'Pattern.R8.jpg': 'ce7c81572bc0a03b079d655aab10ec16924c8d3b313087bd841cf68a6657fe9a',
    'Pattern_BW.jpg': '4a90371097219e5d5604c00bead6710b694e70b48fe66dbc5c2ce31ceedce4cf',
    'Pattern_WB.jpg': '60d50644f26407503267b763bcc48d7bec88dd6f58bb238cf9bec6ba86938f33',
    'Pattern_Corner_TR.jpg': '5e56a49c029013588646b11adbdc4a223217abfb91423dd3cdde26abbf5dcd9c'
}

default_project_config = {
    "SourceDir": "",
    "TargetDir": "",
    "VideoTargetDir": "",
    "FilmType": "S8",
    "PerformCropping": False,
    "PerformSharpness": False,
    "PerformDenoise": False,
    "GenerateVideo": False,
    "VideoFps": "18",
    "CurrentFrame": 0,
    "EncodeAllFrames": True,
    "FramesToEncode": "All",
    "StabilizationThreshold": 220.0,
    "PerformStabilization": False,
    "skip_frame_regeneration": False,
    "VideoFilename": "",
    "VideoTitle": "",
    "FillBorders": False,
    "FillBordersThickness": 5,
    "FillBordersMode": "smear",
    "FakeFillType": "none"
}

general_config = {
}

project_config = default_project_config.copy()


# Film hole search vars
HoleSearchTopLeft = (0, 0)
HoleSearchBottomRight = (0, 0)

# Film frames (in/out) file vars
TargetVideoFilename = ""
TargetVideoTitle = ""
SourceDir = ""
TargetDir = ""
file_type = 'jpg'
file_type_out = file_type
FrameInputFilenamePatternList_jpg = "picture-?????.jpg"
HdrInputFilenamePatternList_jpg = "picture-?????.3.jpg"   # In HDR mode, use 3rd frame as guide
LegacyHdrInputFilenamePatternList_jpg = "hdrpic-?????.3.jpg"   # In legacy HDR mode, use 3rd frame as guide
FrameInputFilenamePatternList_png = "picture-?????.png"
HdrInputFilenamePatternList_png = "picture-?????.3.png"   # In HDR mode, use 3rd frame as guide
LegacyHdrInputFilenamePatternList_png = "hdrpic-?????.3.png"   # In legacy HDR mode, use 3rd frame as guide
FrameInputFilenamePattern = "picture-%05d.%s"   # HDR frames using standard filename (2/12/2023)
FrameHdrInputFilenamePattern = "picture-%05d.%1d.%s"   # HDR frames using standard filename (2/12/2023)
FrameOutputFilenamePattern = "picture_out-%05d.%s"
TitleOutputFilenamePattern = "picture_out(title)-%05d.%s"
FrameOutputFilenamePattern_for_ffmpeg = "picture_out-%05d."
TitleOutputFilenamePattern_for_ffmpeg = "picture_out(title)-%05d."
FrameCheckOutputFilenamePattern = "picture_out-?????.%s"  # Req. for ffmpeg gen.
HdrSetInputFilenamePattern = "hdrpic-%05d.%1d.%s"   # Req. to fetch each HDR frame set
HdrFilesOnly = False   # No HDR by default. Updated when building file list from input folder
MergeMertens = None
AlignMtb = None

SourceDirFileList = []
TargetDirFileList = []
film_type = 'S8'
frame_fill_type = 'fake'

# Dimensions of frames in collection currently loaded: x, y (as it is needed often)
frame_width = 2028
frame_height = 1520

# Flow control vars
ConvertLoopExitRequested = False
ConvertLoopRunning = False
CorrectLoopRunning = False
BatchJobRunning = False
BatchAutostart = False

# preview dimensions (4/3 format) vars
BigSize = True
PreviewWidth = 700
PreviewHeight = 525
PreviewRatio = 1  # Defined globally for homogeneity, to be calculated once per project

# Crop area rectangle drawing vars
ref_point = []
rectangle_drawing = False  # true if mouse is pressed
ix, iy = -1, -1
x_, y_ = 0, 0
CropWindowTitle = "Select area to crop, press Enter to confirm, " \
                  "Escape to cancel"
CustomTemplateTitle = "Select area with film holes to use as template. " \
                       "Press Enter to confirm, Escape to cancel"
RectangleWindowTitle = ""
RotationAngle = 0.0
StabilizeAreaDefined = False
StabilizationThreshold = 220.0
StabilizationThreshold_default = StabilizationThreshold
enable_rectangle_popup = False
enable_soundtrack = False

hole_search_area_adjustment_pending = False
bad_frame_list = []     # List of tuples (5 elements each: Frame index, x offset, y offset, stabilization threshold, is frame saved)
# To migrate content of bad_frame_list to dictionaries (instead of smaller lists)
# bad_frame_list elements = Frame index, x offset, y offset, stabilization threshold, is frame saved)
bad_frame_info = {}
current_bad_frame_index = -1    # Current bad frame being displayed/edited
process_bad_frame_index = -1    # Bad frame index for re-generation
stop_bad_frame_save = False     # Flag to force stop the save bad frame loop
high_sensitive_bad_frame_detection = False
stabilization_bounds_alert = False
CropAreaDefined = False
RectangleTopLeft = (0, 0)
RectangleBottomRight = (0, 0)
# Rectangle of current cropping area
CropTopLeft = (0, 0)
CropBottomRight = (0, 0)
# Rectangle of current custom template
## TemplateTopLeft = (0, 0)
## TemplateBottomRight = (0, 0)
max_loop_count = 0
StabilizationShiftY = 0
StabilizationShiftX = 0
UserDefinedLeftStripeWidthProportion = 0.25
CalculatedLeftStripeWidth = 0

Force43 = False
Force169 = False

# Canvases + image ids to be used globally
draw_capture_canvas = None
template_canvas = None
left_stripe_canvas = None
left_stripe_stabilized_canvas = None


# Video generation vars
VideoFps = 18
FfmpegBinName = ""
FFmpeg_denoise_param='8:6:4:3'
ui_init_done = False
IgnoreConfig = False
global ffmpeg_installed
ffmpeg_state = Enum('ffmpeg_state', ['Pending', 'Running', 'Completed'])
resolution_dict = {
    "Unchanged": "",
    "-- 4:3 --": "",
    "160x120 (QQVGA)": "160:120",
    "320x240 (QVGA)": "320:240",
    "640x480 (VGA)": "640:480",
    "800x600 (SVGA)": "800:600",
    "1024x768 (XGA)": "1024:768",
    "1152x864 (XGA+)": "1152:864",
    "1280x960 (SXGA−)": "1280:960",
    "1400x1050 (SXGA+)": "1400:1050",
    "1600x1200 (UXGA)": "1600:1200",
    "1920x1440 (1080P)": "1920:1440",
    "2048x1536 (QXGA)": "2048:1536",
    "2880x2160 (3K UHD)": "2880:2160",
    "3072x2304 (3K)": "3072:2304",
    "3840x2880 (4K UHD)": "3840:2880",
    "4096x3072 (HXGA)": "4096:3072",
    "5120x3840 (5K)": "5120:3840",
    "6144x4608 (6K)": "6144:4608",
    "7680x5760 (8K UHD)": "7680:5760",
    "8192x6144 (8K)": "8192:6144",
    "-- 16:9 --": "",
    "432x243 (FWQVGA)": "432:243",
    "640x360 (nHD)": "640:360",
    "896x504 (FWVGA)": "896:504",
    "960x540 (qHD)": "960:540",
    "1024x576 (EDTV)": "1024:576",
    "1280x720 (HD Ready)": "1280:720",
    "1360x765 (WXGA)": "1360:765",
    "1600x900 (HD+)": "1600:900",
    "1920x1080 (FHD)": "1920:1080",
    "2048x1152 (2K)": "2048:1152",
    "2560x1440 (QHD)": "2560:1440",
    "3072x1728 (3K)": "3072:1728",
    "3200x1800 (QHD+)": "3200:1800",
    "3840x2160 (4K-UHD)": "3840:2160",
    "4096x2304 (DCI 4K)": "4096:2304",
    "5120x2880 (5K UHD+)": "5120:2880",
    "7680x4320 (8K-UHD)": "7680:4320",
    "8192x4608 (True 8K)": "8192:4608",
    "15360x8640 (16K UHD)": "15360:8640"
}
# Miscellaneous vars
win = None
as_tooltips = None
ExpertMode = True
IsWindows = False
IsLinux = False
IsMac = False

is_demo = False
ForceSmallSize = False
ForceBigSize = False
dev_debug_enabled = False
FrameSync_Viewer_opened = False
FrameSync_Images_Factor = 0.33

GenerateCsv = False
CsvFilename = ""
CsvPathName = ""
CsvFramesOffPercent = 0
match_level_average = None
horizontal_offset_average = None
move_x_average = None
move_y_average = None

SavedWithVersion = None # Used to retrieve version from config file (with wich version was this config last saved)

use_simple_stabilization = False    # Stabilize using simpler (and slightier less precise) algorithm, no templates required
precise_template_match = False

# Info required for usage counter
UserConsent = None
AnonymousUuid = None
LastConsentDate = None

# Token to be inserted in each queue on program closure, to allow threads to shut down cleanly
END_TOKEN = "TERMINATE_PROCESS"
LAST_ITEM_TOKEN = "LAST_ITEM"
last_displayed_image = 0
active_threads = 0
num_threads = 0


"""
#################
Classes
#################
"""
class Template:
    def __init__(self, name, filename, type, position):
        self.name = name
        self.filename = filename
        self.type = type
        if self.type == 'custom':
            self.scale = 1.0
        else:
            self.scale = frame_width/2028
        self.position = position
        self.scaled_position = (int(self.position[0] * self.scale),
                                int(self.position[1] * self.scale))
        self.size = (0,0)
        if os.path.isfile(filename):
            self.template = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
            self.scaled_template = resize_image(self.template, self.scale)
            # Calculate the white on black proportion to help with detection
            self.white_pixel_count = cv2.countNonZero(self.scaled_template)
            total_pixels = self.scaled_template.size
            self.wb_proportion = self.white_pixel_count / total_pixels
            self.size = (self.template.shape[1],self.template.shape[0])
            self.scaled_size = (int(self.size[0] * self.scale),
                                int(self.size[1] * self.scale))
            logging.debug(f"Init Template {self.type}, size: {self.size}, scaled size: {self.scaled_size}")
        else:
            self.template = None
            self.scaled_template = None
            self.wb_proportion = 0.5
            self.size = (0,0)
            self.scaled_size = (0,0)

    def refresh(self):
        if self.type == 'custom':
            self.scale = 1.0
        else:
            self.scale = frame_width/2028
        self.template = cv2.imread(self.filename, cv2.IMREAD_GRAYSCALE)
        self.scaled_template = resize_image(self.template, self.scale)
        self.white_pixel_count = cv2.countNonZero(self.scaled_template)
        total_pixels = self.scaled_template.size
        self.wb_proportion = self.white_pixel_count / total_pixels
        self.size = (self.template.shape[1], self.template.shape[0])
        self.scaled_size = (int(self.size[0] * self.scale),
                            int(self.size[1] * self.scale))
        self.scaled_position = (int(self.position[0] * self.scale),
                                int(self.position[1] * self.scale))
        logging.debug(f"Init Template {self.type}, size: {self.size}, scaled size: {self.scaled_size}")


class TemplateList:
    def __init__(self):
        self.templates = []
        self.active_template = None  # Initialize active_element to None

    def add(self, name, filename, type, position):
        exists = False
        for t in self.templates:
            if t.name == name and t.type == type:  # If already exist, update it
                self.active_template = t
                exists = True
                break
        if exists:
            t.filename = filename
            t.position = position
            t.refresh()
            target = t
        else:
            target = Template(name, filename, type, position)
            self.templates.append(target)
        self.active_template = target   # Set template just added as active
        return target

    def get_all(self):
        return self.templates

    def remove(self, template):
        if template in self.templates:
            self.templates.remove(template)
            if template == self.active_template:
                self.active_template = None  # Reset active_element if removed
            return True
        else:
            return False

    def set_active(self, type, name):
        for t in self.templates:
            if t.type == type and t.name == name:
                self.active_template = t
                return True
        return False

    def get_template(self, type, name):
        for t in self.templates:
            if t.type == type and t.name == name:
                return t.scaled_template
        return None

    def get_active(self):
        return self.active_template

    def get_active_template(self):
        return self.active_template.scaled_template

    def get_active_name(self):
        return self.active_template.name

    def get_active_position(self):
        return self.active_template.scaled_position

    def set_active_position(self, position):
        self.active_template.scaled_position = position
        self.active_template.position =  (int(t.scaled_position[0] / self.active_template.scale),
                                    int(t.scaled_position[1] / self.active_template.scale))
    def get_active_size(self):
        return self.active_template.scaled_size

    def set_active_size(self, size):
        self.active_template.scaled_size = size
        self.active_template.size = (int(size[0] / self.active_template.scale),
                                int(size[1] / self.active_template.scale))
    def get_scale(self):
        # Size reference 2028x1520
        return self.active_template.scale   # Scale is dynamic, as it depends on the set of images currently loaded

    def set_scale(self, new_width):
        # If new image size is different, Update all scaled templates and positions
        # Size reference 2028x1520
        new_scale = new_width/2028
        for t in self.templates:
            if t.type != 'custom' and new_scale != t.scale:
                t.scale = new_scale
                t.scaled_position = (int(t.position[0] * new_scale),
                                    int(t.position[1] * new_scale))
                t.scaled_template = resize_image(t.template, new_scale)
                t.scaled_size = (int(t.size[0] * new_scale),
                                int(t.size[1] * new_scale))

    def get_active_filename(self):
        return self.active_template.filename

    def get_active_type(self):
        return self.active_template.type

    def get_active_white_pixel_count(self):
        return self.active_template.white_pixel_count

    def get_active_wb_proportion(self):
        return self.active_template.wb_proportion

    def set_active_wb_proportion(self, proportion):
        self.active_template.wb_proportion = proportion



"""
#################
Utility functions
#################
"""


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


"""
####################################
Configuration file support functions
####################################
"""


def set_project_defaults():
    global project_config
    global perform_cropping, generate_video, resolution_dropdown_selected
    global frame_slider, encode_all_frames, frames_to_encode_str
    global perform_stabilization, skip_frame_regeneration, ffmpeg_preset
    global video_filename_str, video_title_str
    global frame_from_str, frame_to_str
    global frame_fill_type, extended_stabilization, low_contrast_custom_template
    global perform_denoise, perform_sharpness

    project_config["PerformCropping"] = False
    perform_cropping.set(project_config["PerformCropping"])
    project_config["PerformDenoise"] = False
    perform_denoise.set(project_config["PerformDenoise"])
    project_config["PerformSharpness"] = False
    perform_sharpness.set(project_config["PerformSharpness"])
    project_config["PerformGammaCorrection"] = False
    perform_gamma_correction.set(project_config["PerformGammaCorrection"])
    project_config["FrameFillType"] = 'none'
    frame_fill_type.set(project_config["FrameFillType"])
    project_config["GenerateVideo"] = False
    generate_video.set(project_config["GenerateVideo"])
    project_config["CurrentFrame"] = 0
    frame_slider.set(project_config["CurrentFrame"])
    project_config["EncodeAllFrames"] = True
    encode_all_frames.set(project_config["EncodeAllFrames"])
    project_config["FrameFrom"] = 0
    frame_from_str.set(str(project_config["FrameFrom"]))
    project_config["FrameTo"] = 0
    frame_to_str.set(str(project_config["FrameTo"]))
    project_config["PerformStabilization"] = False
    perform_stabilization.set(project_config["PerformStabilization"])
    project_config["LowContrastCustomTemplate"] = False
    low_contrast_custom_template.set(project_config["LowContrastCustomTemplate"])
    project_config["ExtendedStabilization"] = False
    extended_stabilization.set(project_config["ExtendedStabilization"])
    project_config["skip_frame_regeneration"] = False
    skip_frame_regeneration.set(project_config["skip_frame_regeneration"])
    project_config["VideoFilename"] = ""
    video_filename_str.set(project_config["VideoFilename"])
    project_config["VideoTitle"] = ""
    video_title_str.set(project_config["VideoTitle"])
    project_config["FillBorders"] = False
    project_config["StabilizationShiftY"] = 0
    project_config["StabilizationShiftX"] = 0


def sort_nested_json(data):
    """Sorts keys in nested dictionaries."""
    if isinstance(data, dict):
        return {k: sort_nested_json(data[k]) for k in sorted(data)}
    elif isinstance(data, list):
        return [sort_nested_json(item) for item in data]
    else:
        return data


def save_general_config():
    # Write config data upon exit
    general_config["GeneralConfigDate"] = str(datetime.now())
    general_config["WindowPos"] = win.geometry()
    general_config["Version"] = __version__

    try:
        if template_popup_window.winfo_exists():
            general_config["TemplatePopupWindowPos"] = template_popup_window.geometry()
    except Exception as e:
        logging.debug(f"Error (expected) while trying to save template popup window geometry: {e}")
    if not IgnoreConfig:
        """Saves sorted nested JSON data to a file."""
        sorted_data = sort_nested_json(general_config)
        with open(general_config_filename, 'w') as f:
            json.dump(sorted_data, f, indent=4)


def load_general_config():
    global general_config
    global general_config_filename

    # Check if persisted data file exist: If it does, load it
    if not IgnoreConfig and os.path.isfile(general_config_filename):
        persisted_data_file = open(general_config_filename)
        general_config = json.load(persisted_data_file)
        persisted_data_file.close()
    else:   # No project config file. Set empty config to force defaults
        general_config = {}

    logging.debug("Reading general config")
    for item in general_config:
        logging.debug("%s=%s", item, str(general_config[item]))


def decode_general_config():
    global SourceDir
    global project_name
    global FfmpegBinName, FFmpeg_denoise_param, enable_rectangle_popup, enable_soundtrack
    global general_config
    global UserConsent, AnonymousUuid, LastConsentDate
    global SavedWithVersion, JobListFilename
    global precise_template_match, high_sensitive_bad_frame_detection
    global UserDefinedLeftStripeWidthProportion
    if 'SourceDir' in general_config:
        SourceDir = general_config["SourceDir"]
        # If directory in configuration does not exist, set current working dir
        if not os.path.isdir(SourceDir):
            SourceDir = ""
            project_name = "No Project"
        else:
            # Create a project id (folder name) for the stats logging below
            # Replace any commas by semi colon to avoid problems when generating csv by AfterScanAnalysis
            project_name = os.path.split(SourceDir)[-1].replace(',', ';')

    if 'FfmpegBinName' in general_config:
        FfmpegBinName = general_config["FfmpegBinName"]

    if 'UserConsent' in general_config:
        UserConsent = general_config["UserConsent"]
    if 'AnonymousUuid' in general_config:
        AnonymousUuid = general_config["AnonymousUuid"]
    if 'LastConsentDate' in general_config:
        LastConsentDate = datetime.fromisoformat(general_config["LastConsentDate"])
    if 'Version' in general_config:
        SavedWithVersion = general_config["Version"]
    if 'JobListFilename' in general_config:
        JobListFilename = general_config["JobListFilename"]
    if 'FFmpegHqdn3d' in general_config:
        FFmpeg_denoise_param = general_config["FFmpegHqdn3d"]
    if 'EnablePopups' in general_config:
        enable_rectangle_popup = general_config["EnablePopups"]
    if 'EnableSoundtrack' in general_config and sound_file_available:
        enable_soundtrack = general_config["EnableSoundtrack"]
    if 'PreciseTemplateMatch' in general_config:
        precise_template_match = general_config["PreciseTemplateMatch"]
    if 'HighSensitiveBadFrameDetection' in general_config:
        high_sensitive_bad_frame_detection = general_config["HighSensitiveBadFrameDetection"]



def update_project_settings():
    global project_settings
    global SourceDir
    # SourceDir is the key for each project config inside the global project settings
    if SourceDir in project_settings:
        project_settings.update({SourceDir: project_config.copy()})
    elif SourceDir != '':
        project_settings.update({SourceDir: project_config.copy()})
        # project_settings[project_config["SourceDir"]] = project_config.copy()

def save_project_settings():
    global project_settings, project_settings_filename, project_settings_backup_filename

    if not IgnoreConfig:
        # Delete existing backup file
        if os.path.isfile(project_settings_backup_filename):
            os.remove(project_settings_backup_filename)
        # Rename current project file as backup
        if os.path.isfile(project_settings_filename):
            os.rename(project_settings_filename, project_settings_backup_filename)
            logging.debug("Saving project settings:")
        # Create list with global version info
        global_info = {'data_version': __data_version__, 'code_version': __version__, 'save_date': str(datetime.now())}
        list_to_save = [global_info, project_settings]
        with open(project_settings_filename, 'w+') as f:
            json.dump(list_to_save, f, indent=4)


def load_project_settings():
    global project_settings, project_settings_filename, default_project_config
    global SourceDir, files_to_delete
    global project_name

    projects_loaded = False
    error_while_loading = False

    if not IgnoreConfig and os.path.isfile(project_settings_filename):
        f = open(project_settings_filename)
        try:
            saved_list = json.load(f)
        except Exception as e:
            logging.debug(f"Error while opening projects json file; {e}")
            error_while_loading = True
        f.close()
        if not error_while_loading:
            # Check if project if legacy, since we will not handle it
            if isinstance(saved_list, dict):   # Old version of json files were directly a dictionary
                tk.messagebox.showerror(
                    "Invalid project file",
                    f"The project file {project_settings_filename} saved in disk is invalid."
                    "Project defaults will be loaded and existing file will be overwritten upon exit "
                    "(and a backup file generated in case you want to recover information from it)")
            else:
                # New version is a list
                logging.info(f"Loading project file: {saved_list[0]['data_version']},  {saved_list[0]['code_version']},  {saved_list[0]['save_date']}")
                project_settings = saved_list[1]
                projects_loaded = True
                # Perform some cleanup, in case projects have been deleted
                project_folders = list(project_settings.keys())  # freeze keys iterator into a list
                for folder in project_folders:
                    if not os.path.isdir(folder):   # If project folder no longer exists...
                        if "CustomTemplateFilename" in project_settings[folder]:
                            aux_template_filename = os.path.join(SourceDir, project_settings[folder]["CustomTemplateFilename"])
                            if os.path.isfile(aux_template_filename):
                                os.remove(aux_template_filename)    # ...delete custom template, if it exists
                        project_settings.pop(folder)
                        logging.debug("Deleting %s from project settings, as it no longer exists", folder)
                    elif not os.path.isdir(SourceDir) and os.path.isdir(folder):
                        SourceDir = folder
                        # Create a project id (folder name) for the stats logging below
                        # Replace any commas by semi colon to avoid problems when generating csv by AfterScanAnalysis
                        project_name = os.path.split(SourceDir)[-1].replace(',', ';')

    if not projects_loaded:   # No project settings file. Set empty config to force defaults
        project_settings = {SourceDir: default_project_config.copy()}
        project_settings[SourceDir]["SourceDir"] = SourceDir


def save_project_config():
    global template_list
    global skip_frame_regeneration
    global ffmpeg_preset
    global StabilizeAreaDefined
    global CurrentFrame
    global video_filename_str, video_title_str
    global frame_from_str, frame_to_str
    global perform_denoise, perform_sharpness, perform_gamma_correction

    # Write project data upon exit
    project_config["SourceDir"] = SourceDir
    project_config["TargetDir"] = TargetDir
    project_config["CurrentFrame"] = CurrentFrame
    project_config["skip_frame_regeneration"] = skip_frame_regeneration.get()
    project_config["FFmpegPreset"] = ffmpeg_preset.get()
    project_config["ProjectConfigDate"] = str(datetime.now())
    project_config["PerformCropping"] = perform_cropping.get()
    project_config["PerformDenoise"] = perform_denoise.get()
    project_config["PerformSharpness"] = perform_sharpness.get()
    project_config["PerformGammaCorrection"] = perform_gamma_correction.get()
    project_config["GammaCorrectionValue"] = float(gamma_correction_str.get())
    project_config["FrameFillType"] = frame_fill_type.get()
    project_config["ExtendedStabilization"] = extended_stabilization.get()
    project_config["LowContrastCustomTemplate"] = low_contrast_custom_template.get()
    project_config["VideoTitle"] = video_title_str.get()
    project_config["VideoFilename"] = video_filename_str.get()
    project_config["FrameFrom"] = int(frame_from_str.get())
    project_config["FrameTo"] = int(frame_to_str.get())
    # Next item: widget variable is inside popup, might not be available, so use global variable
    project_config["CurrentBadFrameIndex"] = current_bad_frame_index
    if StabilizeAreaDefined:
        project_config["PerformStabilization"] = perform_stabilization.get()
        project_config["StabilizationShiftY"] = stabilization_shift_y_value.get()
        project_config["StabilizationShiftX"] = stabilization_shift_x_value.get()
        if not encode_all_frames.get():
            project_config["HolePos"] = template_list.get_active_position()
            project_config["HoleScale"] = template_list.get_active_scale()

    # remove deprecated items from config
    if "CustomHolePos" in project_config:
        del project_config["CustomHolePos"]

    if len(bad_frame_list) > 0:
        save_bad_frame_list()   # Bad frames need to be saved even in batch mode

    # Do not save if current project comes from batch job
    if not project_config_from_file or IgnoreConfig:
        return

    # No longer saving to dedicated file, all project settings in common file now
    # with open(project_config_filename, 'w+') as f:
    #     json.dump(project_config, f)

    update_project_settings()
    save_project_settings()

def load_project_config():
    global SourceDir
    global project_config, project_config_from_file
    global project_config_basename, project_config_filename
    global project_settings
    global default_project_config

    if not IgnoreConfig:
        project_config_filename = os.path.join(SourceDir, project_config_basename)
    # Check if persisted project data file exist: If it does, load it
    project_config = default_project_config.copy()  # set default config

    if SourceDir in project_settings:
        logging.debug("Loading project config from consolidated project settings")
        project_config |= project_settings[SourceDir].copy()
    elif os.path.isfile(project_config_filename):
        logging.debug("Loading project config from dedicated project config file")
        persisted_data_file = open(project_config_filename)
        project_config |= json.load(persisted_data_file)
        persisted_data_file.close()
    else:  # No project config file. Set empty config to force defaults
        logging.debug("No project config exists, initializing defaults")
        project_config = default_project_config.copy()
        project_config['SourceDir'] = SourceDir

    for item in project_config:
        logging.debug("%s=%s", item, str(project_config[item]))


    # Allow to determine source of current project, to avoid
    # saving it in case of batch processing
    project_config_from_file = True
    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)

def decode_project_config():        
    global SourceDir, TargetDir
    global project_config
    global template_list
    global project_config_basename, project_config_filename
    global CurrentFrame, frame_slider
    global VideoFps, video_fps_dropdown_selected
    global resolution_dropdown, resolution_dropdown_selected
    global encode_all_frames, frames_to_encode
    global skip_frame_regeneration
    global generate_video, video_filename_name
    global CropTopLeft, CropBottomRight, perform_cropping
    global StabilizeAreaDefined, film_type
    global StabilizationThreshold, low_contrast_custom_template
    global RotationAngle
    global frame_from_str, frame_to_str
    global project_name
    global force_4_3_crop, force_16_9_crop
    global frame_fill_type
    global extended_stabilization
    global Force43, Force169
    global perform_denoise, perform_sharpness, perform_gamma_correction, gamma_correction_str
    global high_sensitive_bad_frame_detection, current_bad_frame_index
    global precise_template_match
    global StabilizationShiftX, StabilizationShiftY
    global UserDefinedLeftStripeWidthProportion

    if 'SourceDir' in project_config:
        SourceDir = project_config["SourceDir"]
        project_name = os.path.split(SourceDir)[-1].replace(',', ';')
        # If directory in configuration does not exist, set current working dir
        if not os.path.isdir(SourceDir):
            SourceDir = ""
            project_name = "No Project"
        else:
            get_source_dir_file_list()
        frames_source_dir.delete(0, 'end')
        frames_source_dir.insert('end', SourceDir)
        frames_source_dir.after(100, frames_source_dir.xview_moveto, 1)
        # Need to retrieve source file list at this point, since win.update at the end of thi sfunction will force a refresh of the preview
        # If we don't do it here, an oimage from the previou ssource folder will be displayed instead
    if 'TargetDir' in project_config:
        TargetDir = project_config["TargetDir"]
        # If directory in configuration does not exist, set current working dir
        if not os.path.isdir(TargetDir):
            TargetDir = ""
        else:
            get_target_dir_file_list()
        frames_target_dir.delete(0, 'end')
        frames_target_dir.insert('end', TargetDir)
        frames_target_dir.after(100, frames_target_dir.xview_moveto, 1)
    if 'VideoTargetDir' in project_config:
        video_target_dir_str.set(project_config["VideoTargetDir"])
        # If directory in configuration does not exist, set current working dir
        if not os.path.isdir(video_target_dir_str.get()):
            video_target_dir_str.set(TargetDir)  # use frames target dir as fallback option
        video_target_dir.after(100, video_target_dir.xview_moveto, 1)
    if 'CurrentFrame' in project_config and not BatchJobRunning: # only if project loaded by user, otherwise it alters start encoding frame in batch mode
        CurrentFrame = project_config["CurrentFrame"]
        CurrentFrame = max(CurrentFrame, 0)
    else:
        CurrentFrame = 0
    if 'EncodeAllFrames' in project_config:
        encode_all_frames.set(project_config["EncodeAllFrames"])
    else:
        encode_all_frames.set(True)
    if 'FrameFrom' in project_config:
        frame_from_str.set(str(project_config["FrameFrom"]))
    else:
        frame_from_str.set('0')
    if 'FrameTo' in project_config:
        frame_to_str.set(str(project_config["FrameTo"]))
    else:
        frame_to_str.set('0')
    if frame_to_str.get() != '' and frame_from_str.get() != '':
        frames_to_encode = int(frame_to_str.get()) - int(frame_from_str.get()) + 1
    else:
        frames_to_encode = 0

    if not 'FilmType' in project_config:
        project_config["FilmType"] = 'S8'
    film_type.set(project_config["FilmType"])

    if 'RotationAngle' in project_config:
        RotationAngle = project_config["RotationAngle"]
        rotation_angle_str.set(RotationAngle)
    else:
        RotationAngle = 0
        rotation_angle_str.set(RotationAngle)
    if ExpertMode:
        if 'StabilizationThreshold' in project_config:
            StabilizationThreshold = float(project_config["StabilizationThreshold"])
            stabilization_threshold_str.set(StabilizationThreshold)
        else:
            StabilizationThreshold = 220.0
            stabilization_threshold_str.set(StabilizationThreshold)
    else:
        StabilizationThreshold = 220.0

    if 'LowContrastCustomTemplate' in project_config:
        low_contrast_custom_template.set(project_config["LowContrastCustomTemplate"])

    if 'ExtendedStabilization' in project_config:
        extended_stabilization.set(project_config["ExtendedStabilization"])

    if 'CustomTemplateDefined' in project_config and project_config["CustomTemplateDefined"]:
        if 'CustomTemplateName' in project_config:  # Load name if it exists, otherwise assign default
            template_name = project_config["CustomTemplateName"]
        else:
            template_name = f"{os.path.split(SourceDir)[-1]}"
        if 'CustomTemplateExpectedPos' in project_config:
            expected_hole_template_pos_custom = project_config["CustomTemplateExpectedPos"]
        else:
            expected_hole_template_pos_custom = (0, 0)
        if 'CustomTemplateFilename' in project_config:
            full_path_template_filename = project_config["CustomTemplateFilename"]
        else:
            template_filename = f"Pattern.custom.{template_name}.jpg"
            full_path_template_filename = os.path.join(resources_dir, template_filename)
        if not os.path.exists(full_path_template_filename):
            tk.messagebox.showwarning(
                "Template in project invalid",
                f"The custom template saved for project {template_name} is invalid."
                "Please redefine custom template for this project.")
            del project_config['CustomTemplateFilename']
            # Invalid custom template defined, set default one
            set_film_type()
            project_config["CustomTemplateDefined"] = False
        else:
            logging.debug(f"Adding custom template {template_name} from configuration to template list (filename {full_path_template_filename})")
            template_list.add(template_name, full_path_template_filename, "custom", expected_hole_template_pos_custom)
            debug_template_refresh_template()
    else:
        # No custom template defined, set default one
        set_film_type()

    if 'PerformCropping' in project_config:
        perform_cropping.set(project_config["PerformCropping"])
    else:
        perform_cropping.set(False)
    if 'PerformDenoise' in project_config:
        perform_denoise.set(project_config["PerformDenoise"])
    else:
        perform_denoise.set(False)
    if 'PerformSharpness' in project_config:
        perform_sharpness.set(project_config["PerformSharpness"])
    else:
        perform_sharpness.set(False)
    if 'PerformGammaCorrection' in project_config:
        perform_gamma_correction.set(project_config["PerformGammaCorrection"])
    else:
        perform_gamma_correction.set(False)
    if 'GammaCorrectionValue' in project_config:
        gamma_correction_str.set(project_config["GammaCorrectionValue"])
    else:
        gamma_correction_str.set("2.2")
    if 'CropRectangle' in project_config:
        CropBottomRight = tuple(project_config["CropRectangle"][1])
        CropTopLeft = tuple(project_config["CropRectangle"][0])
    else:
        CropBottomRight = (0, 0)
        CropTopLeft = (0, 0)
        perform_cropping.set(False)
        project_config["PerformCropping"] = False
    perform_cropping_selection()
    if 'Force_4/3' in project_config:
        force_4_3_crop.set(project_config["Force_4/3"])
    else:
        force_4_3_crop.set(False)
    if 'Force_16/9' in project_config:
        force_16_9_crop.set(project_config["Force_16/9"])
    else:
        force_16_9_crop.set(False)
    if force_4_3_crop.get():    # 4:3 has priority if both set
        force_16_9_crop.set(False)
    Force43 = force_4_3_crop.get()
    Force169 = force_16_9_crop.get()
    if 'FrameFillType' in project_config:
        frame_fill_type.set(project_config["FrameFillType"])
    else:
        project_config["FrameFillType"] = 'fake'
        frame_fill_type.set(project_config["FrameFillType"])

    if 'GenerateVideo' in project_config:
        generate_video.set(project_config["GenerateVideo"])
    else:
        generate_video.set(False)
    generate_video_selection()
    if 'VideoFilename' in project_config:
        video_filename_str.set(project_config["VideoFilename"])
    if 'VideoTitle' in project_config:
        video_title_str.set(project_config["VideoTitle"])
    if 'skip_frame_regeneration' in project_config:
        skip_frame_regeneration.set(project_config["skip_frame_regeneration"])
    else:
        skip_frame_regeneration.set(False)
    if 'FFmpegPreset' in project_config:
        ffmpeg_preset.set(project_config["FFmpegPreset"])
    else:
        ffmpeg_preset.set("veryfast")

    if 'PerformStabilization' in project_config:
        perform_stabilization.set(project_config["PerformStabilization"])
    else:
        perform_stabilization.set(False)

    if 'StabilizationShiftY' in project_config:
        stabilization_shift_y_value.set(project_config["StabilizationShiftY"])
        StabilizationShiftY = stabilization_shift_y_value.get()
    else:
        stabilization_shift_y_value.set(0)

    if 'StabilizationShiftX' in project_config:
        stabilization_shift_x_value.set(project_config["StabilizationShiftX"])
        StabilizationShiftX = stabilization_shift_x_value.get()
    else:
        stabilization_shift_x_value.set(0)

    if 'PerformRotation' in project_config:
        perform_rotation.set(project_config["PerformRotation"])
    else:
        perform_rotation.set(False)

    if 'VideoFps' in project_config:
        VideoFps = eval(project_config["VideoFps"])
        video_fps_dropdown_selected.set(VideoFps)
    else:
        VideoFps = 18
        video_fps_dropdown_selected.set(VideoFps)
    set_fps(str(VideoFps))
    if 'VideoResolution' in project_config:
        resolution_dropdown_selected.set(project_config["VideoResolution"])
    else:
        resolution_dropdown_selected.set('1920x1440 (1080P)')
        project_config["VideoResolution"] = '1920x1440 (1080P)'

    if 'CurrentBadFrameIndex' in project_config:
        current_bad_frame_index = project_config["CurrentBadFrameIndex"]

    if 'UserDefinedLeftStripeWidthProportion' in project_config:
        UserDefinedLeftStripeWidthProportion = project_config["UserDefinedLeftStripeWidthProportion"]
    else:
        UserDefinedLeftStripeWidthProportion = 0.25

    adjust_dimensions_based_on_frame()

    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)

    load_bad_frame_list()

    win.update()


"""
##########################
Job list support functions
##########################
"""

JOB_LIST_NAME_LENGTH = 100
JOB_LIST_DESCRIPTION_LENGTH = 100

def job_list_process_selection(evt):
    global job_list
    global job_list_treeview
    global rerun_job_btn
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return

    # Note here that Tkinter passes an event object to onselect()
    # w = evt.widget - We already know the widget

    if len(job_list_treeview.get_children()) == 0:
        return

    selected_index = job_list_treeview.selection()
    if selected_index:
        item_id = selected_index[0]
        items = job_list_treeview.get_children()
        index = items.index(item_id)  # Get current position
        Name = job_list_treeview.item(item_id, "text")  # Returns a tuple of all column values
        if Name:
            entry = normalize_job_name(Name)  # Get the first element
            rerun_job_btn.config(text='Rerun job' if job_list[entry]['done'] else rerun_job_btn.config(text='Mark as run'))



def job_list_add_current():
    global job_list, template_list
    global CurrentFrame, StartFrame, frames_to_encode
    global project_config, video_filename_str
    global job_list_treeview
    global encode_all_frames, SourceDirFileList
    global frame_from_str, frame_to_str
    global resolution_dropdown_selected
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return
    entry_name = video_filename_str.get()
    if entry_name == "":
        tk.messagebox.showerror("Cannot add new job", "Please fill 'Video filename' field, as it is used to identify the job.")
        return

    if project_config["FilmType"] == 'R8':
        description = "R8, "
    else:
        description = "S8, "
    description = description + "Frames "
    if encode_all_frames.get():
        description = description + "0"
        frames_to_encode = len(SourceDirFileList)
    else:
        description = description + frame_from_str.get()
        frames_to_encode = int(frame_to_str.get()) - int(frame_from_str.get()) + 1
    description = description + "-"
    if encode_all_frames.get():
        description = description + str(len(SourceDirFileList))
    else:
        description = description + frame_to_str.get()
    description = description + " ("
    description = description + str(frames_to_encode)
    description = description + " frames)"
    if perform_rotation.get():
        description = description + ", rotate"
    if perform_stabilization.get():
        description = description + ", stabilize"
    if perform_cropping.get():
        description = description + ", crop"
    if perform_denoise.get():
        description = description + ", denoise"
    if perform_sharpness.get():
        description = description + ", sharpen"
    if perform_gamma_correction.get():
        description = description + f", GC:{gamma_correction_str.get()}"
    description = description + f", fill: {frame_fill_type.get()}"
    if project_config["GenerateVideo"]:
        description = description + ", "
        if ffmpeg_preset.get() == 'veryslow':
            description = description + "HQ video"
        elif ffmpeg_preset.get() == 'veryfast':
            description = description + "Low Q. video"
        else:
            description = description + "medium Q. video"
        if skip_frame_regeneration.get():
            description = description + ", skip FG"
        description = description + f", {VideoFps} FPS"
        if resolution_dropdown_selected.get():
            description = description + ", " + resolution_dropdown_selected.get()
    else:
        description = description + ", no video"

    save_project = True
    item_id = None
    if entry_name in job_list:
        if tk.messagebox.askyesno(
                "Job already exists",
                "A job named " + entry_name + " exists already in the job list. "
                "Do you want to overwrite it?."):
            item_id = search_job_name_in_job_treeview(entry_name)
        else:
            save_project = False
    if save_project:
        save_project_config()  # Make sure all current settings are in project_config
        job_list[entry_name] = {'project': project_config.copy(), 'done': False, 'attempted': False, 'description': description}
        # If a custom pattern is used, copy it with the name of the job, and change it in the joblist/project item
        if template_list.get_active_type() == 'custom' and os.path.isfile(template_list.get_active_filename()):
            CustomTemplateDir = os.path.dirname(template_list.get_active_filename())    # should be resources_dir, but better be safe
            # Maybe we should check here if a video filename has been defined
            TargetTemplateFile = os.path.join(CustomTemplateDir, os.path.splitext(job_list[entry_name]['project']['VideoFilename'])[0]+'.jpg' )
            if template_list.get_active_filename() != TargetTemplateFile:
                shutil.copyfile(template_list.get_active_filename(), TargetTemplateFile)
            job_list[entry_name]['project']['CustomTemplateFilename'] = TargetTemplateFile
        else:
            if 'CustomTemplateFilename' in project_config:
                del project_config['CustomTemplateFilename']
        if item_id is None:
            item_id = job_list_treeview.insert('', 'end', text=entry_name, values=(description,), 
                                               tags=("pending","joblist_font",))
        else:   # Update existing
            job_list_treeview.item(item_id, text=entry_name, values=(description,), 
                                   tags=("pending","joblist_font",) if job_list[entry_name]['done'] == False else ("done","joblist_font",))

        job_list_treeview.selection_set(item_id)  # Select the row
        job_list_treeview.see(item_id)


# gets currently selected job list item and loads it in the UI fields (to allow editing)
def job_list_load_selected():
    global job_list
    global CurrentFrame, StartFrame, frames_to_encode
    global project_config
    global job_list_treeview
    global encode_all_frames, SourceDirFileList
    global frame_from_str, frame_to_str
    global resolution_dropdown_selected
    global job_list_listbox_disabled
    global current_bad_frame_index

    if job_list_listbox_disabled:
        return

    selected_index = job_list_treeview.selection()
    if selected_index:
        item_id = selected_index[0]
        items = job_list_treeview.get_children()
        index = items.index(item_id)  # Get current position
        Name = job_list_treeview.item(item_id, "text")  # Get Name (Colmun #0)
        if Name:
            entry_name = normalize_job_name(Name)  # Get the first element
            if entry_name in job_list:
                # Save misaligned frame list in case new job switches to a different source folder
                if len(bad_frame_list) > 0:
                    save_bad_frame_list()
                # Clear list of bad frames
                bad_frame_list.clear()
                current_bad_frame_index = -1
                # Copy job settings as current project settings
                project_config = job_list[entry_name]['project']
                decode_project_config()

                general_config["SourceDir"] = SourceDir

                if encode_all_frames:
                    CurrentFrame = first_absolute_frame + (last_absolute_frame - first_absolute_frame) // 2
                else:
                    # Set CurrentFrame in the middle of the project frame range
                    CurrentFrame = project_config["FrameFrom"] + (project_config["FrameTo"] - project_config["FrameFrom"]) // 2

                # Enable Start and Crop buttons, plus slider, once we have files to handle
                cropping_btn.config(state=NORMAL)
                frame_slider.config(state=NORMAL)
                Go_btn.config(state=NORMAL)
                frame_slider.set(CurrentFrame)
                init_display()


def job_list_delete_selected():
    global job_list
    global job_list_treeview
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return

    selected_index = job_list_treeview.selection()
    if selected_index:
        item_id = selected_index[0]
        Name = job_list_treeview.item(item_id, "text")  # Get Name (Col. #0)
        if Name:
            # Get index of the selected line
            items = job_list_treeview.get_children()
            index = items.index(item_id) if item_id in items else -1
            entry = normalize_job_name(Name)  # Get the first element
            job_list.pop(entry) # Delete from job list
            job_list_treeview.delete(item_id)    # Delete from tree view
            # Try to select the previous row if it exists
            if index > 0:
                job_list_treeview.selection_set(items[index - 1])  # Select previous row
            elif index == 0 and len(items) > 1:
                job_list_treeview.selection_set(items[1])  # Select the new first row if available


def job_list_rerun_selected():
    global job_list
    global job_list_treeview
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return

    selected_index = job_list_treeview.selection()
    if selected_index:
        item_id = selected_index[0]
        Name = job_list_treeview.item(item_id, "text")  # Get Name (Col. #0)
        if Name:
            entry = normalize_job_name(Name)  # Get the first element
            job_list[entry]['done'] = not job_list[entry]['done']
            job_list[entry]['attempted'] = job_list[entry]['done']
            job_list_treeview.item(item_id, tags=("done","joblist_font",) if job_list[entry]['done'] else ("pending","joblist_font",))
            rerun_job_btn.config(text='Rerun job' if job_list[entry]['done'] else 'Mark as run')


def create_alternate_job_name(name):
    index = 2
    done = False
    new_name = name[:JOB_LIST_NAME_LENGTH]
    while not done:
        if new_name in job_list:
            name_len = len(name)
            name_appendix = f"({index})"
            appendix_req_len = len(name_appendix)
            len_to_cut = name_len + appendix_req_len - JOB_LIST_NAME_LENGTH
            if len_to_cut > 0:
                new_name = name[:len(name)-len_to_cut]
            new_name = new_name + name_appendix
            index += 1
        else:
            done = True

    return new_name


def normalize_job_name(name):
    return name[:JOB_LIST_NAME_LENGTH].strip()


def search_job_name_in_job_treeview(job_name):
    """
    Find the index of the first element in a tuple that starts with search_str.
    Returns -1 if no match is found.
    """
    for item_id in job_list_treeview.get_children():  # Iterate over all items
        name = job_list_treeview.item(item_id, "text")  # Retrieve Name (column #0)
        if name == job_name:  # Check first column
            return item_id
    return -1


def generate_dict_hash(dictionary):
    """Generates a SHA-256 hash from a dictionary."""
    serialized_dict = json.dumps(dictionary, sort_keys=True).encode('utf-8')
    hash_object = hashlib.sha256(serialized_dict)
    return hash_object.hexdigest()


def save_named_job_list():
    global job_list, job_list_hash, JobListFilename
    start_dir = os.path.split(JobListFilename)[0]  
    aux_file = filedialog.asksaveasfilename(
        initialdir=start_dir,
        defaultextension=".json",
        initialfile=JobListFilename,
        filetypes=[("Joblist JSON files", "*.joblist.json"), ("JSON files", "*.json")],
        title="Select file to save job list")
    if len(aux_file) > 0:
        job_list_hash = generate_dict_hash(job_list)
        # Remove only the exact suffix if present
        if not aux_file.endswith(".joblist.json"):
            # Remove .json or .joblist if they exist separately
            aux_file = aux_file.removesuffix(".json").removesuffix(".joblist")
            # Append the correct suffix
            aux_file = f"{aux_file}.joblist.json"
        with open(aux_file, 'w+') as f:
            json.dump(job_list, f, indent=4)
        JobListFilename = aux_file
        general_config["JobListFilename"] = JobListFilename
        display_window_title()


def load_named_job_list():
    global job_list, JobListFilename, job_list_hash

    aux_hash = generate_dict_hash(job_list)
    if job_list_hash != aux_hash:   # Current job list modified since loaded
        if tk.messagebox.askyesno(
            "Save job list?",
            "Current lob list contains unsaved changes.\r\n"
            "Do you want to save them before loading the new job list?\r\n"):
            save_named_job_list()
    start_dir = os.path.split(JobListFilename)[0]  
    aux_file = filedialog.askopenfilename(
        initialdir=start_dir,
        defaultextension=".json",
        filetypes=[("Joblist JSON files", "*.joblist.json"), ("JSON files", "*.json")],
        title="Select file to retrieve job list")
    if len(aux_file) > 0:
        load_job_list(aux_file)
        JobListFilename = aux_file
        general_config["JobListFilename"] = JobListFilename
        job_list_hash = generate_dict_hash(job_list)
        display_window_title()


def save_job_list():
    global job_list, default_job_list_filename

    if not IgnoreConfig:
        with open(default_job_list_filename, 'w+') as f:
            json.dump(job_list, f, indent=4)


def load_job_list(filename = None):
    global job_list, default_job_list_filename, job_list_treeview, job_list_hash

    if filename is None:
        if not os.path.isfile(default_job_list_filename):   
            # if default job list file does not exist, try with legacy one (before 1.20.13)
            filename = default_job_list_filename_legacy
        else:
            filename = default_job_list_filename

    display_window_title()  # setting title of the window

    if not IgnoreConfig and os.path.isfile(filename):
        f = open(filename)
        job_list = json.load(f)
        # Explicitly copy keys
        keys = list(job_list.keys())
        for item_id in job_list_treeview.get_children():
            job_list_treeview.delete(item_id)
        for entry in keys:
            # Check if 'description' field exists
            if "description" not in job_list[entry]:  # Legacy entry, need to adapt
                # Split legacy entry name (long) in two
                parts = entry.split(",", 1)
                new_entry_name = parts[0].strip()  # First part, always exists
                new_entry_name = os.path.splitext(new_entry_name)[0][:JOB_LIST_NAME_LENGTH] # Remove extension if any, limit to 25
                description = parts[1].strip()[:JOB_LIST_DESCRIPTION_LENGTH] if len(parts) > 1 else ""  # Second part or empty string
                # Step 0: check is new entry key already exists
                if new_entry_name in job_list:
                    new_entry_name = create_alternate_job_name(new_entry_name)
                logging.error(f"Detected legacy job list, replacing '{entry}' by '{new_entry_name}'")
                # Step 1: Update entry with new key name
                new_key = entry.replace(entry, new_entry_name)
                job_list[new_key] = job_list.pop(entry)
                # Step 2: Add new field
                job_list[new_key]["description"] = description
                # Update variable with new name for later use
                entry = new_key
            elif len(entry) > JOB_LIST_NAME_LENGTH:  # In case name is longer than JOB_LIST_NAME_LENGTH (25)
                new_entry_name = normalize_job_name(entry)
                logging.error(f"Detected name too long in job list, replacing '{entry}' by '{new_entry_name}'")
                new_key = entry.replace(entry, new_entry_name)
                job_list[new_key] = job_list.pop(entry)
                entry = new_key
            # Add to listbox
            job_list_treeview.insert('', 'end', text=entry, values=(job_list[entry]["description"],),
                                     tags=("pending","joblist_font",) if job_list[entry]['done'] == False else ("done","joblist_font",))
            job_list[entry]['attempted'] = job_list[entry]['done']  # Add default value for new json field
        f.close()
        for entry in job_list:
            item_id = search_job_name_in_job_treeview(entry)
            if item_id is not None:
                job_list_treeview.item(item_id, tags=("done","joblist_font",) if job_list[entry]['done'] else ("pending","joblist_font",))

        job_list_hash = generate_dict_hash(job_list)
    else:   # No job list file. Set empty config to force defaults
        job_list = {}


def start_processing_job_list():
    global BatchJobRunning, start_batch_btn, ConvertLoopExitRequested
    if BatchJobRunning:
        ConvertLoopExitRequested = True
    else:
        BatchJobRunning = True
        widget_status_update(DISABLED, start_batch_btn)
        FrameSync_Viewer_popup_update_widgets(DISABLED)

        for entry in job_list:
            job_list[entry]['attempted'] = job_list[entry]['done'] # Reset attempted flag for those not done yet
        job_processing_loop()


def job_processing_loop():
    global job_list, job_list_treeview
    global project_config
    global CurrentJobEntry
    global BatchJobRunning
    global project_config_from_file
    global suspend_on_completion
    global CurrentFrame, current_bad_frame_index

    logging.debug(f"Starting batch loop")
    job_started = False
    for entry in job_list:
        if not job_list[entry]['done'] and not job_list[entry]['attempted']:
            # Save bad frame list if any
            if len(bad_frame_list) > 0:
                save_bad_frame_list()
                # Clear list of bad frames
                bad_frame_list.clear()
                current_bad_frame_index = -1
            job_list[entry]['attempted'] = True
            for item_id in job_list_treeview.selection():  
                job_list_treeview.selection_remove(item_id)  # Unselect each selected item
            item_id = search_job_name_in_job_treeview(entry)
            if item_id is not None:
                job_list_treeview.item(item_id, tags=("ongoing","joblist_font",))
            CurrentJobEntry = entry
            if 'FrameFrom' in job_list[entry]['project']:
                # At some point FrameFrom and FrameTo were saved to project file as strings, so just in case, convert them.
                CurrentFrame = int(job_list[entry]['project']['FrameFrom'])
                logging.debug(f"Set current Frame to {CurrentFrame}")
            else:
                CurrentFrame = 0
            logging.debug(f"Processing {entry}, starting from frame {CurrentFrame}, {job_list[entry]['project']['FramesToEncode']} frames")
            project_config_from_file = False
            project_config = job_list[entry]['project'].copy()
            decode_project_config()

            # Load matching file list from target dir (source dir list retrieved in decode_project_config)
            get_target_dir_file_list()

            logging.debug(f"Processing batch loop: Loaded {SourceDir} folder")

            start_convert()
            job_started = True
            break
    if not job_started:
        CurrentJobEntry = -1
        generation_exit()
        if suspend_on_completion.get() == 'batch_completion':
            system_suspend()
            time.sleep(2)


def job_list_delete_current(event):
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return
    job_list_delete_selected()


def job_list_load_current(event):
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return
    job_list_load_selected()


def job_list_rerun_current(event):
    global job_list, job_list_treeview
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return

    job_list_rerun_selected()

    selected = job_list_treeview.selection()  # Get selected item(s)
    if not selected:
        return  # Nothing selected, do nothing

    all_items = job_list_treeview.get_children()  # Get all row IDs
    index = all_items.index(selected[0]) if selected[0] in all_items else -1

    if index < len(all_items) - 1:  # Ensure it's not the last row
        next_item = all_items[index + 1]
        job_list_treeview.selection_set(next_item)  # Select next row
        job_list_treeview.focus(next_item)  # Move focus to it


def sync_job_list_with_treeview():
    global job_list_treeview, job_list

    order_list = []
    for item_id in job_list_treeview.get_children():
        name = job_list_treeview.item(item_id, "text")  # Get Name (column #0)
        if name:  
            order_list.append(normalize_job_name(name))  # First column value

    # Create a new dictionary with the desired order
    job_list = {key: job_list[key] for key in order_list if key in job_list}


def job_list_move_up(event):
    global job_list_treeview, job_list
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return
    selected_index = job_list_treeview.selection()
    if selected_index:
        item_id = selected_index[0]
        items = job_list_treeview.get_children()
        index = items.index(item_id)  # Get current position
        if index > 0:  # Ensure it's not already at the top
            job_list_treeview.move(item_id, "", index - 1)  # Move up
            # Update Job list
            Name = job_list_treeview.item(item_id, "text")  # Returns Name column (#0)
            if Name:
                if Name in job_list:
                    if job_list[Name]['done'] == True:
                        job_list_treeview.item(item_id, tags=("pending","joblist_font",) if job_list[Name]['done'] == False else ("done","joblist_font",))
                sync_job_list_with_treeview()


def job_list_move_down(event):
    global job_list_treeview, job_list
    global job_list_listbox_disabled

    if job_list_listbox_disabled:
        return
    selected_index = job_list_treeview.selection()
    if selected_index:
        item_id = selected_index[0]
        items = job_list_treeview.get_children()
        index = items.index(item_id)  # Get current position
        if index < len(items) - 1:  # Ensure it's not already at the bottom
            job_list_treeview.move(item_id, "", index + 1)  # Move down
            # Update Job list
            Name = job_list_treeview.item(item_id, "text")  # Ret¡riebe job name (column #0)
            if Name:
                if Name in job_list:
                    if job_list[Name]['done'] == True:
                        job_list_treeview.item(item_id, tags=("pending","joblist_font",) if job_list[Name]['done'] == False else ("done","joblist_font",))
                sync_job_list_with_treeview()


"""
###############################
User feedback support functions
###############################
"""


def display_ffmpeg_result(ffmpeg_output):
    global win

    ffmpeg_result = Toplevel(win)
    ffmpeg_result.title('Video encoding completed. Results displayed below')
    ffmpeg_result.geometry('600x400')
    ffmpeg_result.geometry('+250+250')
    ffmpeg_label = Text(ffmpeg_result, borderwidth=0)
    ffmpeg_label.insert(1.0, ffmpeg_output)
    ffmpeg_label.pack(side=TOP)
    # creating and placing scrollbar
    ffmpeg_result_sb = Scrollbar(ffmpeg_result, orient=VERTICAL)
    ffmpeg_result_sb.pack(side=RIGHT)
    # binding scrollbar with other widget (Text, Listbox, Frame, etc)
    ffmpeg_label.config(yscrollcommand=ffmpeg_result_sb.set)
    ffmpeg_result_sb.config(command=ffmpeg_label.yview)


def register_frame():
    global FPS_LastMinuteFrameTimes
    global FPS_StartTime
    global FPS_CalculatedValue

    # Get current time
    frame_time = time.time()
    # Determine if we should start new count (last capture older than 5 seconds)
    if len(FPS_LastMinuteFrameTimes) == 0 or FPS_LastMinuteFrameTimes[-1] < frame_time - 12:
        FPS_StartTime = frame_time
        FPS_LastMinuteFrameTimes.clear()
        FPS_CalculatedValue = -1
    # Add current time to list
    FPS_LastMinuteFrameTimes.append(frame_time)
    # Remove entries older than one minute
    FPS_LastMinuteFrameTimes.sort()
    while FPS_LastMinuteFrameTimes[0] <= frame_time-60:
        FPS_LastMinuteFrameTimes.remove(FPS_LastMinuteFrameTimes[0])
    # Calculate current value, only if current count has been going for more than 10 seconds
    if frame_time - FPS_StartTime > 60:  # no calculations needed, frames in list are all in the last 60 seconds
        FPS_CalculatedValue = len(FPS_LastMinuteFrameTimes)/60
    elif frame_time - FPS_StartTime > 10:  # some  calculations needed if less than 60 sec
        FPS_CalculatedValue = int((len(FPS_LastMinuteFrameTimes) * 60) / (frame_time - FPS_StartTime))/60



"""
#######################
File handling functions
#######################
"""


def set_source_folder():
    global SourceDir, frames_source_dir
    global TargetDir, frames_target_dir
    global CurrentFrame, frame_slider, Go_btn, cropping_btn
    global first_absolute_frame
    global project_name
    global current_bad_frame_index
    global ui_init_done

    # Write project data before switching project
    save_project_config()

    aux_dir = filedialog.askdirectory(
        initialdir=SourceDir,
        title="Select folder with captured images to process")

    if not aux_dir or aux_dir == "" or aux_dir == ():
        return
    elif TargetDir == aux_dir:
        tk.messagebox.showerror(
            "Error!",
            "Source folder cannot be the same as target folder.")
        return
    else:
        win.config(cursor="watch")  # Set cursor to hourglass
        ui_init_done = False
        SourceDir = aux_dir
        frames_source_dir.delete(0, 'end')
        frames_source_dir.insert('end', SourceDir)
        frames_source_dir.after(100, frames_source_dir.xview_moveto, 1)
        # Create a project id (folder name) for the stats logging below
        # Replace any commas by semi colon to avoid problems when generating csv by AfterScanAnalysis
        project_name = os.path.split(SourceDir)[-1].replace(',', ';')
        general_config["SourceDir"] = SourceDir


    load_project_config()  # Needs SourceDir defined

    decode_project_config()  # Needs first_absolute_frame defined

    template_list.set_scale(frame_width)    # frame_width set by get_source_dir_file_list

    # If not defined in project, create target folder inside source folder
    if TargetDir == '':
        TargetDir = os.path.join(SourceDir, 'out')
        if not os.path.isdir(TargetDir):
            os.mkdir(TargetDir)
        get_target_dir_file_list()
        frames_target_dir.delete(0, 'end')
        frames_target_dir.insert('end', TargetDir)
        frames_target_dir.after(100, frames_target_dir.xview_moveto, 1)
        set_project_defaults()
        project_config["TargetDir"] = TargetDir

    # Enable Start and Crop buttons, plus slider, once we have files to handle
    cropping_btn.config(state=NORMAL)
    frame_slider.config(state=NORMAL)
    Go_btn.config(state=NORMAL)
    frame_slider.set(CurrentFrame)

    init_display()
    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)
    ui_init_done = True
    win.config(cursor="")  # Reset cursor to standard arrow



def set_frames_target_folder():
    global TargetDir
    global frames_target_dir

    aux_dir = filedialog.askdirectory(
        initialdir=TargetDir,
        title="Select folder where to store generated frames")

    if not aux_dir or aux_dir == "" or aux_dir == ():
        return
    elif aux_dir == SourceDir:
        tk.messagebox.showerror(
            "Error!",
            "Target folder cannot be the same as source folder.")
        return
    else:
        TargetDir = aux_dir
        get_target_dir_file_list()
        frames_target_dir.delete(0, 'end')
        frames_target_dir.insert('end', TargetDir)
        frames_target_dir.after(100, frames_target_dir.xview_moveto, 1)
        set_project_defaults()
        project_config["TargetDir"] = TargetDir


def set_video_target_folder():
    global video_target_dir

    VideoTargetDir = filedialog.askdirectory(
        initialdir=video_target_dir_str.get(),
        title="Select folder where to store generated video")

    if not VideoTargetDir:
        return
    elif VideoTargetDir == SourceDir:
        tk.messagebox.showerror(
            "Error!",
            "Video target folder cannot be the same as source folder.")
        return
    else:
        video_target_dir_str.set(VideoTargetDir)
        video_target_dir.after(100, video_target_dir.xview_moveto, 1)

    project_config["VideoTargetDir"] = video_target_dir_str.get()


"""
###############################
UI support commands & functions
###############################
"""


def widget_status_update(widget_state=0, button_action=0):
    global CropTopLeft, CropBottomRight, CropAreaDefined
    global frame_slider, Go_btn, Exit_btn
    global frames_source_dir, source_folder_btn
    global frames_target_dir, target_folder_btn
    global encode_all_frames, encode_all_frames_checkbox
    global frame_from_entry, frame_to_entry, frames_separator_label
    global frames_to_encode_label
    global rotation_angle_label
    global perform_rotation_checkbox, rotation_angle_spinbox, perform_rotation
    global perform_stabilization
    global perform_stabilization_checkbox, stabilization_threshold_spinbox
    global perform_cropping_checkbox, perform_denoise_checkbox, perform_sharpness_checkbox
    global perform_gamma_correction_checkbox, gamma_correction_spinbox
    global force_4_3_crop_checkbox, force_16_9_crop_checkbox
    global custom_stabilization_btn, low_contrast_custom_template_checkbox
    global generate_video_checkbox, skip_frame_regeneration_cb
    global video_target_dir, video_target_folder_btn
    global video_filename_label, video_title_label, video_title_name
    global video_fps_dropdown
    global resolution_dropdown
    global video_filename_name
    global ffmpeg_preset_rb1, ffmpeg_preset_rb2, ffmpeg_preset_rb3
    global start_batch_btn
    global add_job_btn, delete_job_btn, rerun_job_btn
    global perform_fill_none_rb, perform_fill_fake_rb, perform_fill_dumb_rb
    global extended_stabilization_checkbox
    global SourceDirFileList
    global template_list
    global job_list_listbox_disabled

    if widget_state != 0:
        CropAreaDefined = CropTopLeft != (0, 0) and CropBottomRight != (0, 0)
        frame_slider.config(state=widget_state)
        Go_btn.config(state=widget_state if button_action != Go_btn else NORMAL)
        Exit_btn.config(state=widget_state)
        frames_source_dir.config(state=widget_state)
        source_folder_btn.config(state=widget_state)
        frames_target_dir.config(state=widget_state)
        target_folder_btn.config(state=widget_state)
        encode_all_frames_checkbox.config(state=widget_state)
        frame_from_entry.config(state=widget_state if not encode_all_frames.get() else DISABLED)
        frame_to_entry.config(state=widget_state if not encode_all_frames.get() else DISABLED)
        frames_to_encode_label.config(state=widget_state if not encode_all_frames.get() else DISABLED)
        frames_separator_label.config(state=widget_state if not encode_all_frames.get() else DISABLED)
        perform_rotation_checkbox.config(state=widget_state)
        rotation_angle_spinbox.config(state=widget_state if perform_rotation.get() else DISABLED)
        rotation_angle_label.config(state=widget_state if perform_rotation.get() else DISABLED)
        perform_stabilization_checkbox.config(state=widget_state if not is_demo else NORMAL)
        perform_fill_none_rb.config(state=widget_state if not is_demo else NORMAL)
        perform_fill_fake_rb.config(state=widget_state if not is_demo else NORMAL)
        perform_fill_dumb_rb.config(state=widget_state if not is_demo else NORMAL)
        extended_stabilization_checkbox.config(state=widget_state if perform_stabilization.get() else DISABLED)
        custom_stabilization_btn.config(state=widget_state)
        stabilization_threshold_match_label.config(state=widget_state if perform_stabilization.get() else DISABLED)
        stabilization_shift_label.config(state=widget_state if perform_stabilization.get() else DISABLED)
        stabilization_shift_y_spinbox.config(state=widget_state if perform_stabilization.get() else DISABLED)
        stabilization_shift_x_spinbox.config(state=widget_state if perform_stabilization.get() else DISABLED)
        low_contrast_custom_template_checkbox.config(state=widget_state)
        if ExpertMode:
            stabilization_threshold_spinbox.config(state=widget_state)
        if is_demo:
            perform_cropping_checkbox.config(state=NORMAL)
        else:
            perform_cropping_checkbox.config(state=widget_state if perform_stabilization.get() and CropAreaDefined else DISABLED)
        cropping_btn.config(state=widget_state if perform_stabilization.get() else DISABLED)
        force_4_3_crop_checkbox.config(state=widget_state if perform_stabilization.get() else DISABLED)
        force_16_9_crop_checkbox.config(state=widget_state if perform_stabilization.get() else DISABLED)
        perform_denoise_checkbox.config(state=widget_state)
        perform_sharpness_checkbox.config(state=widget_state)
        perform_gamma_correction_checkbox.config(state=widget_state)
        gamma_correction_spinbox.config(state=widget_state)
        film_type_S8_rb.config(state=DISABLED if template_list.get_active_type() == 'custom' else widget_state)
        film_type_R8_rb.config(state=DISABLED if template_list.get_active_type() == 'custom' else widget_state)
        generate_video_checkbox.config(state=widget_state if ffmpeg_installed else DISABLED)
        skip_frame_regeneration_cb.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        video_target_dir.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        video_target_folder_btn.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        video_filename_label.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        video_title_label.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        video_title_name.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        video_fps_dropdown.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        resolution_dropdown.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        video_fps_label.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        resolution_label.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        video_filename_name.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        ffmpeg_preset_rb1.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        ffmpeg_preset_rb2.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        ffmpeg_preset_rb3.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        start_batch_btn.config(state=widget_state if button_action != start_batch_btn else NORMAL)
        add_job_btn.config(state=widget_state)
        delete_job_btn.config(state=widget_state)
        rerun_job_btn.config(state=widget_state)
        #job_list_treeview.config(state=widget_state)
        if widget_state == DISABLED:
            job_list_listbox_disabled = True
        else:
            job_list_listbox_disabled = False
    # Handle a few specific widgets having extra conditions
    if len(SourceDirFileList) == 0:
        perform_stabilization_checkbox.config(state=DISABLED)
        perform_cropping_checkbox.config(state=DISABLED)
        cropping_btn.config(state=DISABLED)
        force_4_3_crop_checkbox.config(state=DISABLED)
        force_16_9_crop_checkbox.config(state=DISABLED)
        perform_denoise_checkbox.config(state=DISABLED)
        perform_sharpness_checkbox.config(state=DISABLED)
        perform_gamma_correction_checkbox.config(state=DISABLED)
        gamma_correction_spinbox.config(state=DISABLED)
    custom_stabilization_btn.config(relief=SUNKEN if template_list.get_active_type() == 'custom' else RAISED)

    if use_simple_stabilization:
        custom_stabilization_btn.config(state = DISABLED)
        low_contrast_custom_template_checkbox.config(state = DISABLED)
        stabilization_threshold_match_label.config(state = DISABLED)
        extended_stabilization_checkbox.config(state = DISABLED)


def update_frame_from(event):
    global frame_from_str, frame_slider
    global CurrentFrame
    
    if len(frame_from_str.get()) == 0 or frame_from_str.get() == '0' or event.num == 2:
        frame_from_str.set(CurrentFrame)
    else:
        if ui_init_done:
            select_scale_frame(frame_from_str.get())
        frame_slider.set(frame_from_str.get())


def update_frame_to(event):
    global frame_to_str, frame_slider
    global CurrentFrame
    if len(frame_to_str.get()) == 0 or frame_to_str.get() == '0' or event.num == 2:
        frame_to_str.set(CurrentFrame)
    else:
        if ui_init_done:
            select_scale_frame(frame_to_str.get())
        frame_slider.set(frame_to_str.get())

def on_paste_all_entries(event, entry):
    try:
        entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
    except tk.TclError:
        logging.warning("No selection to delete")


def perform_rotation_selection():
    global perform_rotation
    rotation_angle_spinbox.config(
        state=NORMAL if perform_rotation.get() else DISABLED)
    rotation_angle_label.config(
        state=NORMAL if perform_rotation.get() else DISABLED)
    project_config["PerformRotation"] = perform_rotation.get()
    win.after(5, scale_display_update)


def rotation_angle_selection():
    global rotation_angle_spinbox, rotation_angle_str
    global RotationAngle
    RotationAngle = rotation_angle_spinbox.get()
    project_config["RotationAngle"] = RotationAngle
    win.after(5, scale_display_update)


def rotation_angle_spinbox_focus_out(event):
    global rotation_angle_spinbox, rotation_angle_str
    global RotationAngle
    RotationAngle = rotation_angle_spinbox.get()
    project_config["RotationAngle"] = RotationAngle
    win.after(5, scale_display_update)


def perform_stabilization_selection():
    global perform_stabilization

    if ExpertMode:
        stabilization_threshold_spinbox.config(
            state=NORMAL if perform_stabilization.get() else DISABLED)
    project_config["PerformStabilization"] = perform_stabilization.get()
    win.after(5, scale_display_update)
    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)


def low_contrast_custom_template_selection():
    global low_contrast_custom_template

    project_config["LowContrastCustomTemplate"] = low_contrast_custom_template.get()
    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)


def extended_stabilization_selection():
    global extended_stabilization, hole_search_area_adjustment_pending
    project_config["ExtendedStabilization"] = extended_stabilization.get()
    hole_search_area_adjustment_pending = True
    win.after(5, scale_display_update)
    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)


def select_stabilization_shift_y(even=None):
    global StabilizationShiftY
    StabilizationShiftY = stabilization_shift_y_value.get()
    project_config["StabilizationShiftY"] = StabilizationShiftY
    win.after(5, scale_display_update)
    FrameSync_Viewer_popup_update_widgets(NORMAL)


def select_stabilization_shift_x(even=None):
    global StabilizationShiftX
    StabilizationShiftX = stabilization_shift_x_value.get()
    project_config["StabilizationShiftX"] = StabilizationShiftX
    win.after(5, scale_display_update)
    FrameSync_Viewer_popup_update_widgets(NORMAL)


def stabilization_threshold_selection(updown):
    global stabilization_threshold_spinbox, stabilization_threshold_str
    global StabilizationThreshold
    StabilizationThreshold = stabilization_threshold_spinbox.get()
    project_config["StabilizationThreshold"] = StabilizationThreshold


def stabilization_threshold_spinbox_focus_out(event):
    global stabilization_threshold_spinbox, stabilization_threshold_str
    global StabilizationThreshold
    StabilizationThreshold = stabilization_threshold_spinbox.get()
    project_config["StabilizationThreshold"] = StabilizationThreshold


def perform_cropping_selection():
    global perform_cropping
    global perform_stabilization
    global generate_video_checkbox
    global ui_init_done

    generate_video_checkbox.config(state=NORMAL if ffmpeg_installed
                                   else DISABLED)
    project_config["PerformCropping"] = perform_cropping.get()
    if ui_init_done:
        win.after(5, scale_display_update)


def perform_sharpness_selection():
    global perform_sharpness

    project_config["PerformSharpness"] = perform_sharpness.get()
    if ui_init_done:
        win.after(5, scale_display_update)


def perform_denoise_selection():
    global perform_denoise

    project_config["PerformDenoise"] = perform_denoise.get()
    if ui_init_done:
        win.after(5, scale_display_update)


def perform_gamma_correction_selection():
    project_config["PerformGammaCorrection"] = perform_gamma_correction.get()
    if ui_init_done:
        win.after(5, scale_display_update)


def select_gamma_correction_value():
    if ui_init_done:
        win.after(5, scale_display_update)


def force_4_3_selection():
    global perform_cropping
    global generate_video_checkbox
    global ui_init_done
    global force_4_3_crop, Force43
    global force_16_9_crop, Force169

    Force43 = force_4_3_crop.get()
    if Force43:
        force_16_9_crop.set(False)
        Force169 = False
    project_config["Force_4/3"] = force_4_3_crop.get()
    project_config["Force_16/9"] = force_16_9_crop.get()


def force_16_9_selection():
    global perform_cropping
    global generate_video_checkbox
    global ui_init_done
    global force_4_3_crop, Force43
    global force_16_9_crop, Force169

    Force169 = force_16_9_crop.get()
    if Force169:
        force_4_3_crop.set(False)
        Force43= False
    project_config["Force_4/3"] = force_4_3_crop.get()
    project_config["Force_16/9"] = force_16_9_crop.get()


def encode_all_frames_selection():
    global encode_all_frames
    project_config["EncodeAllFrames"] = encode_all_frames.get()
    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)


def generate_video_selection():
    global generate_video

    project_config["GenerateVideo"] = generate_video.get()
    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)


def set_fps(selected):
    global VideoFps

    project_config["VideoFps"] = selected
    VideoFps = eval(selected)


def set_resolution(selected):
    global resolution_dict
    project_config["VideoResolution"] = selected


def display_template_popup_closure():
    if FrameSync_Viewer_opened:
        FrameSync_Viewer_popup()    # Calling while opened will close it


def refresh_current_frame_ui_info(frame_num, frame_first):
    selected_frame_number.config(text=f'Number:{frame_num+frame_first}')
    selected_frame_index.config(text=f'Index:{frame_num+1}')
    selected_frame_time.config(text=f'Film time:{get_frame_time(frame_num)}')
    if FrameSync_Viewer_opened:
        if (len(bad_frame_list) > 1 and
            'original_x' in bad_frame_list[current_bad_frame_index] and 
            'original_y' in bad_frame_list[current_bad_frame_index] and 
            'original_threshold' in bad_frame_list[current_bad_frame_index]):
            pos_before_text.set(f"{bad_frame_list[current_bad_frame_index]['original_x']}, {bad_frame_list[current_bad_frame_index]['original_y']}")
            threshold_before_text.set(f"T:{bad_frame_list[current_bad_frame_index]['original_threshold']}")
            pos_after_text.set(f"{bad_frame_list[current_bad_frame_index]['x']}, {bad_frame_list[current_bad_frame_index]['y']}")
            threshold_after_text.set(f"Ts:{bad_frame_list[current_bad_frame_index]['threshold']}")


def cmd_settings_popup_dismiss():
    global options_dlg
    global BaseFolder, CurrentDir

    options_dlg.grab_release()
    options_dlg.destroy()


def cmd_settings_popup_accept():
    global options_dlg, FfmpegBinName, enable_rectangle_popup, FFmpeg_denoise_param
    global enable_soundtrack, UserDefinedLeftStripeWidthProportion

    general_config["PopupPos"] = options_dlg.geometry()

    save_FfmpegBinName = FfmpegBinName
    FfmpegBinName = custom_ffmpeg_path.get()
    if not is_ffmpeg_installed():
        tk.messagebox.showerror("Error!",
                                "Provided FFMpeg path is invalid.")
        custom_ffmpeg_path.delete(0, 'end')
        custom_ffmpeg_path.insert('end', FfmpegBinName)
        FfmpegBinName = save_FfmpegBinName
    else:
        FfmpegBinName = custom_ffmpeg_path.get()
        general_config["FfmpegBinName"] = FfmpegBinName
    FFmpeg_denoise_param = ffmpeg_denoise_value.get()
    general_config["FFmpegHqdn3d"] = FFmpeg_denoise_param
    enable_rectangle_popup = enable_rectangle_popup_value.get()
    general_config["EnablePopups"] = enable_rectangle_popup
    if sound_file_available:
        enable_soundtrack = enable_soundtrack_value.get()
        general_config["EnableSoundtrack"] = enable_soundtrack
    UserDefinedLeftStripeWidthProportion = left_stripe_width_value.get() / 100
    project_config["UserDefinedLeftStripeWidthProportion"] = UserDefinedLeftStripeWidthProportion

    options_dlg.grab_release()
    options_dlg.destroy()


def cmd_settings_popup():
    global options_dlg
    global custom_ffmpeg_path
    global FFmpeg_denoise_param, FfmpegBinName
    global ffmpeg_denoise_value, enable_rectangle_popup_value, enable_soundtrack_value
    global left_stripe_width_value

    options_row = 0

    options_dlg = tk.Toplevel(win)

    if 'PopupPos' in general_config:
        options_dlg.geometry(f"+{general_config['PopupPos'].split('+', 1)[1]}")

    options_dlg.title("AfterScan Settings")
    # options_dlg.geometry(f"300x100")
    options_dlg.rowconfigure(0, weight=1)
    options_dlg.columnconfigure(0, weight=1)

    ### Add all controls here
    # Custom ffmpeg path
    custom_ffmpeg_path_label = Label(options_dlg, text='FFmpeg path:', font=("Arial", FontSize))
    custom_ffmpeg_path_label.grid(row=options_row, column=0, sticky=W, padx=5, pady=(10,5))
    custom_ffmpeg_path = Entry(options_dlg, width=10, borderwidth=1, font=("Arial", FontSize))
    custom_ffmpeg_path.grid(row=options_row, column=1, sticky=W, padx=5)
    custom_ffmpeg_path.delete(0, 'end')
    custom_ffmpeg_path.insert('end', FfmpegBinName)
    custom_ffmpeg_path.bind('<<Paste>>', lambda event, entry=custom_ffmpeg_path: on_paste_all_entries(event, entry))
    as_tooltips.add(custom_ffmpeg_path, "Path where the ffmpeg executable is installed in your system")

    options_row += 1

    # ffmpeg denoise filter parameters (hqdn3d=8:6:4:3) FFmpeg_denoise_param
    ffmpeg_denoise_label = Label(options_dlg, text='FFmpeg hqdn3d parameter:', font=("Arial", FontSize))
    ffmpeg_denoise_label.grid(row=options_row, column=0, sticky=W, padx=5, pady=(10,5))
    ffmpeg_denoise_value = Entry(options_dlg, width=10, borderwidth=1, font=("Arial", FontSize))
    ffmpeg_denoise_value.grid(row=options_row, column=1, sticky=W, padx=5)
    ffmpeg_denoise_value.delete(0, 'end')
    ffmpeg_denoise_value.insert('end', FFmpeg_denoise_param)
    ffmpeg_denoise_value.bind('<<Paste>>', lambda event, entry=custom_ffmpeg_path: on_paste_all_entries(event, entry))
    as_tooltips.add(ffmpeg_denoise_value, "Parameter to pass to denoise filter (hqdn3d) filter as parameter durign video encoding. Default value is '8:6:4:3'")

    options_row += 1

    # Checkbox to add soundtrack to generated film
    enable_soundtrack_value = tk.BooleanVar(value=enable_soundtrack)
    enable_soundtrack_checkbox = tk.Checkbutton(options_dlg,
                                                         text='Add soundtrack to video',
                                                         variable=enable_soundtrack_value,
                                                         onvalue=True, offvalue=False,
                                                         font=("Arial", FontSize), state=NORMAL if sound_file_available else DISABLED)
    enable_soundtrack_checkbox.grid(row=options_row, column=0, columnspan=2, sticky=W, padx=5, pady=5)
    as_tooltips.add(enable_soundtrack_checkbox, "Add soundtrack (projector sound) to generated videos")
    options_row += 1

    # Checkbox to enable popups for Custom template and cropping definition
    enable_rectangle_popup_value = tk.BooleanVar(value=enable_rectangle_popup)
    enable_rectangle_popup_checkbox = tk.Checkbutton(options_dlg,
                                                         text='Enable popups',
                                                         variable=enable_rectangle_popup_value,
                                                         onvalue=True, offvalue=False,
                                                         font=("Arial", FontSize))
    enable_rectangle_popup_checkbox.grid(row=options_row, column=0, sticky=W, padx=5, pady=5)
    as_tooltips.add(enable_rectangle_popup_checkbox, "Display popup window to define custom template and cropping rectangle (vs definition in main window)")
    options_row += 1

    # Left stripe width value
    left_stripe_width_value = tk.IntVar(value=int(UserDefinedLeftStripeWidthProportion*100))
    left_stripe_width_label = Label(options_dlg, text='Left stripe width %:', font=("Arial", FontSize))
    left_stripe_width_label.grid(row=options_row, column=0, sticky=W, padx=5, pady=(10,5))
    left_stripe_width_spinbox = tk.Spinbox(options_dlg, width=3,
        textvariable=left_stripe_width_value, from_=5, to=95, increment=5, font=("Arial", FontSize))
    left_stripe_width_spinbox.grid(row=options_row, column=1, sticky=W, padx=5)
    as_tooltips.add(left_stripe_width_spinbox, "Left stripe width as percentage of frame width")

    options_row += 1

    # OK / Cancel buttons
    options_cancel_btn = tk.Button(options_dlg, text="Cancel", command=cmd_settings_popup_dismiss, width=8,
                                   font=("Arial", FontSize))
    options_cancel_btn.grid(row=options_row, column=0, padx=5, pady=(5,10), sticky='w')
    options_ok_btn = tk.Button(options_dlg, text="OK", command=cmd_settings_popup_accept, width=8,
                               font=("Arial", FontSize))
    options_ok_btn.grid(row=options_row, column=1, padx=5, pady=(5,10), sticky='e')


    # Arrange status of widgets in options popup
    custom_ffmpeg_path.config(state=NORMAL) # Before this widget was disabled if video generation was unchecked, but no need for that

    options_dlg.resizable(False, False)
    options_dlg.protocol("WM_DELETE_WINDOW", cmd_settings_popup_dismiss)  # intercept close button
    options_dlg.transient(win)  # dialog window is related to main
    options_dlg.wait_visibility()  # can't grab until window appears, so we wait
    options_dlg.grab_set()  # ensure all input goes to our window
    options_dlg.wait_window()  # block until window is destroyed


################################################################
# FrameSync Editor / Bad Fram edetection/Correction functions
################################################################
def cleanup_bad_frame_list(limit):
    """
    Deletes all but the 3 most recent 'bad_frame_list.01_YYYYMMDD_HHMMSS.json' files
    in the specified directory when there are more than 10 files.
    
    Args:
        directory (str): Directory to search for files (default: current directory).
    """
    bad_frame_list_name = f"{os.path.split(SourceDir)[-1]}"
    # Set filename
    bad_frame_list_pattern_name = get_bad_frame_list_filename(with_timestamp=True, with_wildcards=True)
    full_path_bad_frame_list_pattern_name = os.path.join(resources_dir, bad_frame_list_pattern_name)

    # Get list of matching files
    files = glob(full_path_bad_frame_list_pattern_name)
    
    # If there are more than <limit> files (normally 10)
    if len(files) > limit:
        # Sort files by modification time (most recent first)
        files_sorted = sorted(files, key=os.path.getmtime, reverse=True)
        
        # Keep the 3 most recent files, mark the rest for deletion
        files_to_keep = files_sorted[:3]
        files_to_delete = files_sorted[3:]
        
        # Delete the older files
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
            except OSError as e:
                logging.error(f"Error deleting bad frame file {file_path}: {e}")
        
        logging.debug(f"Bad frame file cleanup completed. Kept the 3 most recent files: {files_to_keep}")


def get_bad_frame_list_filename(with_timestamp = False, with_wildcards = False):
    # Set filename to framer source folder
    bad_frame_list_name = f"{os.path.split(SourceDir)[-1]}"
    bad_frame_list_filename = f"{bad_frame_list_name}"
    if with_timestamp:
        if not with_wildcards:
            bad_frame_list_filename += datetime.now().strftime("_%Y%m%d_%H%M%S")
        else:
            bad_frame_list_filename += '*'
    bad_frame_list_filename += ".badframes.json"
    if with_timestamp:
        bad_frame_list_filename += ".bak"
    return os.path.join(resources_dir, bad_frame_list_filename)
    

def save_bad_frame_list(with_timestamp = False):
    full_path_bad_frame_list_filename = get_bad_frame_list_filename(with_timestamp)
    # Serialize (save) the list to a file
    with open(full_path_bad_frame_list_filename, "w") as file:
        json.dump(bad_frame_list, file, indent=4)

    if with_timestamp:  # Delete backup files if more than 10
        cleanup_bad_frame_list(3)


def load_bad_frame_list():
    global bad_frame_list, current_bad_frame_index

    full_path_bad_frame_list_filename = get_bad_frame_list_filename()

    # To read (deserialize) the list back, convert elements to dictionary if required
    if os.path.isfile(full_path_bad_frame_list_filename):  # If hdr frames exist, add them
        with open(full_path_bad_frame_list_filename, "r") as file:
            aux_list = json.load(file)
        if isinstance(aux_list[0], list): # Migrate to dictionary
            for bad_frame in aux_list:
                bad_frame_list.append({'frame_idx': bad_frame[0], 'x': bad_frame[1], 'y': bad_frame[2], 'threshold': bad_frame[3], 'original_threshold': bad_frame[3], 'is_frame_saved': bad_frame[4]})
        else:
            bad_frame_list = aux_list
        logging.debug(f"Loaded bad frame list for {full_path_bad_frame_list_filename}, list length is {len(bad_frame_list)}")

    current_bad_frame_index = -1
    FrameSync_Viewer_popup_refresh()


def save_corrected_frames_loop(count_processed):
    global StabilizationThreshold, process_bad_frame_index, stop_bad_frame_save
    global CorrectLoopRunning

    if stop_bad_frame_save:
        CorrectLoopRunning = False
        stop_bad_frame_save = False

        win.config(cursor="")  # Change cursor to indicate processing
        template_popup_window.config(cursor="") 
        save_button.config(text="Re-generate corrected frames", bg=save_bg, fg=save_fg)
        FrameSync_Viewer_popup_update_widgets(NORMAL)
        widget_status_update(NORMAL, 0)
        if process_bad_frame_index >= len(bad_frame_list):
            tk.messagebox.showinfo("Re-generation complete", f"{count_processed} modified frames have been saved. "
                                   "When generating a video, take care to check 'Skip frame regeneration', otherwise the corrected frames will be overwritten.")
        else:
            tk.messagebox.showinfo("Re-generation interrupted", f"Re-generation interrupted by user. {count_processed} modified frames regenerated before cancelation.")

        process_bad_frame_index = -1

        return

    bad_frame = bad_frame_list[process_bad_frame_index]
    if not bad_frame['is_frame_saved']:
        save_thres = StabilizationThreshold
        StabilizationThreshold = bad_frame['threshold']
        frame_encode(bad_frame['frame_idx'], -1, True, bad_frame['x'], bad_frame['y'])
        StabilizationThreshold = save_thres
        frame_selected.set(bad_frame['frame_idx'])
        frame_slider.set(bad_frame['frame_idx'])
        display_output_frame_by_number(bad_frame['frame_idx'])
        #win.update_idletasks()
        #template_popup_window.update_idletasks()
        #win.update()
        #template_popup_window.update()
        bad_frame['is_frame_saved'] = True # Saved flag
        count_processed += 1

    process_bad_frame_index += 1 

    if process_bad_frame_index >= len(bad_frame_list):
        stop_bad_frame_save = True

    win.after(20, save_corrected_frames_loop, count_processed)  # Next processing slice


def save_corrected_frames():
    global process_bad_frame_index, stop_bad_frame_save
    global CorrectLoopRunning

    if process_bad_frame_index != -1:
        stop_bad_frame_save = True    # Request re-generation loop to end
        return

    count = 0

    for bad_frame in bad_frame_list:
        if not bad_frame['is_frame_saved']:
            count += 1

    if count == 0:
        tk.messagebox.showinfo("No frames to save", "No modified frames pending to be saved")
    else:
        FrameSync_Viewer_popup_update_widgets(DISABLED, True)
        widget_status_update(DISABLED, 0)
        win.config(cursor="watch")  # Set cursor to hourglass
        template_popup_window.config(cursor="watch")  # Set cursor to hourglass
        win.update()
        template_popup_window.update()
        process_bad_frame_index = 0    # Start with first bad frame
        stop_bad_frame_save = False    # Set to False initially
        save_button.config(text="Cancel frame re-generation", bg='red', fg='white')
        CorrectLoopRunning = True
        win.after(100, save_corrected_frames_loop, 0)  # Start processing in chunks 


def delete_detected_bad_frames():
    global current_bad_frame_index

    retvalue = True

    if len(bad_frame_list) > 0:
        if BatchJobRunning or tk.messagebox.askyesno(
                            "Deleting FrameSync info",
                            f"There are currently {len(bad_frame_list)} misaligned registered by AfterScan, "
                            f"as well as user information to align {count_corrected_bad_frames()} of them.\r\n"
                            "Are you sure you want to delete this info?"):
            # To prevent losses, if a relevent number of bad frames exist, save to a file with timestamp
            if len(bad_frame_list) > 20:
                save_bad_frame_list(True)
            bad_frame_list.clear()
            current_bad_frame_index = -1
            FrameSync_Viewer_popup_refresh()
            # Also delete file where frames are saved
            if os.path.isfile(get_bad_frame_list_filename()):
                os.remove(get_bad_frame_list_filename())
            for filename in glob(get_bad_frame_list_filename(with_timestamp=True, with_wildcards=True)):
                if os.path.isfile(filename):
                    os.remove(filename)
        else:
            retvalue = False
    return retvalue


def delete_current_bad_frame_info():
    global current_bad_frame_index, StabilizationThreshold
    # bad_frame_list elements = Frame index, x offset, y offset, stabilization threshold, is frame saved)
    if current_bad_frame_index != -1:
        bad_frame_list[current_bad_frame_index]['x'] = 0
        bad_frame_list[current_bad_frame_index]['y'] = 0
        bad_frame_list[current_bad_frame_index]['threshold'] = bad_frame_list[current_bad_frame_index]['original_threshold']
        bad_frame_list[current_bad_frame_index]['is_frame_saved'] = False
        FrameSync_Viewer_popup_refresh()


def find_closest(sorted_list, target):
    # Check if the list is empty
    if not sorted_list:
        return None

    # Initialize the left and right pointers
    left, right = 0, len(sorted_list) - 1
    
    # If the target is less than or equal to the smallest element or greater than or equal to the largest element
    if target <= sorted_list[left]:
        return sorted_list[left]
    if target >= sorted_list[right]:
        return sorted_list[right]

    # Binary search-like approach
    while left <= right:
        mid = (left + right) // 2
        if sorted_list[mid] == target:
            return sorted_list[mid]
        elif sorted_list[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    # After the while loop, left will be where we insert target to keep the list sorted
    # Check if the target is closer to the element at 'left' or 'right'
    if abs(sorted_list[left] - target) < abs(sorted_list[right] - target):
        return sorted_list[left]
    else:
        return sorted_list[right]
    

def insert_or_replace_sorted(sorted_list, new_inner_dict, key='frame_idx'):
    """
    Insert a new inner dictionary into a sorted list of dictionaries, maintaining order based on the specified key.
    If the key value already exists, replace the existing dictionary with the new one.

    Args:
        sorted_list (list): A sorted list of dictionaries.
        new_inner_dict (dict): The new dictionary to insert or replace with.
        key (str): The key to use for sorting and matching (default: 'frame_number').

    Returns:
        None: Modifies sorted_list in place.
    """
    if not sorted_list:
        sorted_list.append(new_inner_dict)
        return

    target = new_inner_dict[key]  # The key value to match or insert
    left, right = 0, len(sorted_list) - 1

    # Binary search to find the position
    while left <= right:
        mid = (left + right) // 2
        current_index = sorted_list[mid][key]

        if current_index == target:
            # Replace the existing dictionary with the new one
            sorted_list[mid] = new_inner_dict
            return
        elif current_index < target:
            left = mid + 1
        else:
            right = mid - 1

    # If no match found, insert at the correct position
    sorted_list.insert(left, new_inner_dict)

def FrameSync_Viewer_popup_refresh():
    global CurrentFrame, current_bad_frame_index

    if not FrameSync_Viewer_opened or ConvertLoopRunning:    # Nothing to refresh
        return  
    
    if current_bad_frame_index == -1 and len(bad_frame_list) > 0:
        current_bad_frame_index = 0

    if len(bad_frame_list) > 0:
        CurrentFrame = bad_frame_list[current_bad_frame_index]['frame_idx']
        x = bad_frame_list[current_bad_frame_index]['x']
        y = bad_frame_list[current_bad_frame_index]['y']
    else:
        x = 0
        y = 0
    project_config["CurrentFrame"] = CurrentFrame
    refresh_current_frame_ui_info(CurrentFrame, first_absolute_frame)
    frame_selected.set(CurrentFrame)
    frame_slider.set(CurrentFrame)
    scale_display_update(False, x, y)

    bad_frame_text.set(f"Misaligned frames: {len(bad_frame_list)}")
    corrected_bad_frame_text.set(f"Corrected frames: {count_corrected_bad_frames()}")
    bad_frames_on_left_value.set(current_bad_frame_index if current_bad_frame_index != -1 else 0)
    if len(bad_frame_list) > 0:
        bad_frames_on_right_value.set((len(bad_frame_list)-current_bad_frame_index-1) if current_bad_frame_index != -1 else 0)
        threshold_value.set(bad_frame_list[current_bad_frame_index]['threshold'])
    else:
        bad_frames_on_right_value.set(0)
        threshold_value.set(0)

    debug_template_refresh_template()


def display_bad_frame_previous(count, skip_minor = False):
    global current_bad_frame_index, StabilizationThreshold
    if current_bad_frame_index == -1:
        return
    while current_bad_frame_index > 0:
        current_bad_frame_index -= count
        if current_bad_frame_index < 0:
            current_bad_frame_index = 0
            break
        if not skip_minor:
            break
        else:
            if 'match_level' not in bad_frame_list[current_bad_frame_index] or bad_frame_list[current_bad_frame_index]['match_level'] < 0.8:
                break
    StabilizationThreshold = bad_frame_list[current_bad_frame_index]['threshold']
    refresh_current_frame_ui_info(current_bad_frame_index, first_absolute_frame)
    FrameSync_Viewer_popup_refresh()
    debug_template_refresh_template()


def display_bad_frame_previous_1(event = None):
    if event is not None:
        state = event.state
    else:
        state = 0
    display_bad_frame_previous(1, bool(state & 0x0004)) # If Control skip minor displacements


def display_bad_frame_previous_10(event = None):
    display_bad_frame_previous(10)


def display_bad_frame_next(count, skip_minor = False):
    global current_bad_frame_index, StabilizationThreshold
    if current_bad_frame_index == -1:
        return
    while current_bad_frame_index < len(bad_frame_list)-1:
        current_bad_frame_index += count
        if current_bad_frame_index >= len(bad_frame_list):
            current_bad_frame_index = len(bad_frame_list) - 1
            break
        if not skip_minor:
            break
        else:
            if 'match_level' not in bad_frame_list[current_bad_frame_index] or bad_frame_list[current_bad_frame_index]['match_level'] < 0.8:
                break
    StabilizationThreshold = bad_frame_list[current_bad_frame_index]['threshold']
    refresh_current_frame_ui_info(current_bad_frame_index, first_absolute_frame)
    FrameSync_Viewer_popup_refresh()
    debug_template_refresh_template()


def display_bad_frame_next_1(event = None):
    if event is not None:
        state = event.state
    else:
        state = 0
    display_bad_frame_next(1, bool(state & 0x0004)) # If Control skip minor displacements


def display_bad_frame_next_10(event = None):
    display_bad_frame_next(10)


def frame_shift_step_value(state):
    displacement = 100   # Default displacement with keyboard
    if bool(state & 0x0004):   # Control
        displacement = 20
    elif bool(state & 0x0001):  # Shift
        displacement = 5    # Shift used to fine tune (I have seen it elsewhere)
    return displacement


def shift_bad_frame_up(event = None):
    global current_bad_frame_index

    if current_bad_frame_index == -1:
        return
    
    if event == None:
        displacement = 5
    else:
        displacement = frame_shift_step_value(event.state)

    # If moving image manually, reset threshold to origial value
    bad_frame_list[current_bad_frame_index]['threshold'] = bad_frame_list[current_bad_frame_index]['original_threshold']
    bad_frame_list[current_bad_frame_index]['y'] -= displacement
    frame_encode(CurrentFrame, -1, False, bad_frame_list[current_bad_frame_index]['x'], bad_frame_list[current_bad_frame_index]['y'])
    bad_frame_list[current_bad_frame_index]['is_frame_saved'] = False # Just modified, reset saved flag
    pos_after_text.set(f"{bad_frame_list[current_bad_frame_index]['x']}, {bad_frame_list[current_bad_frame_index]['y']}")
    threshold_after_text.set(f"Ts:{bad_frame_list[current_bad_frame_index]['threshold']}")


def shift_bad_frame_down(event = None):
    global current_bad_frame_index

    if current_bad_frame_index == -1:
        return
    
    if event == None:
        displacement = 5
    else:
        displacement = frame_shift_step_value(event.state)

    # If moving image manually, reset threshold to origial value
    bad_frame_list[current_bad_frame_index]['threshold'] = bad_frame_list[current_bad_frame_index]['original_threshold']
    bad_frame_list[current_bad_frame_index]['y'] += displacement
    frame_encode(CurrentFrame, -1, False, bad_frame_list[current_bad_frame_index]['x'], bad_frame_list[current_bad_frame_index]['y'])
    bad_frame_list[current_bad_frame_index]['is_frame_saved'] = False # Just modified, reset saved flag
    pos_after_text.set(f"{bad_frame_list[current_bad_frame_index]['x']}, {bad_frame_list[current_bad_frame_index]['y']}")
    threshold_after_text.set(f"Ts:{bad_frame_list[current_bad_frame_index]['threshold']}")


def shift_bad_frame_left(event = None):
    global current_bad_frame_index

    if current_bad_frame_index == -1:
        return
    
    if event == None:
        displacement = 5
    else:
        displacement = frame_shift_step_value(event.state)

    # If moving image manually, reset threshold to origial value
    bad_frame_list[current_bad_frame_index]['threshold'] = bad_frame_list[current_bad_frame_index]['original_threshold']
    bad_frame_list[current_bad_frame_index]['x'] -= displacement
    frame_encode(CurrentFrame, -1, False, bad_frame_list[current_bad_frame_index]['x'], bad_frame_list[current_bad_frame_index]['y'])
    bad_frame_list[current_bad_frame_index]['is_frame_saved'] = False # Just modified, reset saved flag
    pos_after_text.set(f"{bad_frame_list[current_bad_frame_index]['x']}, {bad_frame_list[current_bad_frame_index]['y']}")
    threshold_after_text.set(f"Ts:{bad_frame_list[current_bad_frame_index]['threshold']}")


def shift_bad_frame_right(event = None):
    global current_bad_frame_index

    if current_bad_frame_index == -1:
        return
    
    if event == None:
        displacement = 5
    else:
        displacement = frame_shift_step_value(event.state)

    # If moving image manually, reset threshold to origial value
    bad_frame_list[current_bad_frame_index]['threshold'] = bad_frame_list[current_bad_frame_index]['original_threshold']
    bad_frame_list[current_bad_frame_index]['x'] += displacement
    frame_encode(CurrentFrame, -1, False, bad_frame_list[current_bad_frame_index]['x'], bad_frame_list[current_bad_frame_index]['y'])
    bad_frame_list[current_bad_frame_index]['is_frame_saved'] = False # Just modified, reset saved flag
    pos_after_text.set(f"{bad_frame_list[current_bad_frame_index]['x']}, {bad_frame_list[current_bad_frame_index]['y']}")
    threshold_after_text.set(f"Ts:{bad_frame_list[current_bad_frame_index]['threshold']}")


def count_corrected_bad_frames():
    count = 0
    for bad_frame in bad_frame_list:
        if not bad_frame['is_frame_saved']:   # If offset modified, but not saved
            count += 1
    return count


def frame_threshold_step_value(state):
    displacement = 25   # Default displacement with keyboard
    if bool(state & 0x0004):   # Control
        displacement = 10
    elif bool(state & 0x0001):  # Shift
        displacement = 1    # Shift used to fine tune (I have seen it elsewhere)
    return displacement


def bad_frames_increase_threshold(value):
    global StabilizationThreshold

    if current_bad_frame_index == -1:
        return

    # If changing threshold manually, reset manual shifts to zero
    bad_frame_list[current_bad_frame_index]['x'] = 0
    bad_frame_list[current_bad_frame_index]['y'] = 0
    save_thres = StabilizationThreshold
    bad_frame_list[current_bad_frame_index]['threshold'] += float(value)
    if (bad_frame_list[current_bad_frame_index]['threshold'] >= 255):
        bad_frame_list[current_bad_frame_index]['threshold'] = 254.0
    StabilizationThreshold = bad_frame_list[current_bad_frame_index]['threshold']
    threshold_value.set(StabilizationThreshold)
    frame_encode(CurrentFrame, -1, False, 0, 0)
    bad_frame_list[current_bad_frame_index]['is_frame_saved'] = False
    StabilizationThreshold = save_thres
    pos_after_text.set(f"0, 0")
    threshold_after_text.set(f"Ts:{bad_frame_list[current_bad_frame_index]['threshold']}")
    

def bad_frames_increase_threshold_n(event = None):
    if event == None:
        step = 1
    else:
        step = frame_threshold_step_value(event.state)
    bad_frames_increase_threshold(step)


def bad_frames_increase_threshold_5(event = None):
    bad_frames_increase_threshold(5)


def bad_frames_decrease_threshold(value):
    global StabilizationThreshold

    if current_bad_frame_index == -1:
        return

    # If changing threshold manually, reset manual shifts to zero
    bad_frame_list[current_bad_frame_index]['x'] = 0
    bad_frame_list[current_bad_frame_index]['y'] = 0
    save_thres = StabilizationThreshold
    bad_frame_list[current_bad_frame_index]['threshold'] -= float(value)
    if (bad_frame_list[current_bad_frame_index]['threshold'] < 0):
        bad_frame_list[current_bad_frame_index]['threshold'] = 0.0
    StabilizationThreshold = bad_frame_list[current_bad_frame_index]['threshold']
    threshold_value.set(StabilizationThreshold)
    frame_encode(CurrentFrame, -1, False, 0, 0)
    bad_frame_list[current_bad_frame_index]['is_frame_saved'] = False
    StabilizationThreshold = save_thres
    pos_after_text.set(f"0, 0")
    threshold_after_text.set(f"Ts:{bad_frame_list[current_bad_frame_index]['threshold']}")


def bad_frames_decrease_threshold_n(event=None):
    if event == None:
        step = 1
    else:
        step = frame_threshold_step_value(event.state)
    bad_frames_decrease_threshold(step)


def bad_frames_decrease_threshold_5(event = None):
    bad_frames_decrease_threshold(5)


def set_high_sensitive_bad_frame_detection():
    global high_sensitive_bad_frame_detection
    high_sensitive_bad_frame_detection = high_sensitive_bad_frame_detection_value.get()


def set_stabilization_bounds_alert():
    global stabilization_bounds_alert
    stabilization_bounds_alert = stabilization_bounds_alert_value.get()


def set_precise_template_match():
    global precise_template_match
    precise_template_match = precise_template_match_value.get()


def FrameSync_Viewer_popup_update_widgets(status, except_save=False):
    if not FrameSync_Viewer_opened:
        return
    frame_up_button.config(state=status)
    frame_left_button.config(state=status)
    frame_down_button.config(state=status)
    frame_right_button.config(state=status)
    next_frame_button_1.config(state=status)
    next_frame_button_10.config(state=status)
    previous_frame_button_1.config(state=status)
    previous_frame_button_10.config(state=status)
    bad_frames_on_left_label.config(state=status)
    bad_frames_on_right_label.config(state=status)
    decrease_threshold_button_5.config(state=status)
    decrease_threshold_button_1.config(state=status)
    threshold_label.config(state=status)
    increase_threshold_button_1.config(state=status)
    increase_threshold_button_5.config(state=status)
    delete_bad_frames_button.config(state=status)
    delete_current_bad_frame_button.config(state=status)
    high_sensitive_bad_frame_detection_checkbox.config(state=status)
    # Do not disable alert checkbox to give a chance to stop the alerts without stopping the encoding
    # stabilization_bounds_alert_checkbox.config(state=status)
    # precise_template_match_checkbox.config(state=status)
    close_button.config(state=status)
    if not except_save:
        save_button.config(state=status)

def FrameSync_Viewer_popup():
    global win
    global template_list
    global template_popup_window
    global CropTopLeft, CropBottomRight
    global FrameSync_Viewer_opened, debug_template_width, debug_template_height
    global current_frame_text, crop_text, film_type_text
    global search_area_text, template_type_text, hole_pos_text, template_size_text, template_wb_proportion_text, template_threshold_text
    global left_stripe_canvas, left_stripe_stabilized_canvas, template_canvas
    global SourceDirFileList, CurrentFrame
    global bad_frame_text, corrected_bad_frame_text, bad_frames_on_left_value, bad_frames_on_right_value
    global frame_up_button, frame_left_button, frame_down_button, frame_right_button
    global next_frame_button_1, next_frame_button_10, previous_frame_button_1, previous_frame_button_10, save_button, close_button
    global bad_frames_on_left_label, bad_frames_on_right_label
    global current_bad_frame_index
    global StabilizationThreshold_default, threshold_value
    global decrease_threshold_button_1, threshold_label, increase_threshold_button_1
    global decrease_threshold_button_5, increase_threshold_button_5
    global delete_bad_frames_button, delete_current_bad_frame_button
    global high_sensitive_bad_frame_detection_checkbox, high_sensitive_bad_frame_detection_value
    global precise_template_match_checkbox, precise_template_match_value
    global precise_template_match, high_sensitive_bad_frame_detection
    global stabilization_bounds_alert, stabilization_bounds_alert_value, stabilization_bounds_alert_checkbox
    global StabilizationThreshold
    global pos_before_text, pos_after_text, threshold_before_text, threshold_after_text

    Terminate = False
    if FrameSync_Viewer_opened: # Already opened, user wants to close
        FrameSync_Viewer_opened = False # Set to false first, to avoid interactions with deleted elements
        StabilizationThreshold = StabilizationThreshold_default   # Restore original value
        general_config["TemplatePopupWindowPos"] = template_popup_window.geometry()
        template_canvas.destroy()
        left_stripe_canvas.destroy()
        left_stripe_stabilized_canvas.destroy()
        template_popup_window.destroy()
        # Release button
        display_template_popup_btn.config(relief=RAISED)
        return

    # Push button
    display_template_popup_btn.config(relief=SUNKEN)

    StabilizationThreshold_default = StabilizationThreshold   # To be restored on exit

    template_popup_window = Toplevel(win)
    template_popup_window.title("FrameSync Editor")
    # Intercept window close (X button)
    template_popup_window.protocol("WM_DELETE_WINDOW", FrameSync_Viewer_popup)

    template_popup_window.minsize(width=300, height=template_popup_window.winfo_height())

    if 'TemplatePopupWindowPos' in general_config:
        template_popup_window.geometry(f"+{general_config['TemplatePopupWindowPos'].split('+', 1)[1]}")

    # Create three vertical frames in the bottom horizontal frame
    left_frame = Frame(template_popup_window, width=60, height=8)
    left_frame.pack(side=LEFT)
    center_left_frame = Frame(template_popup_window, width=160, height=8)
    center_left_frame.pack(side=LEFT)
    center_right_frame = Frame(template_popup_window, width=60, height=8)
    center_right_frame.pack(side=LEFT)
    right_frame = Frame(template_popup_window, width=280, height=8)
    right_frame.pack(side=LEFT)
    # Add a label and a close button to the popup window
    #label = Label(left_frame, text="Current template:")
    #label.pack(pady=5, padx=10, anchor=W)

    # Frame sync image size factor precalculated when loading frames
    active_template = template_list.get_active_template()
    aux = resize_image(active_template, FrameSync_Images_Factor)
    template_canvas_height = int(frame_height*FrameSync_Images_Factor)
    debug_template_width = aux.shape[1]
    debug_template_height = aux.shape[0]
    # Set expected hole template pos
    hole_template_pos = template_list.get_active_position()

    # Create Canvas to display template
    template_canvas = Canvas(left_frame, bg='dark grey',
                                 width=debug_template_width, height=template_canvas_height)
    template_canvas.pack(side=TOP, anchor=N)
    as_tooltips.add(template_canvas, "Active template used to locate sprocket hole(s)")

    DisplayableImage = ImageTk.PhotoImage(Image.fromarray(aux))
    template_canvas.image_id = template_canvas.create_image(0, 0, anchor=NW, image=DisplayableImage)
    template_canvas.coords(template_canvas.image_id, 0, int((hole_template_pos[1] + stabilization_shift_y_value.get()) *FrameSync_Images_Factor))
    template_canvas.image = DisplayableImage
    template_canvas.item_ids = []

    # Create Canvas to display image left stripe (stabilized)
    left_stripe_stabilized_canvas = Canvas(center_left_frame, bg='dark grey',
                                 width=debug_template_width, height=debug_template_height)
    left_stripe_stabilized_canvas.pack(side=TOP, anchor=N)
    left_stripe_stabilized_canvas.image = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0))) #create a transparent 1x1 image.
    left_stripe_stabilized_canvas.image_id = left_stripe_stabilized_canvas.create_image(0, 0, anchor=tk.NW, image=left_stripe_stabilized_canvas.image)
    as_tooltips.add(left_stripe_stabilized_canvas, "Current frame after stabilization, with detected template highlighted in green, orange or red depending on the quality of the match")

    # Create Canvas to display image left stripe (non stabilized)
    left_stripe_canvas = Canvas(center_right_frame, bg='dark grey',
                                 width=debug_template_width, height=debug_template_height)
    left_stripe_canvas.pack(side=TOP, anchor=N)
    left_stripe_canvas.image = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0))) #create a transparent 1x1 image.
    left_stripe_canvas.image_id = left_stripe_canvas.create_image(0, 0, anchor=tk.NW, image=left_stripe_canvas.image)
    as_tooltips.add(left_stripe_canvas, "Template search area for current frame before stabilization, used to find template")

    # Add a label with the film type
    film_type_text = tk.StringVar()
    film_type_label = Label(right_frame, textvariable=film_type_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        film_type_label.forget()
    else:
        film_type_label.pack(pady=5, padx=10, anchor="center")
    film_type_text.set(f"Film type: {film_type.get()}")
    as_tooltips.add(film_type_label, "Type of film currentyl loaded")

    # Add a label with the cropping dimensions
    crop_text = tk.StringVar()
    crop_label = Label(right_frame, textvariable=crop_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        crop_label.forget()
    else:
        crop_label.pack(pady=5, padx=10, anchor="center")
    crop_text.set(f"Crop: {CropTopLeft}, {CropBottomRight}")
    as_tooltips.add(crop_label, "Current cropping coordinates")

    # Add a label with the template type
    template_type_text = tk.StringVar()
    template_type_label = Label(right_frame, textvariable=template_type_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        template_type_label.forget()
    else:
        template_type_label.pack(pady=5, padx=10, anchor="center")
    template_type_text.set(f"Template type: {template_list.get_active_type()}")
    as_tooltips.add(template_type_label, "Current template type being used to stabilize frames")

    # Add a label with the stabilization info
    hole_pos_text = tk.StringVar()
    hole_pos_label = Label(right_frame, textvariable=hole_pos_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        hole_pos_label.forget()
    else:
        hole_pos_label.pack(pady=5, padx=10, anchor="center")
    hole_pos_text.set(f"Expected template pos: {hole_template_pos}")
    as_tooltips.add(hole_pos_label, "Position where the template is expected")

    #Label with template size
    template_size_text = tk.StringVar()
    template_size_label = Label(right_frame, textvariable=template_size_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        template_size_label.forget()
    else:
        template_size_label.pack(pady=5, padx=10, anchor="center")
    template_size_text.set(f"Template Size: {template_list.get_active_size()}")
    as_tooltips.add(template_size_label, "Size of current template")

    '''
    #Label with template white on black proportion
    template_wb_proportion_text = tk.StringVar()
    template_wb_proportion_label = Label(right_frame, textvariable=template_wb_proportion_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        template_wb_proportion_label.forget()
    else:
        template_wb_proportion_label.pack(pady=5, padx=10, anchor="center")
    template_wb_proportion_text.set(f"WoB proportion: {int(template_list.get_active_wb_proportion() * 100)}%")
    '''

    #Label with template white on black proportion
    template_threshold_text = tk.StringVar()
    template_threshold_label = Label(right_frame, textvariable=template_threshold_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        template_threshold_label.forget()
    else:
        template_threshold_label.pack(pady=5, padx=10, anchor="center")
    template_threshold_text.set("Threshold: 0")
    as_tooltips.add(template_threshold_label, "Threshold used to match template")

    #Label with search area
    search_area_text = tk.StringVar()
    search_area_label = Label(right_frame, textvariable=search_area_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        search_area_label.forget()
    else:
        search_area_label.pack(pady=5, padx=10, anchor="center")
    search_area_text.set(f"Search Area: {HoleSearchTopLeft}, {HoleSearchBottomRight})")
    as_tooltips.add(search_area_label, "Area where template will be searched")

    #Label with current Frame details
    current_frame_text = tk.StringVar()
    current_frame_label = Label(right_frame, textvariable=current_frame_text, width=45, font=("Arial", FontSize))
    if not dev_debug_enabled:
        current_frame_label.forget()
    else:
        current_frame_label.pack(pady=5, padx=10, anchor="center")
    current_frame_text.set("Current:")
    as_tooltips.add(current_frame_label, "Current frame details")

    #Label with bad Frame count
    bad_frame_text = tk.StringVar()
    bad_frame_label = Label(right_frame, textvariable=bad_frame_text, width=45, font=("Arial", FontSize))
    bad_frame_label.pack(pady=5, padx=10, anchor="center")
    bad_frame_text.set("Misaligned frames:")
    as_tooltips.add(bad_frame_label, "Number of frames that failed to be stabilized")

    #Label with bad Frames modified
    corrected_bad_frame_text = tk.StringVar()
    corrected_bad_frame_label = Label(right_frame, textvariable=corrected_bad_frame_text, width=45, font=("Arial", FontSize))
    corrected_bad_frame_label.pack(pady=5, padx=10, anchor="center")
    corrected_bad_frame_text.set("Corrected frames:")
    as_tooltips.add(corrected_bad_frame_label, "Number of frames not properly stabilized, that have been manually adjusted")

    # Checkbox to allow high sensitive detencion (match < 0.9)
    precise_template_match_value = tk.BooleanVar(value=precise_template_match)
    precise_template_match_checkbox = tk.Checkbutton(right_frame,
                                                         text='High-Accuracy Alignment',
                                                         variable=precise_template_match_value,
                                                         command=set_precise_template_match,
                                                         onvalue=True, offvalue=False,
                                                         width=40, font=("Arial", FontSize))
    precise_template_match_checkbox.pack(pady=5, padx=10, anchor="center")
    as_tooltips.add(precise_template_match_checkbox, "Activate high accuracy template detection for better stabilization (implies slower encoding)")

    # Checkbox to allow high sensitive detencion (match < 0.9)
    high_sensitive_bad_frame_detection_value = tk.BooleanVar(value=high_sensitive_bad_frame_detection)
    high_sensitive_bad_frame_detection_checkbox = tk.Checkbutton(right_frame,
                                                         text='Enhanced Sensitivity Detection',
                                                         variable=high_sensitive_bad_frame_detection_value,
                                                         command=set_high_sensitive_bad_frame_detection,
                                                         onvalue=True, offvalue=False,
                                                         width=40, font=("Arial", FontSize))
    high_sensitive_bad_frame_detection_checkbox.pack(pady=5, padx=10, anchor="center")
    as_tooltips.add(high_sensitive_bad_frame_detection_checkbox, "Besides frames clearly misaligned, detect also slightly misaligned frames")

    # Checkbox - Beep if stabilization forces image out of cropping bounds
    stabilization_bounds_alert_value = tk.BooleanVar(value=stabilization_bounds_alert)
    stabilization_bounds_alert_checkbox = tk.Checkbutton(right_frame,
                                                         text='Beep when misaligned frame detected',
                                                         variable=stabilization_bounds_alert_value,
                                                         command=set_stabilization_bounds_alert,
                                                         onvalue=True, offvalue=False,
                                                         width=40, font=("Arial", FontSize))
    stabilization_bounds_alert_checkbox.pack(pady=5, padx=10, anchor="center")
    as_tooltips.add(stabilization_bounds_alert_checkbox, "Beep each time a misaligned frame is detected")

    # Frame for manual alignment buttons 
    frame_selection_frame = LabelFrame(right_frame, text="Misaligned frame selection") #, width=50, height=50)
    frame_selection_frame.pack(anchor="center", pady=5, padx=10)   # expand=True, fill="both", 

    #Label with bad frames to the left
    bad_frames_on_left_value = tk.IntVar()
    bad_frames_on_left_label = Label(frame_selection_frame, textvariable=bad_frames_on_left_value, font=("Arial", FontSize+6))
    bad_frames_on_left_label.grid(pady=2, padx=10, row=0, column=0, rowspan = 2)
    bad_frames_on_left_value.set(0)
    as_tooltips.add(bad_frames_on_left_label, "Number of badly-stabilized frames before the one currently selected")

    previous_frame_button_10 = Button(frame_selection_frame, text="◀◀", command=display_bad_frame_previous_10, font=("Arial", FontSize), width=3)
    previous_frame_button_10.grid(pady=2, padx=2, row=0, column=1)
    as_tooltips.add(previous_frame_button_10, "Select previous badly-stabilized frame")

    previous_frame_button_1 = Button(frame_selection_frame, text="◀", command=display_bad_frame_previous_1, font=("Arial", FontSize), width=3)
    previous_frame_button_1.grid(pady=2, padx=2, row=0, column=2)
    as_tooltips.add(previous_frame_button_1, "Select previous badly-stabilized frame (or press PgUp, +Ctrl to previous frame with deviation > 5 pixels)")

    next_frame_button_1 = Button(frame_selection_frame, text="▶", command=display_bad_frame_next_1, font=("Arial", FontSize), width=3)
    next_frame_button_1.grid(pady=2, padx=2, row=0, column=3)
    as_tooltips.add(next_frame_button_1, "Select next badly-stabilized frame (or press PgDn, +Ctrl to find next frame with deviation > 5 pixels)")

    next_frame_button_10 = Button(frame_selection_frame, text="▶▶", command=display_bad_frame_next_10, font=("Arial", FontSize), width=3)
    next_frame_button_10.grid(pady=2, padx=2, row=0, column=4)
    as_tooltips.add(next_frame_button_10, "Select next badly-stabilized frame")

    # Bind Page Up and Page Down
    template_popup_window.bind("<Prior>", display_bad_frame_previous_1)  # Page Up
    template_popup_window.bind("<Next>", display_bad_frame_next_1) # Page Down

    #Label with bad frames to the left
    bad_frames_on_right_value = tk.IntVar()
    bad_frames_on_right_label = Label(frame_selection_frame, textvariable=bad_frames_on_right_value, font=("Arial", FontSize+6))
    bad_frames_on_right_label.grid(pady=2, padx=10, row=0, column=5, rowspan = 2)
    bad_frames_on_right_value.set(0)
    as_tooltips.add(bad_frames_on_right_label, "Number of badly-stabilized frames after the one currently selected")

    # Frame for Threshold adjustment buttons 
    manual_threshold_frame = LabelFrame(right_frame, text="Manual threshold controls") #, width=50, height=50)
    manual_threshold_frame.pack(anchor="center", pady=5, padx=10)   # expand=True, fill="both", 

    decrease_threshold_button_5 = Button(manual_threshold_frame, text="◀◀", command=bad_frames_decrease_threshold_5, font=("Arial", FontSize))
    decrease_threshold_button_5.pack(pady=10, padx=10, side=LEFT, anchor="center")
    as_tooltips.add(decrease_threshold_button_5, "Decrease threshold value by 5 (or press home)")

    decrease_threshold_button_1 = Button(manual_threshold_frame, text="◀", command=bad_frames_decrease_threshold_n, font=("Arial", FontSize))
    decrease_threshold_button_1.pack(pady=10, padx=10, side=LEFT, anchor="center")
    as_tooltips.add(decrease_threshold_button_1, "Decrease threshold value by 1")

    #Label with threshold value
    threshold_value = tk.IntVar()
    threshold_label = Label(manual_threshold_frame, textvariable=threshold_value, font=("Arial", FontSize+6))
    threshold_label.pack(pady=10, padx=10, side=LEFT, anchor="center")
    threshold_value.set(StabilizationThreshold)
    as_tooltips.add(threshold_label, "Current threshold")

    increase_threshold_button_1 = Button(manual_threshold_frame, text="▶", command=bad_frames_increase_threshold_n, font=("Arial", FontSize))
    increase_threshold_button_1.pack(pady=10, padx=10, side=LEFT, anchor="center")
    as_tooltips.add(increase_threshold_button_1, "Increase threshold value by 1")

    increase_threshold_button_5 = Button(manual_threshold_frame, text="▶▶", command=bad_frames_increase_threshold_5, font=("Arial", FontSize))
    increase_threshold_button_5.pack(pady=10, padx=10, side=LEFT, anchor="center")
    as_tooltips.add(increase_threshold_button_1, "Increase threshold value by 5 (or press end)")

    # Bind Page Up and Page Down
    template_popup_window.bind("<Home>", bad_frames_decrease_threshold_n)
    template_popup_window.bind("<End>", bad_frames_increase_threshold_n)

    # Frame for manual alignment buttons + before/after values
    before_after_frame = Frame(right_frame) 
    before_after_frame.pack(anchor="center", pady=5, padx=10)

    # Frame for before values
    values_before_frame = LabelFrame(before_after_frame, text="Original values")
    values_before_frame.pack(side=LEFT, pady=5, padx=10)
    
    pos_before_text = tk.StringVar()
    pos_before_text_label = Label(values_before_frame, textvariable=pos_before_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        pos_before_text_label.forget()
    else:
        pos_before_text_label.pack(side=TOP, pady=5, padx=10, anchor="center")
    pos_before_text.set("Pos: 0,0")
    # as_tooltips.add(pos_before_text_label, "TBD")
    threshold_before_text = tk.StringVar()
    threshold_before_text_label = Label(values_before_frame, textvariable=threshold_before_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        threshold_before_text_label.forget()
    else:
        threshold_before_text_label.pack(side=TOP, pady=5, padx=10, anchor="center")
    threshold_before_text.set("Thres: 0")
    # as_tooltips.add(threshold_before_text_label, "TBD")

    # Frame for manual alignment buttons 
    manual_position_frame = LabelFrame(before_after_frame, text="Manual frame shift controls")
    manual_position_frame.pack(side=LEFT, pady=5, padx=10)  

    frame_up_button = Button(manual_position_frame, text="▲", command=shift_bad_frame_up, font=("Arial", FontSize), width=3)
    frame_up_button.grid(pady=2, padx=2, row=0, column=2)
    as_tooltips.add(frame_up_button, "Move current frame 1 pixel up (use cursor keys to move 20 pixels (10 with Ctrl, 5 with shift)")
    frame_left_button = Button(manual_position_frame, text="◀", command=shift_bad_frame_left, font=("Arial", FontSize), width=3)
    frame_left_button.grid(pady=2, padx=2, row=1, column=1)
    as_tooltips.add(frame_left_button, "Move current frame 1 pixel to the left (use cursor keys to move 20 pixels (10 with Ctrl, 5 with shift))")
    frame_down_button = Button(manual_position_frame, text="▼", command=shift_bad_frame_down, font=("Arial", FontSize), width=3)
    frame_down_button.grid(pady=2, padx=2, row=1, column=2)
    as_tooltips.add(frame_down_button, "Move current frame 1 pixel down (use cursor keys to move 20 pixels (10 with Ctrl, 5 with shift))")
    frame_right_button = Button(manual_position_frame, text="▶", command=shift_bad_frame_right, font=("Arial", FontSize), width=3)
    frame_right_button.grid(pady=2, padx=2, row=1, column=3)
    as_tooltips.add(frame_right_button, "Move current frame 1 pixel to the right (use cursor keys to move 20 pixels (10 with Ctrl, 5 with shift)")
    template_popup_window.bind("<Up>", shift_bad_frame_up)
    template_popup_window.bind("<Down>", shift_bad_frame_down)
    template_popup_window.bind("<Left>", shift_bad_frame_left)
    template_popup_window.bind("<Right>", shift_bad_frame_right)

    # Frame for after values
    values_after_frame = LabelFrame(before_after_frame, text="Modified values")
    values_after_frame.pack(side=LEFT, pady=5, padx=10)

    pos_after_text = tk.StringVar()
    pos_after_text_label = Label(values_after_frame, textvariable=pos_after_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        pos_after_text_label.forget()
    else:
        pos_after_text_label.pack(side=TOP, pady=5, padx=10, anchor="center")
    pos_after_text.set("Pos: 0,0")
    # as_tooltips.add(pos_after_text_label, "TBD")
    threshold_after_text = tk.StringVar()
    threshold_after_text_label = Label(values_after_frame, textvariable=threshold_after_text, font=("Arial", FontSize))
    if not dev_debug_enabled:
        threshold_after_text_label.forget()
    else:
        threshold_after_text_label.pack(side=TOP, pady=5, padx=10, anchor="center")
    threshold_after_text.set("Thres: 0")
    # as_tooltips.add(threshold_after_text_label, "TBD")

    # Frame for delete info buttons 
    delete_info_frame = Frame(right_frame)
    delete_info_frame.pack(anchor="center", pady=5, padx=10)   # expand=True, fill="both", 

    # Frame info delete all button
    delete_bad_frames_button = Button(delete_info_frame, text="Delete all collected frame info", command=delete_detected_bad_frames, font=("Arial", FontSize))
    delete_bad_frames_button.pack(pady=10, padx=10, side=LEFT, anchor="center")
    as_tooltips.add(delete_bad_frames_button, "Delete all the information collected about misaligned frames, along with any changes you have made.")

    # Frame info delete current button
    delete_current_bad_frame_button = Button(delete_info_frame, text="Delete current frame info", command=delete_current_bad_frame_info, font=("Arial", FontSize))
    delete_current_bad_frame_button.pack(pady=10, padx=10, side=RIGHT, anchor="center")
    as_tooltips.add(delete_current_bad_frame_button, "Delete the edited values for this frame.")
    template_popup_window.bind("<Delete>", delete_current_bad_frame_info)

    # Frame for save/exit buttons
    save_exit_frame = Frame(right_frame)
    save_exit_frame.pack(anchor="center", pady=5, padx=10)

    save_button = Button(save_exit_frame, text="Re-generate corrected frames", command=save_corrected_frames, font=("Arial", FontSize))
    save_button.pack(pady=10, padx=10, side=LEFT, anchor="center")
    as_tooltips.add(save_button, "Generate new frames, with user adjustments, to target folder. Beware!!! Make sure you select 'Skip FrameRegeneration' when generating the video, otherwise the manual adjustement will be lost.")

    close_button = Button(save_exit_frame, text="Close", command=display_template_popup_closure, font=("Arial", FontSize))
    close_button.pack(pady=10, padx=10, side=RIGHT, anchor="center")
    as_tooltips.add(close_button, "Close this window")

    # Initialize bad frame index
    if current_bad_frame_index == -1 and len(bad_frame_list) > 0:
        current_bad_frame_index = 0

    # All widgets already created, we can mark this popup as opened, it is required for following updated
    FrameSync_Viewer_opened = True

    # Refresh popup window
    FrameSync_Viewer_popup_refresh()

    # Refresh template to have the alignment helper lines displayed
    debug_template_refresh_template()

    if ConvertLoopRunning:
        FrameSync_Viewer_popup_update_widgets(DISABLED)

    template_popup_window.resizable(False, False)

    # Run a loop for the popup window
    template_popup_window.wait_window()

    precise_template_match = precise_template_match_value.get()
    general_config["PreciseTemplateMatch"] = precise_template_match
    high_sensitive_bad_frame_detection = high_sensitive_bad_frame_detection_value.get()
    general_config["HighSensitiveBadFrameDetection"] = high_sensitive_bad_frame_detection

    FrameSync_Viewer_opened = False


def debug_template_display_info(frame_idx, threshold, top_left, move_x, move_y):
    if FrameSync_Viewer_opened:
        current_frame_text.set(f"Current Frm:{frame_idx}, Tmp.Pos.:{top_left}, ΔX:{move_x}, ΔY:{move_y}")
        template_threshold_text.set(f"Threshold: {threshold}")
        if ConvertLoopRunning:
            if frame_idx-StartFrame > 0:
                BadFramesPercent = len(bad_frame_list) * 100 / (frame_idx-StartFrame)
            else:
                BadFramesPercent = 0
            bad_frame_text.set(f"Misaligned frames: {len(bad_frame_list)} ({BadFramesPercent:.1f})%")



def debug_template_display_frame_raw(img, x, y, width, height, color):
    global left_stripe_canvas

    if FrameSync_Viewer_opened:
        img = np.stack((img,) * 3, axis=-1)
        debug_template_display_frame(left_stripe_canvas, left_stripe_canvas.image_id, img, x, y, width, height, color)


def debug_template_display_frame_stabilized(img, x, y, width, height, color):
    global left_stripe_stabilized_canvas

    if FrameSync_Viewer_opened:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        left_stripe_stabilized_canvas.config(width=img.shape[1]*FrameSync_Images_Factor)
        debug_template_display_frame(left_stripe_stabilized_canvas, left_stripe_stabilized_canvas.image_id, img, x, y, width, height, color)


def debug_template_refresh_template():
    global template_canvas, template_list
    global hole_pos_text, template_type_text, template_size_text, template_wb_proportion_text, film_type_text

    if FrameSync_Viewer_opened:
        hole_template_pos = template_list.get_active_position()
        # Resize factor calculated when settign source folder
        aux = resize_image(template_list.get_active_template(), FrameSync_Images_Factor)
        _, top, bottom = get_target_position(0, aux, 'v')  # get positions to draw template limits
        template_canvas.config(width=int(template_list.get_active_size()[0]*FrameSync_Images_Factor), height=int(frame_height*FrameSync_Images_Factor))
        DisplayableImage = ImageTk.PhotoImage(Image.fromarray(aux))
        # Delete reference to previous image, if any
        aux_image = None
        if hasattr(template_canvas, 'image'):
            aux_image = template_canvas.image
        template_canvas.image = DisplayableImage #keep reference
        if aux_image is not None:
            del aux_image
        template_canvas.itemconfig(template_canvas.image_id, image=template_canvas.image)
        hole_template_pos = template_list.get_active_position()
        template_canvas.coords(template_canvas.image_id, 0, int((hole_template_pos[1] + stabilization_shift_y_value.get()) *FrameSync_Images_Factor))

        # Delete previous lines before drawing new ones
        for id in template_canvas.item_ids:
            template_canvas.delete(id)
        # Draw a line (start x1, y1, end x2, y2)
        y = int((hole_template_pos[1] + stabilization_shift_y_value.get()) * FrameSync_Images_Factor)
        rectangle_id = template_canvas.create_rectangle(0, y, aux.shape[1], y + aux.shape[0], outline="#00FF00", width=1)
        template_canvas.item_ids.append(rectangle_id)
        if top > 0:
            line_id = template_canvas.create_line(0, y + top, aux.shape[1], y + top, fill="cyan", width=1)
            template_canvas.item_ids.append(line_id)
        if bottom < aux.shape[0]-1:
            line_id = template_canvas.create_line(0, y + bottom, aux.shape[1], y + bottom, fill="cyan", width=1)
            template_canvas.item_ids.append(line_id)
        hole_pos_text.set(f"Expected template pos: {hole_template_pos}")
        template_type_text.set(f"Template type: {template_list.get_active_type()}")
        template_size_text.set(f"Template Size: {template_list.get_active_size()}")
        # template_wb_proportion_text.set(f"WoB proportion: {template_list.get_active_wb_proportion()*100:2.1f}%")
        film_type_text.set(f"Film type: {film_type.get()}")


def debug_template_display_frame(canvas, canvas_image_id, img, x, y, width, height, color):
    global debug_template_width, debug_template_height

    if FrameSync_Viewer_opened:
        try:
            img_height, img_width = img.shape[:2]
            # Resize factor precalculated when loading source folder
            resized_image = cv2.resize(img, (int(img_width*FrameSync_Images_Factor), int(img_height*FrameSync_Images_Factor)))
            # After resize, recalculate coordinates and draw rectangle
            x = int((x + stabilization_shift_x_value.get())*FrameSync_Images_Factor)
            y = int((y + stabilization_shift_y_value.get())*FrameSync_Images_Factor)
            width = int(width*FrameSync_Images_Factor)
            height = int(height*FrameSync_Images_Factor)
            cv2.rectangle(resized_image, (x, y), (x + width, y + height), color, 1)
            pil_image = Image.fromarray(resized_image)
            photo_image = ImageTk.PhotoImage(image=pil_image)
            canvas.config(height=int(img_height*FrameSync_Images_Factor), width=int(img_width*FrameSync_Images_Factor))
            # Delete reference to previous image, if any
            aux_image = None
            if hasattr(canvas, 'image'):
                aux_image = canvas.image
            canvas.image = photo_image
            if aux_image is not None:
                del aux_image
            canvas.itemconfig(canvas_image_id, image=canvas.image)
        except Exception as e:
            logging.error(f"Exception {e} when updating canvas")


def load_current_frame_image():
    # If HDR mode, pick the lightest frame to select rectangle
    file3 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (CurrentFrame + 1, 2, file_type))
    if os.path.isfile(file3):  # If hdr frames exist, add them
        file = file3
    else:
        file = SourceDirFileList[CurrentFrame]
    return cv2.imread(file, cv2.IMREAD_UNCHANGED)


def scale_display_update(update_filters=True, offset_x = 0, offset_y = 0):
    global win
    global frame_scale_refresh_done, frame_scale_refresh_pending
    global CurrentFrame
    global perform_stabilization, perform_cropping, perform_rotation, hole_search_area_adjustment_pending
    global CropTopLeft, CropBottomRight
    global SourceDirFileList

    if CurrentFrame >= len(SourceDirFileList):
        return
    img = load_current_frame_image()
    if img is None:
        frame_scale_refresh_done = True
        logging.error(
            "Error reading frame %i, skipping", CurrentFrame)
    else:
        if hole_search_area_adjustment_pending:
            hole_search_area_adjustment_pending = False
            define_template_search_area(img)
        if not frame_scale_refresh_pending:
            if perform_rotation.get():
                img = rotate_image(img)
            # If FrameSync editor opened, call stabilize_image even when not enabled just to display FrameSync images. Image would not be stabilized
            if perform_stabilization.get() or FrameSync_Viewer_opened: 
                img = stabilize_image(CurrentFrame, img, img, offset_x, offset_y)[0]
            if update_filters:  # Only when changing values in UI, not when moving from frame to frame
                if perform_denoise.get():
                    img = denoise_image(img)
                if perform_sharpness.get():
                    # Sharpness code taken from https://www.educative.io/answers/how-to-sharpen-a-blurred-image-using-opencv
                    sharpen_filter = np.array([[-1, -1, -1],
                                            [-1, 9, -1],
                                            [-1, -1, -1]])
                    # applying kernels to the input image to get the sharpened image
                    img = cv2.filter2D(img, -1, sharpen_filter)
        if perform_gamma_correction.get():  # Unconditionalyl done GC if enabled, otherwise it might be confusing
            img = gamma_correct_image(img, float(gamma_correction_str.get()))
        if perform_cropping.get():
            img = crop_image(img, CropTopLeft, CropBottomRight)
        else:
            img = even_image(img)
        if img is not None and not img.size == 0:   # Just in case img is not well generated
            display_image(img)
        if frame_scale_refresh_pending:
            frame_scale_refresh_pending = False
            win.after(100, scale_display_update, update_filters) # If catching up after too many frames refreshed, las one do the refresh with filters
        else:
            frame_scale_refresh_done = True


def select_scale_frame(selected_frame):
    global win
    global SourceDir
    global CurrentFrame
    global SourceDirFileList
    global first_absolute_frame
    global frame_scale_refresh_done, frame_scale_refresh_pending
    global frame_slider

    if int(selected_frame) >= len(SourceDirFileList):
        selected_frame = str(len(SourceDirFileList) - 1)
    if not ConvertLoopRunning and not BatchJobRunning:  # Do not refresh during conversion loop
        frame_slider.focus()
        CurrentFrame = int(selected_frame)
        project_config["CurrentFrame"] = CurrentFrame
        refresh_current_frame_ui_info(CurrentFrame, first_absolute_frame)
        if frame_scale_refresh_done:
            frame_scale_refresh_done = False
            frame_scale_refresh_pending = False
            if ui_init_done:
                win.after(5, scale_display_update, False)
        else:
            frame_scale_refresh_pending = True


def process_scale_value(event):
    """
    This function is called ONLY when the left mouse button (Button 1)
    is released on the Scale widget.
    """
    # Get the current value from the scale widget
    select_scale_frame(frame_slider.get())
    

################################
# Second level support functions
################################


def get_stabilization_threshold():
    return StabilizationThreshold_default if ConvertLoopRunning else StabilizationThreshold


def detect_film_type():
    global template_list
    global CurrentFrame, SourceDirFileList
    global project_config

    # Initialize work values
    count1 = 0
    count2 = 0
    if project_config["FilmType"] == 'R8':
        template_1 = template_list.get_template('aux','WB')
        template_2 = template_list.get_template('aux','BW')
        other_film_type = 'S8'
    else:  # S8 by default
        template_1 = template_list.get_template('aux','BW')
        template_2 = template_list.get_template('aux','WB')
        other_film_type = 'R8'

    if template_1 is None or template_2 is None:
        logging.debug("Invalid detection templated, cannot determine film type.")
        tk.messagebox.showerror("Film detection failed",
            "Templates to detect film type are missing, please set film type manually.")
        return

    # Create a list with 5 evenly distributed values between CurrentFrame and len(SourceDirFileList) - CurrentFrame
    num_frames = min(10,len(SourceDirFileList)-CurrentFrame)
    FramesToCheck = np.linspace(CurrentFrame, len(SourceDirFileList) - CurrentFrame - 1, num_frames).astype(int).tolist()
    for frame_to_check in FramesToCheck:
        img = cv2.imread(SourceDirFileList[frame_to_check], cv2.IMREAD_UNCHANGED)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_bw = cv2.threshold(img_gray, StabilizationThreshold_default, 255, cv2.THRESH_BINARY)[1]
        search_img = get_image_left_stripe(img_bw, calculated=False)
        result = cv2.matchTemplate(search_img, template_1, cv2.TM_CCOEFF_NORMED)
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(result)
        top_left_1 = (maxLoc[1], maxLoc[0])
        result = cv2.matchTemplate(search_img, template_2, cv2.TM_CCOEFF_NORMED)
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(result)
        top_left_2 = (maxLoc[1], maxLoc[0])
        if top_left_1[0] > top_left_2[0]:
            count1 += 1
        else:
            count2 += 1
    if not BatchJobRunning and count1 > count2:
        if tk.messagebox.askyesno(
            "Wrong film type detected",
            f"Current project is defined to handle {project_config['FilmType']}"
            f" film type, however frames seem to be {other_film_type}.\r\n"
            "Do you want to change it now?"):
            film_type.set(other_film_type)
            set_film_type()

        logging.debug(f"Changed film type to {other_film_type}")


def load_image_for_rectangle_definition(file, is_cropping):
    # load the image, clone it, and setup the mouse callback function
    ### img = Image.open(file)  # Store original image
    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
    if not is_cropping:   # only take left stripe if not for cropping
        img = get_image_left_stripe(img, calculated=False)
    # Rotate image if required
    if perform_rotation.get():
        img = rotate_image(img)
    # Stabilize image to make sure target image matches user visual definition
    if is_cropping and perform_stabilization.get():
        img = stabilize_image(CurrentFrame, img, img)[0]
    elif not is_cropping:
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Apply Otsu's thresholding if requested (for low contrast frames)
        if low_contrast_custom_template.get():
            img_bw = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        else:
            img_bw = cv2.threshold(img_gray, float(StabilizationThreshold_default), 255, cv2.THRESH_BINARY)[1]
            #img_bw = cv2.Canny(image=img_gray, threshold1=100, threshold2=20)  # Canny Edge Detection
        # Convert back to color so that we cna draw green lines on it
        img = cv2.cvtColor(img_bw, cv2.COLOR_GRAY2BGR)
    return img


def opencv_to_pil(opencv_image):
    """Converts an OpenCV image (NumPy array) to a PIL Image."""

    if len(opencv_image.shape) == 3:  # Color image
        opencv_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(opencv_image)
    return pil_image


def interactive_rectangle_definition_cv2(image, is_cropping):
    global rectangle_refresh
    global RectangleTopLeft, RectangleBottomRight
    global CropTopLeft, CropBottomRight
    global work_image, base_image, original_image
    global line_thickness
    global ix, iy
    global x_, y_

    original_image = image
    # Try to find best template
    if not is_cropping and (template_list.get_active_position() == (0, 0) or template_list.get_active_size() == (0, 0)): # If no template defined,set default
        ix = 0
        iy = 0
        x_ = 0
        y_ = 0
        RectangleTopLeft = (0,0)
        RectangleBottomRight = (0,0)
        rectangle_refresh = True
    # Scale area selection image as required
    work_image = np.copy(original_image)
    img_width = work_image.shape[1]
    img_height = work_image.shape[0]
    win_x = int(img_width * area_select_image_factor)
    win_y = int(img_height * area_select_image_factor)
    line_thickness = int(2/area_select_image_factor)

    # work_image = np.zeros((512,512,3), np.uint8)
    base_image = np.copy(work_image)
    window_visible = 1
    cv2.namedWindow(RectangleWindowTitle, cv2.WINDOW_GUI_NORMAL | cv2.WINDOW_NORMAL)

    # Capture mouse events
    cv2.setMouseCallback(RectangleWindowTitle, draw_rectangle)
    # rectangle_refresh = False
    cv2.imshow(RectangleWindowTitle, work_image)
    # Cannot make window wider than required since in Windows the image is expanded tpo cover the full width
    if is_demo or ForceSmallSize:
        cv2.resizeWindow(RectangleWindowTitle, round(win_x/2), round(win_y/2))
    else:
        cv2.resizeWindow(RectangleWindowTitle, win_x, win_y)
    while 1:
        window_visible = cv2.getWindowProperty(RectangleWindowTitle, cv2.WND_PROP_VISIBLE)
        if window_visible <= 0:
            break;
        if rectangle_refresh:
            copy = work_image.copy()
            cv2.rectangle(copy, (ix, iy), (x_, y_), (0, 255, 0), line_thickness)
            cv2.imshow(RectangleWindowTitle, copy)
            rectangle_refresh = False
        k = cv2.waitKeyEx(1) & 0xFF
        inc_ix = 0
        inc_x = 0
        inc_iy = 0
        inc_y = 0
        # waitKey is OS dependent. So we'll check lists of possible values for each direction (arrow keys, num pad, letters)
        if not rectangle_drawing:
            if k in [81, 82, 83, 84, ord('2'), ord('4'), ord('6'), ord('8'), ord('u'), ord('d'), ord('l'), ord('r'),
                     ord('U'), ord('D'), ord('L'), ord('R'), ord('w'), ord('W'), ord('t'), ord('T'),
                     ord('s'), ord('S'), ord('n'), ord('N')]:
                ix = RectangleTopLeft[0]
                iy = RectangleTopLeft[1]
                x_ = RectangleBottomRight[0]
                y_ = RectangleBottomRight[1]
            if k == 13:  # Enter: Confirm selection
                retvalue = True
                break
            elif k in [82, ord('8'), ord('u'), ord('U')]:   # Up
                if iy > 0:
                    inc_iy = -1
                    inc_y = -1
            elif k in [84, ord('2'), ord('d'), ord('D')]:   # Down
                if y_ < img_height:
                    inc_iy = 1
                    inc_y = 1
            elif k in [81, ord('4'), ord('l'), ord('L')]:   # Left
                if ix > 0:
                    inc_ix = -1
                    inc_x = -1
            elif k in [83, ord('6'), ord('r'), ord('R')]:   # Right
                if x_ < img_width:
                    inc_ix = 1
                    inc_x = 1
            elif k in [ord('w'), ord('W')]:  # wider
                if x_ - ix < img_width:
                    if ix > 0:
                        inc_ix = -1
                    if x_ < img_width:
                        inc_x = 1
            elif k in [ord('n'), ord('N')]:  # narrower
                if x_ - ix > 4:
                    inc_ix = 1
                    inc_x = -1
            elif k in [ord('t'), ord('T')]:  # taller
                if y_ - iy < img_height:
                    if iy > 0:
                        inc_iy = -1
                    if y_ < img_height:
                        inc_y = 1
            elif k in [ord('s'), ord('S')]:  # shorter
                if y_ - iy > 4:
                    inc_iy = 1
                    inc_y = -1
            elif k == 27:  # Escape: Restore previous selection, for cropping and template
                if is_cropping and CropAreaDefined:
                    RectangleTopLeft = CropTopLeft
                    RectangleBottomRight = CropBottomRight
                    retvalue = True
                if not is_cropping and template_list.get_active_position() != (0, 0) and template_list.get_active_size() != (0, 0):
                    RectangleTopLeft = template_list.get_active_position()
                    RectangleBottomRight = (template_list.get_active_position()[0] + template_list.get_active_size()[0],
                                            template_list.get_active_position()[1] + template_list.get_active_size()[1])
                    retvalue = True
                break
            elif k == 46 or k == 120 or k == 32:     # Space, X or Supr (inNum keypad) delete selection
                break
            if inc_x != 0 or inc_ix != 0 or inc_y != 0 or inc_iy != 0:
                ix += inc_ix
                x_ += inc_x
                iy += inc_iy
                y_ += inc_y
                w = x_ - ix
                h = y_ - iy
                if IsCropping and (Force43 or Force169) and (inc_x != 0 or inc_ix != 0):
                    y_ = iy + round(w/(1.33 if Force43 else 1.78))
                if IsCropping and (Force43 or Force169) and (inc_y != 0 or inc_iy != 0):
                    x_ = ix + round(h*(1.33 if Force43 else 1.78))
                RectangleTopLeft = (ix, iy)
                RectangleBottomRight = (x_, y_)
                rectangle_refresh = True
    #cv2.destroyAllWindows()
    # Remove the mouse callback and destroy the window
    if window_visible:
        cv2.setMouseCallback(RectangleWindowTitle, lambda *args: None)
        cv2.destroyWindow(RectangleWindowTitle)
        logging.debug("Destroying popup window %s", RectangleWindowTitle)
    else:
        logging.debug("Popup window %s closed by user", RectangleWindowTitle)
    
    return retvalue


# (Code below to draw a rectangle to select area to crop or find hole,
# adapted from various authors in Stack Overflow)
def draw_rectangle(event, x, y, flags, param):
    global work_image, base_image, original_image
    global rectangle_drawing
    global ix, iy
    global x_, y_
    # Code posted by Ahsin Shabbir, same Stack overflow thread
    global RectangleTopLeft, RectangleBottomRight
    global rectangle_refresh
    global line_thickness
    global IsCropping

    if event == cv2.EVENT_LBUTTONDOWN:
        if not rectangle_drawing:
            work_image = np.copy(base_image)
            x_, y_ = -10, -10
            ix, iy = -10, -10
            rectangle_drawing = True
            ix, iy = x, y
            x_, y_ = x, y
    elif event == cv2.EVENT_MOUSEMOVE and rectangle_drawing:
        copy = work_image.copy()
        if Force43 and IsCropping:
            w = x - ix
            h = y - iy
            if h * 1.33 > w:
                x = int(h * 1.33) + ix
            else:
                y = int(w / 1.33) + iy
        elif Force169 and IsCropping:
            w = x - ix
            h = y - iy
            if h * 1.78 > w:
                x = int(h * 1.78) + ix
            else:
                y = int(w / 1.78) + iy
        x_, y_ = x, y
        cv2.rectangle(copy, (ix, iy), (x_, y_), (0, 255, 0), line_thickness)
        cv2.imshow(RectangleWindowTitle, copy)
        rectangle_refresh = True
    elif event == cv2.EVENT_LBUTTONUP:
        rectangle_drawing = False
        copy = work_image.copy()
        if Force43 and IsCropping:
            w = x - ix
            h = y - iy
            if h * 1.33 > w:
                x = int(h * 1.33) + ix
            else:
                y = int(w / 1.33) + iy
        elif Force169 and IsCropping:
            w = x - ix
            h = y - iy
            if h * 1.78 > w:
                x = int(h * 1.78) + ix
            else:
                y = int(w / 1.78) + iy
        cv2.rectangle(copy, (ix, iy), (x, y), (0, 255, 0), line_thickness)
        # Update global variables with area
        # Need to account for the fact area calculated with 50% reduced image
        RectangleTopLeft = (max(0, round(min(ix, x))),
                            max(0, round(min(iy, y))))
        RectangleBottomRight = (min(original_image.shape[1], round(max(ix, x))),
                                min(original_image.shape[0], round(max(iy, y))))
        logging.debug("Original image: (%i, %i)", original_image.shape[1], original_image.shape[0])
        logging.debug("Selected area: (%i, %i), (%i, %i)",
                      RectangleTopLeft[0], RectangleTopLeft[1],
                      RectangleBottomRight[0], RectangleBottomRight[1])
        rectangle_refresh = True


def select_rectangle_area(is_cropping=False):
    global CurrentFrame, first_absolute_frame
    global SourceDirFileList
    global rectangle_drawing
    global ix, iy
    global x_, y_
    global area_select_image_factor
    global rectangle_refresh
    global RectangleTopLeft, RectangleBottomRight
    global CropTopLeft, CropBottomRight
    global perform_stabilization, perform_cropping, perform_rotation
    global IsCropping
    global file_type
    global template_list

    IsCropping = is_cropping

    if CurrentFrame >= len(SourceDirFileList):
        return False

    retvalue = False
    ix, iy = -1, -1
    x_, y_ = 0, 0
    rectangle_refresh = False
    if is_cropping and CropAreaDefined:
        ix, iy = CropTopLeft[0], CropTopLeft[1]
        x_, y_ = CropBottomRight[0], CropBottomRight[1]
        RectangleTopLeft = CropTopLeft
        RectangleBottomRight = CropBottomRight
        rectangle_refresh = True
    if not is_cropping and template_list.get_active_position() != (0, 0) and template_list.get_active_size() != (0, 0):  # Custom template definition
        RectangleTopLeft = template_list.get_active_position()
        RectangleBottomRight = (template_list.get_active_position()[0] + template_list.get_active_size()[0], template_list.get_active_position()[1] + template_list.get_active_size()[1])
        ix, iy = RectangleTopLeft[0], RectangleTopLeft[1]
        x_, y_ = RectangleBottomRight[0], RectangleBottomRight[1]
        rectangle_refresh = True

    file = SourceDirFileList[CurrentFrame]
    # If HDR mode, pick the lightest frame to select rectangle
    file3 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (CurrentFrame + 1, 2, file_type))
    if os.path.isfile(file3):  # If hdr frames exist, add them
        file = file3

    image = load_image_for_rectangle_definition(file, is_cropping)
    if enable_rectangle_popup:
        retvalue = interactive_rectangle_definition_cv2(image, is_cropping)
    else:
        image = opencv_to_pil(image)
        if not is_cropping:
            ratio = None
        elif Force43:
            ratio = 4/3
        elif Force169:
            ratio = 16/9
        else:
            ratio = None
        define_rectangle = DefineRectangle(draw_capture_canvas, image, aspect_ratio=ratio)
        define_rectangle.draw_initial_rectangle(RectangleTopLeft[0], RectangleTopLeft[1], RectangleBottomRight[0], RectangleBottomRight[1])
        rectangle_dims = define_rectangle.wait_for_enter()
        if rectangle_dims:
            x1, y1, x2, y2 = rectangle_dims

        define_rectangle.destroy()

        x1 = max(x1, 0)
        y1 = max(y1, 0)
        RectangleTopLeft = (x1, y1)
        RectangleBottomRight = (x2, y2)
        retvalue = True

    return retvalue


def select_cropping_area():
    global win, RectangleWindowTitle
    global perform_cropping
    global CropTopLeft, CropBottomRight
    global CropAreaDefined
    global RectangleTopLeft, RectangleBottomRight
    global project_config
    global encode_all_frames, from_frame, to_frame, ReferenceFrame

    # Disable all buttons in main window
    widget_status_update(DISABLED,0)
    FrameSync_Viewer_popup_update_widgets(DISABLED)

    win.update()

    RectangleWindowTitle = CropWindowTitle

    if select_rectangle_area(is_cropping=True):
        CropAreaDefined = True
        widget_status_update(NORMAL, 0)
        FrameSync_Viewer_popup_update_widgets(NORMAL)
        CropTopLeft = RectangleTopLeft
        CropBottomRight = RectangleBottomRight
        logging.debug("Crop area: (%i,%i) - (%i, %i)", CropTopLeft[0],
                      CropTopLeft[1], CropBottomRight[0], CropBottomRight[1])
    else:
        CropAreaDefined = False
        widget_status_update(DISABLED, 0)
        FrameSync_Viewer_popup_update_widgets(DISABLED)
        perform_cropping.set(False)
        perform_cropping.set(False)
        generate_video_checkbox.config(state=NORMAL if ffmpeg_installed
                                       else DISABLED)
        CropTopLeft = (0, 0)
        CropBottomRight = (0, 0)

    project_config["CropRectangle"] = (CropTopLeft, CropBottomRight)
    perform_cropping_checkbox.config(state=NORMAL if CropAreaDefined
                                     else DISABLED)

    # Enable all buttons in main window
    widget_status_update(NORMAL, 0)
    FrameSync_Viewer_popup_update_widgets(NORMAL)

    if ui_init_done:
        win.after(5, scale_display_update, False)
    win.update()


def select_custom_template():
    global template_list, film_type
    global RectangleWindowTitle
    global area_select_image_factor
    global low_contrast_custom_template

    # First, define custom template name and filename in case it needs to be deleted
    # Template Name = Last folder in the path, plus Frame From,  Frame to it not encoding all
    template_name = f"{os.path.split(SourceDir)[-1]}"
    # Set filename
    template_filename = f"Pattern.custom.{template_name}.jpg"
    full_path_template_filename = os.path.join(resources_dir, template_filename)

    if template_list.get_active_type() == 'custom':
        if os.path.isfile(template_list.get_active_filename()):
            os.remove(template_list.get_active_filename())
        if not set_film_type():
            return
    else:
        if len(SourceDirFileList) <= 0:
            tk.messagebox.showwarning(
                "No frame set loaded",
                "A set of frames is required before a custom template might be defined."
                "Please select a source folder before proceeding.")
            return
        # Disable all buttons in main window
        widget_status_update(DISABLED, 0)
        FrameSync_Viewer_popup_update_widgets(DISABLED)

        win.update()

        RectangleWindowTitle = CustomTemplateTitle

        if select_rectangle_area(is_cropping=False) and CurrentFrame < len(SourceDirFileList):
            # Extract template from image
            file = SourceDirFileList[CurrentFrame]
            file3 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (CurrentFrame + 1, 2, file_type))
            if os.path.isfile(file3):  # If hdr frames exist, add them
                file = file3
            full_img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
            # test to stabilize custom template itself using simple algorithm (commented as it affects custom template definition)
            #move_x, move_y = calculate_frame_displacement_simple(CurrentFrame, img)
            #img = shift_image(img, img.shape[1], img.shape[0], move_x, move_y)

            img = crop_image(full_img, RectangleTopLeft, RectangleBottomRight)
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply Otsu's thresholding if requested (for low contrast frames)
            if low_contrast_custom_template.get():
                img_final = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            else:
                # img_bw = cv2.threshold(img_gray, float(StabilizationThreshold), 255, cv2.THRESH_TRUNC | cv2.THRESH_TRIANGLE)[1]
                img_bw = cv2.threshold(img_gray, float(StabilizationThreshold_default), 255, cv2.THRESH_BINARY)[1]
                # img_edges = cv2.Canny(image=img_bw, threshold1=100, threshold2=20)  # Canny Edge Detection
                img_final = img_bw

            # Write template to disk
            project_config["CustomTemplateFilename"] = full_path_template_filename
            cv2.imwrite(full_path_template_filename, img_final)

            # Add template to list
            template_list.add(template_name, full_path_template_filename, 'custom', RectangleTopLeft)   # size and template automatically refreshed upon addition
            logging.debug(f"Template top left-size: {template_list.get_active_position()} - {template_list.get_active_size()}")
            widget_status_update(NORMAL, 0)
            FrameSync_Viewer_popup_update_widgets(NORMAL)
            custom_stabilization_btn.config(relief=SUNKEN)

            project_config['CustomTemplateExpectedPos'] = template_list.get_active_position()
            project_config['CustomTemplateName'] = template_list.get_active_name()

            define_template_search_area(full_img)  # Adjust hole search area to new template

            if enable_rectangle_popup:
                # Display saved template for information
                CustomTemplateWindowTitle = "Captured custom template. Press any key to continue."
                win_x = int(img_final.shape[1] * area_select_image_factor)
                win_y = int(img_final.shape[0] * area_select_image_factor)
                cv2.namedWindow(CustomTemplateWindowTitle, flags=cv2.WINDOW_GUI_NORMAL)
                cv2.imshow(CustomTemplateWindowTitle, img_final)

                # Cannot force window to be wider than required since in Windows image is expanded as well
                cv2.resizeWindow(CustomTemplateWindowTitle, round(win_x / 2), round(win_y / 2))
                cv2.moveWindow(CustomTemplateWindowTitle, win.winfo_x() + 100, win.winfo_y() + 30)
                window_visible = True
                while cv2.waitKeyEx(100) == -1:
                    window_visible = cv2.getWindowProperty(CustomTemplateWindowTitle, cv2.WND_PROP_VISIBLE)
                    if window_visible <= 0:
                        break
                if window_visible > 0:
                    cv2.destroyAllWindows()
        else:
            if os.path.isfile(full_path_template_filename):  # Delete Template if it exist
                os.remove(full_path_template_filename)
                if not set_film_type():
                    return
            custom_stabilization_btn.config(relief=RAISED)
            widget_status_update(DISABLED, 0)
            FrameSync_Viewer_popup_update_widgets(DISABLED)

    project_config["CustomTemplateDefined"] = True if template_list.get_active_type() == 'custom' else False
    debug_template_refresh_template()

    # Enable all buttons in main window
    widget_status_update(NORMAL, 0)
    FrameSync_Viewer_popup_update_widgets(NORMAL)

    win.update()


def set_film_type():
    global film_type, template_list

    if template_list.set_active(film_type.get(), film_type.get()):
        project_config["FilmType"] = film_type.get()
        debug_template_refresh_template()
        logging.debug(f"Setting {film_type.get()} template as active")
        video_fps_dropdown_selected.set('18' if film_type.get() == 'S8' else '16')
        return True
    else:
        tk.messagebox.showerror(
            "Default template could not be set",
            "Error while reverting back to standard template after disabling custom.")
        return False


def black_percent(img):
    # Count black pixels (value 0)
    black_pixels = np.sum(img == 0)

    # Get total number of pixels
    total_pixels = img.size

    # Calculate percentage of black pixels
    return (black_pixels / total_pixels) * 100


def match_level_color(t):
    if t < 0.7:
        return "red"
    if t < 0.9:
        return "orange"
    return "green"


def match_level_color_bgr(t):
    if t < 0.7:
        return (255,0,0)
    if t < 0.9:
        return (255,255,0)
    return (0,255,0)


def is_valid_template_size():
    tw = template_list.get_active_size()[0]/template_list.get_scale()
    th = template_list.get_active_size()[1]/template_list.get_scale()

    file = SourceDirFileList[CurrentFrame]
    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)

    iw = img.shape[1]
    ih = img.shape[0]

    if (tw >= iw or th >= ih):
        logging.error("Template size (%ix%i) bigger than search area (%ix%i)",tw, th, iw, ih)
        return False
    else:
        return True


def cv2_matchTemplate_with_padding(image, template, algo):
    # Add padding to the source image
    pad_width = max(template.shape[0], template.shape[1])
    padded_image = cv2.copyMakeBorder(image, pad_width, pad_width, pad_width, pad_width, cv2.BORDER_CONSTANT, value=(0, 0, 0))

    result = cv2.matchTemplate(padded_image, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # Adjust the location to account for the padding
    top_left = (max_loc[0] - pad_width, max_loc[1] - pad_width)
    bottom_right = (top_left[0] + template.shape[1], top_left[1] + template.shape[0])

    return max_val, top_left


# img is directly the left stripe (search area)
def match_template(frame_idx, img):
    global min_thres

    template = template_list.get_active_template()
    tw = template.shape[1]
    th = template.shape[0]
    iw = img.shape[1]
    ih = img.shape[0]

    template_pos = template_list.get_active_position()

    if (tw >= iw or th >= ih):
        logging.error("Template (%ix%i) bigger than search area (%ix%i)",
                      tw, th, iw, ih)
        return 0, (0, 0), 0, 0, 0

    Done = False
    retry_with_padding = False
    # Default threshols is useless, use always a loop
    # local_threshold = get_stabilization_threshold()
    # back_percent_checked = False
    if ConvertLoopRunning:
        local_threshold = 254
        limit_threshold = 120
        step_threshold = -5
    else:
        # Threshold needs to be hardcoded for FrameSync dynamic correction to work
        local_threshold = StabilizationThreshold
        limit_threshold = StabilizationThreshold
        step_threshold = -1
        retry_with_padding = True # prevent retry with padding in this case
    #local_threshold = 120
    #limit_threshold = 254
    #step_threshold = +5
    num_loops = 0
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)    # reduced left stripe to calculate white on black proportion
    # Init processing variables
    best_match_level = 0
    best_thres = 0
    best_top_left = None
    best_maxVal = None
    best_img_final = None
    while True: # No do..while in python, use this to retry with padding if needed
        while not Done:
            num_loops += 1
            # convert img to grey, checking various thresholds
            # in order to calculate the white on black proportion correctly, we saved the number of white pixels in the
            # template, but we divide it by the number of pixels in the search area, as it is wider
            if low_contrast_custom_template.get():
                # Apply Otsu's thresholding
                best_thres, img_final = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                local_threshold = best_thres    # So that it is taken as best for OTSU in the code below
                Done = True # Only one try with OTSU, best threshold is whathever it returns
            else:
                # Not interested in best threshold returned usign this algorithm
                _, img_final = cv2.threshold(img_gray, local_threshold, 255, cv2.THRESH_BINARY)

            #img_edges = cv2.Canny(image=img_bw, threshold1=100, threshold2=1)  # Canny Edge Detection
            if retry_with_padding:
                logging.debug(f"Frame {frame_idx+1} stabilized with padding (Top left: {best_top_left})")
                maxVal, top_left = cv2_matchTemplate_with_padding(img_final, template, cv2.TM_CCOEFF_NORMED)
                Done = True
            else:
                aux = cv2.matchTemplate(img_final, template, cv2.TM_CCOEFF_NORMED)
                (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(aux)
                top_left = maxLoc
            pos_criteria = (ih - abs(template_pos[1] - top_left[1])) / ih   # New criteria: How close is the template to the expected position
            if maxVal*pos_criteria >= best_match_level: # Keep best values in any case
                best_match_level = maxVal*pos_criteria
                best_thres = local_threshold
                best_top_left = top_left
                best_maxVal = maxVal
                best_img_final = img_final
            if precise_template_match:
                if best_match_level >= 0.99 or (best_match_level >= 0.9 and maxVal * pos_criteria < best_match_level):  # originally 0.85 and 0.7
                    Done = True # If threshold if really good, or much worse than best so far (means match level started decreasing in this loop), then end
            else:
                if best_match_level >= 0.6 or (best_match_level >= 0.5 and maxVal * pos_criteria < best_match_level):  # originally 0.5 and 0.4
                    Done = True # If threshold if really good, or much worse than best so far (means match level started decreasing in this loop), then end
            if not Done: # Quality not good enough, try another threshold
                local_threshold += step_threshold
                if (step_threshold < 0 and local_threshold <= limit_threshold) or (step_threshold > 0 and local_threshold >= limit_threshold) :
                    Done = True # End when reaching the limit (code for both directions, only one apply, as direction is harcoded in the vars)
                elif abs(limit_threshold-local_threshold) <= 6:
                    step_threshold = -1 if step_threshold < 0 else 1     # Fine tune when near the limit
        if not retry_with_padding and (best_maxVal is None or best_top_left[1] <= 0 or best_top_left[1] + th >= ih):
            retry_with_padding = True
            local_threshold = 254
            limit_threshold = 120
            step_threshold = -5
            best_match_level = 0
            best_thres = 0
            best_top_left = None
            best_maxVal = None
            best_img_final = None
            Done = False
        if Done:
            break

    if best_maxVal == None:
        logging.error(f"Match level not determined: frame_idx {frame_idx}, best_thres: {best_thres}, best_top_left: {best_top_left}, "
                        f"best_maxVal: {best_maxVal}, step_threshold: {step_threshold}, local_threshold: {local_threshold}, limit_threshold: {limit_threshold}")
        best_maxVal = 0.0
    return int(best_thres), best_top_left, round(best_maxVal,2), best_img_final, num_loops


"""
#################################
Multiprocessing Support functions
#################################
"""


def start_threads():
    global num_threads, active_threads
    global frame_encoding_thread_list
    global frame_encoding_event, frame_encoding_queue

    frame_encoding_thread_list = []
    frame_encoding_event = threading.Event()
    for i in range(0, num_threads):
        logging.debug(f"Thread {i} initialized")
        frame_encoding_thread_list.append(threading.Thread(target=frame_encoding_thread, args=(frame_encoding_queue, frame_encoding_event, i)))
        frame_encoding_thread_list[i].start()
        active_threads += 1
    logging.debug(f"{num_threads} threads initialized")


def terminate_threads(user_terminated):
    global win, num_threads, active_threads
    global frame_encoding_thread_list, frame_encoding_event
    global last_displayed_image

    # Terminate threads
    logging.debug("Signaling exit event for threads")
    frame_encoding_event.set()
    while active_threads > 0:
        if frame_encoding_queue.qsize() <= 4:
            frame_encoding_queue.put((END_TOKEN, 0))
            logging.debug("Inserting end token to encoding queue")
        logging.debug(f"Waiting for threads to stop ({active_threads} remaining)")
        check_subprocess_event_queue(user_terminated)
        win.update()
        time.sleep(0.2)

    # Process any remaining items in queue from workers
    logging.debug("Empty any remaining items in frames to read queue")
    empty_queue(frame_encoding_queue)

    logging.debug("Thread queues content>>>>")
    while not frame_encoding_queue.empty():
        logging.debug(frame_encoding_queue.get())
    logging.debug("<<<<Thread queues content")

    try:
        for i in range(0, num_threads):
            logging.debug(f"Joining thread {i} {frame_encoding_thread_list[i]} ...")
            if frame_encoding_thread_list[i].is_alive():
                frame_encoding_thread_list[i].join()
            logging.debug(f"Thread {i} finalized {frame_encoding_thread_list[i]}")
    except Exception as e:
        logging.error(f"Exception during thread {i} join {e}")

    frame_encoding_queue.put(LAST_ITEM_TOKEN)
    logging.debug("Thread Queues content (after join)>>>>")
    item = None
    while item != LAST_ITEM_TOKEN:
        item = frame_encoding_queue.get()
        logging.debug(item)
    logging.debug("<<<<Thread Queues content (after join)")

    # Reinitilize variables used to avoid out-of-order UI update
    last_displayed_image = 0


"""
###################################
Support functions for core business
###################################
"""


def debug_display_image(window_name, img, factor=1):
    if dev_debug_enabled:
        if isinstance(img, ImageTk.PhotoImage):
            img = ImageTk.getimage(img)
        if isinstance(img, Image.Image):
            img = np.array(img)
        cv2.namedWindow(window_name)
        if factor != 1 and img.shape[0] >= 2 and img.shape[1] >= 2:
            img_s = resize_image(img, factor)
        else:
            img_s = img
        cv2.imshow(window_name, img_s)
        cv2.waitKey(0)
        window_visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
        if window_visible > 0:
            cv2.destroyWindow(window_name)


def display_image(img):
    global PreviewWidth, PreviewHeight
    global draw_capture_canvas, left_area_frame
    global perform_cropping

    img = resize_image(img, PreviewRatio)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    DisplayableImage = ImageTk.PhotoImage(Image.fromarray(img))

    image_height = img.shape[0]
    image_width = img.shape[1]
    padding_x = 0
    padding_y = 0
    # Center only when cropping, otherwise image will shake
    if perform_cropping.get():
        if PreviewWidth > image_width:
            padding_x = round((PreviewWidth - image_width) / 2)
        if PreviewHeight > image_height:
            padding_y = round((PreviewHeight - image_height) / 2)

    # Delete reference to previous image, if any
    aux_image = None
    if hasattr(draw_capture_canvas, 'image'):
        aux_image = draw_capture_canvas.image
    draw_capture_canvas.image = DisplayableImage
    if aux_image is not None:
        del aux_image
    draw_capture_canvas.itemconfig(draw_capture_canvas.image_id, image=draw_capture_canvas.image)
    draw_capture_canvas.coords(draw_capture_canvas.image_id, padding_x, padding_y)


# Display frames while video encoding is ongoing
# No need to care about sequencing since video encoding process in AfterScan is single threaded
def display_output_frame_by_number(frame_number):
    global StartFrame
    global TargetDirFileList, file_type_out

    TargetFile = TargetDir + '/' + FrameOutputFilenamePattern % (StartFrame + frame_number, file_type_out)

    if TargetFile in TargetDirFileList:
        img = cv2.imread(TargetFile, cv2.IMREAD_UNCHANGED)
        display_image(img)


def resize_image(img, ratio):
    # Calculate the proportional size of original image
    width = int(img.shape[1] * ratio)
    height = int(img.shape[0] * ratio)

    dsize = (width, height)

    # resize image
    return cv2.resize(img, dsize)


# This old code was supposed to optimize the size of the search area, as it was assumed that the smaller the area, 
# the fastest OpenCV would be in finding the template. However, once simplified (hardcoded to 20% left stripe of 
# the image), it does not seem to cause any additional delay. We leav ethe old code here for the moment.
def get_image_left_stripe_old(img):
    global HoleSearchTopLeft, HoleSearchBottomRight
    global template_list
    # Get partial image where the hole should be (to facilitate template search
    # by OpenCV). We do the calculations inline instead of calling the function
    # since we need the intermediate values
    # Default values defined at display initialization time, after source
    # folder is defined
    # If template wider than search area, make search area bigger (including +100 to have some margin)
    if template_list.get_active_size()[0] > HoleSearchBottomRight[0] - HoleSearchTopLeft[0]:
        logging.debug(f"Making left stripe wider: {HoleSearchBottomRight[0] - HoleSearchTopLeft[0]}")
        HoleSearchBottomRight = (HoleSearchBottomRight[0] + template_list.get_active_size()[0], HoleSearchBottomRight[1])
        logging.debug(f"Making left stripe wider: {HoleSearchBottomRight[0] - HoleSearchTopLeft[0]}")
    horizontal_range = (HoleSearchTopLeft[0], HoleSearchBottomRight[0])
    vertical_range = (HoleSearchTopLeft[1], HoleSearchBottomRight[1])
    return np.copy(img[vertical_range[0]:vertical_range[1], horizontal_range[0]:horizontal_range[1]])

def get_image_left_stripe(img, calculated=True):
    global HoleSearchTopLeft, HoleSearchBottomRight
    global template_list

    width = CalculatedLeftStripeWidth if calculated else int(UserDefinedLeftStripeWidthProportion*img.shape[1])
    return np.copy(img[0:img.shape[1], 0:width])


def gamma_correct_image_old(src, gamma):
    invGamma = 1 / gamma

    table = [((i / 255) ** invGamma) * 255 for i in range(256)]
    table = np.array(table, np.uint8)

    return cv2.LUT(src, table)

def gamma_correct_image(src, gamma):
    """Apply gamma correction to an image using a lookup table."""
    if gamma <= 0:
        raise ValueError("Gamma must be positive")
    
    # Ensure uint8 input
    if src.dtype != np.uint8:
        src = cv2.convertScaleAbs(src, alpha=(255.0/src.max()))
    
    invGamma = 1 / gamma
    table = np.array([((i / 255) ** invGamma) * 255 for i in range(256)], dtype=np.uint8)
    
    return cv2.LUT(src, table)


def rotate_image(img):
    global RotationAngle
    # grab the dimensions of the image and calculate the center of the
    # image
    (h, w) = img.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    # rotate our image by 45 degrees around the center of the image
    M = cv2.getRotationMatrix2D((cX, cY), float(RotationAngle), 1.0)
    rotated = cv2.warpAffine(img, M, (w, h))
    return rotated


# Factorize code to find the target positions, vertical and horizontal:
# Vertical target: Vertical middle of the hole for S8, middle of the inter-hole space for R8
# Horizontal target: Hole right edge (both for S8 and R8)
def get_target_position(frame_idx, img, orientation='v', threshold=10, slice_width=10):
    global draw_capture_canvas

    # Get dimensions of the binary image
    height = img.shape[0]
    width = img.shape[1]

    # Set horizontal rows to make several atempts if required
    pos_list = []
    if orientation == 'v':
        pos_list.append(0)
    else:
        if film_type.get() == 'S8':
            pos_list.append(height // 2 - int(height*0.07) - slice_width // 2)
            pos_list.append(height // 2 - slice_width // 2)
            pos_list.append(height // 2 + int(height*0.07) - slice_width // 2)
        else:
            # For R8, Get a slice on the top or bottom of the image
            slice_height = 0 # use the top hole
            #slice_height = height - int(height*0.15))    # use bottom hole
            pos_list.append(slice_height)
            ### pos_list.append(slice_height + int(height*0.02))
            ### pos_list.append(slice_height + int(height*0.04))

    # Calculate the middle of the vertical and horizontal coordinated
    vertical_middle = height // 2

    for pos in pos_list:
        # First, determine the vertical displacement
        if orientation == 'v':
            # Get a vertical slice on the left of the image
            if slice_width > width:
                raise ValueError("Slice width exceeds image width")
            sliced_image = img[:, pos:pos+slice_width]
        else:
            sliced_image = img[pos:pos+slice_width, :CalculatedLeftStripeWidth]    # Don't need a full horizontal slice, holes must be in the leftmost 25%

        # Convert to pure black and white (binary image)
        _, binary_img = cv2.threshold(sliced_image, get_stabilization_threshold(), 255, cv2.THRESH_BINARY)

        # Sum along the width to get a 1D array representing white pixels at each height
        height_profile = np.sum(binary_img, axis=1 if orientation == 'v' else 0)
        
        # Find where the sum is non-zero (white) for S8 or horizontal search, or zero (black) for R8
        if (film_type.get() == 'R8' and orientation == 'v'):
            slice_values = np.where(height_profile == 0)[0]
        else:
            slice_values = np.where(height_profile > 0)[0]

        areas = []
        start = None
        min_gap_size = int((height*0.08) if orientation == 'v' else (width*0.05))  # Determine minimum hole size depending on the orientation
        previous = None
        for i in slice_values:
            if start is None:
                start = i
            if previous is not None and i-previous > 1: # end of first ares, check size
                if previous-start > min_gap_size:  # min_gap_size is minimum number of consecutive pixels to skip small gaps
                    areas.append((start, previous - 1))
                start = i
            previous = i
        if start is not None and slice_values[-1]-start > min_gap_size:  # Add the last area if it exists
            areas.append((start, slice_values[-1]))
        
        result = 0
        bigger = 0
        area_count = 0
        for start, end in areas:
            area_count += 1
            if area_count > 2:
                break
            if end-start > bigger:
                bigger = end-start
                result = (start + end) // 2 if orientation == 'v' else end
                result_start = start
                result_end = end

    if (area_count > 0):
        if orientation == 'v':
            offset = vertical_middle-result   # Return offset of the center of the biggest area with respect to the frame enter
            if abs(offset) > 300:
                logging.warning(f"Frame {frame_idx}: Vertical offset too big {offset}.")
        else:
            offset = int(width*0.08) - result   # Return offset of the hole vertical edge with respect to the expected position
            horizontal_offset_average.add_value(offset)
            # Difference between actual horizontal offset and average one should be smaller than 30 pixels (not much horizontal movement expected)
            # Make original gap of 30 pizels relative to width of the image (1.5% of width)
            if horizontal_offset_average.get_average() is not None and abs(horizontal_offset_average.get_average()-offset) > int(width*0.015):
                logging.warning(f"Frame {frame_idx}: Too much deviation of horizontal offset {offset}, respect to average {int(horizontal_offset_average.get_average())}.")
                offset = horizontal_offset_average.get_average()
    else:
        offset = 0
        result_start = 0
        result_end = 0

    return int(offset), result_start, result_end


# Based on FrameAlignmentChecker 'is_frame_centered' algorithm
# Templates to be dropped, vertical displacement to be calculated based on position 
# of the center of the hole (S8) or the space between two holes (R8)
def calculate_frame_displacement_simple(frame_idx, img, threshold=10, slice_width=10):
    vertical_offset, _, _ = get_target_position(frame_idx, img, 'v')
    horizontal_offset, _, _ = get_target_position(frame_idx, img, 'h')

    return horizontal_offset, vertical_offset


# sanitize_displacement: if displacement too big, set it to zero
def sanitize_displacement(frame_idx, img, match_level, move_x, move_y):
    # Get imag edimensions
    width = img.shape[1]
    height = img.shape[0]

    # Calculate rolling average of match level
    match_level_average.add_value(match_level)
    move_too_big = False

    if len(move_x_average.window) > 10 and move_x_average.get_average() is not None and abs(move_x - move_x_average.get_average()) > width*0.03:
        move_too_big = True
    else:
        move_x_average.add_value(move_x)

    if len(move_y_average.window) > 10 and move_y_average.get_average() is not None and abs(move_y - move_y_average.get_average()) > height*0.10:
        move_too_big = True
    else:
        move_y_average.add_value(move_y)

    if move_too_big:
        # If calculates displacement is too much, leave frame as is (probably captured position as-is is better)
        logging.warning(f"Frame {frame_idx:5d}: Calculated displacement ({move_x}, {move_y}) is too big, ignoring it.")
        move_x = 0
        move_y = 0
        match_level = 0

    return match_level, move_x, move_y


# Original algorithm based on templates
# Extracted code to calculate displacement to use with the manual option
def calculate_frame_displacement_with_templates(frame_idx, img_ref, img_ref_alt = None, id = -1):
    # Set hole template expected position
    hole_template_pos = template_list.get_active_position()
    film_hole_template = template_list.get_active_template()

    # Search film hole pattern
    best_match_level = 0
    best_top_left = [0,0]

    # Get sprocket hole area
    left_stripe_image = get_image_left_stripe(img_ref)
    img_ref_alt_used = False
    while True:
        frame_treshold, top_left, match_level, img_matched, num_loops = match_template(frame_idx, left_stripe_image)
        match_level = max(0, match_level)   # in some cases, not sure why, match level is negative
        if match_level >= 0.90:
            break
        else:
            if match_level >= best_match_level:
                best_match_level = match_level
                best_top_left = top_left
                best_img_matched = img_matched
        if not img_ref_alt_used and img_ref_alt is not None:
            left_stripe_image = get_image_left_stripe(img_ref_alt)
            img_ref_alt_used = True
        else:
            match_level = best_match_level
            top_left = best_top_left
            img_matched = best_img_matched
            break

    if top_left is not None and top_left[1] != -1 and match_level > 0.5:
        move_x = hole_template_pos[0] - top_left[0]
        move_y = hole_template_pos[1] - top_left[1]
    else:   # If match is not good, keep the frame where it is, will probably look better
        logging.warning(f"Frame {frame_idx:5d}: Template match not good ({match_level}""), ignoring it.")
        move_x = 0
        move_y = 0
        top_left = [0,0]
    log_line = f"T{id} - " if id != -1 else ""

    if top_left is not None:
        logging.debug(log_line+f"Frame_idx: {frame_idx:5d}, Frame: {frame_idx+first_absolute_frame:5d}, threshold: {frame_treshold:3d}, match_level: {match_level}, template: ({hole_template_pos[0]:4d},{hole_template_pos[1]:4d}), top left: ({top_left[0]:4d},{top_left[1]:4d}), move_x:{move_x:4d}, move_y:{move_y:4d}")
        debug_template_display_frame_raw(img_matched, top_left[0] - stabilization_shift_x_value.get(), top_left[1] - stabilization_shift_y_value.get(), film_hole_template.shape[1], film_hole_template.shape[0], match_level_color_bgr(match_level))
        debug_template_display_info(frame_idx, frame_treshold, top_left, move_x, move_y)
    return move_x, move_y, top_left, match_level, frame_treshold, num_loops


def shift_image(img, width, height, move_x, move_y):
    translation_matrix = np.array([
        [1, 0, move_x],
        [0, 1, move_y]
    ], dtype=np.float32)
    # Apply the translation to the image
    return cv2.warpAffine(src=img, M=translation_matrix, dsize=(width, height))


def calculate_missing_rows(height, move_y):
    # Try to figure out if there will be a part missing
    # at the bottom, or the top
    missing_rows = 0
    missing_bottom = 0
    missing_top = 0
    if move_y < 0:
        if height + move_y < CropBottomRight[1]:
            missing_bottom = -(CropBottomRight[1] - (height + move_y))
        missing_rows = -missing_bottom
    if move_y > 0:
        if move_y > CropTopLeft[1]:
            missing_top = CropTopLeft[1] - move_y
        missing_rows = -missing_top

    return missing_rows, missing_top, missing_bottom



def fill_image(source_img, stabilized_img, move_x, move_y, offset_x = 0, offset_y = 0):
    width = source_img.shape[1]
    height = source_img.shape[0]

    missing_rows, missing_top, missing_bottom = calculate_missing_rows(height, move_y)

    ### if missing_rows > 0 and perform_rotation.get():
    ###    missing_rows = missing_rows + 10  # If image is rotated, add 10 to cover gap between image and fill

    move_x += offset_x
    move_y += offset_y
    # Check if frame fill is enabled, and required: Extract missing fragment
    if frame_fill_type.get() == 'fake' and (ConvertLoopRunning or CorrectLoopRunning) and missing_rows > 0:
        # Perform temporary horizontal stabilization only first, to extract missing fragment
        translated_image = shift_image(source_img, width, height, move_x, 0)
        if missing_top < 0:
            missing_fragment = translated_image[CropBottomRight[1]-missing_rows:CropBottomRight[1],0:width]
        elif missing_bottom < 0:
            missing_fragment = translated_image[CropTopLeft[1]:CropTopLeft[1]+missing_rows, 0:width]

    # Check if frame fill is enabled, and required: Add missing fragment
    # Check if there is a gap in the frame, if so, and one of the 'fill' functions is enabled, fill accordingly
    if missing_rows > 0 and (ConvertLoopRunning or CorrectLoopRunning):
        if frame_fill_type.get() == 'fake':
            if missing_top < 0:
                stabilized_img[CropTopLeft[1]:CropTopLeft[1]+missing_rows,0:width] = missing_fragment
                #cv2.rectangle(stabilized_img, (0, CropTopLeft[1]), (width, CropTopLeft[1]+missing_rows), (0,255,0), 3)
            elif missing_bottom < 0:
                stabilized_img[CropBottomRight[1]-missing_rows:CropBottomRight[1],0:width] = missing_fragment
                #cv2.rectangle(stabilized_img, (0, CropBottomRight[1]-missing_rows), (width, CropBottomRight[1]), (0,255,0), 3)
        elif frame_fill_type.get() == 'dumb':
            if missing_top < 0:
                stabilized_img = stabilized_img[missing_rows+CropTopLeft[1]:height,0:width]
                stabilized_img = cv2.copyMakeBorder(src=stabilized_img, top=missing_rows+CropTopLeft[1], bottom=0, left=0, right=0,
                                                        borderType=cv2.BORDER_REPLICATE)
            elif missing_bottom < 0:
                stabilized_img = stabilized_img[0:CropBottomRight[1]-missing_rows, 0:width]
                stabilized_img = cv2.copyMakeBorder(src=stabilized_img, top=0, bottom=CropBottomRight[1]-missing_rows, left=0, right=0,
                                                        borderType=cv2.BORDER_REPLICATE)
    return stabilized_img


def stabilize_image(frame_idx, img, img_ref, offset_x = 0, offset_y = 0, img_ref_alt = None, id = -1):
    """
    frame_idx: Index of frame being stabilize
    img: Source Image being stabilized
    img_ref: Reference image use to calculate displacements (normally same as img, can be fifferent, for HDR)
    offset_x:  Additional displacement in x direction (compensation x in UI)
    offset_y:  Additional displacement in y direction (compensation y in UI)
    img_ref_alt: 
    id: Thread identifier, for debugging purposes
    """
    global SourceDirFileList
    global first_absolute_frame, StartFrame
    global CropTopLeft, CropBottomRight, win
    global project_name
    global frame_fill_type, extended_stabilization
    global CsvFramesOffPercent
    global stabilization_threshold_match_label
    global perform_stabilization
    global template_list

    if not perform_stabilization.get(): # Not really needed, stabilize_image only called when enabled but just in case
        return img, 1.0, 0, 0
    
    # Get image dimensions to perform image shift later
    width = img_ref.shape[1]
    height = img_ref.shape[0]

    if use_simple_stabilization:  # Standard stabilization using templates (use if selected via command line, or when browsing)
        move_x, move_y = calculate_frame_displacement_simple(frame_idx, img_ref)
        match_level = 1
        frame_threshold = get_stabilization_threshold()
        num_loops = 1
    else:
        move_x, move_y, top_left, match_level, frame_threshold, num_loops  = calculate_frame_displacement_with_templates(frame_idx, img_ref, img_ref_alt, id)
        
    missing_rows = calculate_missing_rows(height, move_y)[0]

    # Log frame alignment info for analysis (only when in convert loop)
    # Items logged: Tag, project id, Frame number, missing pixel rows, location (bottom/top), Vertical shift
    stabilization_threshold_match_label.config(fg='white', bg=match_level_color(match_level),
                                               text=str(int(match_level * 100)))

    match_level, move_x, move_y = sanitize_displacement(frame_idx, img, match_level, move_x, move_y)

    if ConvertLoopRunning: # Only add frames to misaligned list, or to csv file, when running conversion loop
        if missing_rows > 0 or match_level < 0.9:
            if match_level < (0.7 if not high_sensitive_bad_frame_detection else 0.9):   # Only add really bad matches
                ### Record bad frames always
                if True or FrameSync_Viewer_opened:  # Generate bad frame list only if popup opened
                    insert_or_replace_sorted(bad_frame_list, {'frame_idx': frame_idx, 'x': 0, 'y': 0, 
                                                              'original_x' : top_left[0], 'original_y': top_left[1],
                                                              'threshold': frame_threshold, 'original_threshold': frame_threshold, 
                                                              'match_level': match_level, 'is_frame_saved': True})
                    if stabilization_bounds_alert:
                        win.bell()
            if GenerateCsv:
                with open(CsvPathName, 'a') as csv_file:
                    csv_file.write(f"{first_absolute_frame+frame_idx}, {missing_rows}, {frame_threshold}, {num_loops}, {int(match_level*100)}, {move_x}, {move_y}\n")
    if match_level > 0 and match_level < 0.4:   # If match level is too bad, leave frame as captured
        move_x = 0
        move_y = 0
    # Apply stabilization offsets in all cases (even if perfect match)
    move_x += offset_x
    move_y += offset_y
    # Add vertical offset as decided by user, to compensate for vertically assimmetrical films
    translated_image = shift_image(img, width, height, move_x + StabilizationShiftX, move_y + StabilizationShiftY)
    # Draw stabilization rectangles only for image in popup debug window to allow having it activated while encoding
    if not use_simple_stabilization and FrameSync_Viewer_opened and top_left[1] != -1 :
        move_x -= offset_x
        move_y -= offset_y
        left_stripe_img = get_image_left_stripe(translated_image)
        # No need for a search area rectangle, since the image in the debug popup is already that rectangle
        debug_template_display_frame_stabilized(left_stripe_img, top_left[0] + move_x, top_left[1] + move_y,
                                                template_list.get_active_size()[0], template_list.get_active_size()[1],
                                                match_level_color_bgr(match_level))

    return translated_image, match_level, move_x, move_y


def even_image(img):
    # Get image dimensions to check whether one dimension is odd
    width = img.shape[1]
    height = img.shape[0]

    X_end = width
    Y_end = height

    # FFmpeg does not like odd dimensions
    # Adjust (decreasing BottomRight)in case of odd width/height
    if width % 2 == 1:
        X_end -= 1
    if height % 2 == 1:
        Y_end -= 1
    if X_end != 0 or Y_end != 0:
        return img[0:Y_end, 0:X_end]
    else:
        return img


def crop_image(img, top_left, botton_right):
    # Get image dimensions to perform image shift later
    width = img.shape[1]
    height = img.shape[0]

    Y_start = top_left[1]
    Y_end = min(botton_right[1], height)
    X_start = top_left[0]
    X_end = min (botton_right[0], width)

    # FFmpeg does not like odd dimensions
    # Adjust (decreasing BottomRight)in case of odd width/height
    if (X_end - X_start) % 2 == 1:
        X_end -= 1
    if (Y_end - Y_start) % 2 == 1:
        Y_end -= 1

    return img[Y_start:Y_end, X_start:X_end]


def denoise_image(img):
    temp_denoise_frame_deque.append(img)
    if len(temp_denoise_frame_deque) == denoise_window_size:
        if not HAS_TEMPORAL_DENOISE:
            # denoised_img = np.median(np.array(list(temp_denoise_frame_deque)), axis=0).astype(np.uint8)   # Temporal median filtering does not work very well for moving images
            denoised_img = cv2.fastNlMeansDenoisingColored(img, None, 5, 5, 21, 7)
        else:
            denoised_img = cv2.temporalDenoising(np.array(list(temp_denoise_frame_deque)), None, 3)
    else:
        # For the first denoise_window_size frames, return the original frame
        denoised_img = img 
    return denoised_img


def is_ffmpeg_installed():
    global ffmpeg_installed
    global FfmpegBinName
    global ffmpeg_process

    cmd_ffmpeg = [FfmpegBinName, '-h']

    try:
        ffmpeg_process = sp.Popen(cmd_ffmpeg, stderr=sp.PIPE, stdout=sp.PIPE)
        ffmpeg_installed = True
    except FileNotFoundError:
        ffmpeg_installed = False
        logging.error("ffmpeg is NOT installed.")

    return ffmpeg_installed


def system_suspend():
    global IsWindows, IsLinux, IsMac

    if IsLinux:
        cmd_suspend = ['systemctl', 'suspend']
    elif IsWindows:
        cmd_suspend = ['rundll32.exe',  'powrprof.dll,SetSuspendState', '0,1,0']
    elif IsMac:
        cmd_suspend = ['pmset',  'sleepnow']

    try:
        sp.Popen(cmd_suspend, stderr=sp.PIPE, stdout=sp.PIPE)
    except:
        logging.error("Cannot suspend.")


def get_source_dir_file_list():
    global SourceDir, frame_width, frame_height
    global project_config
    global SourceDirFileList
    global CurrentFrame, first_absolute_frame, last_absolute_frame
    global frame_slider
    global area_select_image_factor, screen_height
    global frames_target_dir
    global HdrFilesOnly
    global CropBottomRight
    global file_type, file_type_out
    global FrameSync_Images_Factor
    global frame_height, frame_width

    if not os.path.isdir(SourceDir):
        return

    # Try first with standard scan filename template
    SourceDirFileList_jpg = list(glob(os.path.join(
        SourceDir,
        FrameInputFilenamePatternList_jpg)))
    if len(SourceDirFileList_jpg) == 0:     # Only try to read if there are no JPG at all
        SourceDirFileList_png = list(glob(os.path.join(
            SourceDir,
            FrameInputFilenamePatternList_png)))
        SourceDirFileList = sorted(SourceDirFileList_png)
        file_type_out = 'png'  # If we have png files in the input, we default to png for the output
    else:
        SourceDirFileList = sorted(SourceDirFileList_jpg)
        file_type_out = 'jpg'

    SourceDirHdrFileList_jpg = list(glob(os.path.join(
        SourceDir,
        HdrInputFilenamePatternList_jpg)))
    SourceDirHdrFileList_png = list(glob(os.path.join(
        SourceDir,
        HdrInputFilenamePatternList_png)))
    SourceDirHdrFileList = sorted(SourceDirHdrFileList_jpg + SourceDirHdrFileList_png)
    if len(SourceDirHdrFileList_png) != 0:
        file_type_out = 'png'   # If we have png files in the input, we default to png for the output
    elif len(SourceDirHdrFileList_jpg) != 0:
        file_type_out = 'jpg'

    SourceDirLegacyHdrFileList_jpg = list(glob(os.path.join(
        SourceDir,
        LegacyHdrInputFilenamePatternList_jpg)))
    SourceDirLegacyHdrFileList_png = list(glob(os.path.join(
        SourceDir,
        LegacyHdrInputFilenamePatternList_png)))
    SourceDirLegacyHdrFileList = sorted(SourceDirLegacyHdrFileList_jpg + SourceDirLegacyHdrFileList_png)
    if len(SourceDirLegacyHdrFileList_png) != 0:
        file_type_out = 'png'   # If we have png files in the input, we default to png for the output
    elif len(SourceDirLegacyHdrFileList_jpg) != 0:
        file_type_out = 'jpg'

    NumFiles = len(SourceDirFileList)
    NumHdrFiles = len(SourceDirHdrFileList)
    NumLegacyHdrFiles = len(SourceDirLegacyHdrFileList)
    if NumFiles != 0 and NumLegacyHdrFiles != 0:
        if tk.messagebox.askyesno(
                "Frame conflict",
                f"Found both standard and HDR files in source folder. "
                f"There are {NumFiles} standard frames and {NumLegacyHdrFiles} HDR files.\r\n"
                f"Do you want to continue using the {'standard' if NumFiles > NumLegacyHdrFiles else 'HDR'} files?.\r\n"
                f"You might want ot clean up that source folder, it is strongly recommended to have only a single type of frames in the source folder."):
                    if NumLegacyHdrFiles > NumFiles:
                        SourceDirFileList = SourceDirLegacyHdrFileList
    elif NumFiles == 0 and NumHdrFiles == 0: # Only Legacy HDR
        SourceDirFileList = SourceDirLegacyHdrFileList

    if len(SourceDirFileList) == 0:
        tk.messagebox.showerror("Error!",
                                "No files match pattern name. "
                                "Please specify new one and try again")
        frames_target_dir.delete(0, 'end')
        return
    else:
        HdrFilesOnly = NumLegacyHdrFiles > NumFiles

    # Sanity check for CurrentFrame
    if CurrentFrame >= len(SourceDirFileList):
        CurrentFrame = 0

    # Extract frame number from filename
    temp = re.findall(r'\d+', os.path.basename(SourceDirFileList[0]))
    numbers = list(map(int, temp))
    first_absolute_frame = numbers[0]
    last_absolute_frame = first_absolute_frame + len(SourceDirFileList)-1
    frame_slider.config(from_=0, to=len(SourceDirFileList)-1)
    refresh_current_frame_ui_info(CurrentFrame, first_absolute_frame)

    # In order to determine template dimensons, no not take the first frame, as often
    # it is not so good. Take a frame 10% ahead in the set
    sample_frame = int(len(SourceDirFileList) * 0.1)
    aux_image = cv2.imread(SourceDirFileList[sample_frame], cv2.IMREAD_UNCHANGED)
    # Set frame dimensions in global variable, for use everywhere
    frame_width = aux_image.shape[1]
    frame_height = aux_image.shape[0]
    template_list.set_scale(frame_width)    # frame_width set by get_source_dir_file_list

    return len(SourceDirFileList)


def adjust_dimensions_based_on_frame():
    global CropBottomRight, frame_height, frame_width, FrameSync_Images_Factor

    # In order to determine template dimensons, no not take the first frame, as often
    # it is not so good. Take a frame 10% ahead in the set
    sample_frame = int(len(SourceDirFileList) * 0.1)
    aux_image = cv2.imread(SourceDirFileList[sample_frame], cv2.IMREAD_UNCHANGED)
    # Frame dimensions, and template scale, are established as soon as new frame set is loaded
    
    # Set reduction factor for frameview images
    FrameSync_Images_Factor = 670 / frame_width
    # Next 3 statements were done only if batch mode was not active, but they are needed in all cases
    if BatchJobRunning:
        # why skipping it?
        # logging.debug("Skipping hole template adjustment in batch mode")
        logging.debug("Adjusting hole template in batch mode...")
        define_template_search_area(aux_image)
        detect_film_type()
    else:
        logging.debug("Adjusting hole template in standard mode...")
        define_template_search_area(aux_image)
        detect_film_type()
    # Select area window should be proportional to screen height
    # Deduct 120 pixels (approximately) for taskbar + window title
    area_select_image_factor = (screen_height - 200) / frame_height
    area_select_image_factor = min(1, area_select_image_factor)
    # If no cropping defined, set whole image dimensions
    if CropBottomRight == (0,0):
        CropBottomRight = (frame_width, frame_height)

    widget_status_update(NORMAL)
    FrameSync_Viewer_popup_update_widgets(NORMAL)
    


def get_target_dir_file_list():
    global TargetDir
    global TargetDirFileList
    global out_frame_width, out_frame_height
    global file_type_out

    if not os.path.isdir(TargetDir):
        return

    TargetDirFileList = sorted(list(glob(os.path.join(
        TargetDir, FrameCheckOutputFilenamePattern % file_type_out))))
    if len(TargetDirFileList) != 0:
        # read image
        img = cv2.imread(TargetDirFileList[0], cv2.IMREAD_UNCHANGED)
        out_frame_width = img.shape[1]
        out_frame_height = img.shape[0]
    else:
        out_frame_width = 0
        out_frame_height = 0


def valid_generated_frame_range():
    global StartFrame, frames_to_encode, first_absolute_frame
    global TargetDirFileList, file_type_out

    file_count = 0
    for i in range(first_absolute_frame + StartFrame,
                   first_absolute_frame + StartFrame + frames_to_encode):
        file_to_check = os.path.join(TargetDir,
                                     FrameOutputFilenamePattern % (i, file_type_out))
        if file_to_check in TargetDirFileList:
            file_count += 1
        else:
            # Double check if file really does not exist
            if os.path.exists(file_to_check):
                logging.warning("File %s missing from target list, but file exists.", file_to_check)
                file_count += 1
            else:
                logging.error("File %s missing.", file_to_check)

    logging.debug("Checking frame range %i-%i: %i files found",
                  first_absolute_frame + StartFrame,
                  first_absolute_frame + StartFrame + frames_to_encode,
                  file_count)

    return file_count == frames_to_encode


# Determine width of template search area based on the template used
def define_template_search_area(img):
    global HoleSearchTopLeft, HoleSearchBottomRight
    global TemplateTopLeft, template_list
    global template_wb_proportion_text
    global extended_stabilization
    global CalculatedLeftStripeWidth

    # Sproket hole corner to be detected in image, to adjust search area width
    aux_template = template_list.get_active_template()
    if aux_template.shape[1] > int(img.shape[1]*UserDefinedLeftStripeWidthProportion):
        TemplateSearchAreaWidth = aux_template.shape[1]
    else:
        TemplateSearchAreaWidth = int(img.shape[1]*UserDefinedLeftStripeWidthProportion)
    # Adjust left stripe width (search area)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_bw = cv2.threshold(img_gray, 240, 255, cv2.THRESH_BINARY)[1]
    img_target = img_bw[:, :TemplateSearchAreaWidth]  # Search only in the left area of the image (user defined %)

    result = cv2.matchTemplate(img_target, aux_template, cv2.TM_CCOEFF_NORMED)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(result)
    CalculatedLeftStripeWidth = maxLoc[0] + template_list.get_active_size()[0]
    CalculatedLeftStripeWidth += int(80 * img.shape[0]/1520)   # Increase width, proportional to the image size (250 pixels for default size 2028x1520)
    logging.debug(f"Calculated left stripe width: {CalculatedLeftStripeWidth}")
    if extended_stabilization.get():
        logging.debug("Extended stabilization requested: Widening search area by 50 pixels")
        CalculatedLeftStripeWidth += 50     # If precise stabilization, make search area wider (although not clear this will help instead of making it worse)

"""
########################
Core top level functions
########################
"""

def get_frame_number_from_filename(filename):
    numbers = re.findall(r'\d\d\d\d\d', filename)

    if len(numbers) >= 1:
        return int(numbers[-1])
    else:
        # Return a default value or handle the case where no numbers are found
        return None


def get_frame_time(frame_idx):
    fps = 18 if film_type.get() == 'S8' else 16
    return f"{(frame_idx // fps) // 60:02}:{(frame_idx // fps) % 60:02}"


def start_convert():
    global ConvertLoopExitRequested, ConvertLoopRunning
    global generate_video
    global video_writer
    global SourceDirFileList
    global TargetVideoFilename
    global CurrentFrame, StartFrame
    global encode_all_frames
    global frames_to_encode
    global ffmpeg_success, ffmpeg_encoding_status
    global frame_from_str, frame_to_str
    global project_name
    global BatchJobRunning
    global job_list, CurrentJobEntry
    global CsvFilename, CsvPathName
    global FPS_LastMinuteFrameTimes
    global current_bad_frame_index

    if ConvertLoopRunning:
        ConvertLoopExitRequested = True
        ConvertLoopRunning = False
    else:
        if not skip_frame_regeneration.get() and not delete_detected_bad_frames():
            return
        # Enforce minimum value for Gamma in case user clicks starts rigth after having manually entered a zero in GC box
        gamma_enforce_min_value()
        # Save current project status
        save_general_config()
        save_project_config()
        save_job_list()
        # Empty FPS register list
        FPS_LastMinuteFrameTimes.clear()
        # Centralize 'frames_to_encode' update here
        if encode_all_frames.get():
            StartFrame = 0
            #frames_to_encode = len(SourceDirFileList)
            frames_to_encode = get_frame_number_from_filename(SourceDirFileList[-1]) - get_frame_number_from_filename(SourceDirFileList[0]) + 1
        else:
            StartFrame = int(frame_from_str.get())
            frames_to_encode = int(frame_to_str.get()) - int(frame_from_str.get()) + 1
            if StartFrame + frames_to_encode > len(SourceDirFileList):
                frames_to_encode = len(SourceDirFileList) - StartFrame
        CurrentFrame = StartFrame
        if frames_to_encode <= 1:
            tk.messagebox.showwarning(
                "No frames match range",
                "No frames to encode.\r\n"
                "The range specified (current frame - number of frames to "
                "encode) does not match any frame.\r\n"
                "Please review your settings and try again.")
            return
        if not is_valid_template_size():
            tk.messagebox.showwarning(
                "Invalid template",
                "Template associated with this jos is bigger the search area.\r\n"
                "Please redefine template and try again.")
            return
        if BatchJobRunning:
            start_batch_btn.config(text="Stop batch", bg='red', fg='white')
            # Disable all buttons in main window
            widget_status_update(DISABLED, start_batch_btn)
        else:
            Go_btn.config(text="Stop", bg='red', fg='white')
            # Disable all buttons in main window
            widget_status_update(DISABLED, Go_btn)
        FrameSync_Viewer_popup_update_widgets(DISABLED)
        win.update()

        if project_config["GenerateVideo"]:
            TargetVideoFilename = video_filename_str.get()
            name, ext = os.path.splitext(TargetVideoFilename)
            if TargetVideoFilename == "":   # Assign default if no filename
                TargetVideoFilename = (
                    "AfterScan-" +
                    datetime.now().strftime("%Y_%m_%d-%H-%M-%S") + ".mp4")
                video_filename_str.set(TargetVideoFilename)
            elif ext not in ['.mp4', '.MP4', '.mkv', '.MKV']:     # ext == "" does not work if filename contains dots ('Av. Manzanares')
                TargetVideoFilename += ".mp4"
                video_filename_str.set(TargetVideoFilename)
            elif os.path.isfile(os.path.join(video_target_dir_str.get(), TargetVideoFilename)):
                if not BatchJobRunning:
                    error_msg = (TargetVideoFilename + " already exist in target "
                                 "folder. Overwrite?")
                    if not tk.messagebox.askyesno("Error!", error_msg):
                        generation_exit()
                        return

        ConvertLoopRunning = True

        if not generate_video.get() or not skip_frame_regeneration.get():
            # Check if CSV option selected
            if GenerateCsv:
                CsvFilename = video_filename_str.get()
                name, ext = os.path.splitext(CsvFilename)
                if name == "":  # Assign default if no filename
                    name = "AfterScan-"
                CsvFilename = datetime.now().strftime("%Y_%m_%d-%H-%M-%S_") + name + '.csv'
                CsvPathName = resources_dir
                if CsvPathName == "":
                    CsvPathName = os.getcwd()
                CsvPathName = os.path.join(CsvPathName, CsvFilename)
                # Write header
                with open(CsvPathName, 'w') as csv_file:
                    csv_file.write("Frame, Missing rows, Threshold, Num loops, Match level, move_x, move_y\n")
            match_level_average.clear()
            horizontal_offset_average.clear()
            move_x_average.clear()
            move_y_average.clear()
            # Disable manual stabilize popup widgets
            FrameSync_Viewer_popup_update_widgets(DISABLED)
            # Multiprocessing: Start all threads before encoding
            start_threads()
            win.after(1, frame_generation_loop)
        elif generate_video.get():
            # first check if resolution has been set
            if resolution_dict[project_config["VideoResolution"]] == '':
                if not BatchJobRunning:
                    logging.error("Error, no video resolution selected")
                    tk.messagebox.showerror("Error!", "Please specify video resolution.")
                else:
                    logging.error(f"Cannot generate video {TargetVideoFilename}, no video resolution selected")
                generation_exit(success = False)
            else:
                ffmpeg_success = False
                ffmpeg_encoding_status = ffmpeg_state.Pending
                win.after(1000, video_generation_loop)


def generation_exit(success = True):
    global win
    global ConvertLoopExitRequested
    global ConvertLoopRunning
    global Go_btn, save_bg, save_fg
    global BatchJobRunning
    global job_list, CurrentJobEntry, job_list_treeview

    go_suspend = False
    stop_batch = False

    if BatchJobRunning:
        if ConvertLoopExitRequested or CurrentJobEntry == -1:
            stop_batch = True
            if (CurrentJobEntry != -1):
                item_id = search_job_name_in_job_treeview(CurrentJobEntry)
                if item_id != -1:
                    job_list_treeview.item(item_id, tags=("pending","joblist_font",))
        else:
            if success:
                job_list[CurrentJobEntry]['done'] = True    # Flag as done
                item_id = search_job_name_in_job_treeview(CurrentJobEntry)
                if item_id != -1:
                    job_list_treeview.item(item_id, tags=("done","joblist_font",))
            else:
                item_id = search_job_name_in_job_treeview(CurrentJobEntry)
                if item_id != -1:
                    job_list_treeview.item(item_id, tags=("pending","joblist_font",))
            if suspend_on_completion.get() == 'job_completion':
                stop_batch = True # Exit convert loop before suspend
                go_suspend = True
            else:
                win.after(100, job_processing_loop)         # Continue with next
    else:
        Go_btn.config(text="Start", bg=save_bg, fg=save_fg)
    ConvertLoopExitRequested = False  # Reset flags
    ConvertLoopRunning = False
    # Enable all buttons in main window
    widget_status_update(NORMAL, 0)
    FrameSync_Viewer_popup_update_widgets(NORMAL)
    win.update()
    
    if stop_batch:
        start_batch_btn.config(text="Start batch", bg=save_bg, fg=save_fg)
        BatchJobRunning = False
    if go_suspend:
        system_suspend()
        time.sleep(2)


def frame_encode(frame_idx, id, do_save = True, offset_x = 0, offset_y = 0):
    global SourceDir, TargetDir
    global HdrFilesOnly , first_absolute_frame, frames_to_encode
    global FrameInputFilenamePattern, HdrSetInputFilenamePattern, FrameHdrInputFilenamePattern, FrameOutputFilenamePattern
    global CropTopLeft, CropBottomRight
    global app_status_label
    global subprocess_event_queue
    global file_type, file_type_out

    images_to_merge = []
    img_ref_aux = None

    if dev_debug_enabled:
        logging.debug(f"Thread {id}, starting to encode Frame {frame_idx}")

    # Get current file(s)
    if HdrFilesOnly:    # Legacy HDR (before 2 Dec 2023): Dedicated filename
        images_to_merge.clear()
        file1 = os.path.join(SourceDir, HdrSetInputFilenamePattern % (frame_idx + first_absolute_frame, 1, file_type))
        img_ref = cv2.imread(file1, cv2.IMREAD_UNCHANGED)   # Keep first frame of the set for stabilization reference
        images_to_merge.append(img_ref)
        file2 = os.path.join(SourceDir, HdrSetInputFilenamePattern % (frame_idx + first_absolute_frame, 2, file_type))
        images_to_merge.append(cv2.imread(file2, cv2.IMREAD_UNCHANGED))
        file3 = os.path.join(SourceDir, HdrSetInputFilenamePattern % (frame_idx + first_absolute_frame, 3, file_type))
        images_to_merge.append(cv2.imread(file3, cv2.IMREAD_UNCHANGED))
        file4 = os.path.join(SourceDir, HdrSetInputFilenamePattern % (frame_idx + first_absolute_frame, 4, file_type))
        images_to_merge.append(cv2.imread(file4, cv2.IMREAD_UNCHANGED))
        AlignMtb.process(images_to_merge, images_to_merge)
        img = MergeMertens.process(images_to_merge)
        img = img - img.min()  # Now between 0 and 8674
        img = img / img.max() * 255
        img = np.uint8(img)
    else:
        file1 = os.path.join(SourceDir, FrameInputFilenamePattern % (frame_idx + first_absolute_frame, file_type))
        if not os.path.isfile(file1):
            file_type = 'png' if file_type == 'jpg' else 'jpg'  # Try with the other file type
            file1 = os.path.join(SourceDir, FrameInputFilenamePattern % (frame_idx + first_absolute_frame, file_type))
        # read image
        img = cv2.imread(file1, cv2.IMREAD_UNCHANGED)
        img_ref = img   # Reference image is the same image for standard capture
        # Check if HDR frames exist. Can handle between 2 and 5
        file2 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (frame_idx + first_absolute_frame, 2, file_type))
        if os.path.isfile(file2):   # If hdr frames exist, add them
            images_to_merge.clear()
            images_to_merge.append(img_ref)     # Add first frame
            img_ref_aux = img_ref
            img_ref = cv2.imread(file2, cv2.IMREAD_UNCHANGED) # Override stabilization reference with HDR#2
            images_to_merge.append(img_ref)
            file3 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (frame_idx + first_absolute_frame, 3, file_type))
            if os.path.isfile(file3):  # If hdr frames exist, add them
                images_to_merge.append(cv2.imread(file3, cv2.IMREAD_UNCHANGED))
                file4 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (frame_idx + first_absolute_frame, 4, file_type))
                if os.path.isfile(file4):  # If hdr frames exist, add them
                    images_to_merge.append(cv2.imread(file4, cv2.IMREAD_UNCHANGED))
                    file5 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (frame_idx + first_absolute_frame, 5, file_type))
                    if os.path.isfile(file5):  # If hdr frames exist, add them
                        images_to_merge.append(cv2.imread(file5, cv2.IMREAD_UNCHANGED))

            AlignMtb.process(images_to_merge, images_to_merge)
            img = MergeMertens.process(images_to_merge)
            img = img - img.min()  # Now between 0 and 8674
            img = img / img.max() * 255
            img = np.uint8(img)

    if img is None:
        logging.error(
            "Error reading frame %i, skipping", frame_idx)
    else:
        register_frame()
        if perform_rotation.get():
            img = rotate_image(img)
        # If FrameSync editor opened, call stabilize_image even when not enabled just to display FrameSync images. Image would not be stabilized
        if perform_stabilization.get() or FrameSync_Viewer_opened:
            stabilized_img, match_level, move_x, move_y = stabilize_image(frame_idx, img, img_ref, offset_x, offset_y, img_ref_aux, id)
            img = fill_image(img, stabilized_img, move_x, move_y, offset_x, offset_y)
        else:
            move_x = move_y = match_level = 0 # Required as it is stored in bad frame list
        if perform_cropping.get():
            img = crop_image(img, CropTopLeft, CropBottomRight)
        else:
            img = even_image(img)
        if perform_denoise.get():
            img = denoise_image(img)
        if perform_sharpness.get():
            # Sharpness code taken from https://www.educative.io/answers/how-to-sharpen-a-blurred-image-using-opencv
            sharpen_filter = np.array([[-1, -1, -1],
                                       [-1, 9, -1],
                                       [-1, -1, -1]])
            # applying kernels to the input image to get the sharpened image
            img = cv2.filter2D(img, -1, sharpen_filter)
        if perform_gamma_correction.get():
            img = gamma_correct_image(img, float(gamma_correction_str.get()))

        # Before we used to display every other frame, but just discovered that it makes no difference to performance
        # Instead of displaying image, we add it to a queue to be processed in main loop
        if ConvertLoopRunning:
            queue_item = tuple(("processed_image", frame_idx, img, len(images_to_merge) != 0))
            subprocess_event_queue.put(queue_item)

        if img.shape[1] % 2 == 1 or img.shape[0] % 2 == 1:
            logging.error("Target size, one odd dimension")
            status_str = "Status: Frame %d - odd size" % frame_idx
            app_status_label.config(text=status_str, fg='red')
            frame_idx = StartFrame + frames_to_encode - 1

        if do_save and os.path.isdir(TargetDir):
            target_file = os.path.join(TargetDir, FrameOutputFilenamePattern % (first_absolute_frame + frame_idx, file_type_out))
            cv2.imwrite(target_file, img)
    if dev_debug_enabled:
        logging.debug(f"Thread {id}, finalized to encode Frame {frame_idx}")

    return len(images_to_merge) != 0, match_level, move_x, move_y

def frame_update_ui(frame_idx, merged):
    global first_absolute_frame, StartFrame, frames_to_encode, FPS_CalculatedValue
    global app_status_label

    frame_selected.set(frame_idx)
    frame_slider.set(frame_idx)
    refresh_current_frame_ui_info(frame_idx, first_absolute_frame)
    status_str = f"Status: Generating{' merged' if merged else ''} frames {((frame_idx - StartFrame+1) * 100 / frames_to_encode):.1f}%"
    if FPS_CalculatedValue != -1:  # FPS not calculated yet, display some indication
        status_str = status_str + f' (FPS:{FPS_CalculatedValue:.1f})'
    app_status_label.config(text=status_str, fg='black')


def frame_encoding_thread(queue, event, id):
    global SourceDir
    global ConvertLoopExitRequested, ConvertLoopRunning
    global active_threads, working_threads
    global last_displayed_image

    try:
        logging.debug(f"Thread {id} started")
        while not event.is_set():
            message = queue.get()
            if not os.path.isdir(SourceDir):
                logging.error(f"Source dir {SourceDir} unmounted: Stop encoding session")
            if message[0] == "encode_frame":
                # Encode frame
                merged = frame_encode(message[1], id)[0]
                # Update UI with progress so far (double check we have not ended, it might happen during frame encoding)
                if ConvertLoopRunning:
                    if message[1] >= last_displayed_image:
                        frame_update_ui(message[1], merged)
            elif message[0] == END_TOKEN:
                logging.debug(f"Thread {id}: Received terminate token, exiting")
                break
        logging.debug(f"Exiting frame_encoding_thread n.{id}")
        queue_item = tuple(("exit_thread", id))
        subprocess_event_queue.put(queue_item)
    except Exception as e:
        logging.error(f"Thread {id}: Exception happen {e}")


def check_subprocess_event_queue(user_terminated):
    global TargetDir, FrameOutputFilenamePattern
    global first_absolute_frame, frame_idx
    global subprocess_event_queue
    global last_displayed_image, active_threads
    global ConvertLoopRunning
    global file_type_out

    # Process requests coming from workers
    while not subprocess_event_queue.empty():
        message = subprocess_event_queue.get()
        # Display encoded images from queue
        if message[0] == "processed_image":
            img = message[2]
            frame_idx = message[1]
            if img.shape[1] % 2 == 1 or img.shape[0] % 2 == 1:
                logging.error("Target size, one odd dimension")
                status_str = "Status: Frame %d - odd size" % message[1]
                app_status_label.config(text=status_str, fg='red')
                #frame_idx = StartFrame + frames_to_encode - 1
            if os.path.isdir(TargetDir):
                target_file = os.path.join(TargetDir, FrameOutputFilenamePattern % (first_absolute_frame + frame_idx, file_type_out))
                cv2.imwrite(target_file, img)
            if not user_terminated:    # Display image
                if frame_idx >= last_displayed_image:
                    last_displayed_image = frame_idx
                    # display_image(img)    # Terminating, no need to display remaining images
                    # Update UI with progress so far (double check we have not ended, it might happen during frame encoding)
                    if ConvertLoopRunning:
                        frame_update_ui(message[1], message[3])
        elif message[0] == "exit_thread":
            logging.debug(f"Thread {message[1]}:Exiting frame_encoding_thread")
            active_threads -= 1


def frame_generation_loop():
    global perform_stabilization, perform_cropping, perform_rotation, perform_denoise, perform_sharpness
    global ConvertLoopExitRequested
    global TargetDir
    global CurrentFrame, first_absolute_frame
    global StartFrame, frames_to_encode, frame_selected
    global FrameOutputFilenamePattern
    global BatchJobRunning
    global ffmpeg_success, ffmpeg_encoding_status
    global TargetDirFileList
    global frame_slider
    global MergeMertens
    global FPS_CalculatedValue
    global HdrFilesOnly
    global frame_encoding_queue
    global last_displayed_image, working_threads
    global frame_encoding_queue, subprocess_event_queue
    global file_type_out

    # Display encoded images from queue
    if not subprocess_event_queue.empty():
        message = subprocess_event_queue.get()
        if message[0] == "processed_image" and message[1] > last_displayed_image:
            last_displayed_image = message[1]
            if subprocess_event_queue.qsize() < 5:
                display_image(message[2])
            

    if CurrentFrame >= StartFrame + frames_to_encode and last_displayed_image+1 >= StartFrame + frames_to_encode:
        FPS_CalculatedValue = -1
        # write average match quality in the status line, and in the widget
        status_str = f"Status: Frame generation OK - AvgQ: {int(match_level_average.get_average()*100)}"
        app_status_label.config(text=status_str, fg='green')
        stabilization_threshold_match_label.config(fg='white', bg=match_level_color(match_level_average.get_average()),
                                                   text=str(int(match_level_average.get_average() * 100)))
        # Clear display queue (does not seem to work as expected, leave commented for now)
        # subprocess_event_queue.queue.clear()
        last_displayed_image = 0
        win.update()
        # Refresh Target dir file list
        TargetDirFileList = sorted(list(glob(os.path.join(
            TargetDir, FrameCheckOutputFilenamePattern % file_type_out))))
        if GenerateCsv:
            name, ext = os.path.splitext(CsvPathName)
            name = f"{name} ({frames_to_encode} frames, {CsvFramesOffPercent:.1f}% KO, Avg match level {int(match_level_average.get_average()*100)}).csv"
            os.rename(CsvPathName, name)
        # Stop threads
        terminate_threads(False)
        # Sort bad frame list
        bad_frame_list.sort(key=lambda x: x['frame_idx'])
        # Generate video if requested or terminate
        if generate_video.get():
            ffmpeg_success = False
            ffmpeg_encoding_status = ffmpeg_state.Pending
            win.after(1000, video_generation_loop)
        else:
            generation_exit()
        CurrentFrame -= 1  # Prevent being out of range
        # Refresh popup window
        FrameSync_Viewer_popup_refresh()
        # Enable manual stabilize popup widgets
        FrameSync_Viewer_popup_update_widgets(NORMAL)
        win.update()
        return

    if ConvertLoopExitRequested:  # Stop button pressed
        # Process user requested termination
        logging.debug("User requested termination")
        status_str = "Status: Stopping encoding..."
        app_status_label.config(text=status_str, fg='orange')
        last_displayed_image = 0
        win.update()
        # Close CSV file
        if GenerateCsv:
            os.unlink(CsvPathName)  # Processing was stopped half-way, delete csv file as results are not representative
        # Stop workers
        terminate_threads(True)
        # Sort bad frame list
        bad_frame_list.sort(key=lambda x: x['frame_idx'])
        logging.debug(f"frames_to_encode_queue.qsize = {frame_encoding_queue.qsize()}")
        logging.debug(f"subprocess_event_queue.qsize = {subprocess_event_queue.qsize()}")
        logging.debug("Exiting threads terminate")
        status_str = "Status: Cancelled by user"
        app_status_label.config(text=status_str, fg='red')
        generation_exit(success = False)
        stabilization_threshold_match_label.config(fg='lightgray', bg='lightgray', text='')
        FPS_CalculatedValue = -1
        # Refresh popup window
        FrameSync_Viewer_popup_refresh()
        # Enable manual stabilize popup widgets
        FrameSync_Viewer_popup_update_widgets(NORMAL)
        win.update()
        return

    # Add item to encoding queue
    if CurrentFrame < StartFrame + frames_to_encode and not frame_encoding_queue.full():
        frame_encoding_queue.put(("encode_frame", CurrentFrame))
        # If inserting the first few frames, add a delay so that workers are interleaved
        # Improves visual preview, no effect on processing speed
        if CurrentFrame < StartFrame + num_threads:
            time.sleep(0.3)
        CurrentFrame += 1
        project_config["CurrentFrame"] = CurrentFrame
        win.after(1, frame_generation_loop)
    else:   # If queue is full, wait a bit longer
        win.after(100, frame_generation_loop)


def get_text_dimensions(text_string, font):
    # https://stackoverflow.com/a/46220683/9263761
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return (text_width, text_height)


def get_adjusted_font(image, text):
    global IsWindows, IsLinux, IsMac
    max_size = 96
    try_again = False
    # draw = ImageDraw.Draw(image)
    image_width, image_height = image.size
    lines = textwrap.wrap(text, width=40)
    while max_size > 8:
        status_str = "Status: Calculating title font size %u" % max_size
        app_status_label.config(text=status_str, fg='black')
        font = font_manager.FontProperties(family='sans-serif', weight='bold')
        file = font_manager.findfont(font)
        font = ImageFont.truetype(file, max_size)
        try_again = False
        num_lines = 0
        for line in lines:
            #line_width, line_height = font.getsize(line)
            line_width, line_height = get_text_dimensions(line,font)
            if line_width > int(image_width*0.8):
                max_size -= 1
                try_again = True
                break
            else:
                num_lines += 1
        if not try_again:
            return font, num_lines
    return 0


def draw_multiple_line_text(image, text, font, text_color, num_lines):
    '''
    From unutbu on [python PIL draw multiline text on image](https://stackoverflow.com/a/7698300/395857)
    '''
    draw = ImageDraw.Draw(image)
    image_width, image_height = image.size
    lines = textwrap.wrap(text, width=40)
    line_num = 0
    for line in lines:
        #line_width, line_height = font.getsize(line)
        line_width, line_height = get_text_dimensions(line,font)
        y_text = (image_height-(line_height*num_lines))/2 + line_num * line_height
        draw.text(((image_width - line_width) / 2, y_text),
                  line, font=font, fill=text_color)
        line_num += 1
    draw.rectangle([int(image_width*0.05), int(image_height*0.05), int(image_width*0.95), int(image_height*0.95)], fill=None, outline='white', width=20)


def video_create_title():
    global video_title_str
    global VideoFps
    global StartFrame, first_absolute_frame, title_num_frames, frames_to_encode
    global file_type_out

    if len(video_title_str.get()): 
        title_duration = round(len(video_title_str.get())*50/1000) # 50 ms per char
        title_duration = min(title_duration, 10)    # no more than 10 sec
        title_duration = max(title_duration, 3)    # no less than 3 sec
        title_num_frames = min(title_duration * VideoFps, frames_to_encode-1)
        # Custom font style and font size
        img = Image.open(os.path.join(TargetDir, FrameOutputFilenamePattern % (StartFrame + first_absolute_frame, file_type_out)))
        myFont, num_lines = get_adjusted_font(img, video_title_str.get())
        if myFont == 0:
            return
        title_frame_idx = StartFrame + first_absolute_frame
        title_first_frame = random.randint(StartFrame + first_absolute_frame, StartFrame + first_absolute_frame + frames_to_encode - title_num_frames - 1)
        for i in range (title_first_frame, title_first_frame + title_num_frames):
            status_str = "Status: Generating title %.1f%%" % (((i - title_first_frame) * 100 / title_num_frames))
            app_status_label.config(text=status_str, fg='black')
            # Open an Image
            img = Image.open(os.path.join(TargetDir, FrameOutputFilenamePattern % ((int(i/2)+1)*2, file_type_out)))

            # Call draw Method to add 2D graphics in an image
            #I1 = ImageDraw.Draw(img)
            # Add Text to an image
            draw_multiple_line_text(img, video_title_str.get(), myFont, (255,255,255), num_lines)
            # Display edited image
            #img.show()

            # Save the edited image
            img.save(os.path.join(TargetDir, TitleOutputFilenamePattern % (title_frame_idx, file_type_out)))
            title_frame_idx += 1
            win.update()
    else:
        title_duration = 0
        title_num_frames = 0


def convert_ffmpeg_list_to_command_line(ffmpeg_list):
    """
    Converts a list of ffmpeg arguments to a command line string.

    Args:
        ffmpeg_list: A list of ffmpeg arguments.

    Returns:
        A string representing the ffmpeg command line.
    """

    quoted_list = []
    for item in ffmpeg_list:
        if ' ' in item or ';' in item or '[' in item or ']' in item or ',' in item or ':' in item or '=' in item: #add more characters as needed.
            quoted_list.append(f'"{item}"')
        else:
            quoted_list.append(item)

    return ' '.join(quoted_list)


def call_ffmpeg():
    global VideoTargetDir, TargetDir
    global cmd_ffmpeg
    global ffmpeg_preset
    global FfmpegBinName
    global TargetVideoFilename
    global StartFrame
    global ffmpeg_process, ffmpeg_success
    global ffmpeg_encoding_status
    global FrameOutputFilenamePattern
    global first_absolute_frame, frames_to_encode
    global out_frame_width, out_frame_height
    global title_num_frames
    global file_type_out

    if resolution_dict[project_config["VideoResolution"]] != '':
        video_width = resolution_dict[project_config["VideoResolution"]].split(':')[0]
        video_height = resolution_dict[project_config["VideoResolution"]].split(':')[1]

    cmd_ffmpeg = [FfmpegBinName,
                  '-y',
                  '-loglevel', 'error',
                  '-stats',
                  '-flush_packets', '1']
    if title_num_frames > 0:   # There is a title
        pattern = TitleOutputFilenamePattern_for_ffmpeg + file_type_out
        cmd_ffmpeg.extend(['-f', 'image2',
                           '-framerate', str(VideoFps),
                           '-start_number', str(StartFrame + first_absolute_frame),
                           '-i', os.path.join(TargetDir, pattern)])
    pattern = FrameOutputFilenamePattern_for_ffmpeg + file_type_out
    cmd_ffmpeg.extend(['-f', 'image2',
                       '-framerate', str(VideoFps),
                       '-start_number', str(StartFrame + first_absolute_frame),
                       '-i', os.path.join(TargetDir, pattern)])
    # Add soundtrack if enabled
    if enable_soundtrack:
        cmd_ffmpeg.extend(['-stream_loop', '-1', '-i', soundtrack_file_path])
    # Create filter_complex or one or two inputs
    filter_complex_options=''
    # Title sequence
    if title_num_frames > 0:   # There is a title
        filter_complex_options+='[0:v]'
        if (out_frame_width != 0 and out_frame_height != 0):
            filter_complex_options+='scale=w='+video_width+':h='+video_height+':'
        filter_complex_options+='force_original_aspect_ratio=decrease,pad='+video_width+':'+video_height+':(ow-iw)/2:(oh-ih)/2,setsar=1'
        if perform_denoise.get():
            filter_complex_options+=f',hqdn3d={FFmpeg_denoise_param}'
        filter_complex_options+='[v0];'
    # Main video
    # trim filter: Problems with some specific number of frames, which cause video encoding to extend till the end
    # Initially thought it happen with prime number, later verified it can be any number
    frames_to_encode_trim = frames_to_encode
    if title_num_frames > 0:   # There is a title
        filter_complex_options+='[1:v]'
    else:
        filter_complex_options += '[0:v]'
    filter_complex_options+='trim=start_frame=0:end_frame='+str(frames_to_encode_trim)+',setpts=PTS-STARTPTS[v1];'  # Limit number of frames of main video
    filter_complex_options+='[v1]'
    if (out_frame_width != 0 and out_frame_height != 0):
        filter_complex_options+='scale=w='+video_width+':h='+video_height+':'
    filter_complex_options+='force_original_aspect_ratio=decrease,pad='+video_width+':'+video_height+':(ow-iw)/2:(oh-ih)/2,setsar=1'
    if perform_denoise.get():
        filter_complex_options+=f',hqdn3d={FFmpeg_denoise_param}'
    filter_complex_options+='[v2];'
    # Concatenate title (if exists) + main video
    if title_num_frames > 0:   # There is a title
        filter_complex_options += '[v0]'
    filter_complex_options+='[v2]concat=n='+str(2 if title_num_frames>0 else 1)+':v=1[v]'
    cmd_ffmpeg.extend(['-filter_complex', filter_complex_options])

    if not enable_soundtrack:
        cmd_ffmpeg.extend(['-an'])  # no audio
    cmd_ffmpeg.extend(
        ['-vcodec', 'libx264',
         '-preset', ffmpeg_preset.get(),
         '-crf', '18',
         '-pix_fmt', 'yuv420p',
         '-map', '[v]'])
    if enable_soundtrack:
        if title_num_frames > 0:   # There is a title
            cmd_ffmpeg.extend(['-map', '2:a'])
        else:
            cmd_ffmpeg.extend(['-map', '1:a'])
    cmd_ffmpeg.extend(
         ['-frames:v', str(title_num_frames + frames_to_encode_trim),
         os.path.join(video_target_dir_str.get(),
                      TargetVideoFilename)])

    logging.debug("Generated ffmpeg command: %s", cmd_ffmpeg)
    logging.debug("Generated ffmpeg command (command line): %s", convert_ffmpeg_list_to_command_line(cmd_ffmpeg))
    ffmpeg_process = sp.Popen(cmd_ffmpeg, stderr=sp.STDOUT,
                              stdout=sp.PIPE,
                              universal_newlines=True)
    ffmpeg_success = ffmpeg_process.wait() == 0
    ffmpeg_encoding_status = ffmpeg_state.Completed


def video_generation_loop():
    global Go_btn
    global VideoTargetDir
    global TargetVideoFilename
    global ffmpeg_success, ffmpeg_encoding_status
    global ffmpeg_process
    global frames_to_encode, title_num_frames
    global app_status_label
    global BatchJobRunning
    global StartFrame, first_absolute_frame, frames_to_encode
    global frame_selected, last_displayed_image
    global frame_slider

    if ffmpeg_encoding_status == ffmpeg_state.Pending:
        # Check for special cases first
        if frames_to_encode == 0:
            status_str = "Status: No frames to encode"
            app_status_label.config(text=status_str, fg='red')
            if not BatchJobRunning:
                tk.messagebox.showwarning(
                    "No frames match range to generate video",
                    "Video cannot be generated.\r\n"
                    "No frames in target folder match the specified range.\r\n"
                    "Please review your settings and try again.")
            logging.error(f"Cannot generate video {TargetVideoFilename}, no frames to encode")
            generation_exit(success = False)  # Restore all settings to normal
        elif not valid_generated_frame_range():
            status_str = "Status: No frames to encode"
            app_status_label.config(text=status_str, fg='red')
            logging.error(f"Cannot generate video {TargetVideoFilename}, due to some frames missing in range "
                          f"{StartFrame+first_absolute_frame}, {StartFrame+first_absolute_frame+frames_to_encode}")
            if not BatchJobRunning:
                tk.messagebox.showerror(
                    "Frames missing",
                    "Video cannot be generated.\r\n"
                    f"Not all frames in specified range ({StartFrame+first_absolute_frame}, {StartFrame+first_absolute_frame+frames_to_encode}) exist in target folder to "
                    "allow video generation.\r\n"
                    "Please regenerate frames making sure option "
                    "\'Skip Frame regeneration\' is not selected, and try again.")
            generation_exit(success = False)  # Restore all settings to normal
        else:
            get_target_dir_file_list()  # Refresh target dir file list here as well for batch mode encoding
            logging.debug(
                "First filename in list: %s, extracted number: %s",
                os.path.basename(SourceDirFileList[0]), first_absolute_frame)
            video_create_title()
            ffmpeg_success = False
            ffmpeg_encoding_thread = threading.Thread(target=call_ffmpeg)
            ffmpeg_encoding_thread.daemon = True
            ffmpeg_encoding_thread.start()
            win.update()
            ffmpeg_encoding_status = ffmpeg_state.Running
            win.after(200, video_generation_loop)
    elif ffmpeg_encoding_status == ffmpeg_state.Running:
        if ConvertLoopExitRequested:
            ffmpeg_process.terminate()
            logging.warning("Video generation terminated by user for %s",
                         os.path.join(video_target_dir_str.get(), TargetVideoFilename))
            status_str = "Status: Cancelled by user"
            app_status_label.config(text=status_str, fg='red')
            tk.messagebox.showinfo(
                "FFMPEG encoding interrupted by user",
                "\r\nVideo generation by FFMPEG has been stopped by user "
                "action.")
            generation_exit(success = False)  # Restore all settings to normal
            os.remove(os.path.join(video_target_dir_str.get(), TargetVideoFilename))
        else:
            line = ffmpeg_process.stdout.readline().strip()
            logging.debug(line)
            if line:
                frame_str = str(line)[:-1].replace('=', ' ').split()[1]
                if is_a_number(frame_str):  # Sometimes ffmpeg output might be corrupted on the way
                    encoded_frame = int(frame_str)
                    frame_selected.set(StartFrame + first_absolute_frame + encoded_frame)
                    frame_slider.set(StartFrame + first_absolute_frame + encoded_frame)
                    refresh_current_frame_ui_info(encoded_frame, first_absolute_frame)
                    status_str = f"Status: Generating video {encoded_frame*100/(frames_to_encode+title_num_frames):.1f}%"
                    app_status_label.config(text=status_str, fg='black')
                    display_output_frame_by_number(encoded_frame)
                else:
                    app_status_label.config(text='Error, ffmpeg sync lost', fg='red')
                    logging.error("Error, ffmpeg sync lost. Line parsed: %s", line)
            else:
                status_str = "No feedback from ffmpeg"
                app_status_label.config(text=status_str, fg='red')
            win.after(200, video_generation_loop)
    elif ffmpeg_encoding_status == ffmpeg_state.Completed:
        status_str = "Status: Generating video 100%"
        app_status_label.config(text=status_str, fg='black')
        last_displayed_image = 0
        # And display results
        if ffmpeg_success:
            logging.debug("Video generated OK: %s", os.path.join(video_target_dir_str.get(), TargetVideoFilename))
            status_str = "Status: Video generated OK"
            app_status_label.config(text=status_str, fg='green')
            if not BatchJobRunning:
                tk.messagebox.showinfo(
                    "Video generation by ffmpeg has ended",
                    "\r\nVideo encoding has finalized successfully. "
                    "You can find your video in the target folder, "
                    "as stated below\r\n" +
                    os.path.join(video_target_dir_str.get(), TargetVideoFilename))
        else:
            logging.error("Video generation failed for %s", os.path.join(video_target_dir_str.get(), TargetVideoFilename))
            status_str = "Status: Video generation failed"
            app_status_label.config(text=status_str, fg='red')
            if not BatchJobRunning:
                tk.messagebox.showinfo(
                    "FFMPEG encoding failed",
                    "\r\nVideo generation by FFMPEG has failed\r\nPlease "
                    "check the logs to determine what the problem was.")
            else:
                logging.error(f"FFMPEG encoding failed for video {TargetVideoFilename}")
        generation_exit(success = ffmpeg_success)  # Restore all settings to normal


"""
###############################
Application top level functions
###############################
"""

# Validation function for different widgets
def validate_entry_length(P, widget_name):
    max_lengths = {
        "video_filename": 100,  # First Entry widget (Tkinter auto-names widgets)
        "video_title": 200,   # Second Entry widget
    }

    max_length = max_lengths.get(widget_name.split(".")[-1], 10)  # Default to 10 if not found
    if len(P) > max_length:
        tk.messagebox.showerror("Error!",
                            f"Maximum length for this field is {max_length}")
        return 
    return len(P) <= max_length


def gamma_enforce_min_value(event=None):
    """Ensure value is strictly greater than zero when focus is lost."""
    try:
        value = float(gamma_correction_spinbox.get())
        if value <= 0:
            gamma_correction_spinbox.delete(0, tk.END)
            gamma_correction_spinbox.insert(0, "0.1")  # Reset to smallest valid value
    except ValueError:
        gamma_correction_spinbox.delete(0, tk.END)
        gamma_correction_spinbox.insert(0, "0.1")  # Reset if input is completely invalid


def multiprocessing_init():
    global num_threads
    global frame_encoding_queue, subprocess_event_queue

    num_cores = os.cpu_count()

    if num_threads == 0:
        if num_cores is not None:
            logging.debug(f"{num_cores} cores available")
            num_threads = int(num_cores/2)
        else:
            logging.debug("Unable to determine number of cores available")
            num_threads = 4

    logging.debug(f"Creating {num_threads} threads")

    frame_encoding_queue = queue.Queue(maxsize=20)
    subprocess_event_queue = queue.Queue(maxsize=20)


def init_display():
    global SourceDir
    global CurrentFrame
    global SourceDirFileList
    global PreviewWidth, PreviewHeight, PreviewRatio

    # Get first file
    if SourceDir == "":
        tk.messagebox.showerror("Error!",
                                "Please specify source and target folders.")
        return

    os.chdir(SourceDir)

    if len(SourceDirFileList) == 0:
        return

    if CurrentFrame >= len(SourceDirFileList):
        CurrentFrame = len(SourceDirFileList) - 1
    file = SourceDirFileList[CurrentFrame]

    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)

    # Calculate preview image display ratio
    image_height = img.shape[0]
    image_width = img.shape[1]
    if abs(PreviewWidth - image_width) > abs(PreviewHeight - image_height):
        PreviewRatio = PreviewWidth/image_width
    else:
        PreviewRatio = PreviewHeight/image_height

    frame_slider.set(CurrentFrame)
    select_scale_frame(CurrentFrame)
    win.after(5, scale_display_update)


def init_logging():
    global LogLevel
    # Initialize logging
    log_path = logs_dir
    if log_path == "":
        log_path = os.getcwd()
    log_file_fullpath = log_path + "/AfterScan." + time.strftime("%Y%m%d") + ".log"
    logging.basicConfig(
        level=LogLevel,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file_fullpath),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info("AfterScann %s (%s)", __version__, __date__)
    logging.info("Log file: %s", log_file_fullpath)


def verify_templates():
    retvalue = True
    error_message = ""
    files_missing = []
    files_invalid = []
    for jpg, expected in EXPECTED_HASHES.items():
        if not os.path.exists(os.path.join(script_dir, jpg)):
            retvalue = False
            files_missing.append(jpg)
            continue
        with open(os.path.join(script_dir, jpg), 'rb') as f:
            current = hashlib.sha256(f.read()).hexdigest()
        if current != expected:
            retvalue = False
            files_invalid.append(jpg)
    if not retvalue:
        error_message = "Error when loading template files.\r\n"
        if len(files_missing) > 0:
            error_message += f"Missing files: {', '.join(files_missing)}"
            if len(files_invalid) > 0:
                error_message += "\r\n"
        if len(files_invalid) > 0:
            error_message += f"Invalid files: {', '.join(files_invalid)}"
        error_message += f"\r\nPlease install the correct template files for AfterScan {__version__} and try again."
        tk.messagebox.showerror("Error!", error_message)
    return retvalue, error_message


def afterscan_init():
    global win, as_tooltips
    global TopWinX
    global TopWinY
    global WinInitDone
    global SourceDir
    global PreviewWidth, PreviewHeight
    global screen_height
    global BigSize, FontSize
    global MergeMertens, AlignMtb
    global match_level_average, horizontal_offset_average, move_x_average, move_y_average

    win = Tk()  # Create main window, store it in 'win'

    # Get screen size - maxsize gives the usable screen size
    screen_width, screen_height = win.maxsize()
    # Set dimensions of UI elements adapted to screen size
    if (screen_height >= 1000 and not ForceSmallSize) or ForceBigSize:
        BigSize = True
        FontSize = 11
        PreviewWidth = 700
        PreviewHeight = 525
        app_width = PreviewWidth + 420
        app_height = PreviewHeight + 330
    else:
        BigSize = False
        FontSize = 8
        PreviewWidth = 500
        PreviewHeight = 375
        app_width = PreviewWidth + 380
        app_height = PreviewHeight + 330

    display_window_title()  # setting title of the window
    if 'WindowPos' in general_config:
         win.geometry(f"+{general_config['WindowPos'].split('+', 1)[1]}")

    win.update_idletasks()

    # Set default font size
    # Change the default Font that will affect in all the widgets
    win.option_add("*font", "TkDefaultFont 10")

    # Init ToolTips
    as_tooltips = Tooltips(FontSize)

    # Init rolling Averages
    match_level_average = RollingAverage(50)
    horizontal_offset_average = RollingAverage(50)
    move_x_average = RollingAverage(50)
    move_y_average = RollingAverage(50)

    # Get Top window coordinates
    TopWinX = win.winfo_x()
    TopWinY = win.winfo_y()

    # Create MergeMertens Object for HDR
    MergeMertens = cv2.createMergeMertens()
    # Create Align MTB object for HDR
    AlignMtb = cv2.createAlignMTB()

    WinInitDone = True

    if not HAS_TEMPORAL_DENOISE:
        logging.info(f"Temporal denoise not available. OpenCV version is {cv2.__version__}")

    logging.debug("AfterScan initialized")


def display_window_title():
    title = f"{__module__} {__version__}"
    if JobListFilename != default_job_list_filename:
        aux = os.path.split(JobListFilename)[1]
        if aux.endswith('.json'):
            aux = aux.removesuffix('.json')
        if aux.endswith('.joblist'):
            aux = aux.removesuffix('.joblist')
        title += f" - {aux}"
    win.title(title)  # setting title of the window


# To avoid gap in the right of last column, adjust last column width once
def adjust_last_column():
    total_width = job_list_treeview.winfo_width()
    other_columns_width = sum(job_list_treeview.column(col, "width") for col in job_list_treeview["columns"][:-1])
    last_col = job_list_treeview["columns"][-1]
    job_list_treeview.column(last_col, width=max(100, total_width - other_columns_width))    


def build_ui():
    global win
    global SourceDir
    global frames_source_dir, frames_target_dir, video_target_dir, video_target_dir_str
    global perform_cropping, cropping_btn
    global perform_denoise, perform_denoise_checkbox
    global perform_sharpness, perform_sharpness_checkbox
    global perform_gamma_correction_checkbox, gamma_correction_spinbox
    global generate_video, generate_video_checkbox
    global encode_all_frames, encode_all_frames_checkbox
    global frames_to_encode_str, frames_to_encode, frames_to_encode_label
    global save_bg, save_fg
    global source_folder_btn, target_folder_btn
    global perform_stabilization, perform_stabilization_checkbox
    global stabilization_threshold_spinbox, stabilization_threshold_str
    global stabilization_threshold_match_label
    global perform_rotation, perform_rotation_checkbox, rotation_angle_label
    global rotation_angle_spinbox, rotation_angle_str
    global custom_stabilization_btn, stabilization_threshold_label, low_contrast_custom_template_checkbox
    global perform_cropping_checkbox, Crop_btn
    global perform_gamma_correction, gamma_correction_str
    global force_4_3_crop_checkbox, force_4_3_crop
    global force_16_9_crop_checkbox, force_16_9_crop
    global Go_btn
    global Exit_btn
    global video_fps_dropdown_selected, skip_frame_regeneration_cb
    global video_fps_dropdown, video_fps_label, video_filename_name, video_filename_str, video_title_name, video_title_str
    global resolution_dropdown, resolution_label, resolution_dropdown_selected
    global video_target_folder_btn, video_filename_label, video_title_label
    global ffmpeg_preset
    global ffmpeg_preset_rb1, ffmpeg_preset_rb2, ffmpeg_preset_rb3
    global FfmpegBinName
    global skip_frame_regeneration
    global frame_slider, selected_frame_time, CurrentFrame, frame_selected, selected_frame_number, selected_frame_index
    global film_type
    global job_list_treeview, job_list_listbox_disabled
    global app_status_label
    global PreviewWidth, PreviewHeight
    global left_area_frame
    global draw_capture_canvas
    global custom_ffmpeg_path
    global project_config
    global start_batch_btn, add_job_btn, delete_job_btn, rerun_job_btn
    global film_type_S8_rb, film_type_R8_rb
    global frame_from_str, frame_to_str, frame_from_entry, frame_to_entry, frames_separator_label
    global suspend_on_joblist_end
    global frame_fill_type
    global extended_stabilization, extended_stabilization_checkbox
    global RotationAngle
    global suspend_on_completion
    global perform_fill_none_rb, perform_fill_fake_rb, perform_fill_dumb_rb
    global ExpertMode
    global BigSize, FontSize
    global template_list
    global low_contrast_custom_template
    global display_template_popup_btn
    global stabilization_shift_y_value, stabilization_shift_label, stabilization_shift_y_spinbox
    global stabilization_shift_x_value, stabilization_shift_x_spinbox

    # Menu bar
    menu_bar = tk.Menu(win)
    win.config(menu=menu_bar)
    
    # Register max length validation function
    vcmd = (win.register(validate_entry_length), "%P", "%W")  # Pass widget name (%W)

    # File menu
    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="File", menu=file_menu, font=("Arial", FontSize))
    file_menu.add_command(label="Save job list", command=save_named_job_list, font=("Arial", FontSize))
    file_menu.add_command(label="Load job list", command=load_named_job_list, font=("Arial", FontSize))
    file_menu.add_separator()  # Optional divider
    file_menu.add_command(label="Exit", command=exit_app, font=("Arial", FontSize))

    # Help Menu
    help_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Help", menu=help_menu, font=("Arial", FontSize))
    help_menu.add_command(label="User Guide", font=("Arial", FontSize), 
                          command=lambda: webbrowser.open("https://github.com/jareff-g/AfterScan/wiki/AfterScan-user-interface-description"))
    help_menu.add_command(label="Discord Server", font=("Arial", FontSize), 
                          command=lambda: webbrowser.open("https://discord.gg/r2UGkH7qg2"))
    help_menu.add_command(label="AfterScan Wiki", font=("Arial", FontSize), 
                          command=lambda: webbrowser.open("https://github.com/jareff-g/AfterScan/wiki"))
    if UserConsent == "no":
        help_menu.add_command(label="Report AfterScan usage", font=("Arial", FontSize), 
                              command=lambda: get_consent(True))
    help_menu.add_command(label="About AfterScan", font=("Arial", FontSize), 
                          command=lambda: webbrowser.open("https://github.com/jareff-g/AfterScan/wiki/AfterScan:-8mm,-Super-8-film-post-scan-utility"))

    # Create a frame to add a border to the preview
    left_area_frame = Frame(win)
    #left_area_frame.grid(row=0, column=0, padx=5, pady=5, sticky=N)
    left_area_frame.pack(side=LEFT, padx=5, pady=5, anchor=N)
    # Create a LabelFrame to act as a border
    border_frame = tk.LabelFrame(left_area_frame, bd=2, relief=tk.GROOVE)
    border_frame.pack(expand=True, fill="both", padx=5, pady=5)
    # Create the canvas
    draw_capture_canvas = Canvas(border_frame, bg='dark grey', width=PreviewWidth, height=PreviewHeight)
    draw_capture_canvas.pack(side=TOP, anchor=N)
    # Initialize canvas image (to avoid multiple use of create_image)
    #Create an empty photoimage
    draw_capture_canvas.image = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0))) #create a transparent 1x1 image.
    draw_capture_canvas.image_id = draw_capture_canvas.create_image(0, 0, anchor=tk.NW, image=draw_capture_canvas.image)

    # New scale under canvas 
    frame_selected = IntVar()
    frame_slider = Scale(border_frame, orient=HORIZONTAL, from_=0, to=0, showvalue=False,
                         variable=frame_selected, highlightthickness=1,
                         length=PreviewWidth, takefocus=1, font=("Arial", FontSize))
    frame_slider.bind("<ButtonRelease-1>", process_scale_value)
    frame_slider.bind("<KeyRelease>", process_scale_value)
    frame_slider.pack(side=BOTTOM, pady=4)
    frame_slider.set(CurrentFrame)
    as_tooltips.add(frame_slider, "Browse around frames to be processed")

    # Frame for standard widgets to the right of the preview
    right_area_frame = Frame(win)
    #right_area_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky=N)
    right_area_frame.pack(side=LEFT, padx=5, pady=5, anchor=N)

    # Frame for top section of standard widgets ******************************
    regular_top_section_frame = Frame(right_area_frame)
    regular_top_section_frame.pack(side=TOP, padx=2, pady=2)

    # Create frame to display current frame and slider
    frame_frame = LabelFrame(regular_top_section_frame, text='Current frame',
                               width=35, height=10, font=("Arial", FontSize-2))
    frame_frame.grid(row=1, column=0, sticky='nsew')

    selected_frame_number = Label(frame_frame, width=12, text='Number:', font=("Arial", FontSize))
    selected_frame_number.pack(side=TOP, pady=2)
    as_tooltips.add(selected_frame_number, "Frame number, as stated in the filename")

    selected_frame_index = Label(frame_frame, width=12, text='Index:', font=("Arial", FontSize))
    selected_frame_index.pack(side=TOP, pady=2)
    as_tooltips.add(selected_frame_index, "Sequential frame index, from 1 to n")

    selected_frame_time = Label(frame_frame, width=12, text='Time:', font=("Arial", FontSize))
    selected_frame_time.pack(side=TOP, pady=2)
    as_tooltips.add(selected_frame_time, "Time in the source film where this frame is located")

    # Application status label
    app_status_label = Label(regular_top_section_frame, width=46 if BigSize else 46, borderwidth=2,
                             relief="groove", text='Status: Idle',
                             highlightthickness=1, font=("Arial", FontSize))
    app_status_label.grid(row=2, column=0, columnspan=3, pady=5, sticky=EW)

    # Application Exit button
    Exit_btn = Button(regular_top_section_frame, text="Exit", width=10,
                      height=5, command=exit_app, activebackground='red',
                      activeforeground='white', wraplength=80, font=("Arial", FontSize))
    Exit_btn.grid(row=0, column=1, rowspan=2, padx=10, sticky='nsew')

    as_tooltips.add(Exit_btn, "Exit AfterScan")

    # Application start button
    Go_btn = Button(regular_top_section_frame, text="Start", width=12, height=5,
                    command=start_convert, activebackground='green',
                    activeforeground='white', wraplength=80, font=("Arial", FontSize))
    Go_btn.grid(row=0, column=2, rowspan=2, sticky='nsew')

    as_tooltips.add(Go_btn, "Start post-processing using current settings")

    # Add AfterScan Logo
    win.update_idletasks()
    available_width = frame_frame.winfo_width()
    logo_file = os.path.join(script_dir, "AfterScan_logo.jpeg")
    try:
        logo_image = Image.open(logo_file)  # Replace with your logo file name
    except FileNotFoundError as e:
        logo_image = None
        logging.warning(f"Could not find AfterScan logo file: {e}")
    if logo_image != None:
        # Resize the image (e.g., to 50% of its original size)
        ratio = available_width / logo_image.width
        new_width = int(logo_image.width * ratio)
        new_height = int(logo_image.height * ratio)
        resized_logo = logo_image.resize((new_width, new_height), Image.LANCZOS) #use LANCZOS for high quality resizing.
        # Convert to PhotoImage
        logo_image = ImageTk.PhotoImage(resized_logo)
        if logo_image:
            logo_label = tk.Label(regular_top_section_frame, image=logo_image)

            # Delete reference to previous image, if any
            aux_image = None
            if hasattr(logo_label, 'image'):
                aux_image = logo_label.image
            logo_label.image = logo_image  # Keep a reference!
            if aux_image:
                del aux_image
            logo_label.grid(row=0, column=0, sticky='nsew')

    # Create frame to select source and target folders *******************************
    folder_frame = LabelFrame(right_area_frame, text='Folder selection', width=30,
                              height=8, font=("Arial", FontSize-2))
    folder_frame.pack(padx=2, pady=2, ipadx=5, expand=True, fill="both")

    source_folder_frame = Frame(folder_frame)
    source_folder_frame.pack(side=TOP)
    frames_source_dir = Entry(source_folder_frame, width=34 if BigSize else 34,
                                    borderwidth=1, font=("Arial", FontSize))
    frames_source_dir.pack(side=LEFT)
    frames_source_dir.delete(0, 'end')
    frames_source_dir.insert('end', SourceDir)
    frames_source_dir.after(100, frames_source_dir.xview_moveto, 1)
    frames_source_dir.bind('<<Paste>>', lambda event, entry=frames_source_dir: on_paste_all_entries(event, entry))

    as_tooltips.add(frames_source_dir, "Directory where the source frames are located")

    source_folder_btn = Button(source_folder_frame, text='Source', width=6,
                               height=1, command=set_source_folder,
                               activebackground='green',
                               activeforeground='white', wraplength=80, font=("Arial", FontSize))
    source_folder_btn.pack(side=LEFT)

    as_tooltips.add(source_folder_btn, "Selects the directory where the source frames are located")

    target_folder_frame = Frame(folder_frame)
    target_folder_frame.pack(side=TOP)
    frames_target_dir = Entry(target_folder_frame, width=34 if BigSize else 34,
                                    borderwidth=1, font=("Arial", FontSize))
    frames_target_dir.pack(side=LEFT)
    frames_target_dir.bind('<<Paste>>', lambda event, entry=frames_target_dir: on_paste_all_entries(event, entry))
    
    as_tooltips.add(frames_target_dir, "Directory where generated frames will be stored")

    target_folder_btn = Button(target_folder_frame, text='Target', width=6,
                               height=1, command=set_frames_target_folder,
                               activebackground='green',
                               activeforeground='white', wraplength=80, font=("Arial", FontSize))
    target_folder_btn.pack(side=LEFT)

    as_tooltips.add(target_folder_btn, "Selects the directory where the generated frames will be stored")

    save_bg = source_folder_btn['bg']
    save_fg = source_folder_btn['fg']

    folder_bottom_frame = Frame(folder_frame)
    folder_bottom_frame.pack(side=BOTTOM, ipady=2)

    # Define post-processing area *********************************************
    postprocessing_frame = LabelFrame(right_area_frame,
                                      text='Frame post-processing',
                                      width=40, height=8, font=("Arial", FontSize-2))
    postprocessing_frame.pack(padx=2, pady=2, ipadx=5, expand=True, fill="both")
    postprocessing_row = 0
    postprocessing_frame.grid_columnconfigure(0, weight=1)
    postprocessing_frame.grid_columnconfigure(1, weight=1)
    postprocessing_frame.grid_columnconfigure(2, weight=1)

    # Radio buttons to select R8/S8. Required to select adequate pattern, and match position
    film_type = StringVar()
    film_type_S8_rb = Radiobutton(postprocessing_frame, text="Super 8", variable=film_type, command=set_film_type,
                                  width=11 if BigSize else 11, value='S8', font=("Arial", FontSize))
    film_type_S8_rb.grid(row=postprocessing_row, column=0, sticky=W)
    as_tooltips.add(film_type_S8_rb, "Handle as Super 8 film")
    film_type_R8_rb = Radiobutton(postprocessing_frame, text="Regular 8", variable=film_type, command=set_film_type,
                                  width=11 if BigSize else 11, value='R8', font=("Arial", FontSize))
    film_type_R8_rb.grid(row=postprocessing_row, column=1, sticky=W)
    as_tooltips.add(film_type_R8_rb, "Handle as 8mm (Regular 8) film")
    film_type.set(project_config["FilmType"])
    postprocessing_row += 1

    # Check box to select encoding of all frames
    encode_all_frames = tk.BooleanVar(value=False)
    encode_all_frames_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Encode all frames',
        variable=encode_all_frames, onvalue=True, offvalue=False,
        command=encode_all_frames_selection, width=14, font=("Arial", FontSize))
    encode_all_frames_checkbox.grid(row=postprocessing_row, column=0,
                                           columnspan=3, sticky=W)
    as_tooltips.add(encode_all_frames_checkbox, "If selected, all frames in source folder will be encoded")
    postprocessing_row += 1

    # Entry to enter start/end frames
    frames_to_encode_label = tk.Label(postprocessing_frame,
                                      text='Frame range:',
                                      width=12, font=("Arial", FontSize))
    frames_to_encode_label.grid(row=postprocessing_row, column=0, columnspan=2, sticky=W)
    frame_from_str = tk.StringVar(value=str(from_frame))
    frame_from_entry = Entry(postprocessing_frame, textvariable=frame_from_str, width=5, borderwidth=1, font=("Arial", FontSize))
    frame_from_entry.grid(row=postprocessing_row, column=1, sticky=W)
    frame_from_entry.config(state=NORMAL)
    frame_from_entry.bind("<Double - Button - 1>", update_frame_from)
    frame_from_entry.bind("<Button - 2>", update_frame_from)
    frame_from_entry.bind('<<Paste>>', lambda event, entry=frame_from_entry: on_paste_all_entries(event, entry))
    as_tooltips.add(frame_from_entry, "First frame to be processed, if not encoding the entire set")
    frame_to_str = tk.StringVar(value=str(from_frame))
    frames_separator_label = tk.Label(postprocessing_frame, text='to', width=2, font=("Arial", FontSize))
    frames_separator_label.grid(row=postprocessing_row, column=1)
    frame_to_entry = Entry(postprocessing_frame, textvariable=frame_to_str, width=5, borderwidth=1, font=("Arial", FontSize))
    frame_to_entry.grid(row=postprocessing_row, column=1, sticky=E)
    frame_to_entry.config(state=NORMAL)
    frame_to_entry.bind("<Double - Button - 1>", update_frame_to)
    frame_to_entry.bind("<Button - 2>", update_frame_to)
    frame_to_entry.bind('<<Paste>>', lambda event, entry=frame_to_entry: on_paste_all_entries(event, entry))
    as_tooltips.add(frame_to_entry, "Last frame to be processed, if not encoding the entire set")

    postprocessing_row += 1

    # Check box to do rotate image
    perform_rotation = tk.BooleanVar(value=False)
    perform_rotation_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Rotate image:',
        variable=perform_rotation, onvalue=True, offvalue=False, width=11,
        command=perform_rotation_selection, font=("Arial", FontSize))
    perform_rotation_checkbox.grid(row=postprocessing_row, column=0,
                                        columnspan=1, sticky=W)
    perform_rotation_checkbox.config(state=NORMAL)
    as_tooltips.add(perform_rotation_checkbox, "Rotate generated frames")

    # Spinbox to select rotation angle
    rotation_angle_str = tk.StringVar(value=str(0))
    #rotation_angle_selection_aux = postprocessing_frame.register(rotation_angle_selection)
    rotation_angle_spinbox = tk.Spinbox(
        postprocessing_frame,
        command=rotation_angle_selection, width=5,
        textvariable=rotation_angle_str, from_=-5, to=5,
        format="%.1f", increment=0.1, font=("Arial", FontSize))
    rotation_angle_spinbox.grid(row=postprocessing_row, column=1, sticky=W)
    rotation_angle_spinbox.bind("<FocusOut>", rotation_angle_spinbox_focus_out)
    as_tooltips.add(rotation_angle_spinbox, "Angle to use when rotating frames")
    #rotation_angle_selection('down')
    rotation_angle_label = tk.Label(postprocessing_frame,
                                      text='°',
                                      width=1, font=("Arial", FontSize))
    rotation_angle_label.grid(row=postprocessing_row, column=1)
    rotation_angle_label.config(state=NORMAL)
    postprocessing_row += 1

    ### Stabilization controls
    # Custom film perforation template
    custom_stabilization_btn = Button(postprocessing_frame,
                                      text='Define custom template',
                                      width=18, height=1,
                                      command=select_custom_template,
                                      activebackground='green',
                                      activeforeground='white', font=("Arial", FontSize))
    custom_stabilization_btn.config(relief=SUNKEN if template_list.get_active_type() == 'Custom' else RAISED)
    custom_stabilization_btn.grid(row=postprocessing_row, column=0, columnspan=2, padx=5, pady=5, sticky=W)
    as_tooltips.add(custom_stabilization_btn,
                  "Define a custom template for this project (vs the automatic template defined by AfterScan)")

    low_contrast_custom_template = tk.BooleanVar(value=False)
    low_contrast_custom_template_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Low contrast helper',
        variable=low_contrast_custom_template, onvalue=True, offvalue=False, width=16,
        command=low_contrast_custom_template_selection, font=("Arial", FontSize))
    low_contrast_custom_template_checkbox.grid(row=postprocessing_row, column=1,
                                        columnspan=2, sticky=E)
    as_tooltips.add(low_contrast_custom_template_checkbox, "Activate when defining a custom template using a low contrast frame")

    postprocessing_row += 1

    # Check box to do stabilization or not
    perform_stabilization = tk.BooleanVar(value=False)
    perform_stabilization_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Stabilize',
        variable=perform_stabilization, onvalue=True, offvalue=False, width=7,
        command=perform_stabilization_selection, font=("Arial", FontSize))
    perform_stabilization_checkbox.grid(row=postprocessing_row, column=0,
                                        columnspan=1, sticky=W)
    as_tooltips.add(perform_stabilization_checkbox, "Stabilize generated frames. Sprocket hole is used as common reference, it needs to be clearly visible")
    # Label to display the match level of current frame to template
    stabilization_threshold_match_label = Label(postprocessing_frame, width=4, borderwidth=1, relief='sunken', font=("Arial", FontSize))
    stabilization_threshold_match_label.grid(row=postprocessing_row, column=0, sticky=E)
    as_tooltips.add(stabilization_threshold_match_label, "Dynamically displays the match quality of the sprocket hole template. Green is good, orange acceptable, red is bad")

    # Extended search checkbox (replace radio buttons for fast/precise stabilization)
    extended_stabilization = tk.BooleanVar(value=False)
    extended_stabilization_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Extend',
        variable=extended_stabilization, onvalue=True, offvalue=False, width=6,
        command=extended_stabilization_selection, font=("Arial", FontSize))
    #extended_stabilization_checkbox.grid(row=postprocessing_row, column=1, columnspan=1, sticky=W)
    extended_stabilization_checkbox.forget()
    as_tooltips.add(extended_stabilization_checkbox, "Extend the area where AfterScan looks for sprocket holes. In some cases this might help")

    # Stabilization shift: Since film might not be centered around hole(s) this gives the option to move it up/down
    # Spinbox for gamma correction
    stabilization_shift_label = tk.Label(postprocessing_frame, text='Offset X/Y:',
                                        width=14, font=("Arial", FontSize))
    stabilization_shift_label.grid(row=postprocessing_row, column=1, columnspan=1, sticky=E)

    stabilization_shift_x_value = tk.IntVar(value=0)
    stabilization_shift_x_spinbox = tk.Spinbox(postprocessing_frame, width=3, command=select_stabilization_shift_x,
        textvariable=stabilization_shift_x_value, from_=-150, to=150, increment=-5, font=("Arial", FontSize))
    stabilization_shift_x_spinbox.grid(row=postprocessing_row, column=2, sticky=W)
    as_tooltips.add(stabilization_shift_x_spinbox, "Allows to shift the frame left or right after stabilization "
                                "(to compensate for films where the frame is not centered around the hole/holes)")
    stabilization_shift_x_spinbox.bind("<FocusOut>", select_stabilization_shift_x)

    stabilization_shift_y_value = tk.IntVar(value=0)
    stabilization_shift_y_spinbox = tk.Spinbox(postprocessing_frame, width=3, command=select_stabilization_shift_y,
        textvariable=stabilization_shift_y_value, from_=-150, to=150, increment=-5, font=("Arial", FontSize))
    stabilization_shift_y_spinbox.grid(row=postprocessing_row, column=2, sticky=E)
    as_tooltips.add(stabilization_shift_y_spinbox, "Allows to shift the frame up or down after stabilization "
                                "(to compensate for films where the frame is not centered around the hole/holes)")
    stabilization_shift_y_spinbox.bind("<FocusOut>", select_stabilization_shift_y)

    postprocessing_row += 1

    ### Cropping controls
    # Check box to do cropping or not
    cropping_btn = Button(postprocessing_frame, text='Define crop area',
                          width=12, height=1, command=select_cropping_area,
                          activebackground='green', activeforeground='white',
                          wraplength=120, font=("Arial", FontSize))
    cropping_btn.grid(row=postprocessing_row, column=0, sticky=E)
    as_tooltips.add(cropping_btn, "Open popup window to define the cropping rectangle")

    perform_cropping = tk.BooleanVar(value=False)
    perform_cropping_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Crop', variable=perform_cropping,
        onvalue=True, offvalue=False, command=perform_cropping_selection,
        width=4, font=("Arial", FontSize))
    perform_cropping_checkbox.grid(row=postprocessing_row, column=1, sticky=W)
    as_tooltips.add(perform_cropping_checkbox, "Crop generated frames to the user-defined limits ('Define crop area' button)")

    force_4_3_crop = tk.BooleanVar(value=False)
    force_4_3_crop_checkbox = tk.Checkbutton(
        postprocessing_frame, text='4:3', variable=force_4_3_crop,
        onvalue=True, offvalue=False, command=force_4_3_selection,
        width=4, font=("Arial", FontSize))
    force_4_3_crop_checkbox.grid(row=postprocessing_row, column=1, sticky=E)
    as_tooltips.add(force_4_3_crop_checkbox, "Enforce 4:3 aspect ratio when defining the cropping rectangle")

    force_16_9_crop = tk.BooleanVar(value=False)
    force_16_9_crop_checkbox = tk.Checkbutton(
        postprocessing_frame, text='16:9', variable=force_16_9_crop,
        onvalue=True, offvalue=False, command=force_16_9_selection,
        width=4, font=("Arial", FontSize))
    force_16_9_crop_checkbox.grid(row=postprocessing_row, column=2, sticky=W)
    as_tooltips.add(force_16_9_crop_checkbox, "Enforce 16:9 aspect ratio when defining the cropping rectangle")

    postprocessing_row += 1

    # Check box to perform denoise
    perform_denoise = tk.BooleanVar(value=False)
    perform_denoise_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Denoise', variable=perform_denoise,
        onvalue=True, offvalue=False, command=perform_denoise_selection,
        font=("Arial", FontSize))
    perform_denoise_checkbox.grid(row=postprocessing_row, column=0, sticky=W)
    as_tooltips.add(perform_denoise_checkbox, "Apply denoise algorithm (using OpenCV's 'fastNlMeansDenoisingColored') to the generated frames")

    # Check box to perform sharpness
    perform_sharpness = tk.BooleanVar(value=False)
    perform_sharpness_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Sharpen', variable=perform_sharpness,
        onvalue=True, offvalue=False, command=perform_sharpness_selection,
        font=("Arial", FontSize))
    perform_sharpness_checkbox.grid(row=postprocessing_row, column=1, sticky=W)
    as_tooltips.add(perform_sharpness_checkbox, "Apply sharpen algorithm (using OpenCV's 'filter2D') to the generated frames")

    # Check box to do gamma correction
    perform_gamma_correction = tk.BooleanVar(value=False)
    perform_gamma_correction_checkbox = tk.Checkbutton(
        postprocessing_frame, text='GC:', variable=perform_gamma_correction, command=perform_gamma_correction_selection,
        onvalue=True, offvalue=False, font=("Arial", FontSize))
    perform_gamma_correction_checkbox.grid(row=postprocessing_row, column=2, sticky=W)
    perform_gamma_correction_checkbox.config(state=NORMAL)
    as_tooltips.add(perform_gamma_correction_checkbox, "Apply gamma correction to the generated frames")

    # Spinbox for gamma correction
    gamma_correction_str = tk.StringVar(value="2.2")
    gamma_correction_spinbox = tk.Spinbox(postprocessing_frame, width=3, command=select_gamma_correction_value,
        textvariable=gamma_correction_str, from_=0.1, to=4, format="%.1f", increment=0.1, font=("Arial", FontSize))
    gamma_correction_spinbox.grid(row=postprocessing_row, column=2, sticky=E)
    as_tooltips.add(gamma_correction_spinbox, "Gamma correction value (default is 2.2, has to be greater than zero)")
    # Bind focus-out event to enforce the minimum value
    gamma_correction_spinbox.bind("<FocusOut>", gamma_enforce_min_value)

    postprocessing_row += 1

    # This checkbox enables 'fake' frame completion when, due to stabilization process, part of the frame is lost at the
    # top or at the bottom. It is named 'fake' because to fill in the missing part, a fragment of the previous or next
    # frame is used. Not perfect, but better than leaving the missing part blank, as it would happen without this.
    # Also, for this to work the cropping rectangle should encompass the full frame, top to bottom.
    # And yes, in theory we could pick the missing fragment of the same frame by picking the picture of the
    # next/previous frame, BUT it is not given that it will be there, as the next/previous frame might have been
    # captured without the required part.
    frame_fill_type = StringVar()
    perform_fill_none_rb = Radiobutton(postprocessing_frame, text='No frame fill',
                                    variable=frame_fill_type, value='none', font=("Arial", FontSize))
    perform_fill_none_rb.grid(row=postprocessing_row, column=0, sticky=W)
    as_tooltips.add(perform_fill_none_rb, "Badly aligned frames will be left with the missing part of the image black after stabilization")
    perform_fill_fake_rb = Radiobutton(postprocessing_frame, text='Fake fill',
                                    variable=frame_fill_type, value='fake', font=("Arial", FontSize))
    perform_fill_fake_rb.grid(row=postprocessing_row, column=1, sticky=W)
    as_tooltips.add(perform_fill_fake_rb, "Badly aligned frames will have the missing part of the image completed with a fragment of the next/previous frame after stabilization")
    perform_fill_dumb_rb = Radiobutton(postprocessing_frame, text='Dumb fill',
                                    variable=frame_fill_type, value='dumb', font=("Arial", FontSize))
    perform_fill_dumb_rb.grid(row=postprocessing_row, column=2, sticky=W)
    as_tooltips.add(perform_fill_dumb_rb, "Badly aligned frames will have the missing part of the image filled with the adjacent pixel row after stabilization")
    frame_fill_type.set('fake')

    postprocessing_row += 1

    # Define video generating area ************************************
    video_frame = LabelFrame(right_area_frame,
                             text='Video generation',
                             width=30, height=8, font=("Arial", FontSize-2))
    video_frame.pack(padx=2, pady=2, ipadx=5, expand=True, fill="both")
    video_row = 0
    video_frame.grid_columnconfigure(0, weight=1)
    video_frame.grid_columnconfigure(1, weight=1)
    video_frame.grid_columnconfigure(2, weight=1)

    # Check box to generate video or not
    generate_video = tk.BooleanVar(value=False)
    generate_video_checkbox = tk.Checkbutton(video_frame,
                                             text='Video',
                                             variable=generate_video,
                                             onvalue=True, offvalue=False,
                                             command=generate_video_selection,
                                             width=5, font=("Arial", FontSize))
    generate_video_checkbox.grid(row=video_row, column=0, sticky=W, padx=5)
    generate_video_checkbox.config(state=NORMAL if ffmpeg_installed
                                   else DISABLED)
    as_tooltips.add(generate_video_checkbox, "Generate an MP4 video, once all frames have been processed")

    # Check box to skip frame regeneration
    skip_frame_regeneration = tk.BooleanVar(value=False)
    skip_frame_regeneration_cb = tk.Checkbutton(
        video_frame, text='Skip Frame regeneration',
        variable=skip_frame_regeneration, onvalue=True, offvalue=False,
        width=20, font=("Arial", FontSize))
    skip_frame_regeneration_cb.grid(row=video_row, column=1,
                                    columnspan=2, sticky=W, padx=5)
    skip_frame_regeneration_cb.config(state=NORMAL if ffmpeg_installed
                                      else DISABLED)
    as_tooltips.add(skip_frame_regeneration_cb, "If frames have ben already generated in a previous run, and you want to only generate the vieo, check this one")

    video_row += 1

    # Video target folder
    video_target_dir_str = StringVar()
    video_target_dir = Entry(video_frame, textvariable=video_target_dir_str, width=30, borderwidth=1, font=("Arial", FontSize))
    video_target_dir.grid(row=video_row, column=0, columnspan=2, sticky=W, padx=5)
    video_target_dir.bind('<<Paste>>', lambda event, entry=video_target_dir: on_paste_all_entries(event, entry))
    as_tooltips.add(video_target_dir, "Directory where the generated video will be stored")

    video_target_folder_btn = Button(video_frame, text='Target', width=6,
                               height=1, command=set_video_target_folder,
                               activebackground='green',
                               activeforeground='white', wraplength=80, font=("Arial", FontSize))
    video_target_folder_btn.grid(row=video_row, column=2, columnspan=2, sticky=W, padx=5)
    as_tooltips.add(video_target_folder_btn, "Selects directory where the generated video will be stored")
    video_row += 1

    # Video filename
    video_filename_str = StringVar()
    video_filename_label = Label(video_frame, text='Video filename:', font=("Arial", FontSize))
    video_filename_label.grid(row=video_row, column=0, sticky=W, padx=5)
    video_filename_name = Entry(video_frame, textvariable=video_filename_str, name="video_filename", 
                                validate="key", validatecommand=vcmd,
                                width=26 if BigSize else 26, borderwidth=1, font=("Arial", FontSize))
    video_filename_name.grid(row=video_row, column=1, columnspan=2, sticky=W, padx=5)
    video_filename_name.bind('<<Paste>>', lambda event, entry=video_filename_name: on_paste_all_entries(event, entry))
    as_tooltips.add(video_filename_name, "Filename of video to be created")

    video_row += 1

    # Video title (add title at the start of the video)
    video_title_str = StringVar()
    video_title_label = Label(video_frame, text='Video title:', font=("Arial", FontSize))
    video_title_label.grid(row=video_row, column=0, sticky=W, padx=5)
    video_title_name = Entry(video_frame, textvariable=video_title_str, name="video_title", 
                             validate="key", validatecommand=vcmd,
                             width=26 if BigSize else 26, borderwidth=1, font=("Arial", FontSize))
    video_title_name.grid(row=video_row, column=1, columnspan=2, sticky=W, padx=5)
    video_title_name.bind('<<Paste>>', lambda event, entry=video_title_name: on_paste_all_entries(event, entry))
    as_tooltips.add(video_title_name, "Video title. If entered, a simple title sequence will be generated at the start of the video, using a sequence randomly selected from the same video, running at half speed")

    video_row += 1

    # Drop down to select FPS
    # Dropdown menu options
    fps_list = [
        "8",
        "9",
        "16",
        "16.67",
        "18",
        "24",
        "25",
        "29.97",
        "30",
        "48",
        "50"
    ]

    # datatype of menu text
    video_fps_dropdown_selected = StringVar()

    # initial menu text
    video_fps_dropdown_selected.set("18")

    # Create FPS Dropdown menu
    video_fps_frame = Frame(video_frame)
    video_fps_frame.grid(row=video_row, column=0, sticky=W)
    video_fps_label = Label(video_fps_frame, text='FPS:', font=("Arial", FontSize))
    video_fps_label.pack(side=LEFT, anchor=W, padx=5)
    video_fps_label.config(state=DISABLED)
    video_fps_dropdown = OptionMenu(video_fps_frame,
                                    video_fps_dropdown_selected, *fps_list,
                                    command=set_fps)
    video_fps_dropdown.config(takefocus=1, font=("Arial", FontSize))
    video_fps_dropdown.pack(side=LEFT, anchor=E, padx=5)
    video_fps_dropdown.config(state=DISABLED)
    as_tooltips.add(video_fps_dropdown, "Number of frames per second (FPS) of the video to be generated. Usually Super8 goes at 18 FPS, and Regular 8 at 16 FPS, although some cameras allowed to use other speeds (faster for smoother movement, slower for extended play time)")

    # Create FFmpeg preset options
    ffmpeg_preset_frame = Frame(video_frame)
    ffmpeg_preset_frame.grid(row=video_row, column=1, columnspan=2, sticky=W, padx=5)
    ffmpeg_preset = StringVar()
    ffmpeg_preset_rb1 = Radiobutton(ffmpeg_preset_frame,
                                    text="Best quality (slow)",
                                    variable=ffmpeg_preset, value='veryslow', font=("Arial", FontSize))
    ffmpeg_preset_rb1.pack(side=TOP, anchor=W, padx=5)
    ffmpeg_preset_rb1.config(state=DISABLED)
    as_tooltips.add(ffmpeg_preset_rb1, "Best quality, but very slow encoding. Maps to the same ffmpeg option")

    ffmpeg_preset_rb2 = Radiobutton(ffmpeg_preset_frame, text="Medium",
                                    variable=ffmpeg_preset, value='medium', font=("Arial", FontSize))
    ffmpeg_preset_rb2.pack(side=TOP, anchor=W, padx=5)
    ffmpeg_preset_rb2.config(state=DISABLED)
    as_tooltips.add(ffmpeg_preset_rb2, "Compromise between quality and encoding speed. Maps to the same ffmpeg option")
    ffmpeg_preset_rb3 = Radiobutton(ffmpeg_preset_frame,
                                    text="Fast (low quality)",
                                    variable=ffmpeg_preset, value='veryfast', font=("Arial", FontSize))
    ffmpeg_preset_rb3.pack(side=TOP, anchor=W, padx=5)
    ffmpeg_preset_rb3.config(state=DISABLED)
    as_tooltips.add(ffmpeg_preset_rb3, "Faster encoding speed, lower quality (but not so much IMHO). Maps to the same ffmpeg option")
    ffmpeg_preset.set('medium')
    video_row += 1

    # Drop down to select resolution
    # datatype of menu text
    resolution_dropdown_selected = StringVar()

    # initial menu text
    resolution_dropdown_selected.set("1920x1440 (1080P)")

    # Create resolution Dropdown menu
    resolution_frame = Frame(video_frame)
    resolution_frame.grid(row=video_row, column=0, columnspan= 2, sticky=W)
    resolution_label = Label(resolution_frame, text='Resolution:', font=("Arial", FontSize))
    resolution_label.pack(side=LEFT, anchor=W, padx=5)
    resolution_label.config(state=DISABLED)
    resolution_dropdown = OptionMenu(resolution_frame,
                                    resolution_dropdown_selected, *resolution_dict.keys(),
                                    command=set_resolution)
    resolution_dropdown.config(takefocus=1, font=("Arial", FontSize))
    resolution_dropdown.pack(side=LEFT, anchor=E, padx=5)
    resolution_dropdown.config(state=DISABLED)
    as_tooltips.add(resolution_dropdown, "Resolution to be used when generating the video")

    video_row += 1

    # Extra (expert) area ***************************************************
    if ExpertMode:
        extra_frame = LabelFrame(right_area_frame,
                                 text='Expert options',
                                 width=50, height=8, font=("Arial", FontSize-2))
        extra_frame.pack(padx=5, pady=5, ipadx=5, ipady=5, expand=True, fill="both")
        extra_frame.grid_columnconfigure(0, weight=1)
        extra_frame.grid_columnconfigure(1, weight=1)
        extra_row = 0

        # Check box to display misaligned frame monitor/editor
        display_template_popup_btn = Button(extra_frame,
                                            text='FrameSync Editor',
                                            command=FrameSync_Viewer_popup,
                                            width=15, font=("Arial", FontSize))
        display_template_popup_btn.config(relief=SUNKEN if FrameSync_Viewer_opened else RAISED)
        display_template_popup_btn.grid(row=extra_row, column=0, padx=5, sticky="nsew")
        ### extra_frame.grid_columnconfigure(0, weight=1)
        as_tooltips.add(display_template_popup_btn, "Display popup window with dynamic debug information.Useful for developers only")

        # Settings button, at the bottom of top left area
        options_btn = Button(extra_frame, text="Settings", command=cmd_settings_popup, width=15,
                            relief=RAISED, font=("Arial", FontSize), name='options_btn')
        options_btn.widget_type = "general"
        options_btn.grid(row=extra_row, column=1, padx=5, sticky="nsew")
        as_tooltips.add(options_btn, "Set AfterScan options.")
        extra_row += 1

        # Spinbox to select stabilization threshold - Ignored, to be removed in the future
        stabilization_threshold_label = tk.Label(extra_frame,
                                                 text='Threshold:',
                                                 width=11, font=("Arial", FontSize))
        #stabilization_threshold_label.grid(row=extra_row, column=1, columnspan=1, sticky=E)
        stabilization_threshold_label.grid_forget()
        stabilization_threshold_str = tk.StringVar(value=str(StabilizationThreshold))
        stabilization_threshold_selection_aux = extra_frame.register(
            stabilization_threshold_selection)
        stabilization_threshold_spinbox = tk.Spinbox(
            extra_frame,
            command=(stabilization_threshold_selection_aux, '%d'), width=6,
            textvariable=stabilization_threshold_str, from_=0, to=255, font=("Arial", FontSize))
        #stabilization_threshold_spinbox.grid(row=extra_row, column=2, sticky=W)
        stabilization_threshold_spinbox.grid_forget()
        stabilization_threshold_spinbox.bind("<FocusOut>", stabilization_threshold_spinbox_focus_out)
        as_tooltips.add(stabilization_threshold_spinbox, "Threshold value to isolate the sprocket hole from the rest of the image while definint the custom template")

        extra_row += 1

    # Define job list area ***************************************************
    # Replace listbox with treeview
    # Define style for labelframe
    style = ttk.Style()
    style.configure("TLabelframe.Label", font=("Arial", FontSize-2))
    # Create a frame to hold Treeview and scrollbars
    job_list_frame = ttk.LabelFrame(left_area_frame,
                             text='Job List',
                             width=50, height=8)
    job_list_frame.pack(side=TOP, padx=2, pady=2, anchor=W)

    # Create Treeview with a single column
    job_list_treeview = ttk.Treeview(job_list_frame, columns=("description"))

    # Define style for headings
    style.configure("Treeview.Heading", font=("Arial", FontSize, "bold")) #Change header font.

    # Define the single column
    name_width = 130 if ForceSmallSize else 200
    description_width = 250 if ForceSmallSize else 340
    job_list_treeview.heading("#0", text="Name")
    job_list_treeview.heading("description", text="Description")
    job_list_treeview.column("#0", anchor="w", width=name_width, minwidth=name_width, stretch=tk.NO)
    job_list_treeview.column("description", anchor="w", width=description_width, minwidth=1400, stretch=tk.NO)

    # job listbox scrollbars
    job_list_listbox_scrollbar_y = ttk.Scrollbar(job_list_frame, orient="vertical", command=job_list_treeview.yview)
    job_list_treeview.configure(yscrollcommand=job_list_listbox_scrollbar_y.set)
    job_list_listbox_scrollbar_y.grid(row=0, column=1, sticky=NS)
    job_list_listbox_scrollbar_x = ttk.Scrollbar(job_list_frame, orient="horizontal", command=job_list_treeview.xview)
    job_list_treeview.configure(xscrollcommand=job_list_listbox_scrollbar_x.set)
    job_list_listbox_scrollbar_x.grid(row=1, column=0, columnspan=1, sticky=EW)

    # Layout
    job_list_treeview.grid(column=0, row=0, padx=5, pady=2, ipadx=5)

    # Define tags for different row colors
    job_list_treeview.tag_configure("pending", foreground="black")
    job_list_treeview.tag_configure("ongoing", foreground="blue")
    job_list_treeview.tag_configure("done", foreground="green")
    job_list_treeview.tag_configure("joblist_font", font=("Arial", FontSize))

    # Bind the keys to be used alog
    job_list_treeview.bind("<Delete>", job_list_delete_current)
    job_list_treeview.bind("<Return>", job_list_load_current)
    job_list_treeview.bind("<KP_Enter>", job_list_load_current)
    job_list_treeview.bind("<Double - Button - 1>", job_list_load_current)
    job_list_treeview.bind("r", job_list_rerun_current)
    job_list_treeview.bind('<<ListboxSelect>>', job_list_process_selection)
    job_list_treeview.bind("u", job_list_move_up)
    job_list_treeview.bind("d", job_list_move_down)
    job_list_listbox_disabled = False   # to prevent processing clicks on listbox, as disabling it will prevent checkign status of each job
    
    # Define job list button area
    job_list_btn_frame = Frame(job_list_frame,
                             width=50, height=8)
    job_list_btn_frame.grid(row=0, column=2, padx=2, pady=2, sticky=W)

    # Add job button
    add_job_btn = Button(job_list_btn_frame, text="Add job", width=12, height=1,
                    command=job_list_add_current, activebackground='green',
                    activeforeground='white', wraplength=100, font=("Arial", FontSize))
    add_job_btn.pack(side=TOP, padx=2, pady=2)
    as_tooltips.add(add_job_btn, "Add to job list a new job using the current settings defined on the right area of the AfterScan window")

    # Delete job button
    delete_job_btn = Button(job_list_btn_frame, text="Delete job", width=12, height=1,
                    command=job_list_delete_selected, activebackground='green',
                    activeforeground='white', wraplength=100, font=("Arial", FontSize))
    delete_job_btn.pack(side=TOP, padx=2, pady=2)
    as_tooltips.add(delete_job_btn, "Delete currently selected job from list")

    # Rerun job button
    rerun_job_btn = Button(job_list_btn_frame, text="Rerun job", width=12, height=1,
                    command=job_list_rerun_selected, activebackground='green',
                    activeforeground='white', wraplength=100, font=("Arial", FontSize))
    rerun_job_btn.pack(side=TOP, padx=2, pady=2)
    as_tooltips.add(rerun_job_btn, "Toggle 'run' state of currently selected job in list")

    # Start processing job button
    start_batch_btn = Button(job_list_btn_frame, text="Start batch", width=12, height=1,
                    command=start_processing_job_list, activebackground='green',
                    activeforeground='white', wraplength=100, font=("Arial", FontSize))
    start_batch_btn.pack(side=TOP, padx=2, pady=2)
    as_tooltips.add(start_batch_btn, "Start processing jobs in list")

    # Suspend on end checkbox
    # suspend_on_joblist_end = tk.BooleanVar(value=False)
    # suspend_on_joblist_end_cb = tk.Checkbutton(
    #     job_list_btn_frame, text='Suspend on end',
    #     variable=suspend_on_joblist_end, onvalue=True, offvalue=False,
    #     width=13)
    # suspend_on_joblist_end_cb.pack(side=TOP, padx=2, pady=2)

    suspend_on_completion_label = Label(job_list_btn_frame, text='Suspend on:', font=("Arial", FontSize))
    suspend_on_completion_label.pack(side=TOP, anchor=W, padx=2, pady=2)
    suspend_on_completion = StringVar()
    suspend_on_batch_completion_rb = Radiobutton(job_list_btn_frame, text="Job completion",
                                  variable=suspend_on_completion, value='job_completion', font=("Arial", FontSize))
    suspend_on_batch_completion_rb.pack(side=TOP, anchor=W, padx=2, pady=2)
    as_tooltips.add(suspend_on_batch_completion_rb, "Suspend computer when all jobs in list have been processed")
    suspend_on_job_completion_rb = Radiobutton(job_list_btn_frame, text="Batch completion",
                                  variable=suspend_on_completion, value='batch_completion', font=("Arial", FontSize))
    suspend_on_job_completion_rb.pack(side=TOP, anchor=W, padx=2, pady=2)
    as_tooltips.add(suspend_on_batch_completion_rb, "Suspend computer when current job being processed is complete")
    no_suspend_rb = Radiobutton(job_list_btn_frame, text="No suspend",
                                  variable=suspend_on_completion, value='no_suspend', font=("Arial", FontSize))
    no_suspend_rb.pack(side=TOP, anchor=W, padx=2, pady=2)
    as_tooltips.add(suspend_on_batch_completion_rb, "Do not suspend when done")

    suspend_on_completion.set("no_suspend")

    postprocessing_bottom_frame = Frame(video_frame, width=30)
    postprocessing_bottom_frame.grid(row=video_row, column=0)


# Function to copy files from temp to templates folder the first time version 1.12 version is run
def copy_jpg_files(source_folder, destination_folder):
    try:
        # Create destination folder if it doesn't exist
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            logging.debug(f"copy_jpg_files. Created destination folder: {destination_folder}")

        # Iterate through all files in the source folder
        for filename in os.listdir(source_folder):
            # Check if the file is a JPG file (case-insensitive)
            if filename.lower().endswith('.jpg'):
                source_path = os.path.join(source_folder, filename)
                destination_path = os.path.join(destination_folder, filename)

                # Check if it's a file (not a directory)
                if os.path.isfile(source_path):
                    shutil.copy2(source_path, destination_path)
                    logging.debug(f"copy_jpg_files. Copied: {filename} to {destination_folder}")

        logging.debug("copy_jpg_files. All JPG files copied successfully!")

    except Exception as e:
        logging.debug(f"copy_jpg_files. An error occurred: {e}")


def exit_app():  # Exit Application
    global win
    global active_threads
    global frame_encoding_event, frame_encoding_queue, num_threads

    # Terminate threads
    # frame_encoding_event.set()
    for i in range(0, num_threads):
        frame_encoding_queue.put((END_TOKEN, 0))
        logging.debug("Inserting end token to encoding queue")

    while active_threads > 0:
        win.update()
        logging.debug(f"Waiting for threads to exit, {active_threads} pending")
        time.sleep(0.2)

    save_general_config()
    save_project_config()
    save_job_list()
    win.destroy()


# Get or generate persistent user ID
def get_user_id():
    global AnonymousUuid, general_config
    if AnonymousUuid != None:
        return AnonymousUuid
    else:
        serial = None
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        serial = line.split(':')[1].strip()
                        break # exit for loop after finding serial number.
        except FileNotFoundError:
            logging.error(f"e")
        if serial == None:
            AnonymousUuid = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
            logging.debug(f"Generating generic uuid: {AnonymousUuid}")
        else:
            AnonymousUuid = hashlib.sha256(serial.encode()).hexdigest()
            logging.debug(f"Generating RPi uuid: {AnonymousUuid}")
        general_config['AnonymousUuid'] = AnonymousUuid
        return AnonymousUuid


def get_consent(force = False):
    global UserConsent, general_config, LastConsentDate
    # Check reporting consent
    if requests_loaded:
        if force or UserConsent == None or LastConsentDate == None or (UserConsent == 'no' and (datetime.today()-LastConsentDate).days >= 60):
            consent = tk.messagebox.askyesno(
                "AfterScan User Count",
                "Help us count AfterScan users anonymously? Reports versions to track usage. No personal data is collected, just an anonymous hash plus AfterScan versions."
            )
            LastConsentDate = datetime.today()
            general_config['LastConsentDate'] = LastConsentDate.isoformat()
            UserConsent = "yes" if consent else "no"
            general_config['UserConsent'] = UserConsent


# Ping server if requests is available (call once at startup)
def report_usage():
    if UserConsent == "yes" and requests_loaded:
        encoded_2 = "Rucy5uZXQ6NTAwMC9jb3VudA=="
        user_id = get_user_id()  # Reuse persistent ID
        payload = {
            "id": user_id,
            "versions": {"product": __module__, "ui": __version__, "controller": ""}
        }
        encoded_1 = "aHR0cDovL2phdW4uZG"
        server_url = base64.b64decode(encoded_1+encoded_2).decode("utf-8")        
        try:
            requests.post(server_url, json=payload, timeout=1)
            logging.debug("Usage reporting done.")
        except requests.RequestException:
            pass  # Silent fail if offline
    elif not requests_loaded:
        logging.warning("Usage reporting skipped—install 'python3-requests' to enable (optional).")


def main(argv):
    global LogLevel, LoggingMode
    global template_list
    global ExpertMode
    global FfmpegBinName
    global IsWindows, IsLinux, IsMac
    global project_config_filename, project_config_basename
    global perform_stabilization
    global ui_init_done
    global IgnoreConfig
    global job_list
    global project_settings
    global default_project_config
    global is_demo, ForceSmallSize, ForceBigSize
    global GenerateCsv
    global suspend_on_joblist_end
    global BatchAutostart
    global num_threads
    global use_simple_stabilization
    global dev_debug_enabled
    
    LoggingMode = "INFO"
    go_disable_tooptips = False
    goanyway = False

    # Create job dictionary
    # Dictionary fields
    # 'description': Added in 1.12.09, to split job list entry name in two
    # 'project': Contents of project_config
    # 'done': Job already completed
    # 'attempted': Job started but not completed
    job_list = {}

    # Create project settings dictionary
    project_settings = default_project_config.copy()

    opts, args = getopt.getopt(argv, "hiel:dcst:12nab", ["goanyway"])

    for opt, arg in opts:
        if opt == '-l':
            LoggingMode = arg
        elif opt == '-c':
            GenerateCsv = True
        elif opt == '-e':
            ExpertMode = True
        elif opt == '-i':
            IgnoreConfig = True
        elif opt == '-d':
            is_demo = True
        elif opt == '-s':
            BatchAutostart = True
        elif opt == '-t':
            num_threads = int(arg)
        elif opt == '-1':
            ForceSmallSize = True
        elif opt == '-2':
            ForceBigSize = True
        elif opt == '-n':
            go_disable_tooptips = True
        elif opt == '-a':
            use_simple_stabilization = True
        elif opt == '-b':
            dev_debug_enabled = True
        elif opt == '--goanyway':
            goanyway = True
        elif opt == '-h':
            print("AfterScan")
            print("  -l <log mode>  Set log level:")
            print("      <log mode> = [DEBUG|INFO|WARNING|ERROR]")
            print("  -i             Ignore existing config")
            print("  -n             Disable Tooltips")
            print("  -e             Enable expert mode")
            print("  -c             Generate CSV file with misaligned frames")
            print("  -s             Initiate batch on startup (and suspend on batch completion)")
            print("  -t <num>       Number of threads")
            print("  -1             Initiate on 'small screen' mode (resolution lower than than Full HD)")
            print("  -a             Use simple stabilization algorithm, not requiring templates (but slightly less precise)")
            exit()

    if goanyway:
        print("Work in progress, version not usable yet.")
        tk.messagebox.showerror("WIP", "Work in progress, version not usable yet.")
        return

    # Set our CWD to the same folder where the script is. 
    # Otherwise webbrowser failt to launch (cannot open path of the current working directory: Permission denied)
    os.chdir(script_dir) 

    LogLevel = getattr(logging, LoggingMode.upper(), None)
    if not isinstance(LogLevel, int):
        raise ValueError('Invalid log level: %s' % LogLevel)
    else:
        init_logging()

    # Add default templates to template list
    template_list = TemplateList()
    template_list.add("S8", hole_template_filename_s8, "S8", (66, 838))     # New, smaller
    template_list.add("R8", hole_template_filename_r8, "R8", (65, 1080)) # Default R8 (bottom hole)
    template_list.add("BW", hole_template_filename_bw, "aux", (0, 0))
    template_list.add("WB", hole_template_filename_wb, "aux", (0, 0))
    template_list.add("Corner", hole_template_filename_corner, "aux", (0, 0))

    templates_ok, error_msg = verify_templates()
    if not templates_ok:
        logging.error(error_msg)
        return

    load_general_config()

    afterscan_init()

    if go_disable_tooptips:
        as_tooltips.disable()

    decode_general_config()

    # Check reporting consent on first run
    get_consent()

    multiprocessing_init()

    # Try to detect if ffmpeg is installed
    ffmpeg_installed = False
    if platform.system() == 'Windows':
        IsWindows = True
        if FfmpegBinName is None or FfmpegBinName == "":
            FfmpegBinName = 'C:\\ffmpeg\\bin\\ffmpeg.exe'
        AltFfmpegBinName = 'ffmpeg.exe'
        logging.debug("Detected Windows OS")
    elif platform.system() == 'Linux':
        IsLinux = True
        if FfmpegBinName is None or FfmpegBinName == "":
            FfmpegBinName = 'ffmpeg'
        AltFfmpegBinName = 'ffmpeg'
        logging.debug("Detected Linux OS")
    elif platform.system() == 'Darwin':
        IsMac = True
        if FfmpegBinName is None or FfmpegBinName == "":
            FfmpegBinName = 'ffmpeg'
        AltFfmpegBinName = 'ffmpeg'
        logging.debug("Detected Darwin (MacOS) OS")
    else:
        if FfmpegBinName is None or FfmpegBinName == "":
            FfmpegBinName = 'ffmpeg'
        AltFfmpegBinName = 'ffmpeg'
        logging.debug("OS not recognized: " + platform.system())

    if is_ffmpeg_installed():
        ffmpeg_installed = True
    elif platform.system() == 'Windows':
        FfmpegBinName = AltFfmpegBinName
        if is_ffmpeg_installed():
            ffmpeg_installed = True
    if not ffmpeg_installed:
        tk.messagebox.showerror(
            "Error: ffmpeg is not installed",
            f"FFmpeg is not installed in this computer at the designated path '{FfmpegBinName}'.\r\n"
            "It is not mandatory for the application to run; "
            "Frame stabilization and cropping will still work, "
            "video generation will not")

    build_ui()
    win.config(cursor="watch")  # Set cursor to hourglass
    widget_status_update()

    if SourceDir is not None:
        project_config_filename = os.path.join(SourceDir,
                                               project_config_basename)
    load_project_settings()
    
    load_project_config()
    decode_project_config()

    load_job_list()

    get_target_dir_file_list()

    adjust_last_column()

    # If Templates folder do not exist (introduced with AfterScan 1.12), copy over files from temp folder
    if copy_templates_from_temp:
        copy_jpg_files(temp_dir, resources_dir)

    ui_init_done = True

    template_list.set_scale(frame_width)    # frame_width set by get_source_dir_file_list

    # Disable a few items that should be not operational without source folder
    if len(SourceDir) == 0:
        Go_btn.config(state=DISABLED)
        cropping_btn.config(state=DISABLED)
        frame_slider.config(state=DISABLED)
    else:
        Go_btn.config(state=NORMAL)
        cropping_btn.config(state=NORMAL)
        frame_slider.config(state=NORMAL)

    init_display()

    win.resizable(False, False) # Lock window size once all widgets have been added (make sure all fits)

    report_usage()

    # If BatchAutostart, enable suspend on completion and start batch
    if BatchAutostart:
        suspend_on_joblist_end.set(True)
        win.after(2000, start_processing_job_list) # Wait 2 sec. to allow main loop to start

    win.config(cursor="")  # Set cursor to hourglass

    # Main Loop
    win.mainloop()  # running the loop that works as a trigger


if __name__ == '__main__':
    main(sys.argv[1:])
