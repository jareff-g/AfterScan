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
__copyright__ = "Copyright 2022, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__version__ = "1.10.9"
__data_version__ = "1.0"
__date__ = "2024-02-02"
__version_highlight__ = "Bugfixes after template factorization"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import tkinter as tk
from tkinter import filedialog

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
from tooltip import disable_tooltips, setup_tooltip, init_tooltips

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
# FPM calculation (taken from ALT-Scann8)
FPM_LastMinuteFrameTimes = list()
FPM_StartTime = time.ctime()
FPM_CalculatedValue = -1


# Configuration & support file vars
script_dir = os.path.realpath(sys.argv[0])
script_dir = os.path.dirname(script_dir)
general_config_filename = os.path.join(script_dir, "AfterScan.json")
project_settings_filename = os.path.join(script_dir, "AfterScan-projects.json")
project_settings_backup_filename = os.path.join(script_dir, "AfterScan-projects.json.bak")
project_config_basename = "AfterScan-project.json"
project_config_filename = ""
project_config_from_file = True
project_name = "No Project"
job_list_filename = os.path.join(script_dir, "AfterScan_job_list.json")
aux_dir = os.path.join(script_dir, "aux")
if not os.path.exists(aux_dir):
    os.mkdir(aux_dir)
template_list = None
hole_template_filename_r8 = os.path.join(script_dir, "Pattern.R8.jpg")
hole_template_filename_s8 = os.path.join(script_dir, "Pattern.S8.jpg")
hole_template_filename_custom = os.path.join(script_dir, "Pattern.custom.jpg")
hole_template_filename_corner = os.path.join(script_dir, "Pattern_Corner_TR.jpg")
hole_template_filename_bw = os.path.join(aux_dir, "Pattern_BW.jpg")
hole_template_filename_wb = os.path.join(aux_dir, "Pattern_WB.jpg")
hole_template_filename = hole_template_filename_s8
files_to_delete = []

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
    "VideoResolution": "Unchanged",
    "CurrentFrame": 0,
    "EncodeAllFrames": True,
    "FramesToEncode": "All",
    "StabilizationThreshold": "220",
    "PerformStabilization": False,
    "skip_frame_regeneration": False,
    "FFmpegPreset": "veryslow",
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
VideoTargetDir = ""
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
frame_width = 2048
frame_height = 1520

# Flow control vars
ConvertLoopExitRequested = False
ConvertLoopRunning = False
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
stabilization_bounds_alert_counter = 0
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

Force43 = False
Force169 = False

# Video generation vars
VideoFps = 18
FfmpegBinName = ""
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
global win
ExpertMode = False
IsWindows = False
IsLinux = False
IsMac = False

is_demo = False
ForceSmallSize = False
ForceBigSize = False
dev_debug_enabled = False
debug_template_match = False
developer_debug = False
developer_debug_file_flag = os.path.join(script_dir, "developer.txt")

GenerateCsv = True
CsvFilename = ""
CsvPathName = ""
CsvFile = 0
CsvFramesOffPercent = 0

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
        self.scale = int(frame_width/2028)
        self.position = position
        self.scaled_position = (int(self.position[0] * self.scale),
                                int(self.position[1] * self.scale))
        self.size = (0,0)
        if os.path.isfile(filename):
            self.template = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
            self.scaled_template = resize_image(self.template, self.scale)
            # Calculate the white on black proportion to help with detection
            white_pixel_count = cv2.countNonZero(self.scaled_template)
            total_pixels = self.scaled_template.size
            self.wb_proportion = white_pixel_count / total_pixels
            self.size = (self.template.shape[1],self.template.shape[0])
            self.scaled_size = (int(self.size[0] * self.scale),
                                int(self.size[1] * self.scale))
        else:
            self.template = None
            self.scaled_template = None
            self.wb_proportion = 0.5
            self.size = (0,0)
            self.scaled_size = (0,0)

    def refresh(self):
        self.template = cv2.imread(self.filename, cv2.IMREAD_GRAYSCALE)
        self.scaled_template = resize_image(self.template, self.scale)
        white_pixel_count = cv2.countNonZero(self.scaled_template)
        total_pixels = self.scaled_template.size
        self.wb_proportion = white_pixel_count / total_pixels
        self.size = (self.template.shape[1], self.template.shape[0])
        self.scaled_size = (int(self.size[0] * self.scale),
                            int(self.size[1] * self.scale))


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
        self.active_template.position = position

    def get_active_size(self):
        return self.active_template.size

    def set_active_size(self, size):
        self.active_template.size = size

    def get_scale(self):
        # Size reference 2028x1520
        return self.active_template.scale   # Scale is dynamic, as it depends on the set of images currently loaded

    def get_active_filename(self):
        return self.active_template.filename

    def get_active_type(self):
        return self.active_template.type

    def get_active_wb_proportion(self):
        return self.active_template.wb_proportion



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
    global video_filename_name, video_title_name
    global frame_from_str, frame_to_str
    global frame_fill_type, extended_stabilization
    global perform_denoise, perform_sharpness

    project_config["PerformCropping"] = False
    perform_cropping.set(project_config["PerformCropping"])
    project_config["PerformSharpness"] = False
    perform_sharpness.set(project_config["PerformSharpness"])
    project_config["PerformDenoise"] = False
    perform_denoise.set(project_config["PerformDenoise"])
    project_config["FrameFillType"] = 'none'
    frame_fill_type.set(project_config["FrameFillType"])
    project_config["GenerateVideo"] = False
    generate_video.set(project_config["GenerateVideo"])
    project_config["VideoResolution"] = "Unchanged"
    resolution_dropdown_selected.set(project_config["VideoResolution"])
    project_config["CurrentFrame"] = 0
    frame_slider.set(project_config["CurrentFrame"])
    project_config["EncodeAllFrames"] = True
    encode_all_frames.set(project_config["EncodeAllFrames"])
    project_config["FrameFrom"] = "0"
    frame_from_str.set(project_config["FrameFrom"])
    project_config["FrameTo"] = "0"
    frame_to_str.set(project_config["FrameTo"])
    project_config["PerformStabilization"] = False
    perform_stabilization.set(project_config["PerformStabilization"])
    project_config["ExtendedStabilization"] = False
    extended_stabilization.set(project_config["ExtendedStabilization"])
    project_config["skip_frame_regeneration"] = False
    skip_frame_regeneration.set(project_config["skip_frame_regeneration"])
    project_config["FFmpegPreset"] = "veryslow"
    ffmpeg_preset.set(project_config["FFmpegPreset"])
    project_config["VideoFilename"] = ""
    video_filename_name.delete(0, 'end')
    video_filename_name.insert('end', project_config["VideoFilename"])
    project_config["VideoTitle"] = ""
    video_title_name.delete(0, 'end')
    video_title_name.insert('end', project_config["VideoTitle"])
    project_config["FillBorders"] = False


def save_general_config():
    # Write config data upon exit
    general_config["GeneralConfigDate"] = str(datetime.now())
    if not IgnoreConfig:
        with open(general_config_filename, 'w+') as f:
            json.dump(general_config, f)


def load_general_config():
    global general_config
    global general_config_filename
    global LastSessionDate
    global SourceDir, TargetDir
    global project_name
    global FfmpegBinName

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
            json.dump(list_to_save, f)


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
                global_info = {'data_version': __data_version__, 'code_version': __version__,
                               'save_date': str(datetime.now())}
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
    global video_filename_name, video_title_name
    global frame_from_str, frame_to_str
    global perform_denoise, perform_sharpness

    # Do not save if current project comes from batch job
    if not project_config_from_file or IgnoreConfig:
        return
    # Write project data upon exit
    project_config["SourceDir"] = SourceDir
    project_config["TargetDir"] = TargetDir
    project_config["CurrentFrame"] = CurrentFrame
    project_config["skip_frame_regeneration"] = skip_frame_regeneration.get()
    project_config["FFmpegPreset"] = ffmpeg_preset.get()
    project_config["ProjectConfigDate"] = str(datetime.now())
    project_config["PerformCropping"] = perform_cropping.get()
    project_config["PerformSharpness"] = perform_sharpness.get()
    project_config["PerformDenoise"] = perform_denoise.get()
    project_config["FrameFillType"] = frame_fill_type.get()
    project_config["ExtendedStabilization"] = extended_stabilization.get()
    project_config["VideoFilename"] = video_filename_name.get()
    project_config["VideoTitle"] = video_title_name.get()
    project_config["FrameFrom"] = frame_from_str.get()
    project_config["FrameTo"] = frame_to_str.get()
    if StabilizeAreaDefined:
        project_config["PerformStabilization"] = perform_stabilization.get()
        if not encode_all_frames.get():
            project_config["HolePos"] = template_list.get_active_position()
            project_config["HoleScale"] = template_list.get_active_scale()

    # remove deprecated items from config
    if "CustomHolePos" in project_config:
        del project_config["CustomHolePos"]

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

def decode_project_config():        
    global SourceDir, TargetDir, VideoTargetDir
    global project_config
    global template_list
    global project_config_basename, project_config_filename
    global CurrentFrame, frame_slider
    global VideoFps, video_fps_dropdown_selected
    global resolution_dropdown, resolution_dropdown_selected
    global encode_all_frames, frames_to_encode
    global skip_frame_regeneration
    global generate_video, video_filename_name, video_title_name
    global CropTopLeft, CropBottomRight, perform_cropping
    global StabilizeAreaDefined, film_type
    global StabilizationThreshold
    global RotationAngle
    global frame_from_str, frame_to_str
    global project_name
    global force_4_3_crop, force_16_9_crop
    global frame_fill_type
    global extended_stabilization
    global Force43, Force169
    global perform_denoise, perform_sharpness

    if 'SourceDir' in project_config:
        SourceDir = project_config["SourceDir"]
        project_name = os.path.split(SourceDir)[-1].replace(',', ';')
        # If directory in configuration does not exist, set current working dir
        if not os.path.isdir(SourceDir):
            SourceDir = ""
            project_name = "No Project"
        frames_source_dir.delete(0, 'end')
        frames_source_dir.insert('end', SourceDir)
        frames_source_dir.after(100, frames_source_dir.xview_moveto, 1)
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
        VideoTargetDir = project_config["VideoTargetDir"]
        # If directory in configuration does not exist, set current working dir
        if not os.path.isdir(VideoTargetDir):
            VideoTargetDir = TargetDir  # use frames target dir as fallback option
        video_target_dir.delete(0, 'end')
        video_target_dir.insert('end', VideoTargetDir)
        video_target_dir.after(100, video_target_dir.xview_moveto, 1)
    if 'CurrentFrame' in project_config and not BatchJobRunning: # only if project loaded by user, otherwise it alters start encoding frame in batch mode
        CurrentFrame = project_config["CurrentFrame"]
        CurrentFrame = max(CurrentFrame, 0)
        frame_slider.set(CurrentFrame)
    else:
        CurrentFrame = 0
        frame_slider.set(CurrentFrame)
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
            StabilizationThreshold = project_config["StabilizationThreshold"]
            stabilization_threshold_str.set(StabilizationThreshold)
        else:
            StabilizationThreshold = 220
            stabilization_threshold_str.set(StabilizationThreshold)
    else:
        StabilizationThreshold = 220

    if 'ExtendedStabilization' in project_config:
        extended_stabilization.set(project_config["ExtendedStabilization"])

    if 'CustomTemplateDefined' in project_config and project_config["CustomTemplateDefined"] and 'CustomTemplateFilename' in project_config:
        if 'CustomTemplateName' in project_config:  # Load name if it exists, otherwise assign default
            template_name = project_config["CustomTemplateName"]
        else:
            if 'FrameFrom' in project_config and 'FrameTo' in project_config:
                template_name = f"{os.path.split(SourceDir)[-1]}-{project_config['FrameFrom']}-{project_config['FrameTo']}"
            else:
                template_name = f"{os.path.split(SourceDir)[-1]}-all"
        if 'CustomTemplateExpectedPos' in project_config:
            expected_hole_template_pos_custom = project_config["CustomTemplateExpectedPos"]
        else:
            expected_hole_template_pos_custom = (0, 0)
        template_filename = f"Pattern.custom.{template_name}.jpg"
        full_path_template_filename = os.path.join(aux_dir, template_filename)
        project_custom_template_filename = project_config["CustomTemplateFilename"]
        if project_custom_template_filename != full_path_template_filename:
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
    if 'PerformSharpness' in project_config:
        perform_sharpness.set(project_config["PerformSharpness"])
    else:
        perform_sharpness.set(False)
    if 'PerformDenoise' in project_config:
        perform_denoise.set(project_config["PerformDenoise"])
    else:
        perform_denoise.set(False)
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
        TargetVideoFilename = project_config["VideoFilename"]
        video_filename_name.delete(0, 'end')
        video_filename_name.insert('end', TargetVideoFilename)
    else:
        video_filename_name.delete(0, 'end')
    if 'VideoTitle' in project_config:
        TargetVideoTitle = project_config["VideoTitle"]
        video_title_name.delete(0, 'end')
        video_title_name.insert('end', TargetVideoTitle)
    else:
        video_title_name.delete(0, 'end')
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
        resolution_dropdown_selected.set('Unchanged')
        project_config["VideoResolution"] = 'Unchanged'

    widget_status_update(NORMAL)

    win.update()


"""
##########################
Job list support functions
##########################
"""

def job_list_process_selection(evt):
    global job_list
    global job_list_listbox
    global rerun_job_btn

    # Note here that Tkinter passes an event object to onselect()
    # w = evt.widget - We already know the widget

    if job_list_listbox.size() == 0:
        return

    selected_indices = job_list_listbox.curselection()
    if selected_indices:
        selected = int(job_list_listbox.curselection()[0])
        entry = job_list_listbox.get(selected)
        rerun_job_btn.config(text='Rerun job' if job_list[entry]['done'] else rerun_job_btn.config(text='Mark as run'))


def job_list_add_current():
    global job_list, template_list
    global CurrentFrame, StartFrame, frames_to_encode
    global project_config, video_filename_name
    global job_list_listbox
    global encode_all_frames, SourceDirFileList
    global frame_from_str, frame_to_str
    global resolution_dropdown_selected

    entry_name = video_filename_name.get()
    if entry_name == "":
        entry_name = os.path.split(SourceDir)[1]
    if project_config["FilmType"] == 'R8':
        entry_name = entry_name + ", R8, "
    else:
        entry_name = entry_name + ", S8, "
    entry_name = entry_name + "Frames "
    if encode_all_frames.get():
        entry_name = entry_name + "0"
        frames_to_encode = len(SourceDirFileList)
    else:
        entry_name = entry_name + frame_from_str.get()
        frames_to_encode = int(frame_to_str.get()) - int(frame_from_str.get()) + 1
    entry_name = entry_name + "-"
    if encode_all_frames.get():
        entry_name = entry_name + str(len(SourceDirFileList))
    else:
        entry_name = entry_name + frame_to_str.get()
    entry_name = entry_name + " ("
    entry_name = entry_name + str(frames_to_encode)
    entry_name = entry_name + " frames)"
    if project_config["GenerateVideo"]:
        if ffmpeg_preset.get() == 'veryslow':
            entry_name = entry_name + ", HQ video"
        elif ffmpeg_preset.get() == 'veryfast':
            entry_name = entry_name + ", Low Q. video"
        else:
            entry_name = entry_name + ", medium Q. video"
    else:
        entry_name = entry_name + ", no video"
    if resolution_dropdown_selected.get():
        entry_name = entry_name + ", " + resolution_dropdown_selected.get()

    save_project = True
    listbox_index = 'end'
    if entry_name in job_list:
        if tk.messagebox.askyesno(
                "Job already exists",
                "A job named " + entry_name + " exists already in the job list. "
                "Do you want to overwrite it?."):
            listbox_index = job_list_listbox.get(0, "end").index(entry_name)
            job_list_listbox.delete(listbox_index)
        else:
            save_project = False
    if save_project:
        save_project_config()  # Make sure all current settings are in project_config
        job_list[entry_name] = {'project': project_config.copy(), 'done': False, 'attempted': False}
        # If a custom pattern is used, copy it with the name of the job, and change it in the joblist/project item
        if template_list.get_active_type() == 'custom' and os.path.isfile(template_list.get_active_filename()):
            CustomTemplateDir = os.path.dirname(template_list.get_active_filename())    # should be aux_dir, but better be safe
            # Maybe we should check here if a video filename has been defined
            TargetTemplateFile = os.path.join(CustomTemplateDir, os.path.splitext(job_list[entry_name]['project']['VideoFilename'])[0]+'.jpg' )
            if template_list.get_active_filename() != TargetTemplateFile:
                shutil.copyfile(template_list.get_active_filename(), TargetTemplateFile)
            job_list[entry_name]['project']['CustomTemplateFilename'] = TargetTemplateFile
        else:
            if 'CustomTemplateFilename' in project_config:
                del project_config['CustomTemplateFilename']
        job_list_listbox.insert(listbox_index, entry_name)
        job_list_listbox.itemconfig(listbox_index)
        job_list_listbox.select_set(listbox_index)


# gets currently selected job list item adn loads it in the UI fields (to allow editing)
def job_list_load_selected():
    global job_list
    global CurrentFrame, StartFrame, frames_to_encode
    global project_config, video_filename_name
    global job_list_listbox
    global encode_all_frames, SourceDirFileList
    global frame_from_str, frame_to_str
    global resolution_dropdown_selected

    selected = job_list_listbox.curselection()
    if selected != ():
        entry_name = job_list_listbox.get(selected[0])  # we pick fist item as curselection returns a list

        if entry_name in job_list:
            # Copy job settings as current project settings
            project_config = job_list[entry_name]['project']
            decode_project_config()
            # Load matching file list from newly selected dir
            get_source_dir_file_list()  # first_absolute_frame is set here
            general_config["SourceDir"] = SourceDir

            # Enable Start and Crop buttons, plus slider, once we have files to handle
            cropping_btn.config(state=NORMAL)
            frame_slider.config(state=NORMAL)
            Go_btn.config(state=NORMAL)
            frame_slider.set(CurrentFrame)
            init_display()


def job_list_delete_selected():
    global job_list
    global job_list_listbox
    selected = job_list_listbox.curselection()
    if selected != ():
        job_list.pop(job_list_listbox.get(selected))
        job_list_listbox.delete(selected)
        if selected[0] < job_list_listbox.size():
            job_list_listbox.select_set(selected[0])
        elif job_list_listbox.size() > 0:
            job_list_listbox.select_set(selected[0]-1)


def job_list_rerun_selected():
    global job_list
    global job_list_listbox

    selected_indices = job_list_listbox.curselection()
    if selected_indices != ():
        selected = int(job_list_listbox.curselection()[0])
        entry = job_list_listbox.get(selected)

        job_list[entry]['done'] = not job_list[entry]['done']
        job_list[entry]['attempted'] = job_list[entry]['done']
        job_list_listbox.itemconfig(selected, fg='green' if job_list[entry]['done'] else 'black')
        rerun_job_btn.config(text='Rerun job' if job_list[entry]['done'] else 'Mark as run')


def save_job_list():
    global job_list, job_list_filename

    if not IgnoreConfig:
        with open(job_list_filename, 'w+') as f:
            json.dump(job_list, f)


def load_job_list():
    global job_list, job_list_filename, job_list_listbox

    if not IgnoreConfig and os.path.isfile(job_list_filename):
        f = open(job_list_filename)
        job_list = json.load(f)
        for entry in job_list:
            job_list_listbox.insert('end', entry)   # Add to listbox
            job_list[entry]['attempted'] = job_list[entry]['done']  # Add default value for new json field
        f.close()
        idx = 0
        for entry in job_list:
            job_list_listbox.itemconfig(idx, fg='black' if job_list[entry]['done'] == False else 'green')
            idx += 1
    else:   # No job list file. Set empty config to force defaults
        job_list = {}



def start_processing_job_list():
    global BatchJobRunning, start_batch_btn, ConvertLoopExitRequested
    if BatchJobRunning:
        ConvertLoopExitRequested = True
    else:
        BatchJobRunning = True
        widget_status_update(DISABLED, start_batch_btn)
        for entry in job_list:
            job_list[entry]['attempted'] = job_list[entry]['done'] # Reset attempted flag for those not done yet
        job_processing_loop()


def job_processing_loop():
    global job_list, job_list_listbox
    global project_config
    global CurrentJobEntry
    global BatchJobRunning
    global project_config_from_file
    global suspend_on_completion
    global CurrentFrame

    job_started = False
    for entry in job_list:
        if  not job_list[entry]['done'] and not job_list[entry]['attempted']:
            job_list[entry]['attempted'] = True
            job_list_listbox.selection_clear(0, END)
            idx = job_list_listbox.get(0, "end").index(entry)
            job_list_listbox.itemconfig(idx, fg='blue')
            CurrentJobEntry = entry
            if 'FrameFrom' in job_list[entry]['project']:
                CurrentFrame = job_list[entry]['project']['FrameFrom']
                logging.debug(f"Set current Frame to {CurrentFrame}")
            else:
                CurrentFrame = 0
            logging.debug(f"Processing {entry}, starting from frame {CurrentFrame}, {job_list[entry]['project']['FramesToEncode']} frames")
            project_config_from_file = False
            project_config = job_list[entry]['project'].copy()
            decode_project_config()

            # Load matching file list from newly selected dir
            get_source_dir_file_list()  # first_absolute_frame is set here
            get_target_dir_file_list()

            start_convert()
            job_started = True
            break
        #job_list_listbox.selection_clear(idx)
    if not job_started:
        CurrentJobEntry = -1
        generation_exit()
        if suspend_on_completion.get() == 'batch_completion':
            system_suspend()
            time.sleep(2)


def job_list_delete_current(event):
    job_list_delete_selected()


def job_list_load_current(event):
    job_list_load_selected()


def job_list_rerun_current(event):
    global job_list, job_list_listbox
    job_list_rerun_selected()
    selected_index = job_list_listbox.curselection()
    if selected_index:
        idx = selected_index[0]
        job_list_listbox.selection_clear(0, tk.END)
        if idx < job_list_listbox.size() - 1:
            job_list_listbox.selection_set(idx + 1)


def get_job_listbox_index(CurrentJobEntry):
    global job_list, job_list_listbox
    idx = -1
    if CurrentJobEntry in job_list:
        idx = job_list_listbox.get(0, "end").index(CurrentJobEntry)
    return idx


def sync_job_list_with_listbox():
    global job_list_listbox, job_list

    order_list=[]
    for idx in range(0, job_list_listbox.size()):
        order_list.append(job_list_listbox.get(idx))

    # Create a new dictionary with the desired order
    job_list = {key: job_list[key] for key in order_list}


def job_list_move_up(event):
    global job_list_listbox, job_list
    selected_index = job_list_listbox.curselection()
    if selected_index:
        idx = selected_index[0]
        if idx > 0:
            item = job_list_listbox.get(idx)
            job_list_listbox.delete(idx)
            job_list_listbox.insert(idx - 1, item)
            job_list_listbox.selection_clear(0, tk.END)
            job_list_listbox.selection_set(idx - 1)
            job_list_listbox.activate(idx - 1)
            job_list_listbox.see(idx - 1)  # Scroll to the new selection
            if item in job_list:
                if job_list[item]['done'] == True:
                    job_list_listbox.itemconfig(idx - 1, fg='green')
            sync_job_list_with_listbox()
            #return "break"


def job_list_move_down(event):
    global job_list_listbox, job_list
    selected_index = job_list_listbox.curselection()
    if selected_index:
        idx = selected_index[0]
        if idx < job_list_listbox.size() - 1:
            item = job_list_listbox.get(idx)
            job_list_listbox.delete(idx)
            job_list_listbox.insert(idx + 1, item)
            job_list_listbox.selection_clear(0, tk.END)
            job_list_listbox.selection_set(idx + 1)
            job_list_listbox.activate(idx + 1)
            job_list_listbox.see(idx + 1)  # Scroll to the new selection
            if item in job_list:
                if job_list[item]['done'] == True:
                    job_list_listbox.itemconfig(selected_index + 1, fg='green')
            sync_job_list_with_listbox()
            #return "break"


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
    global FPM_LastMinuteFrameTimes
    global FPM_StartTime
    global FPM_CalculatedValue

    # Get current time
    frame_time = time.time()
    # Determine if we should start new count (last capture older than 5 seconds)
    if len(FPM_LastMinuteFrameTimes) == 0 or FPM_LastMinuteFrameTimes[-1] < frame_time - 12:
        FPM_StartTime = frame_time
        FPM_LastMinuteFrameTimes.clear()
        FPM_CalculatedValue = -1
    # Add current time to list
    FPM_LastMinuteFrameTimes.append(frame_time)
    # Remove entries older than one minute
    FPM_LastMinuteFrameTimes.sort()
    while FPM_LastMinuteFrameTimes[0] <= frame_time-60:
        FPM_LastMinuteFrameTimes.remove(FPM_LastMinuteFrameTimes[0])
    # Calculate current value, only if current count has been going for more than 10 seconds
    if frame_time - FPM_StartTime > 60:  # no calculations needed, frames in list are all in th elast 60 seconds
        FPM_CalculatedValue = len(FPM_LastMinuteFrameTimes)
    elif frame_time - FPM_StartTime > 10:  # some  calculations needed if less than 60 sec
        FPM_CalculatedValue = int((len(FPM_LastMinuteFrameTimes) * 60) / (frame_time - FPM_StartTime))



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

    # Load matching file list from newly selected dir
    get_source_dir_file_list()  # first_absolute_frame is set here

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
    global VideoTargetDir
    global video_target_dir

    VideoTargetDir = filedialog.askdirectory(
        initialdir=VideoTargetDir,
        title="Select folder where to store generated video")

    if not VideoTargetDir:
        return
    elif VideoTargetDir == SourceDir:
        tk.messagebox.showerror(
            "Error!",
            "Video target folder cannot be the same as source folder.")
        return
    else:
        video_target_dir.delete(0, 'end')
        video_target_dir.insert('end', VideoTargetDir)
        video_target_dir.after(100, video_target_dir.xview_moveto, 1)

    project_config["VideoTargetDir"] = VideoTargetDir


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
    global force_4_3_crop_checkbox, force_16_9_crop_checkbox
    global custom_stabilization_btn
    global generate_video_checkbox, skip_frame_regeneration_cb
    global video_target_dir, video_target_folder_btn
    global video_filename_label, video_title_label, video_title_name
    global video_fps_dropdown
    global resolution_dropdown
    global video_filename_name
    global ffmpeg_preset_rb1, ffmpeg_preset_rb2, ffmpeg_preset_rb3
    global start_batch_btn
    global add_job_btn, delete_job_btn, rerun_job_btn
    global stabilization_bounds_alert_checkbox
    global perform_fill_none_rb, perform_fill_fake_rb, perform_fill_dumb_rb
    global extended_stabilization_checkbox
    global SourceDirFileList
    global template_list

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
        if ExpertMode:
            custom_stabilization_btn.config(state=widget_state)
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
        video_filename_name.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        ffmpeg_preset_rb1.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        ffmpeg_preset_rb2.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        ffmpeg_preset_rb3.config(state=widget_state if project_config["GenerateVideo"] else DISABLED)
        start_batch_btn.config(state=widget_state if button_action != start_batch_btn else NORMAL)
        add_job_btn.config(state=widget_state)
        delete_job_btn.config(state=widget_state)
        rerun_job_btn.config(state=widget_state)
        job_list_listbox.config(state=widget_state)
    # Handle a few specific widgets having extra conditions
    if len(SourceDirFileList) == 0:
        perform_stabilization_checkbox.config(state=DISABLED)
        perform_cropping_checkbox.config(state=DISABLED)
        cropping_btn.config(state=DISABLED)
        force_4_3_crop_checkbox.config(state=DISABLED)
        force_16_9_crop_checkbox.config(state=DISABLED)
        perform_denoise_checkbox.config(state=DISABLED)
        perform_sharpness_checkbox.config(state=DISABLED)
    if ExpertMode:
        custom_stabilization_btn.config(relief=SUNKEN if template_list.get_active_type() == 'custom' else RAISED)


def update_frame_from(event):
    global frame_from_str, frame_slider
    global CurrentFrame
    if len(frame_from_str.get()) == 0:
        frame_from_str.set(CurrentFrame)
    else:
        select_scale_frame(frame_from_str.get())
        frame_slider.set(frame_from_str.get())


def update_frame_to(event):
    global frame_to_str, frame_slider
    global CurrentFrame
    if len(frame_to_str.get()) == 0:
        frame_to_str.set(CurrentFrame)
    else:
        select_scale_frame(frame_to_str.get())
        frame_slider.set(frame_to_str.get())

def on_paste_all_entries(event, entry):
    try:
        entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
    except tk.TclError:
        logging.warning("No selection to delete")

def custom_ffmpeg_path_focus_out(event):
    global custom_ffmpeg_path, FfmpegBinName

    if not is_ffmpeg_installed():
        tk.messagebox.showerror("Error!",
                                "Provided FFMpeg path is invalid.")
        custom_ffmpeg_path.delete(0, 'end')
        custom_ffmpeg_path.insert('end', FfmpegBinName)
    else:
        FfmpegBinName = custom_ffmpeg_path.get()
        general_config["FfmpegBinName"] = FfmpegBinName


def perform_rotation_selection():
    global perform_rotation
    rotation_angle_spinbox.config(
        state=NORMAL if perform_rotation.get() else DISABLED)
    rotation_angle_label.config(
        state=NORMAL if perform_rotation.get() else DISABLED)
    project_config["PerformRotation"] = perform_rotation.get()
    win.after(5, scale_display_update)


def rotation_angle_selection(updown):
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
    global stabilization_bounds_alert_checkbox

    if ExpertMode:
        stabilization_threshold_spinbox.config(
            state=NORMAL if perform_stabilization.get() else DISABLED)
    project_config["PerformStabilization"] = perform_stabilization.get()
    win.after(5, scale_display_update)
    widget_status_update(NORMAL)


def extended_stabilization_selection():
    global extended_stabilization
    project_config["ExtendedStabilization"] = extended_stabilization.get()
    win.after(5, scale_display_update)
    widget_status_update(NORMAL)


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
    global stabilization_bounds_alert_checkbox

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


def generate_video_selection():
    global generate_video

    project_config["GenerateVideo"] = generate_video.get()
    widget_status_update(NORMAL)

def set_fps(selected):
    global VideoFps

    project_config["VideoFps"] = selected
    VideoFps = eval(selected)


def set_resolution(selected):
    global resolution_dict
    project_config["VideoResolution"] = selected


def display_template_popup_closure():
    global template_popup_window, display_template_popup, debug_template_match

    debug_template_match = False

    display_template_popup.set(False)

    template_popup_window.destroy()


def debug_template_popup():
    global win
    global template_list
    global display_template_popup
    global template_popup_window
    global CropTopLeft, CropBottomRight
    global debug_template_match, debug_template_width, debug_template_height
    global current_frame_text, crop_text, film_type_text
    global search_area_text, template_type_text, hole_pos_text, template_size_text, template_wb_proportion_text
    global left_stripe_canvas, left_stripe_stabilized_canvas, template_canvas
    global SourceDirFileList, CurrentFrame

    if not developer_debug:
        return

    if not display_template_popup.get():
        debug_template_match = False
        template_popup_window.destroy()
        return

    debug_template_match = True

    template_popup_window = Toplevel(win)
    template_popup_window.title("Hole Template match debug info")

    template_popup_window.minsize(width=300, height=template_popup_window.winfo_height())

    # Create three vertical frames in the bottom horizontal frame
    left_frame = Frame(template_popup_window, width=60, height=8)
    left_frame.pack(side=LEFT)
    center_frame = Frame(template_popup_window, width=60, height=8)
    center_frame.pack(side=LEFT)
    right_frame = Frame(template_popup_window, width=280, height=8)
    right_frame.pack(side=LEFT)
    # Add a label and a close button to the popup window
    #label = Label(left_frame, text="Current template:")
    #label.pack(pady=5, padx=10, anchor=W)

    ratio = 0.33  # Reduce template to one third
    active_template = template_list.get_active_template()
    aux = resize_image(active_template, ratio)
    template_canvas_height = int(frame_height*ratio)
    debug_template_width = aux.shape[1]
    debug_template_height = aux.shape[0]
    # Set expected hole template pos
    hole_template_pos = template_list.get_active_position()

    # Create Canvas to display template
    template_canvas = Canvas(left_frame, bg='dark grey',
                                 width=debug_template_width, height=template_canvas_height)
    template_canvas.pack(side=TOP, anchor=N)
    setup_tooltip(template_canvas, "Active template used to locate sprocket hole(s)")

    DisplayableImage = ImageTk.PhotoImage(Image.fromarray(aux))
    template_canvas.create_image(0, int(hole_template_pos[1]*0.33), anchor=NW, image=DisplayableImage)
    template_canvas.image = DisplayableImage

    # Create Canvas to display image left stripe (stabilized)
    left_stripe_stabilized_canvas = Canvas(center_frame, bg='dark grey',
                                 width=debug_template_width, height=debug_template_height)
    left_stripe_stabilized_canvas.pack(side=LEFT, anchor=N)
    setup_tooltip(left_stripe_stabilized_canvas, "Current frame after stabilization, with detected template highlighted in green")

    # Create Canvas to display image left stripe (non stabilized)
    left_stripe_canvas = Canvas(center_frame, bg='dark grey',
                                 width=debug_template_width, height=debug_template_height)
    left_stripe_canvas.pack(side=LEFT, anchor=N)
    setup_tooltip(left_stripe_canvas, "Template search area for current frame, as used to spot template")

    # Add a label with the film type
    film_type_text = tk.StringVar()
    film_type_label = Label(right_frame, textvariable=film_type_text, font=("Arial", FontSize))
    film_type_label.pack(pady=5, padx=10, anchor="center")
    film_type_text.set(f"Film type: {film_type.get()}")

    # Add a label with the cropping dimensions
    crop_text = tk.StringVar()
    crop_label = Label(right_frame, textvariable=crop_text, font=("Arial", FontSize))
    crop_label.pack(pady=5, padx=10, anchor="center")
    crop_text.set(f"Crop: {CropTopLeft}, {CropBottomRight}")

    # Add a label with the template type
    template_type_text = tk.StringVar()
    template_type_label = Label(right_frame, textvariable=template_type_text, font=("Arial", FontSize))
    template_type_label.pack(pady=5, padx=10, anchor="center")
    template_type_text.set(f"Template type: {template_list.get_active_type()}")

    # Add a label with the stabilization info
    hole_pos_text = tk.StringVar()
    hole_pos_label = Label(right_frame, textvariable=hole_pos_text, font=("Arial", FontSize))
    hole_pos_label.pack(pady=5, padx=10, anchor="center")
    hole_pos_text.set(f"Expected template pos: {hole_template_pos}")

    #Label with template size
    template_size_text = tk.StringVar()
    template_size_label = Label(right_frame, textvariable=template_size_text, font=("Arial", FontSize))
    template_size_label.pack(pady=5, padx=10, anchor="center")
    template_size_text.set(f"Template Size: {template_list.get_active_size()}")

    #Label with template white on black proportion
    template_wb_proportion_text = tk.StringVar()
    template_wb_proportion_label = Label(right_frame, textvariable=template_wb_proportion_text, font=("Arial", FontSize))
    template_wb_proportion_label.pack(pady=5, padx=10, anchor="center")
    template_wb_proportion_text.set(f"WoB proportion: {int(template_list.get_active_wb_proportion() * 100)}%")

    #Label with search area
    search_area_text = tk.StringVar()
    search_area_label = Label(right_frame, textvariable=search_area_text, font=("Arial", FontSize))
    search_area_label.pack(pady=5, padx=10, anchor="center")
    search_area_text.set(f"Search Area: {HoleSearchTopLeft}, {HoleSearchBottomRight})")

    current_frame_text = tk.StringVar()
    current_frame_label = Label(right_frame, textvariable=current_frame_text, width=45, font=("Arial", FontSize))
    current_frame_label.pack(pady=5, padx=10, anchor="center")
    current_frame_text.set("Current:")

    close_button = Button(right_frame, text="Close", command=display_template_popup_closure, font=("Arial", FontSize))
    close_button.pack(pady=10, padx=10, anchor="center")

    # Run a loop for the popup window
    template_popup_window.wait_window()

    display_template_popup.set(False)
    debug_template_match = False


def debug_template_display_info(frame_idx, top_left, move_x, move_y):
    global current_frame_text
    if debug_template_match:
        current_frame_text.set(f"Current Frm:{frame_idx}, Tmp.Pos.:{top_left}, ΔX:{move_x}, ΔY:{move_y}")


def debug_template_display_frame_raw(img):
    global left_stripe_canvas, left_stripe_stabilized_canvas

    if debug_template_match:
        try:
            left_stripe_canvas.config(width=int(img.shape[1]*0.33))
            left_stripe_stabilized_canvas.config(width=img.shape[1]*0.33)
        except Exception as e:
            logging.error(f"Exception {e} when configuring canvas")
        debug_template_display_frame(left_stripe_canvas, img)


def debug_template_display_frame_stabilized(img):
    global left_stripe_stabilized_canvas

    if debug_template_match:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        debug_template_display_frame(left_stripe_stabilized_canvas, img)


def debug_template_refresh_template():
    global template_canvas, template_list
    global hole_pos_text, template_type_text, template_size_text, template_wb_proportion_text, film_type_text

    if debug_template_match:
        hole_template_pos = template_list.get_active_position()
        ratio = 0.33  # Reduce template to one third
        aux = resize_image(template_list.get_active_template(), ratio)
        template_canvas.config(width=int(template_list.get_active_size()[0]*ratio))
        template_canvas.delete('all')
        DisplayableImage = ImageTk.PhotoImage(Image.fromarray(aux))
        template_canvas.create_image(0, int(hole_template_pos[1] * 0.33), anchor=NW, image=DisplayableImage)
        template_canvas.image = DisplayableImage
        hole_pos_text.set(f"Expected template pos: {hole_template_pos}")
        template_type_text.set(f"Template type: {template_list.get_active_type()}")
        template_size_text.set(f"Template Size: {template_list.get_active_size()}")
        template_wb_proportion_text.set(f"WoB proportion: {int(template_list.get_active_wb_proportion()*100)}%")
        film_type_text.set(f"Film type: {film_type.get()}")

def debug_template_display_frame(canvas, img):
    global debug_template_width, debug_template_height

    if debug_template_match:
        try:
            height, width = img.shape[:2]
            ratio = debug_template_height / height
            ratio = 0.33
            resized_image = cv2.resize(img, (int(width*ratio), int(height*ratio)))
            pil_image = Image.fromarray(resized_image)
            photo_image = ImageTk.PhotoImage(image=pil_image)
            canvas.config(height=int(height*ratio))
            canvas.create_image(0, 0, anchor=NW, image=photo_image)
            canvas.image = photo_image
        except Exception as e:
            logging.error(f"Exception {e} when updating canvas")


def scale_display_update():
    global win
    global frame_scale_refresh_done, frame_scale_refresh_pending
    global CurrentFrame
    global perform_stabilization, perform_cropping, perform_rotation
    global CropTopLeft, CropBottomRight
    global SourceDirFileList
    global debug_template_match

    frame_to_display = CurrentFrame
    if frame_to_display >= len(SourceDirFileList):
        return
    # If HDR mode, pick the lightest frame to select rectangle
    file3 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (frame_to_display + 1, 2, file_type))
    if os.path.isfile(file3):  # If hdr frames exist, add them
        file = file3
    else:
        file = SourceDirFileList[frame_to_display]
    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
    if img is None:
        frame_scale_refresh_done = True
        logging.error(
            "Error reading frame %i, skipping", frame_to_display)
    else:
        if not frame_scale_refresh_pending:
            if perform_rotation.get():
                img = rotate_image(img)
            if perform_stabilization.get() or debug_template_match:
                img = stabilize_image(CurrentFrame, img, img)
        if perform_cropping.get():
            img = crop_image(img, CropTopLeft, CropBottomRight)
        else:
            img = even_image(img)
        if img is not None and not img.size == 0:   # Just in case img is nto well generated
            display_image(img)
        if frame_scale_refresh_pending:
            frame_scale_refresh_pending = False
            win.after(100, scale_display_update)
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
        frame_slider.config(label='Global:'+
                            str(CurrentFrame+first_absolute_frame))
        if frame_scale_refresh_done:
            frame_scale_refresh_done = False
            frame_scale_refresh_pending = False
            win.after(5, scale_display_update)
        else:
            frame_scale_refresh_pending = True


################################
# Second level support functions
################################


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
        logging.debug(f"Invalid detection templated, cannot determine film type.")
        tk.messagebox.showerror("Film detection failed",
            "Templates to detect film type are missing, please set film type manually.")
        return

    # Create a list with 5 evenly distributed values between CurrentFrame and len(SourceDirFileList) - CurrentFrame
    num_frames = min(10,len(SourceDirFileList)-CurrentFrame)
    FramesToCheck = np.linspace(CurrentFrame, len(SourceDirFileList) - CurrentFrame - 1, num_frames).astype(int).tolist()
    for frame_to_check in FramesToCheck:
        img = cv2.imread(SourceDirFileList[frame_to_check], cv2.IMREAD_UNCHANGED)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_bw = cv2.threshold(img_gray, 220, 255, cv2.THRESH_BINARY)[1]
        search_img = get_image_left_stripe(img_bw)
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
    global work_image, base_image, original_image
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
    global line_thickness
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

    # load the image, clone it, and setup the mouse callback function
    original_image = cv2.imread(file, cv2.IMREAD_UNCHANGED)
    if not is_cropping:   # only take left stripe if not for cropping
        original_image = get_image_left_stripe(original_image)
    # Rotate image if required
    if perform_rotation.get():
        original_image = rotate_image(original_image)
    # Stabilize image to make sure target image matches user visual definition
    if is_cropping and perform_stabilization.get():
        original_image = stabilize_image(CurrentFrame, original_image, original_image)
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
    cv2.namedWindow(RectangleWindowTitle, cv2.WINDOW_GUI_NORMAL)
    # Force the window to have focus (otherwise it won't take any keys)
    # No valid method has been found so far to force the opencv to hav efocus. Apparently it is not simple
    cv2.setWindowProperty(RectangleWindowTitle,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
    cv2.setWindowProperty(RectangleWindowTitle,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_NORMAL)

    # Capture mouse events
    cv2.setMouseCallback(RectangleWindowTitle, draw_rectangle)
    # rectangle_refresh = False
    cv2.imshow(RectangleWindowTitle, work_image)
    # Cannot make window wider than required since in Windows the image is expanded tpo cover the full width
    if is_demo:
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
    win.update()

    RectangleWindowTitle = CropWindowTitle


    if select_rectangle_area(is_cropping=True):
        CropAreaDefined = True
        widget_status_update(NORMAL, 0)
        CropTopLeft = RectangleTopLeft
        CropBottomRight = RectangleBottomRight
        logging.debug("Crop area: (%i,%i) - (%i, %i)", CropTopLeft[0],
                      CropTopLeft[1], CropBottomRight[0], CropBottomRight[1])
    else:
        CropAreaDefined = False
        widget_status_update(DISABLED, 0)
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

    win.after(5, scale_display_update)
    win.update()


def select_custom_template():
    global template_list, film_type
    global RectangleWindowTitle
    global area_select_image_factor

    if not ExpertMode:
        return

    # First, define custom template name and filename in case it needs to be deleted
    # Template Name = Last folder in the path, plus Frame From,  Frame to it not encoding all
    if encode_all_frames.get():
        template_name = f"{os.path.split(SourceDir)[-1]}-all"
    else:
        template_name = f"{os.path.split(SourceDir)[-1]}-{frame_from_str.get()}-{frame_to_str.get()}"
    # Set filename
    template_filename = f"Pattern.custom.{template_name}.jpg"
    full_path_template_filename = os.path.join(aux_dir, template_filename)

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
        win.update()

        RectangleWindowTitle = CustomTemplateTitle

        if select_rectangle_area(is_cropping=False) and CurrentFrame < len(SourceDirFileList):
            # Extract template from image
            file = SourceDirFileList[CurrentFrame]
            file3 = os.path.join(SourceDir, FrameHdrInputFilenamePattern % (CurrentFrame + 1, 2, file_type))
            if os.path.isfile(file3):  # If hdr frames exist, add them
                file = file3
            img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
            img = crop_image(img, RectangleTopLeft, RectangleBottomRight)
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # img_bw = cv2.threshold(img_gray, float(StabilizationThreshold), 255, cv2.THRESH_TRUNC | cv2.THRESH_TRIANGLE)[1]
            img_bw = cv2.threshold(img_gray, float(StabilizationThreshold), 255, cv2.THRESH_BINARY)[1]
            # img_edges = cv2.Canny(image=img_bw, threshold1=100, threshold2=20)  # Canny Edge Detection
            img_final = img_bw

            # Write template to disk
            project_config["CustomTemplateFilename"] = full_path_template_filename
            cv2.imwrite(full_path_template_filename, img_final)

            # Add template to list
            template_list.add(template_name, full_path_template_filename, 'custom', RectangleTopLeft)   # size and template automatically refreshed upon addition
            logging.debug(f"Template top left-size: {template_list.get_active_position()} - {template_list.get_active_size()}")
            widget_status_update(NORMAL, 0)
            custom_stabilization_btn.config(relief=SUNKEN)

            project_config['CustomTemplateExpectedPos'] = template_list.get_active_position()
            project_config['CustomTemplateName'] = template_list.get_active_name()

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

    project_config["CustomTemplateDefined"] = True if template_list.get_active_type() == 'custom' else False
    debug_template_refresh_template()

    # Enable all buttons in main window
    widget_status_update(NORMAL, 0)
    win.update()




def set_film_type():
    global film_type, template_list

    if template_list.set_active(film_type.get(), film_type.get()):
        project_config["FilmType"] = film_type.get()
        debug_template_refresh_template()
        logging.debug(f"Setting {film_type.get()} template as active")
        return True
    else:
        tk.messagebox.showerror(
            "Default template could not be set",
            "Error while reverting back to standard template after disabling custom.")
        return False


def match_level_color(t):
    if t < 0.7:
        return "red"
    if t < 0.9:
        return "orange"
    return "green"


def match_level_color_bgr(t):
    if t < 0.7:
        return (0,0,255)
    if t < 0.9:
        return (0,165,255)
    return (0,255,0)


def match_template(frame_idx, template, img):
    tw = template.shape[1]
    th = template.shape[0]
    iw = img.shape[1]
    ih = img.shape[0]
    if (tw >= iw or th >= ih):
        logging.error("Template (%ix%i) bigger than search area (%ix%i)",
                      tw, th, iw, ih)
        return (0, 0, 0)

    # convert img to grey, checking various thresholds
    best_thres = 0
    best_wb_proportion = 1
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    for thres in range(55, 255, 10):
        img_bw = cv2.threshold(img_gray, thres, 255, cv2.THRESH_BINARY)[1]  #THRESH_TRUNC, THRESH_BINARY
        white_pixel_count = cv2.countNonZero(img_bw)
        total_pixels = img_bw.size
        if abs((white_pixel_count/total_pixels)-template_list.get_active_wb_proportion()) < best_wb_proportion:
            best_wb_proportion = abs((white_pixel_count/total_pixels)-template_list.get_active_wb_proportion())
            best_thres = thres
            img_final = img_bw

    #img_edges = cv2.Canny(image=img_bw, threshold1=100, threshold2=1)  # Canny Edge Detection
    aux = cv2.matchTemplate(img_final, template, cv2.TM_CCOEFF_NORMED)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(aux)
    top_left = maxLoc

    return best_thres, top_left, round(maxVal,2), img_final


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


def debug_display_image(window_name, img):
    if dev_debug_enabled:
        cv2.namedWindow(window_name)
        if img.shape[0] >= 2 and img.shape[1] >= 2:
            img_s = resize_image(img, 0.5)
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

    draw_capture_canvas.create_image(padding_x, padding_y, anchor=NW, image=DisplayableImage)
    draw_capture_canvas.image = DisplayableImage

# Display frames while video encoding is ongoing
# No need to care about sequencing since video encoding process in AfterScan is single threaded
def display_output_frame_by_number(frame_number):
    global StartFrame
    global TargetDirFileList, file_type_out

    TargetFile = TargetDir + '/' + FrameOutputFilenamePattern % (StartFrame + frame_number, file_type_out)

    if TargetFile in TargetDirFileList:
        img = cv2.imread(TargetFile, cv2.IMREAD_UNCHANGED)
        display_image(img)


def clear_image():
    global draw_capture_canvas
    draw_capture_canvas.delete('all')


def resize_image(img, ratio):
    # Calculate the proportional size of original image
    width = int(img.shape[1] * ratio)
    height = int(img.shape[0] * ratio)

    dsize = (width, height)

    # resize image
    return cv2.resize(img, dsize)


def get_image_left_stripe(img):
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

def stabilize_image(frame_idx, img, img_ref, img_ref_alt = None, id = -1):
    global SourceDirFileList
    global first_absolute_frame, StartFrame
    global HoleSearchTopLeft, HoleSearchBottomRight
    global CropTopLeft, CropBottomRight, win
    global stabilization_bounds_alert, stabilization_bounds_alert_counter
    global stabilization_bounds_alert_checkbox
    global project_name
    global frame_fill_type, extended_stabilization
    global CsvFile, GenerateCsv, CsvFramesOffPercent
    global stabilization_threshold_match_label
    global debug_template_match
    global perform_stabilization
    global template_list

    # Get image dimensions to perform image shift later
    width = img_ref.shape[1]
    height = img_ref.shape[0]
    # Set hole template expected position
    hole_template_pos = template_list.get_active_position()
    film_hole_template = template_list.get_active_template()

    # Search film hole pattern
    best_match_level = 0
    best_top_left = [0,0]

    # Get sprocket hole area
    left_stripe_image = get_image_left_stripe(img_ref)
    #WorkStabilizationThreshold = np.percentile(left_stripe_image, 90)
    img_ref_alt_used = False
    while True:
        thres, top_left, match_level, img_matched = match_template(frame_idx, film_hole_template, left_stripe_image)
        if match_level >= 0.85:
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
    debug_template_display_frame_raw(img_matched)

    if top_left[1] != -1 and match_level > 0.1:
        move_x = hole_template_pos[0] - top_left[0]
        move_y = hole_template_pos[1] - top_left[1]
        if abs(move_x) > 150 or abs(move_y) > 350:  # if shift too big, ignore it, probably for the better
            logging.warning(f"Shift too big ({move_x}, {move_y}), ignoring it.")
            move_x = 0
            move_y = 0
    else:   # If match is not good, keep the frame where it is, will probably look better
        logging.warning(f"Template match not good ({match_level}, ignoring it.")
        move_x = 0
        move_y = 0
    log_line = f"T{id} - " if id != -1 else ""
    logging.debug(log_line+f"Frame {frame_idx:5d}: threshold: {thres:3d}, top left: ({top_left[0]:4d},{top_left[0]:4d}), move_x:{move_x:4d}, move_y:{move_y:4d}")
    debug_template_display_info(frame_idx, top_left, move_x, move_y)
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

    if missing_rows > 0 and perform_rotation.get():
        missing_rows = missing_rows + 10  # If image is rotated, add 10 to cover gap between image and fill

    # Log frame alignment info for analysis (only when in convert loop)
    # Items logged: Tag, project id, Frame number, missing pixel rows, location (bottom/top), Vertical shift
    stabilization_threshold_match_label.config(fg='white', bg=match_level_color(match_level),
                                               text=str(int(match_level * 100)))
    if ConvertLoopRunning:
        if missing_bottom < 0 or missing_top < 0:
            stabilization_bounds_alert_counter += 1
            if stabilization_bounds_alert.get():
                win.bell()
            if GenerateCsv:
                CsvFile.write('%i, %i, %i\n' % (first_absolute_frame+frame_idx, missing_rows, int(match_level*100)))
    if frame_idx-StartFrame > 0:
        CsvFramesOffPercent = stabilization_bounds_alert_counter * 100 / (frame_idx-StartFrame)
    stabilization_bounds_alert_checkbox.config(text='Alert when image out of bounds (%i, %.1f%%)' % (
            stabilization_bounds_alert_counter, CsvFramesOffPercent))
    # Create the translation matrix using move_x and move_y (NumPy array): This is the actual stabilization
    # We double-check the check box since this function might be called just to debug template detection
    if perform_stabilization.get():
        # Check if frame fill is enabled, and required: Extract missing fragment
        if frame_fill_type.get() == 'fake' and ConvertLoopRunning and missing_rows > 0:
            # Perform temporary horizontal stabilization only first, to extract missing fragment
            translation_matrix = np.array([
                [1, 0, move_x],
                [0, 1, 0]
            ], dtype=np.float32)
            # Apply the translation to the image
            translated_image = cv2.warpAffine(src=img, M=translation_matrix,
                                              dsize=(width, height))
            if missing_top < 0:
                missing_fragment = translated_image[CropBottomRight[1]-missing_rows:CropBottomRight[1],0:width]
            elif missing_bottom < 0:
                missing_fragment = translated_image[CropTopLeft[1]:CropTopLeft[1]+missing_rows, 0:width]

        translation_matrix = np.array([
            [1, 0, move_x],
            [0, 1, move_y]
        ], dtype=np.float32)
        # Apply the translation to the image
        translated_image = cv2.warpAffine(src=img, M=translation_matrix,
                                          dsize=(width, height))
        # Check if frame fill is enabled, and required: Add missing fragment
        # Check if there is a gap in the frame, if so, and one of the 'fill' functions is enabled, fill accordingly
        if missing_rows > 0 and ConvertLoopRunning:
            if frame_fill_type.get() == 'fake':
                if missing_top < 0:
                    translated_image[CropTopLeft[1]:CropTopLeft[1]+missing_rows,0:width] = missing_fragment
                elif missing_bottom < 0:
                    translated_image[CropBottomRight[1]-missing_rows:CropBottomRight[1],0:width] = missing_fragment
            elif frame_fill_type.get() == 'dumb':
                if missing_top < 0:
                    translated_image = translated_image[missing_rows+CropTopLeft[1]:height,0:width]
                    translated_image = cv2.copyMakeBorder(src=translated_image, top=missing_rows+CropTopLeft[1], bottom=0, left=0, right=0,
                                                          borderType=cv2.BORDER_REPLICATE)
                elif missing_bottom < 0:
                    translated_image = translated_image[0:CropBottomRight[1]-missing_rows, 0:width]
                    translated_image = cv2.copyMakeBorder(src=translated_image, top=0, bottom=CropBottomRight[1]-missing_rows, left=0, right=0,
                                                          borderType=cv2.BORDER_REPLICATE)
    else:
        translated_image = img
    # Drew stabilization rectangles only for image in popup debug window to allow having it activated while encoding
    if debug_template_match and top_left[1] != -1 :
        if not perform_stabilization.get():
            move_x = 0
            move_y = 0
        left_stripe_img = get_image_left_stripe(translated_image)
        cv2.rectangle(left_stripe_img, (top_left[0] + move_x, top_left[1] + move_y),
                      (top_left[0] + template_list.get_active_size()[0] + move_x, top_left[1] + template_list.get_active_size()[1] + move_y), match_level_color_bgr(match_level), 2)
        # No need for a search area rectangle, since the image in the debug popup is already that rectangle
        # cv2.rectangle(left_stripe_img, (HoleSearchTopLeft[0] + move_x, HoleSearchTopLeft[1] + move_y), (HoleSearchBottomRight[0] + move_x, HoleSearchBottomRight[1] + move_y), (255, 255, 255), 2)
        debug_template_display_frame_stabilized(left_stripe_img)

    return translated_image


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

    if not os.path.isdir(SourceDir):
        return

    # Try first with standard scan filename template
    SourceDirFileList_jpg = list(glob(os.path.join(
        SourceDir,
        FrameInputFilenamePatternList_jpg)))
    SourceDirFileList_png = list(glob(os.path.join(
        SourceDir,
        FrameInputFilenamePatternList_png)))
    SourceDirFileList = sorted(SourceDirFileList_jpg + SourceDirFileList_png)
    if len(SourceDirFileList_png) != 0:
        file_type_out = 'png'   # If we have png files in the input, we default to png for the output
    else:
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
    else:
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
    else:
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
        clear_image()
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
    frame_slider.config(from_=0, to=len(SourceDirFileList)-1,
                        label='Global:'+str(CurrentFrame+first_absolute_frame))

    # In order to determine hole height, no not take the first frame, as often
    # it is not so good. Take a frame 10% ahead in the set
    sample_frame = CurrentFrame + int((len(SourceDirFileList) - CurrentFrame) * 0.1)
    work_image = cv2.imread(SourceDirFileList[sample_frame], cv2.IMREAD_UNCHANGED)
    # Set frame dimensions in globañl variable, for use everywhere
    frame_width = work_image.shape[1]
    frame_height = work_image.shape[0]
    # Next 3 statements were done only if batch mode was not active, but they are needed in all cases
    if BatchJobRunning:
        logging.debug("Skipping hole template adjustment in batch mode")
    else:
        logging.debug("Adjusting hole template...")
        set_hole_search_area(work_image)
        detect_film_type()
    # Select area window should be proportional to screen height
    # Deduct 120 pixels (approximately) for taskbar + window title
    area_select_image_factor = (screen_height - 200) / frame_height
    area_select_image_factor = min(1, area_select_image_factor)
    # If no cropping defined, set whole image dimensions
    if CropBottomRight == (0,0):
        CropBottomRight = (frame_width, frame_height)

    widget_status_update(NORMAL)

    return len(SourceDirFileList)


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


def set_hole_search_area(img):
    global HoleSearchTopLeft, HoleSearchBottomRight
    global TemplateTopLeft
    global extended_stabilization

    # Adjust left stripe width (search area)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_bw = cv2.threshold(img_gray, 240, 255, cv2.THRESH_BINARY)[1]
    img_target = img_bw[:, :int(img_bw.shape[1]/4)]  # Search only in the left 25% of the image
    # Detect corner in image, to adjust search area width
    film_corner_template = template_list.get_template('aux','Corner')
    result = cv2.matchTemplate(img_target, film_corner_template, cv2.TM_CCOEFF_NORMED)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(result)
    left_stripe_width = maxLoc[0] + template_list.get_active_size()[0]
    left_stripe_width += 250 * int(img.shape[0]/1520)   # Increase width, proportional to the image size (250 pixels for default size 2028x1520)
    logging.debug(f"Calculated left stripe width: {left_stripe_width}")
    if extended_stabilization.get():
        logging.debug("Extended stabilization requested: Widening search area by 50 pixels")
        left_stripe_width += 50     # If precise stabilization, make search area wider (although not clear this will help instead of making it worse)
    # limit search area with fo 25% of the image at most
    left_stripe_width = min(left_stripe_width, int(img_bw.shape[1]/4))
    # Initialize default values for perforation search area,
    # as they are relative to image size
    # Get image dimensions first
    height = img.shape[0]
    # Default values are needed before the stabilization search area
    # has been defined, therefore we initialized them here
    HoleSearchTopLeft = (0, 0)
    HoleSearchBottomRight = (left_stripe_width, height)   # Before, search area width was 20% of image width


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
    global stabilization_bounds_alert_counter
    global CsvFilename, CsvPathName, GenerateCsv, CsvFile
    global FPM_LastMinuteFrameTimes

    if ConvertLoopRunning:
        ConvertLoopExitRequested = True
        ConvertLoopRunning = False
    else:
        # Save current project status
        save_general_config()
        save_project_config()
        save_job_list()
        # Reset frames out of bounds counter
        stabilization_bounds_alert_counter = 0
        # Empty FPM register list
        FPM_LastMinuteFrameTimes.clear()
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
        if BatchJobRunning:
            start_batch_btn.config(text="Stop batch", bg='red', fg='white')
            # Disable all buttons in main window
            widget_status_update(DISABLED, start_batch_btn)
        else:
            Go_btn.config(text="Stop", bg='red', fg='white')
            # Disable all buttons in main window
            widget_status_update(DISABLED, Go_btn)
        win.update()

        if project_config["GenerateVideo"]:
            TargetVideoFilename = video_filename_name.get()
            name, ext = os.path.splitext(TargetVideoFilename)
            if TargetVideoFilename == "":   # Assign default if no filename
                TargetVideoFilename = (
                    "AfterScan-" +
                    datetime.now().strftime("%Y_%m_%d-%H-%M-%S") + ".mp4")
                video_filename_name.delete(0, 'end')
                video_filename_name.insert('end', TargetVideoFilename)
            elif ext not in ['.mp4', '.MP4', '.mkv', '.MKV']:     # ext == "" does not work if filename contains dots ('Av. Manzanares')
                TargetVideoFilename += ".mp4"
                video_filename_name.delete(0, 'end')
                video_filename_name.insert('end', TargetVideoFilename)
            elif os.path.isfile(os.path.join(VideoTargetDir, TargetVideoFilename)):
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
                CsvFilename = video_filename_name.get()
                name, ext = os.path.splitext(CsvFilename)
                if name == "":  # Assign default if no filename
                    name = "AfterScan-"
                CsvFilename = datetime.now().strftime("%Y_%m_%d-%H-%M-%S_") + name + '.csv'
                CsvPathName = aux_dir
                if CsvPathName == "":
                    CsvPathName = os.getcwd()
                CsvPathName = os.path.join(CsvPathName, CsvFilename)
                CsvFile = open(CsvPathName, "w")
            clear_image()
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
                clear_image()
                win.after(1000, video_generation_loop)


def generation_exit(success = True):
    global win
    global ConvertLoopExitRequested
    global ConvertLoopRunning
    global Go_btn, save_bg, save_fg
    global BatchJobRunning
    global job_list, CurrentJobEntry, job_list_listbox

    go_suspend = False
    stop_batch = False

    if BatchJobRunning:
        if ConvertLoopExitRequested or CurrentJobEntry == -1:
            stop_batch = True
            if (CurrentJobEntry != -1):
                idx = get_job_listbox_index(CurrentJobEntry)
                if idx != -1:
                    job_list_listbox.itemconfig(idx, fg='black')
        else:
            if success:
                job_list[CurrentJobEntry]['done'] = True    # Flag as done
                idx = get_job_listbox_index(CurrentJobEntry)
                if idx != -1:
                    job_list_listbox.itemconfig(idx, fg='green')
            else:
                idx = get_job_listbox_index(CurrentJobEntry)
                if idx != -1:
                    job_list_listbox.itemconfig(idx, fg='black')
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
    win.update()
    
    if stop_batch:
        start_batch_btn.config(text="Start batch", bg=save_bg, fg=save_fg)
        BatchJobRunning = False
    if go_suspend:
        system_suspend()
        time.sleep(2)


def frame_encode(frame_idx, id):
    global SourceDir, TargetDir
    global HdrFilesOnly , first_absolute_frame, frames_to_encode
    global FrameInputFilenamePattern, HdrSetInputFilenamePattern, FrameHdrInputFilenamePattern, FrameOutputFilenamePattern
    global CropTopLeft, CropBottomRight
    global app_status_label
    global subprocess_event_queue
    global debug_template_match
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
        if perform_stabilization.get() or debug_template_match:
            img = stabilize_image(frame_idx, img, img_ref, img_ref_aux, id)
        if perform_cropping.get():
            img = crop_image(img, CropTopLeft, CropBottomRight)
        else:
            img = even_image(img)
        if perform_denoise.get():
            img = cv2.fastNlMeansDenoisingColored(img, None, 5, 5, 21, 7)
        if perform_sharpness.get():
            # Sharpness code taken from https://www.educative.io/answers/how-to-sharpen-a-blurred-image-using-opencv
            sharpen_filter = np.array([[-1, -1, -1],
                                       [-1, 9, -1],
                                       [-1, -1, -1]])
            # applying kernels to the input image to get the sharpened image
            img = cv2.filter2D(img, -1, sharpen_filter)

        # Before we used to display every other frame, but just discovered that it makes no difference to performance
        # Instead of displaying image, we add it to a queue to be processed in main loop
        queue_item = tuple(("processed_image", frame_idx, img, len(images_to_merge) != 0))
        subprocess_event_queue.put(queue_item)

        if img.shape[1] % 2 == 1 or img.shape[0] % 2 == 1:
            logging.error("Target size, one odd dimension")
            status_str = "Status: Frame %d - odd size" % frame_idx
            app_status_label.config(text=status_str, fg='red')
            frame_idx = StartFrame + frames_to_encode - 1

        if os.path.isdir(TargetDir):
            target_file = os.path.join(TargetDir, FrameOutputFilenamePattern % (first_absolute_frame + frame_idx, file_type_out))
            cv2.imwrite(target_file, img)
    if dev_debug_enabled:
        logging.debug(f"Thread {id}, finalized to encode Frame {frame_idx}")

    return len(images_to_merge) != 0

def frame_update_ui(frame_idx, merged):
    global first_absolute_frame, StartFrame, frames_to_encode, FPM_CalculatedValue
    global app_status_label

    frame_selected.set(frame_idx)
    frame_slider.set(frame_idx)
    frame_slider.config(label='Processed:' +
                              str(frame_idx + first_absolute_frame - StartFrame))
    fps = 18 if film_type.get() == 'S8' else 16
    time_str = f"Film time: {(frame_idx//fps) // 60:02}:{(frame_idx//fps) % 60:02}"
    frame_slider_time.config(text=time_str)
    status_str = f"Status: Generating{' merged' if merged else ''} frames {((frame_idx - StartFrame+1) * 100 / frames_to_encode):.1f}%"
    if FPM_CalculatedValue != -1:  # FPM not calculated yet, display some indication
        status_str = status_str + f' (FPM:{FPM_CalculatedValue})'
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
                merged = frame_encode(message[1], id)
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
    global stabilization_bounds_alert_checkbox, stabilization_bounds_alert_counter
    global CsvFramesOffPercent
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
                    display_image(img)
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
    global GenerateCsv, CsvFile
    global frame_slider
    global MergeMertens
    global FPM_CalculatedValue
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
            display_image(message[2])

    if CurrentFrame >= StartFrame + frames_to_encode and last_displayed_image+1 >= StartFrame + frames_to_encode:
        FPM_CalculatedValue = -1
        status_str = "Status: Frame generation OK"
        app_status_label.config(text=status_str, fg='green')
        # Clear display queue
        #subprocess_event_queue.queue.clear()
        last_displayed_image = 0
        win.update()
        # Refresh Target dir file list
        TargetDirFileList = sorted(list(glob(os.path.join(
            TargetDir, FrameCheckOutputFilenamePattern % file_type_out))))
        if GenerateCsv:
            CsvFile.close()
            name, ext = os.path.splitext(CsvPathName)
            name = name + ' (%d frames, %.1f%% KO)' % (frames_to_encode, CsvFramesOffPercent) + '.csv'
            os.rename(CsvPathName, name)
        # Stop threads
        terminate_threads(False)
        # Generate video if requested or terminate
        if generate_video.get():
            ffmpeg_success = False
            ffmpeg_encoding_status = ffmpeg_state.Pending
            win.after(1000, video_generation_loop)
        else:
            generation_exit()
        CurrentFrame -= 1  # Prevent being out of range
        stabilization_threshold_match_label.config(fg='lightgray', bg='lightgray', text='')
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
            CsvFile.close()
            os.unlink(CsvPathName)  # Processing was stopped half-way, delete csv file as results are not representative
        # Stop workers
        terminate_threads(True)
        logging.debug(f"frames_to_encode_queue.qsize = {frame_encoding_queue.qsize()}")
        logging.debug(f"subprocess_event_queue.qsize = {subprocess_event_queue.qsize()}")
        logging.debug("Exiting threads terminate")
        status_str = "Status: Cancelled by user"
        app_status_label.config(text=status_str, fg='red')
        generation_exit(success = False)
        stabilization_threshold_match_label.config(fg='lightgray', bg='lightgray', text='')
        FPM_CalculatedValue = -1
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
    global video_title_name, TargetVideoTitle
    global VideoFps
    global StartFrame, first_absolute_frame, title_num_frames, frames_to_encode
    global file_type_out

    if len(video_title_name.get()):   # if title defined --> kiki
        TargetVideoTitle = video_title_name.get()
        title_duration = round(len(video_title_name.get())*50/1000) # 50 ms per char
        title_duration = min(title_duration, 10)    # no more than 10 sec
        title_duration = max(title_duration, 3)    # no less than 3 sec
        title_num_frames = min(title_duration * VideoFps, frames_to_encode-1)
        # Custom font style and font size
        img = Image.open(os.path.join(TargetDir, FrameOutputFilenamePattern % (StartFrame + first_absolute_frame, file_type_out)))
        myFont, num_lines = get_adjusted_font(img, TargetVideoTitle)
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
            #I1.multiline_text((28, 36), TargetVideoTitle, font=myFont, fill=(255, 0, 0))
            draw_multiple_line_text(img, TargetVideoTitle, myFont, (255,255,255), num_lines)
            # Display edited image
            #img.show()

            # Save the edited image
            img.save(os.path.join(TargetDir, TitleOutputFilenamePattern % (title_frame_idx, file_type_out)))
            title_frame_idx += 1
            win.update()
    else:
        title_duration = 0
        title_num_frames = 0



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
    # Create filter_complex or one or two inputs
    filter_complex_options=''
    # Title sequence
    if title_num_frames > 0:   # There is a title
        filter_complex_options+='[0:v]'
        if (out_frame_width != 0 and out_frame_height != 0):
            filter_complex_options+='scale=w='+video_width+':h='+video_height+':'
        filter_complex_options+='force_original_aspect_ratio=decrease,pad='+video_width+':'+video_height+':(ow-iw)/2:(oh-ih)/2,setsar=1[v0];'
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
    filter_complex_options+='force_original_aspect_ratio=decrease,pad='+video_width+':'+video_height+':(ow-iw)/2:(oh-ih)/2,setsar=1[v2];'
    # Concatenate title (if exists) + main video
    if title_num_frames > 0:   # There is a title
        filter_complex_options += '[v0]'
    filter_complex_options+='[v2]concat=n='+str(2 if title_num_frames>0 else 1)+':v=1[v]'
    cmd_ffmpeg.extend(['-filter_complex', filter_complex_options])

    cmd_ffmpeg.extend(
        ['-an',  # no audio
         '-vcodec', 'libx264',
         '-preset', ffmpeg_preset.get(),
         '-crf', '18',
         '-pix_fmt', 'yuv420p',
         '-map', '[v]',
         os.path.join(VideoTargetDir,
                      TargetVideoFilename)])

    logging.debug("Generated ffmpeg command: %s", cmd_ffmpeg)
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
                         os.path.join(VideoTargetDir, TargetVideoFilename))
            status_str = "Status: Cancelled by user"
            app_status_label.config(text=status_str, fg='red')
            tk.messagebox.showinfo(
                "FFMPEG encoding interrupted by user",
                "\r\nVideo generation by FFMPEG has been stopped by user "
                "action.")
            generation_exit(success = False)  # Restore all settings to normal
            os.remove(os.path.join(VideoTargetDir, TargetVideoFilename))
        else:
            line = ffmpeg_process.stdout.readline().strip()
            logging.debug(line)
            if line:
                frame_str = str(line)[:-1].replace('=', ' ').split()[1]
                if is_a_number(frame_str):  # Sometimes ffmpeg output might be corrupted on the way
                    encoded_frame = int(frame_str)
                    frame_selected.set(StartFrame + first_absolute_frame + encoded_frame)
                    frame_slider.set(StartFrame + first_absolute_frame + encoded_frame)
                    frame_slider.config(label='Processed:' +
                                              str(encoded_frame))
                    fps = 18 if film_type.get() == 'S8' else 16
                    time_str = f"Film time: {(encoded_frame // fps) // 60:02}:{(encoded_frame // fps) % 60:02}"
                    frame_slider_time.config(text=time_str)
                    status_str = "Status: Generating video %.1f%%" % (encoded_frame*100/(frames_to_encode+title_num_frames))
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
            logging.debug("Video generated OK: %s", os.path.join(VideoTargetDir, TargetVideoFilename))
            status_str = "Status: Video generated OK"
            app_status_label.config(text=status_str, fg='green')
            if not BatchJobRunning:
                tk.messagebox.showinfo(
                    "Video generation by ffmpeg has ended",
                    "\r\nVideo encoding has finalized successfully. "
                    "You can find your video in the target folder, "
                    "as stated below\r\n" +
                    os.path.join(VideoTargetDir, TargetVideoFilename))
        else:
            logging.error("Video generation failed for %s", os.path.join(VideoTargetDir, TargetVideoFilename))
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

    file = SourceDirFileList[CurrentFrame]

    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)

    # Calculate preview image display ratio
    image_height = img.shape[0]
    image_width = img.shape[1]
    if abs(PreviewWidth - image_width) > abs(PreviewHeight - image_height):
        PreviewRatio = PreviewWidth/image_width
    else:
        PreviewRatio = PreviewHeight/image_height

    win.after(5, scale_display_update)


def afterscan_init():
    global win
    global TopWinX
    global TopWinY
    global WinInitDone
    global SourceDir
    global LogLevel
    global PreviewWidth, PreviewHeight
    global screen_height
    global BigSize, FontSize
    global MergeMertens, AlignMtb

    # Initialize logging
    log_path = aux_dir
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

    win = Tk()  # Create main window, store it in 'win'

    # Get screen size - maxsize gives the usable screen size
    screen_width, screen_height = win.maxsize()
    # Set dimensions of UI elements adapted to screen size
    if (screen_height >= 1000 and not ForceSmallSize) or ForceBigSize:
        BigSize = True
        FontSize = 11
        PreviewWidth = 700
        PreviewHeight = 540
        app_width = PreviewWidth + 420
        app_height = PreviewHeight + 330
    else:
        BigSize = False
        FontSize = 8
        PreviewWidth = 500
        PreviewHeight = 380
        app_width = PreviewWidth + 380
        app_height = PreviewHeight + 330

    win.title('AfterScan ' + __version__)  # setting title of the window
    win.geometry('1080x700')  # setting the size of the window
    win.geometry('+50+50')  # setting the position of the window
    # Prevent window resize
    win.minsize(app_width, app_height)
    win.maxsize(app_width, app_height)

    win.update_idletasks()

    # Set default font size
    # Change the default Font that will affect in all the widgets
    win.option_add("*font", "TkDefaultFont 10")
    win.resizable(False, False)

    # Init ToolTips
    init_tooltips(FontSize)

    # Get Top window coordinates
    TopWinX = win.winfo_x()
    TopWinY = win.winfo_y()

    # Create MergeMertens Object for HDR
    MergeMertens = cv2.createMergeMertens()
    # Create Align MTB object for HDR
    AlignMtb = cv2.createAlignMTB()

    WinInitDone = True

    logging.debug("AfterScan initialized")


def build_ui():
    global win
    global SourceDir
    global frames_source_dir, frames_target_dir, video_target_dir
    global perform_cropping, cropping_btn
    global perform_denoise, perform_denoise_checkbox
    global perform_sharpness, perform_sharpness_checkbox
    global generate_video, generate_video_checkbox
    global encode_all_frames, encode_all_frames_checkbox
    global frames_to_encode_str, frames_to_encode, frames_to_encode_label
    global save_bg, save_fg
    global source_folder_btn, target_folder_btn
    global perform_stabilization, perform_stabilization_checkbox
    global stabilization_threshold_spinbox, stabilization_threshold_str
    global StabilizationThreshold
    global stabilization_threshold_match_label
    global perform_rotation, perform_rotation_checkbox, rotation_angle_label
    global rotation_angle_spinbox, rotation_angle_str
    global custom_stabilization_btn, stabilization_threshold_label
    global perform_cropping_checkbox, Crop_btn
    global force_4_3_crop_checkbox, force_4_3_crop
    global force_16_9_crop_checkbox, force_16_9_crop
    global Go_btn
    global Exit_btn
    global video_fps_dropdown_selected, skip_frame_regeneration_cb
    global video_fps_dropdown, video_fps_label, video_filename_name, video_title_name
    global resolution_dropdown, resolution_label, resolution_dropdown_selected
    global video_target_dir, video_target_folder_btn, video_filename_label, video_title_label
    global ffmpeg_preset
    global ffmpeg_preset_rb1, ffmpeg_preset_rb2, ffmpeg_preset_rb3
    global FfmpegBinName
    global skip_frame_regeneration
    global frame_slider, frame_slider_time, CurrentFrame, frame_selected
    global film_type
    global job_list_listbox
    global app_status_label
    global PreviewWidth, PreviewHeight
    global left_area_frame
    global draw_capture_canvas
    global custom_ffmpeg_path
    global project_config
    global start_batch_btn, add_job_btn, delete_job_btn, rerun_job_btn
    global stabilization_bounds_alert_checkbox, stabilization_bounds_alert
    global film_type_S8_rb, film_type_R8_rb
    global frame_from_str, frame_to_str, frame_from_entry, frame_to_entry, frames_separator_label
    global suspend_on_joblist_end
    global frame_fill_type
    global extended_stabilization, extended_stabilization_checkbox
    global RotationAngle
    global suspend_on_completion
    global perform_fill_none_rb, perform_fill_fake_rb, perform_fill_dumb_rb
    global ExpertMode
    global display_template_popup
    global BigSize, FontSize
    global template_list

    # Create a frame to add a border to the preview
    left_area_frame = Frame(win)
    #left_area_frame.grid(row=0, column=0, padx=5, pady=5, sticky=N)
    left_area_frame.pack(side=LEFT, padx=5, pady=5, anchor=N)
    # Create a LabelFrame to act as a border
    border_frame = tk.LabelFrame(left_area_frame, bd=2, relief=tk.GROOVE)
    border_frame.pack(expand=True, fill="both", padx=5, pady=5)
    # Create the canvas
    draw_capture_canvas = Canvas(border_frame, bg='dark grey',
                                 width=PreviewWidth, height=PreviewHeight)
    draw_capture_canvas.pack(side=TOP, anchor=N)

    # Frame for standard widgets
    right_area_frame = Frame(win, width=320, height=450)
    #right_area_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky=N)
    right_area_frame.pack(side=LEFT, padx=5, pady=5, anchor=N)

    # Frame for top section of standard widgets ******************************
    regular_top_section_frame = Frame(right_area_frame, width=50, height=50)
    regular_top_section_frame.pack(side=TOP, padx=2, pady=2)

    # Create frame to display current frame and slider
    frame_frame = LabelFrame(regular_top_section_frame, text='Current frame',
                               width=35, height=10, font=("Arial", FontSize-2))
    frame_frame.grid(row=0, column=0, sticky=W)

    frame_slider_time = Label(frame_frame, width=12, text='Film time:', font=("Arial", FontSize-2))
    frame_slider_time.pack(side=BOTTOM)

    frame_selected = IntVar()
    frame_slider = Scale(frame_frame, orient=HORIZONTAL, from_=0, to=0,
                         variable=frame_selected, command=select_scale_frame,
                         length=120, label='Global:',
                         highlightthickness=1, takefocus=1, font=("Arial", FontSize))
    frame_slider.pack(side=BOTTOM, ipady=4)
    frame_slider.set(CurrentFrame)

    setup_tooltip(frame_slider, "Use the slider to browse around the frames to be processed.")

    # Application status label
    app_status_label = Label(regular_top_section_frame, width=46 if BigSize else 55, borderwidth=2,
                             relief="groove", text='Status: Idle',
                             highlightthickness=1, font=("Arial", FontSize))
    app_status_label.grid(row=1, column=0, columnspan=3, pady=5)

    # Application Exit button
    Exit_btn = Button(regular_top_section_frame, text="Exit", width=10,
                      height=5, command=exit_app, activebackground='red',
                      activeforeground='white', wraplength=80, font=("Arial", FontSize))
    Exit_btn.grid(row=0, column=1, sticky=W, padx=5)

    setup_tooltip(Exit_btn, "Click here to exit AfterScan.")

    # Application start button
    Go_btn = Button(regular_top_section_frame, text="Start", width=12, height=5,
                    command=start_convert, activebackground='green',
                    activeforeground='white', wraplength=80, font=("Arial", FontSize))
    Go_btn.grid(row=0, column=2, sticky=W)

    setup_tooltip(Go_btn, "Click here to start post-processing with the current parameters")

    # Create frame to select source and target folders *******************************
    folder_frame = LabelFrame(right_area_frame, text='Folder selection', width=50,
                              height=8, font=("Arial", FontSize-2))
    folder_frame.pack(side=TOP, padx=2, pady=2, ipadx=5)

    source_folder_frame = Frame(folder_frame)
    source_folder_frame.pack(side=TOP)
    frames_source_dir = Entry(source_folder_frame, width=36 if BigSize else 42,
                                    borderwidth=1, font=("Arial", FontSize))
    frames_source_dir.pack(side=LEFT)
    frames_source_dir.delete(0, 'end')
    frames_source_dir.insert('end', SourceDir)
    frames_source_dir.after(100, frames_source_dir.xview_moveto, 1)
    frames_source_dir.bind('<<Paste>>', lambda event, entry=frames_source_dir: on_paste_all_entries(event, entry))

    setup_tooltip(frames_source_dir, "Enter the directory where the source frames are located.")

    source_folder_btn = Button(source_folder_frame, text='Source', width=6,
                               height=1, command=set_source_folder,
                               activebackground='green',
                               activeforeground='white', wraplength=80, font=("Arial", FontSize))
    source_folder_btn.pack(side=LEFT)

    setup_tooltip(source_folder_btn, "Click here to select the directory where the source frames are located.")

    target_folder_frame = Frame(folder_frame)
    target_folder_frame.pack(side=TOP)
    frames_target_dir = Entry(target_folder_frame, width=36 if BigSize else 42,
                                    borderwidth=1, font=("Arial", FontSize))
    frames_target_dir.pack(side=LEFT)
    frames_target_dir.bind('<<Paste>>', lambda event, entry=frames_target_dir: on_paste_all_entries(event, entry))
    
    setup_tooltip(frames_target_dir, "Enter the directory where the generated frames will be stored.")

    target_folder_btn = Button(target_folder_frame, text='Target', width=6,
                               height=1, command=set_frames_target_folder,
                               activebackground='green',
                               activeforeground='white', wraplength=80, font=("Arial", FontSize))
    target_folder_btn.pack(side=LEFT)

    setup_tooltip(target_folder_btn, "Click here to select the directory where the generated frames will be stored.")

    save_bg = source_folder_btn['bg']
    save_fg = source_folder_btn['fg']

    folder_bottom_frame = Frame(folder_frame)
    folder_bottom_frame.pack(side=BOTTOM, ipady=2)

    # Define post-processing area *********************************************
    postprocessing_frame = LabelFrame(right_area_frame,
                                      text='Frame post-processing',
                                      width=40, height=8, font=("Arial", FontSize-2))
    postprocessing_frame.pack(side=TOP, padx=2, pady=2, ipadx=5)
    postprocessing_row = 0

    # Radio buttons to select R8/S8. Required to select adequate pattern, and match position
    film_type = StringVar()
    film_type_S8_rb = Radiobutton(postprocessing_frame, text="Super 8", variable=film_type, command=set_film_type,
                                  width=11 if BigSize else 14, value='S8', font=("Arial", FontSize))
    film_type_S8_rb.grid(row=postprocessing_row, column=0, sticky=W)
    setup_tooltip(film_type_S8_rb, "Select for Super 8 film.")
    film_type_R8_rb = Radiobutton(postprocessing_frame, text="Regular 8", variable=film_type, command=set_film_type,
                                  width=11 if BigSize else 14, value='R8', font=("Arial", FontSize))
    film_type_R8_rb.grid(row=postprocessing_row, column=1, sticky=W)
    setup_tooltip(film_type_R8_rb, "Select for 8mm (Regular 8) film.")
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
    setup_tooltip(encode_all_frames_checkbox, "If selected, all frames in source folder will be encoded")
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
    frame_from_entry.bind('<<Paste>>', lambda event, entry=frame_from_entry: on_paste_all_entries(event, entry))
    setup_tooltip(frame_from_entry, "Enter first frame to be processed, if not encoding the entire set.")
    frame_to_str = tk.StringVar(value=str(from_frame))
    frames_separator_label = tk.Label(postprocessing_frame, text='to', width=2, font=("Arial", FontSize))
    frames_separator_label.grid(row=postprocessing_row, column=1)
    frame_to_entry = Entry(postprocessing_frame, textvariable=frame_to_str, width=5, borderwidth=1, font=("Arial", FontSize))
    frame_to_entry.grid(row=postprocessing_row, column=1, sticky=E)
    frame_to_entry.config(state=NORMAL)
    frame_to_entry.bind("<Double - Button - 1>", update_frame_to)
    frame_to_entry.bind('<<Paste>>', lambda event, entry=frame_to_entry: on_paste_all_entries(event, entry))
    setup_tooltip(frame_to_entry, "Enter last frame to be processed, if not encoding the entire set.")

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
    setup_tooltip(perform_rotation_checkbox, "Check if frames need to be rotated.")

    # Spinbox to select rotation angle
    rotation_angle_str = tk.StringVar(value=str(0))
    rotation_angle_selection_aux = postprocessing_frame.register(
        rotation_angle_selection)
    rotation_angle_spinbox = tk.Spinbox(
        postprocessing_frame,
        command=(rotation_angle_selection_aux, '%d'), width=5,
        textvariable=rotation_angle_str, from_=-5, to=5,
        format="%.1f", increment=0.1, font=("Arial", FontSize))
    rotation_angle_spinbox.grid(row=postprocessing_row, column=1, sticky=W)
    rotation_angle_spinbox.bind("<FocusOut>", rotation_angle_spinbox_focus_out)
    setup_tooltip(rotation_angle_spinbox, "Enter the frame rotation angle.")
    rotation_angle_selection('down')
    rotation_angle_label = tk.Label(postprocessing_frame,
                                      text='°',
                                      width=1, font=("Arial", FontSize))
    rotation_angle_label.grid(row=postprocessing_row, column=1)
    rotation_angle_label.config(state=NORMAL)
    postprocessing_row += 1

    # Check box to do stabilization or not
    perform_stabilization = tk.BooleanVar(value=False)
    perform_stabilization_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Stabilize',
        variable=perform_stabilization, onvalue=True, offvalue=False, width=7,
        command=perform_stabilization_selection, font=("Arial", FontSize))
    perform_stabilization_checkbox.grid(row=postprocessing_row, column=0,
                                        columnspan=1, sticky=W)
    setup_tooltip(perform_stabilization_checkbox, "Check to stabilize frames. Sprocket hole is used as common reference, it needs to be clearly visible.")
    # Label to display the match level of current frame to template
    stabilization_threshold_match_label = Label(postprocessing_frame, width=4, borderwidth=1, relief='sunken', font=("Arial", FontSize))
    stabilization_threshold_match_label.grid(row=postprocessing_row, column=1, sticky=W)
    setup_tooltip(stabilization_threshold_match_label, "This value shows the dynamic quality of sprocket hole template matching. Green is good, orange acceptable, red is bad.")

    # Extended search checkbox (replace radio buttons for fast/precise stabilization)
    extended_stabilization = tk.BooleanVar(value=False)
    extended_stabilization_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Extended search',
        variable=extended_stabilization, onvalue=True, offvalue=False, width=20,
        command=extended_stabilization_selection, font=("Arial", FontSize))
    #extended_stabilization_checkbox.grid(row=postprocessing_row, column=1, columnspan=2)
    extended_stabilization_checkbox.forget()
    setup_tooltip(extended_stabilization_checkbox, "Check to xtend the area where AfterScan looks for sprocket holes. In some rare cases this might help.")

    # Custom film perforation template
    custom_stabilization_btn = Button(postprocessing_frame,
                                      text='Custom hole template',
                                      width=16, height=1,
                                      command=select_custom_template,
                                      activebackground='green',
                                      activeforeground='white', font=("Arial", FontSize))
    custom_stabilization_btn.config(relief=SUNKEN if template_list.get_active_type() == 'Custom' else RAISED)
    custom_stabilization_btn.grid(row=postprocessing_row, column=1, columnspan=2, padx=5, pady=5, sticky=E)
    setup_tooltip(custom_stabilization_btn,
                  "If you prefer to use a customized template for your project, instead of the automatic one selected by AfterScan, lick on this button to define it.")

    postprocessing_row += 1

    # Check box to do cropping or not
    perform_cropping = tk.BooleanVar(value=False)
    perform_cropping_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Crop', variable=perform_cropping,
        onvalue=True, offvalue=False, command=perform_cropping_selection,
        width=4, font=("Arial", FontSize))
    perform_cropping_checkbox.grid(row=postprocessing_row, column=0, sticky=W)
    setup_tooltip(perform_cropping_checkbox, "Check to crop frames to the defined limits ('Define crop area' button).")
    force_4_3_crop = tk.BooleanVar(value=False)
    force_4_3_crop_checkbox = tk.Checkbutton(
        postprocessing_frame, text='4:3', variable=force_4_3_crop,
        onvalue=True, offvalue=False, command=force_4_3_selection,
        width=4, font=("Arial", FontSize))
    force_4_3_crop_checkbox.grid(row=postprocessing_row, column=0, sticky=E)
    setup_tooltip(force_4_3_crop_checkbox, "Check to enforce 4:3 aspect ratio when defining the cropping rectangle.")
    force_16_9_crop = tk.BooleanVar(value=False)
    force_16_9_crop_checkbox = tk.Checkbutton(
        postprocessing_frame, text='16:9', variable=force_16_9_crop,
        onvalue=True, offvalue=False, command=force_16_9_selection,
        width=4, font=("Arial", FontSize))
    force_16_9_crop_checkbox.grid(row=postprocessing_row, column=1, sticky=W)
    setup_tooltip(force_16_9_crop_checkbox, "Check to enforce 16:9 aspect ratio when defining the cropping rectangle.")
    cropping_btn = Button(postprocessing_frame, text='Define crop area',
                          width=12, height=1, command=select_cropping_area,
                          activebackground='green', activeforeground='white',
                          wraplength=120, font=("Arial", FontSize))
    cropping_btn.grid(row=postprocessing_row, column=2, sticky=E)
    setup_tooltip(cropping_btn, "Click in order to open a popup window to define the cropping rectange.")

    postprocessing_row += 1

    # Check box to perform sharpness
    perform_sharpness = tk.BooleanVar(value=False)
    perform_sharpness_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Sharpen', variable=perform_sharpness,
        onvalue=True, offvalue=False, command=perform_sharpness_selection,
        width=7, font=("Arial", FontSize))
    perform_sharpness_checkbox.grid(row=postprocessing_row, column=0, sticky=W)
    setup_tooltip(perform_sharpness_checkbox, "Check to apply sharpen algorithm (using 'filter2D' in OpenCV) to the generated frames")

    # Check box to perform denoise
    perform_denoise = tk.BooleanVar(value=False)
    perform_denoise_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Denoise', variable=perform_denoise,
        onvalue=True, offvalue=False, command=perform_denoise_selection,
        width=7, font=("Arial", FontSize))
    perform_denoise_checkbox.grid(row=postprocessing_row, column=1, sticky=W)
    setup_tooltip(perform_denoise_checkbox, "Check to apply denoise algorithm (using 'fastNlMeansDenoisingColored(' in OpenCV) to the generated frames")
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
    setup_tooltip(perform_fill_none_rb, "Badly aligned frames will be left with the missing part of the image black after stabilization.")
    perform_fill_fake_rb = Radiobutton(postprocessing_frame, text='Fake fill',
                                    variable=frame_fill_type, value='fake', font=("Arial", FontSize))
    perform_fill_fake_rb.grid(row=postprocessing_row, column=1, sticky=W)
    setup_tooltip(perform_fill_fake_rb, "Badly aligned frames will have the missing part of the image completed with a fragment of the next/previous frame after stabilization.")
    perform_fill_dumb_rb = Radiobutton(postprocessing_frame, text='Dumb fill',
                                    variable=frame_fill_type, value='dumb', font=("Arial", FontSize))
    perform_fill_dumb_rb.grid(row=postprocessing_row, column=2, sticky=W)
    setup_tooltip(perform_fill_dumb_rb, "Badly aligned frames will have the missing part of the image filled with the adjacent pixel row after stabilization.")
    frame_fill_type.set('fake')

    postprocessing_row += 1

    # Checkbox - Beep if stabilization forces image out of cropping bounds
    stabilization_bounds_alert = tk.BooleanVar(value=False)
    stabilization_bounds_alert_checkbox = tk.Checkbutton(postprocessing_frame,
                                                         text='Alert when image out of bounds',
                                                         variable=stabilization_bounds_alert,
                                                         onvalue=True, offvalue=False,
                                                         width=40, font=("Arial", FontSize))
    stabilization_bounds_alert_checkbox.grid(row=postprocessing_row, column=0, columnspan=3, sticky=W)
    setup_tooltip(stabilization_bounds_alert_checkbox, "Check to sound an alert each time a badly aligned frame (requiring fill-in) is detected.")

    postprocessing_row += 1

    # Define video generating area ************************************
    video_frame = LabelFrame(right_area_frame,
                             text='Video generation',
                             width=50, height=8, font=("Arial", FontSize-2))
    video_frame.pack(side=TOP, padx=2, pady=2, ipadx=5)
    video_row = 0

    # Check box to generate video or not
    generate_video = tk.BooleanVar(value=False)
    generate_video_checkbox = tk.Checkbutton(video_frame,
                                             text='Video',
                                             variable=generate_video,
                                             onvalue=True, offvalue=False,
                                             command=generate_video_selection,
                                             width=5, font=("Arial", FontSize))
    generate_video_checkbox.grid(row=video_row, column=0, sticky=W)
    generate_video_checkbox.config(state=NORMAL if ffmpeg_installed
                                   else DISABLED)
    setup_tooltip(generate_video_checkbox, "Check to generate an MP4 video, after all frames have been processed.")

    # Check box to skip frame regeneration
    skip_frame_regeneration = tk.BooleanVar(value=False)
    skip_frame_regeneration_cb = tk.Checkbutton(
        video_frame, text='Skip Frame regeneration',
        variable=skip_frame_regeneration, onvalue=True, offvalue=False,
        width=20, font=("Arial", FontSize))
    skip_frame_regeneration_cb.grid(row=video_row, column=1,
                                    columnspan=2, sticky=W)
    skip_frame_regeneration_cb.config(state=NORMAL if ffmpeg_installed
                                      else DISABLED)
    setup_tooltip(skip_frame_regeneration_cb, "If frames have ben already generated in a previous run, and you want to only generate the vieo, check this one.")

    video_row += 1

    # Video target folder
    video_target_dir = Entry(video_frame, width=36, borderwidth=1, font=("Arial", FontSize))
    video_target_dir.grid(row=video_row, column=0, columnspan=2,
                             sticky=W)
    video_target_dir.delete(0, 'end')
    video_target_dir.insert('end', '')
    video_target_dir.bind('<<Paste>>', lambda event, entry=video_target_dir: on_paste_all_entries(event, entry))
    setup_tooltip(video_target_dir, "Enter the directory where the generated video will be stored.")

    video_target_folder_btn = Button(video_frame, text='Target', width=6,
                               height=1, command=set_video_target_folder,
                               activebackground='green',
                               activeforeground='white', wraplength=80, font=("Arial", FontSize))
    video_target_folder_btn.grid(row=video_row, column=2, columnspan=2, sticky=W)
    setup_tooltip(video_target_folder_btn, "Click to select the directory where the generated video will be stored.")
    video_row += 1

    # Video filename
    video_filename_label = Label(video_frame, text='Video filename:', font=("Arial", FontSize))
    video_filename_label.grid(row=video_row, column=0, sticky=W)
    video_filename_name = Entry(video_frame, width=26 if BigSize else 33, borderwidth=1, font=("Arial", FontSize))
    video_filename_name.grid(row=video_row, column=1, columnspan=2,
                             sticky=W)
    video_filename_name.delete(0, 'end')
    video_filename_name.insert('end', TargetVideoFilename)
    video_filename_name.bind('<<Paste>>', lambda event, entry=video_filename_name: on_paste_all_entries(event, entry))
    setup_tooltip(video_filename_name, "Enter the filename of the video to be created.")

    video_row += 1

    # Video title (add title at the start of the video)
    video_title_label = Label(video_frame, text='Video title:', font=("Arial", FontSize))
    video_title_label.grid(row=video_row, column=0, sticky=W)
    video_title_name = Entry(video_frame, width=26 if BigSize else 33, borderwidth=1, font=("Arial", FontSize))
    video_title_name.grid(row=video_row, column=1, columnspan=2,
                             sticky=W)
    video_title_name.delete(0, 'end')
    video_title_name.insert('end', TargetVideoTitle)
    video_title_name.bind('<<Paste>>', lambda event, entry=video_title_name: on_paste_all_entries(event, entry))
    setup_tooltip(video_title_name, "Video title. If entered, a simple title sequence will be generated at the start of the video, using a sequence randomly selected from the same video, running at half speed.")

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
    video_fps_label.pack(side=LEFT, anchor=W)
    video_fps_label.config(state=DISABLED)
    video_fps_dropdown = OptionMenu(video_fps_frame,
                                    video_fps_dropdown_selected, *fps_list,
                                    command=set_fps)
    video_fps_dropdown.config(takefocus=1, font=("Arial", FontSize))
    video_fps_dropdown.pack(side=LEFT, anchor=E)
    video_fps_dropdown.config(state=DISABLED)
    setup_tooltip(video_fps_dropdown, "Select the number of frames per second (FPS) of the video to be generated. Usually Super8 goes at 18 FPS, and Regular 8 at 16 FPS, although some cameras allowed to use other speeds (faster for smoother movement, slower for extended play time)")

    # Create FFmpeg preset options
    ffmpeg_preset_frame = Frame(video_frame)
    ffmpeg_preset_frame.grid(row=video_row, column=1, columnspan=2,
                             sticky=W)
    ffmpeg_preset = StringVar()
    ffmpeg_preset_rb1 = Radiobutton(ffmpeg_preset_frame,
                                    text="Best quality (slow)",
                                    variable=ffmpeg_preset, value='veryslow', font=("Arial", FontSize))
    ffmpeg_preset_rb1.pack(side=TOP, anchor=W)
    ffmpeg_preset_rb1.config(state=DISABLED)
    setup_tooltip(ffmpeg_preset_rb1, "Best quality, but very slow encoding. Maps to the same ffmpeg option.")

    ffmpeg_preset_rb2 = Radiobutton(ffmpeg_preset_frame, text="Medium",
                                    variable=ffmpeg_preset, value='medium', font=("Arial", FontSize))
    ffmpeg_preset_rb2.pack(side=TOP, anchor=W)
    ffmpeg_preset_rb2.config(state=DISABLED)
    setup_tooltip(ffmpeg_preset_rb2, "Compromise between quality and encoding speed. Maps to the same ffmpeg option.")
    ffmpeg_preset_rb3 = Radiobutton(ffmpeg_preset_frame,
                                    text="Fast (low quality)",
                                    variable=ffmpeg_preset, value='veryfast', font=("Arial", FontSize))
    ffmpeg_preset_rb3.pack(side=TOP, anchor=W)
    ffmpeg_preset_rb3.config(state=DISABLED)
    setup_tooltip(ffmpeg_preset_rb3, "Faster encoding speed, lower quality (but not so much IMHO). Maps to the same ffmpeg option.")
    ffmpeg_preset.set('medium')
    video_row += 1

    # Drop down to select resolution
    # datatype of menu text
    resolution_dropdown_selected = StringVar()

    # initial menu text
    resolution_dropdown_selected.set("Unchanged")

    # Create resolution Dropdown menu
    resolution_frame = Frame(video_frame)
    resolution_frame.grid(row=video_row, column=0, columnspan= 2, sticky=W)
    resolution_label = Label(resolution_frame, text='Resolution:', font=("Arial", FontSize))
    resolution_label.pack(side=LEFT, anchor=W)
    resolution_label.config(state=DISABLED)
    resolution_dropdown = OptionMenu(resolution_frame,
                                    resolution_dropdown_selected, *resolution_dict.keys(),
                                    command=set_resolution)
    resolution_dropdown.config(takefocus=1, font=("Arial", FontSize))
    resolution_dropdown.pack(side=LEFT, anchor=E)
    resolution_dropdown.config(state=DISABLED)
    setup_tooltip(resolution_dropdown, "Select the resolution to be used when generating the video.")

    video_row += 1

    # Custom ffmpeg path
    custom_ffmpeg_path_label = Label(video_frame, text='Custom FFMpeg path:', font=("Arial", FontSize))
    custom_ffmpeg_path_label.grid(row=video_row, column=0, sticky=W)
    custom_ffmpeg_path = Entry(video_frame, width=26 if BigSize else 33, borderwidth=1, font=("Arial", FontSize))
    custom_ffmpeg_path.grid(row=video_row, column=1, columnspan=2, sticky=W)
    custom_ffmpeg_path.delete(0, 'end')
    custom_ffmpeg_path.insert('end', FfmpegBinName)
    custom_ffmpeg_path.bind("<FocusOut>", custom_ffmpeg_path_focus_out)
    custom_ffmpeg_path.bind('<<Paste>>', lambda event, entry=custom_ffmpeg_path: on_paste_all_entries(event, entry))
    setup_tooltip(custom_ffmpeg_path, "Enter the path where the ffmpeg executable is installed in your system.")

    video_row += 1

    # Extra (expert) area ***************************************************
    if ExpertMode:
        extra_frame = LabelFrame(right_area_frame,
                                 text='Extra options',
                                 width=50, height=8, font=("Arial", FontSize-2))
        extra_frame.pack(side=TOP, padx=5, pady=5, ipadx=5, ipady=5)
        extra_row = 0

        # Spinbox to select stabilization threshold - Ignored, to be removed in the future
        stabilization_threshold_label = tk.Label(extra_frame,
                                                 text='Threshold:',
                                                 width=11, font=("Arial", FontSize))
        #stabilization_threshold_label.grid(row=extra_row, column=1, columnspan=1, sticky=E)
        stabilization_threshold_label.forget()
        stabilization_threshold_str = tk.StringVar(value=str(StabilizationThreshold))
        stabilization_threshold_selection_aux = extra_frame.register(
            stabilization_threshold_selection)
        stabilization_threshold_spinbox = tk.Spinbox(
            extra_frame,
            command=(stabilization_threshold_selection_aux, '%d'), width=6,
            textvariable=stabilization_threshold_str, from_=0, to=255, font=("Arial", FontSize))
        #stabilization_threshold_spinbox.grid(row=extra_row, column=2, sticky=W)
        stabilization_threshold_spinbox.forget()
        stabilization_threshold_spinbox.bind("<FocusOut>", stabilization_threshold_spinbox_focus_out)
        setup_tooltip(stabilization_threshold_spinbox, "Threshold value to isolate the sprocket hole from the rest of the image while definint the custom template.")

        extra_row += 1

        # Check box to display postprod info, only if developer enabled
        if True or developer_debug:
            display_template_popup = tk.BooleanVar(value=False)
            display_template_popup_checkbox = tk.Checkbutton(extra_frame,
                                                     text='Display template troubleshooting info',
                                                     variable=display_template_popup,
                                                     onvalue=True, offvalue=False,
                                                     command=debug_template_popup,
                                                     width=33 if BigSize else 41, font=("Arial", FontSize))
            display_template_popup_checkbox.grid(row=extra_row, column=0, columnspan=2, sticky=W)
            setup_tooltip(display_template_popup_checkbox, "Display popup window with dynamic debug information.Useful for developers only")


    # Define job list area ***************************************************
    job_list_frame = LabelFrame(left_area_frame,
                             text='Job List',
                             width=67, height=8, font=("Arial", FontSize-2))
    job_list_frame.pack(side=TOP, padx=2, pady=2, anchor=W)

    # job listbox
    job_list_listbox = Listbox(job_list_frame, width=65 if BigSize else 60, height=13 if BigSize else 19, font=("Arial", FontSize))
    job_list_listbox.grid(column=0, row=0, padx=5, pady=2, ipadx=5)
    job_list_listbox.bind("<Delete>", job_list_delete_current)
    job_list_listbox.bind("<Return>", job_list_load_current)
    job_list_listbox.bind("<KP_Enter>", job_list_load_current)
    job_list_listbox.bind("<Double - Button - 1>", job_list_load_current)
    job_list_listbox.bind("r", job_list_rerun_current)
    job_list_listbox.bind('<<ListboxSelect>>', job_list_process_selection)
    job_list_listbox.bind("u", job_list_move_up)
    job_list_listbox.bind("d", job_list_move_down)

    # job listbox scrollbars
    job_list_listbox_scrollbar_y = Scrollbar(job_list_frame, orient="vertical")
    job_list_listbox_scrollbar_y.config(command=job_list_listbox.yview)
    job_list_listbox_scrollbar_y.grid(row=0, column=1, sticky=NS)
    job_list_listbox_scrollbar_x = Scrollbar(job_list_frame, orient="horizontal")
    job_list_listbox_scrollbar_x.config(command=job_list_listbox.xview)
    job_list_listbox_scrollbar_x.grid(row=1, column=0, columnspan=1, sticky=EW)

    job_list_listbox.config(xscrollcommand=job_list_listbox_scrollbar_x.set)
    job_list_listbox.config(yscrollcommand=job_list_listbox_scrollbar_y.set)

    # Define job list button area
    job_list_btn_frame = Frame(job_list_frame,
                             width=50, height=8)
    job_list_btn_frame.grid(row=0, column=2, padx=2, pady=2, sticky=W)

    # Add job button
    add_job_btn = Button(job_list_btn_frame, text="Add job", width=12, height=1,
                    command=job_list_add_current, activebackground='green',
                    activeforeground='white', wraplength=100, font=("Arial", FontSize))
    add_job_btn.pack(side=TOP, padx=2, pady=2)
    setup_tooltip(add_job_btn, "Add to job list a new job using the current settings defined on the right area of the AfterScan window.")

    # Delete job button
    delete_job_btn = Button(job_list_btn_frame, text="Delete job", width=12, height=1,
                    command=job_list_delete_selected, activebackground='green',
                    activeforeground='white', wraplength=100, font=("Arial", FontSize))
    delete_job_btn.pack(side=TOP, padx=2, pady=2)
    setup_tooltip(delete_job_btn, "Delete currently selected job from list.")

    # Rerun job button
    rerun_job_btn = Button(job_list_btn_frame, text="Rerun job", width=12, height=1,
                    command=job_list_rerun_selected, activebackground='green',
                    activeforeground='white', wraplength=100, font=("Arial", FontSize))
    rerun_job_btn.pack(side=TOP, padx=2, pady=2)
    setup_tooltip(rerun_job_btn, "Toggle 'run' state of currently selected job in list.")

    # Start processing job button
    start_batch_btn = Button(job_list_btn_frame, text="Start batch", width=12, height=1,
                    command=start_processing_job_list, activebackground='green',
                    activeforeground='white', wraplength=100, font=("Arial", FontSize))
    start_batch_btn.pack(side=TOP, padx=2, pady=2)
    setup_tooltip(start_batch_btn, "Start processing jobs in list.")

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
    setup_tooltip(suspend_on_batch_completion_rb, "Suspend computer when all jobs in list have been processed.")
    suspend_on_job_completion_rb = Radiobutton(job_list_btn_frame, text="Batch completion",
                                  variable=suspend_on_completion, value='batch_completion', font=("Arial", FontSize))
    suspend_on_job_completion_rb.pack(side=TOP, anchor=W, padx=2, pady=2)
    setup_tooltip(suspend_on_batch_completion_rb, "Suspend computer when current job being processed is complete.")
    no_suspend_rb = Radiobutton(job_list_btn_frame, text="No suspend",
                                  variable=suspend_on_completion, value='no_suspend', font=("Arial", FontSize))
    no_suspend_rb.pack(side=TOP, anchor=W, padx=2, pady=2)
    setup_tooltip(suspend_on_batch_completion_rb, "Do not suspend when done.")

    suspend_on_completion.set("no_suspend")


    postprocessing_bottom_frame = Frame(video_frame, width=30)
    postprocessing_bottom_frame.grid(row=video_row, column=0)


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
    global developer_debug

    LoggingMode = "INFO"
    go_disable_tooptips = False

    # Create job dictionary
    job_list = {}

    # Create project settings dictionary
    project_settings = default_project_config.copy()

    # Get developr file flag
    if os.path.isfile(developer_debug_file_flag):
        developer_debug = True

    template_list = TemplateList()
    template_list.add("S8", hole_template_filename_s8, "S8", (44, 400))
    template_list.add("R8", hole_template_filename_r8, "R8", (44, 44))
    template_list.add("BW", hole_template_filename_bw, "aux", (0, 0))
    template_list.add("WB", hole_template_filename_wb, "aux", (0, 0))
    template_list.add("Corner", hole_template_filename_corner, "aux", (0, 0))

    opts, args = getopt.getopt(argv, "hiel:dcst:12n")

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
        if opt == '-t':
            num_threads = int(arg)
        if opt == '-1':
            ForceSmallSize = True
        if opt == '-2':
            ForceBigSize = True
        if opt == '-n':
            go_disable_tooptips = True
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
            exit()

    LogLevel = getattr(logging, LoggingMode.upper(), None)
    if not isinstance(LogLevel, int):
        raise ValueError('Invalid log level: %s' % LogLevel)

    afterscan_init()
    if go_disable_tooptips:
        disable_tooltips()

    load_general_config()

    multiprocessing_init()

    ffmpeg_installed = False
    if platform.system() == 'Windows':
        IsWindows = True
        FfmpegBinName = 'C:\\ffmpeg\\bin\\ffmpeg.exe'
        AltFfmpegBinName = 'ffmpeg.exe'
        logging.debug("Detected Windows OS")
    elif platform.system() == 'Linux':
        IsLinux = True
        FfmpegBinName = 'ffmpeg'
        AltFfmpegBinName = 'ffmpeg'
        logging.debug("Detected Linux OS")
    elif platform.system() == 'Darwin':
        IsMac = True
        FfmpegBinName = 'ffmpeg'
        AltFfmpegBinName = 'ffmpeg'
        logging.debug("Detected Darwin (MacOS) OS")
    else:
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
            "FFmpeg is not installed in this computer.\r\n"
            "It is not mandatory for the application to run; "
            "Frame stabilization and cropping will still work, "
            "video generation will not")

    build_ui()
    widget_status_update()

    if SourceDir is not None:
        project_config_filename = os.path.join(SourceDir,
                                               project_config_basename)
    load_project_settings()
    
    load_project_config()
    decode_project_config()

    load_job_list()

    get_source_dir_file_list()
    get_target_dir_file_list()

    ui_init_done = True

    # Disable a few items that should be not operational without source folder
    if len(SourceDir) == 0:
        Go_btn.config(state=DISABLED)
        cropping_btn.config(state=DISABLED)
        frame_slider.config(state=DISABLED)
    else:
        Go_btn.config(state=NORMAL)
        cropping_btn.config(state=NORMAL)
        frame_slider.config(state=NORMAL)
        frame_slider.set(CurrentFrame)

    init_display()

    # If BatchAutostart, enable suspend on completion and start batch
    if BatchAutostart:
        suspend_on_joblist_end.set(True)
        win.after(2000, start_processing_job_list) # Wait 2 sec. to allow main loop to start

    # Main Loop
    win.mainloop()  # running the loop that works as a trigger


if __name__ == '__main__':
    main(sys.argv[1:])
