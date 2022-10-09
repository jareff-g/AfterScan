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
__version__ = "0.9beta"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import tkinter as tk
from tkinter import filedialog

import tkinter.messagebox
from tkinter import *

import tkinter.font as tkFont

from PIL import ImageTk, Image

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
import threading
import re

PerformStabilization = True
PerformCropping = False
GenerateVideo = False
StartFromCurrentFrame = False
FirstAbsoluteFrame = 0
LastAbsoluteFrame = 0
FrameScaleRefreshDone = True
FrameScaleRefreshPending = False
FramesToEncode = 0
# Python scrips folder, to store the json file with configuration data
ScriptDir = os.path.realpath(sys.argv[0])
ScriptDir = os.path.dirname(ScriptDir)
ConfigDataFilename = os.path.join(ScriptDir, "AfterScan.json")
PatternFilename = os.path.join(ScriptDir, "Pattern.S8.jpg")
TargetVideoFilename = ""
SourceDir = ""
TargetDir = ""
FrameFilenameOutputPattern = "picture-%05d.jpg"
FrameCheckFilenameOutputPattern = "picture-*.jpg"  # We need this because ...
FrameFilenameInputPattern = "picture-*.jpg"  # ...this one can be customized
SourceDirFileList = []
CurrentFrame = 0
StartFrame = 0
ConvertLoopExitRequested = False
ConvertLoopRunning = False
# preview dimensions (4/3 format)
PreviewWidth = 700
PreviewHeight = 525
VideoEncodingDoNotWarnAgain = False
ExpertMode = False
IsWindows = False
IsLinux = False

# Crop area rectangle drawing vars
ref_point = []
rectangle_drawing = False  # true if mouse is pressed
ix, iy = -1, -1
x_, y_ = 0, 0
CropWindowTitle = "Select area to crop, press Enter to confirm, " \
                  "Escape to cancel"
StabilizeWindowTitle = "Select area where to search film hole " \
                       "(small area around it), press Enter to confirm, " \
                       "Escape to cancel"
RectangleWindowTitle = ""
StabilizeAreaDefined = False
CropAreaDefined = False
RectangleTopLeft = (0, 0)
RectangleBottomRight = (0, 0)
StabilizeTopLeft = (0, 0)
StabilizeBottomRight = (0, 0)
CropTopLeft = (0, 0)
CropBottomRight = (0, 0)
VideoFps = 18
FfmpegBinName = ""
ExtendedStabilization = False

global win
global ffmpeg_installed
global work_image
global img_original

ConfigData = {
}

# Code below to draw a rectangle to select area to crop or find hole, taken
# from various authors in Stack Overflow:


def draw_rectangle(event, x, y, flags, param):
    global work_image
    global img_original
    global rectangle_drawing
    global ix, iy
    global x_, y_
    # Code posted by Ahsin Shabbir, same Stack overflow thread
    global RectangleTopLeft, RectangleBottomRight
    global preview_factor

    if event == cv2.EVENT_LBUTTONDOWN:
        if not rectangle_drawing:
            work_image = np.copy(img_original)
            x_, y_ = -10, -10
            ix, iy = -10, -10
        rectangle_drawing = True
        ix, iy = x, y
        x_, y_ = x, y
    elif event == cv2.EVENT_MOUSEMOVE and rectangle_drawing:
        copy = work_image.copy()
        x_, y_ = x, y
        cv2.rectangle(copy, (ix, iy), (x_, y_), (0, 255, 0), 1)
        cv2.imshow(RectangleWindowTitle, copy)
    elif event == cv2.EVENT_LBUTTONUP:
        rectangle_drawing = False
        cv2.rectangle(work_image, (ix, iy), (x, y), (0, 255, 0), 1)
        # Update global variables with area
        # Need to account for the fact area calculated with 50% reduced image
        RectangleTopLeft = (min(round(ix/preview_factor),
                                round(x/preview_factor)),
                            min(round(iy/preview_factor),
                                round(y/preview_factor)))
        RectangleBottomRight = (max(round(ix/preview_factor),
                                    round(x/preview_factor)),
                                max(round(iy/preview_factor),
                                    round(y/preview_factor)))
        logging.debug("Selected area: (%i, %i), (%i, %i)",
                      RectangleTopLeft[0], RectangleTopLeft[1],
                      RectangleBottomRight[0], RectangleBottomRight[1])


def select_rectangle_area():
    global work_image
    global CurrentFrame
    global SourceDirFileList
    global rectangle_drawing
    global ix, iy
    global x_, y_
    global img_original
    global preview_factor

    retvalue = False
    ix, iy = -1, -1
    x_, y_ = 0, 0

    file = SourceDirFileList[CurrentFrame]

    # load the image, clone it, and setup the mouse callback function
    work_image = cv2.imread(file, cv2.IMREAD_UNCHANGED)
    # Image is stabilized to have an accurate selection of crop area.
    # This leads to some interesting situation...
    work_image = stabilize_image(work_image, StabilizeTopLeft,
                                 StabilizeBottomRight)
    work_image = resize_image(work_image, 100*preview_factor)

    # work_image = np.zeros((512,512,3), np.uint8)
    img_original = np.copy(work_image)
    cv2.namedWindow(RectangleWindowTitle)
    cv2.setMouseCallback(RectangleWindowTitle, draw_rectangle)
    while 1:
        cv2.imshow(RectangleWindowTitle, work_image)
        if not cv2.EVENT_MOUSEMOVE:
            copy = work_image.copy()
            cv2.rectangle(copy, (ix, iy), (x_, y_), (0, 255, 0), 1)
            cv2.imshow(RectangleWindowTitle, copy)
        k = cv2.waitKey(1) & 0xFF
        if k == 13 and not rectangle_drawing:  # Enter: Confirm selection
            retvalue = True
            break
        elif k == 27:  # Escape: Cancel selection
            break
    cv2.destroyAllWindows()
    return retvalue


def select_stabilization_area():
    global RectangleWindowTitle
    global PerformStabilization
    global StabilizeTopLeft, StabilizeBottomRight
    global StabilizeAreaDefined

    # Disable all buttons in main window
    button_status_change_except(0, True)
    win.update()

    RectangleWindowTitle = StabilizeWindowTitle

    if select_rectangle_area():
        StabilizeAreaDefined = True
        PerformStabilization = True
        StabilizeTopLeft = RectangleTopLeft
        StabilizeBottomRight = RectangleBottomRight
        logging.debug("Selected Rectangle: (%i,%i) - (%i, %i)",
                      RectangleTopLeft[0], RectangleTopLeft[1],
                      RectangleBottomRight[0], RectangleBottomRight[1])
        logging.debug("Hole search area: (%i,%i) - (%i, %i)",
                      StabilizeTopLeft[0], StabilizeTopLeft[1],
                      StabilizeBottomRight[0], StabilizeBottomRight[1])
    else:
        StabilizeAreaDefined = False
        PerformStabilization = False
        StabilizeTopLeft = (0, 0)
        StabilizeBottomRight = (0, 0)

    # Update UI
    if ExpertMode:
        perform_stabilization.set(PerformStabilization)

    # Enable all buttons in main window
    button_status_change_except(0, False)
    win.update()


def select_cropping_area():
    global RectangleWindowTitle
    global PerformCropping
    global CropTopLeft, CropBottomRight
    global CropAreaDefined

    # Disable all buttons in main window
    button_status_change_except(0, True)
    win.update()

    RectangleWindowTitle = CropWindowTitle

    if select_rectangle_area():
        CropAreaDefined = True
        button_status_change_except(0, False)
        PerformCropping = perform_cropping.get()
        CropTopLeft = RectangleTopLeft
        CropBottomRight = RectangleBottomRight
        logging.debug("Crop area: (%i,%i) - (%i, %i)", CropTopLeft[0],
                      CropTopLeft[1], CropBottomRight[0], CropBottomRight[1])
    else:
        CropAreaDefined = False
        button_status_change_except(0, True)
        PerformCropping = False
        perform_cropping.set(False)
        generate_video_checkbox.config(state=NORMAL if ffmpeg_installed and
                                       PerformCropping else DISABLED)
        CropTopLeft = (0, 0)
        CropBottomRight = (0, 0)

    perform_cropping_checkbox.config(state=NORMAL if CropAreaDefined
                                     else DISABLED)

    # Enable all buttons in main window
    button_status_change_except(0, False)
    win.update()


def button_status_change_except(except_button, active):
    global source_folder_btn, target_folder_btn
    global perform_stabilization_checkbox
    global perform_cropping_checkbox, Crop_btn
    global Go_btn
    global Exit_btn

    if except_button != source_folder_btn:
        source_folder_btn.config(state=DISABLED if active else NORMAL)
    if except_button != target_folder_btn:
        target_folder_btn.config(state=DISABLED if active else NORMAL)
    if except_button != perform_cropping_checkbox:
        perform_cropping_checkbox.config(state=DISABLED if active else NORMAL)
    # if except_button != Crop_btn:
    #    Crop_btn.config(state=DISABLED if active else NORMAL)
    if except_button != Go_btn:
        Go_btn.config(state=DISABLED if active else NORMAL)
    if except_button != Exit_btn:
        Exit_btn.config(state=DISABLED if active else NORMAL)
    if ExpertMode:
        if except_button != perform_stabilization_checkbox:
            perform_stabilization_checkbox.config(state=DISABLED if active
                                                  else NORMAL)

    if not CropAreaDefined:
        perform_cropping_checkbox.config(state=DISABLED)


def match_template(template, img, thres):
    w, h = template.shape[::-1]
    # convert img to grey
    img_grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(img_grey, template, cv2.TM_CCOEFF_NORMED)
    # Best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    # Drawing rectangle only for debugging
    # cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), 2)
    return top_left

# ***********************************************************


def video_encoding_do_not_warn_again_selection():
    global video_encoding_do_not_warn_again
    global VideoEncodingDoNotWarnAgain
    global warn_again_from_toplevel

    VideoEncodingDoNotWarnAgain = video_encoding_do_not_warn_again.get()
    ConfigData["VideoEncodingDoNotWarnAgain"] = str(
        VideoEncodingDoNotWarnAgain)


def close_video_encoding_warning():
    global video_encoding_warning

    video_encoding_warning.destroy()
    video_encoding_warning.quit()


def video_encoding_warning():
    global win
    global video_encoding_warning
    global video_encoding_do_not_warn_again
    global VideoEncodingDoNotWarnAgain
    global warn_again_from_toplevel

    if VideoEncodingDoNotWarnAgain:
        return

    warn_again_from_toplevel = tk.BooleanVar()
    video_encoding_warning = Toplevel(win)
    video_encoding_warning.title('*** Video generation warning ***')
    video_encoding_warning.geometry('500x300')
    video_encoding_warning.geometry('+250+250')
    video_encoding_label = Label(
        video_encoding_warning,
        text='\rThis utility uses FFmpeg to generate video from S8/R8 frames '
        'produced by a film scanner.\r\nFFmpeg is invoked in a synchronous '
        'manner from this application, so it is not posible (or better, I '
        'haven\'t found the way) to display video encoding progress '
        'information in the UI in a nice way.\r\nTherefore, as a workaround, '
        'output from FFmpeg is redirected to the console, in order to provide '
        'feedback on the encoding process, that in most cases will be quite '
        'long.', wraplength=450, justify=LEFT)
    video_encoding_do_not_warn_again = tk.BooleanVar(
        value=VideoEncodingDoNotWarnAgain)
    video_encoding_btn = Button(video_encoding_warning, text="OK", width=2,
                                height=1, command=close_video_encoding_warning)
    video_encoding_checkbox = tk.Checkbutton(
        video_encoding_warning, text='Do not show this warning again',
        height=1, variable=video_encoding_do_not_warn_again, onvalue=True,
        offvalue=False, command=video_encoding_do_not_warn_again_selection)

    video_encoding_label.pack(side=TOP)
    video_encoding_btn.pack(side=TOP, pady=10)
    video_encoding_checkbox.pack(side=TOP)

    video_encoding_warning.mainloop()


# ***********************************************************
def display_ffmpeg_progress():
    global win
    global ffmpeg_process
    global stop_event, stop_event_lock
    global TargetDir, TargetVideoFilename

    Exit = False
    while not Exit:
        time.sleep(0.5)
        if stop_event.is_set():
            Exit = True
        consolidated_info = " "
        while True:
            line = ffmpeg_process.stdout.readline()
            if not line:
                break
            else:
                # logging.info(str(line))
                # Now this is part of the tool functionality, so we display
                # it using print, to avoid dependencies on log level
                print(time.strftime("%H:%M:%S", time.localtime()) + " - " +
                      str(line)[:-1])


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


def resize_image(img, percent):
    # Calculate the proportional size of original image
    width = int(img.shape[1] * percent / 100)
    height = int(img.shape[0] * percent / 100)

    # dsize
    dsize = (width, height)

    # resize image
    return cv2.resize(img, dsize)


def stabilize_image(img, top_left, botton_right):
    global SourceDirFileList, CurrentFrame
    global StabilizeTopLeft, StabilizeBottomRight
    # Get image dimensions to perform image shift later
    width = img.shape[1]
    height = img.shape[0]
    # Get partial image where the hole should be (to facilitate template search
    # by OpenCV). We do the calculations inline instead of calling the function
    # since we need the intermediate values
    # Default values defined at display initialization time, after source
    # folder is defined
    horizontal_range = (StabilizeTopLeft[0], StabilizeBottomRight[0])
    vertical_range = (StabilizeTopLeft[1], StabilizeBottomRight[1])
    cropped_image = img[vertical_range[0]:vertical_range[1],
                        horizontal_range[0]:horizontal_range[1]]

    # Search film hole pattern
    try:
        top_left = match_template(s8_template, cropped_image, 0.6)
        # The coordinates returned by match template are relative to the
        # cropped image. In order to calculate the correct values to provide
        # to the translation matrix, need to convert to absolute coordinates
        top_left = (top_left[0] + StabilizeTopLeft[0],
                    top_left[1] + StabilizeTopLeft[1])
        # According to tests done during the development, the ideal top left
        # position for a match of the hole template used (63*339 pixels) should
        # be situated at 12% of the horizontal axis, and 38% of the vertical
        # axis. Calculate shift, according to those proportions

        move_x = round((12*width / 100)) - top_left[0]
        move_y = round((38*height / 100)) - top_left[1]
        logging.debug("Stabilizing frame: (%i,%i) to move (%i, %i)",
                      top_left[0], top_left[1], move_x, move_y)

        # Create the translation matrix using move_x and move_y (NumPy array)
        translation_matrix = np.array([
            [1, 0, move_x],
            [0, 1, move_y]
        ], dtype=np.float32)
        # Apply the translation to the image
        translated_image = cv2.warpAffine(src=img, M=translation_matrix,
                                          dsize=(width+move_x, height+move_y))
    except Exception as ex:
        exception_template = ("An exception of type {0} occurred. "
                              "Arguments:\n{1!r}")
        exception_details = template.format(type(ex).__name__, ex.args)
        logging.debug("Error in match_template (file %s), "
                      "returning original image. %s",
                      SourceDirFileList[CurrentFrame], exception_details)
        translated_image = img
    return translated_image


def crop_image(img, top_left, botton_right):
    # Get image dimensions to perform image shift later
    width = img.shape[1]
    height = img.shape[0]

    Y_start = top_left[1]
    Y_end = botton_right[1]
    X_start = top_left[0]
    X_end = botton_right[0]

    return img[Y_start:Y_end, X_start:X_end]


def get_pattern_file():
    global PatternFilename, pattern_filename
    global pattern_canvas

    pattern_file = tk.filedialog.askopenfilename(
        initialdir=os.path.dirname(PatternFilename),
        title="Select perforation hole pattern file",
        filetypes=(("jpeg files", "*.jpg"),
                   ("png files", "*.png"),
                   ("all files", "*.*")))

    if not pattern_file:
        return
    else:
        pattern_filename.delete(0, 'end')
        pattern_filename.insert('end', pattern_file)
        PatternFilename = pattern_filename.get()

    ConfigData["PatternFilename"] = PatternFilename

    display_pattern(PatternFilename)


def display_pattern(PatternFilename):
    global pattern_canvas

    # If file does not exists, return
    if not os.path.isfile(PatternFilename):
        return

    # Get canvas size
    canvas_width = pattern_canvas.winfo_reqwidth()
    canvas_height = pattern_canvas.winfo_reqheight()
    # Load hole pattern image
    img = cv2.imread(PatternFilename, cv2.IMREAD_UNCHANGED)
    # Calculate resize ratio (% calculated with 90 instead of 100
    # to keep some margins
    if img.shape[1] > canvas_width:
        width_ratio = round(canvas_width*90/img.shape[1])
    if img.shape[0] > canvas_height:
        height_ratio = round(canvas_height*90/img.shape[0])
    resize_ratio = min(width_ratio, height_ratio)
    # Display image in dedicated space
    img = resize_image(img, resize_ratio)
    DisplayImage = ImageTk.PhotoImage(Image.fromarray(img))
    # Label widget can be used to display a text or image on the screen.
    pattern_canvas.create_image(round((canvas_width-img.shape[1])/2),
                                round((canvas_height-img.shape[0])/2),
                                anchor=NW, image=DisplayImage)
    pattern_canvas.image = DisplayImage
    # pattern_canvas.pack()
    win.update()


def set_source_folder():
    global SourceDir, CurrentFrame, frame_slider, Go_btn, cropping_btn
    global FirstAbsoluteFrame

    SourceDir = tk.filedialog.askdirectory(
        initialdir=SourceDir,
        title="Select folder with captured images to process")

    if not SourceDir:
        return
    elif TargetDir == SourceDir:
        tk.messagebox.showerror(
            "Error!",
            "Source folder cannot be the same as target folder.")
        return
    else:
        folder_frame_source_dir.delete(0, 'end')
        folder_frame_source_dir.insert('end', SourceDir)

    ConfigData["SourceDir"] = SourceDir
    # Load matching file list from newly selected dir
    get_current_dir_file_list()
    CurrentFrame = 0
    # Enable Start and Crop buttons, plus slider, once we have files to handle
    cropping_btn.config(state=NORMAL)
    frame_slider.config(state=NORMAL)
    Go_btn.config(state=NORMAL)
    frame_slider.set(CurrentFrame + FirstAbsoluteFrame)
    init_display()


def set_target_folder():
    global TargetDir
    global folder_frame_target_dir

    TargetDir = tk.filedialog.askdirectory(
        initialdir=TargetDir,
        title="Select folder where to store processed images/video")

    if not TargetDir:
        return
    elif TargetDir == SourceDir:
        tk.messagebox.showerror(
            "Error!",
            "Target folder cannot be the same as source folder.")
        return
    else:
        folder_frame_target_dir.delete(0, 'end')
        folder_frame_target_dir.insert('end', TargetDir)

    ConfigData["TargetDir"] = TargetDir


def set_frame_pattern_filename_folder():
    global FrameFilenameInputPattern, frame_filename_input_pattern_name

    FrameFilenameInputPattern = frame_filename_input_pattern_name.get()
    ConfigData["FrameFilenameInputPattern"] = FrameFilenameInputPattern


def perform_stabilization_selection():
    global perform_stabilization, PerformStabilization
    PerformStabilization = perform_stabilization.get()


def extended_stabilization_selection():
    global extended_stabilization, ExtendedStabilization
    ExtendedStabilization = extended_stabilization.get()
    init_display()


def perform_cropping_selection():
    global perform_cropping, PerformCropping
    global generate_video_checkbox
    PerformCropping = perform_cropping.get()
    generate_video_checkbox.config(state=NORMAL if ffmpeg_installed
                                   and PerformCropping else DISABLED)


def from_current_frame_selection():
    global from_current_frame, StartFromCurrentFrame
    StartFromCurrentFrame = from_current_frame.get()


def frames_to_encode_selection(updown):
    global frames_to_encode_spinbox, frames_to_encode
    spinbox_content = frames_to_encode_spinbox.get()
    if spinbox_content == '0':
        if updown == 'up':
            frames_to_encode.set('1')
        else:
            frames_to_encode.set('All')


def generate_video_selection():
    global generate_video, GenerateVideo
    global video_fps_dropdown, video_fps_label, video_filename_name
    global ffmpeg_preset_rb1, ffmpeg_preset_rb2, ffmpeg_preset_rb3

    GenerateVideo = generate_video.get()
    video_fps_dropdown.config(state=NORMAL if GenerateVideo else DISABLED)
    video_fps_label.config(state=NORMAL if GenerateVideo else DISABLED)
    video_filename_name.config(state=NORMAL if GenerateVideo else DISABLED)
    ffmpeg_preset_rb1.config(state=NORMAL if GenerateVideo else DISABLED)
    ffmpeg_preset_rb2.config(state=NORMAL if GenerateVideo else DISABLED)
    ffmpeg_preset_rb3.config(state=NORMAL if GenerateVideo else DISABLED)


def set_fps(selected):
    global VideoFps

    ConfigData["VideoFps"] = eval(selected)
    VideoFps = eval(selected)


def exit_app():  # Exit Application
    global win

    # Write config data upon exit
    with open(ConfigDataFilename, 'w') as f:
        json.dump(ConfigData, f)

    win.destroy()


def display_image(img):
    global PreviewWidth

    width = img.shape[1]

    img = resize_image(img, round((PreviewWidth/width)*100))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    DisplayableImage = ImageTk.PhotoImage(Image.fromarray(img))

    # The Label widget can be used to display a text or image on the screen.
    draw_capture_label.config(image=DisplayableImage)
    draw_capture_label.image = DisplayableImage
    draw_capture_label.pack()
    win.update()


def is_ffmpeg_installed():
    global ffmpeg_installed

    cmd_ffmpeg = [FfmpegBinName, '-h']

    try:
        ffmpeg_process = sp.Popen(cmd_ffmpeg, stderr=sp.PIPE, stdout=sp.PIPE)
        ffmpeg_installed = True
    except FileNotFoundError:
        ffmpeg_installed = False
        logging.debug("ffmpeg is NOT installed.")

    return ffmpeg_installed


def valid_generated_frame_range():
    global StartFrame, FramesToEncode, FirstAbsoluteFrame

    file_count = 0
    generated_frame_list = list(glob(os.path.join(
        TargetDir, FrameCheckFilenameOutputPattern)))
    for i in range(FirstAbsoluteFrame + StartFrame,
                   FirstAbsoluteFrame + StartFrame + FramesToEncode):
        file_to_check = os.path.join(TargetDir,
                                     FrameFilenameOutputPattern % i)
        if file_to_check in generated_frame_list:
            file_count += 1
    logging.debug("Checking frame range %i-%i: %i files found",
                  FirstAbsoluteFrame + StartFrame,
                  FirstAbsoluteFrame + StartFrame + FramesToEncode, file_count)

    return file_count == FramesToEncode


def start_convert():
    global ConvertLoopExitRequested, ConvertLoopRunning
    global GenerateVideo
    global Exit_btn
    global video_writer
    global pipe_ffmpeg
    global cmd_ffmpeg
    global SourceDirFileList
    global TargetVideoFilename
    global CurrentFrame, StartFrame
    global StartFromCurrentFrame
    global FramesToEncode

    if ConvertLoopRunning:
        ConvertLoopExitRequested = True
    else:
        if not StartFromCurrentFrame:
            CurrentFrame = 0
        StartFrame = CurrentFrame
        # Centralize 'FramesToEncode' update here
        if frames_to_encode_spinbox.get() == 'All':
            FramesToEncode = len(SourceDirFileList) - StartFrame
        else:
            FramesToEncode = int(frames_to_encode_spinbox.get())
            if StartFrame + FramesToEncode >= len(SourceDirFileList):
                FramesToEncode = len(SourceDirFileList) - StartFrame
        if FramesToEncode == 0:
            tk.messagebox.showwarning(
                "No frames match range",
                "No frames to encode.\r\n"
                "The range specified (current frame - number of frames to "
                "encode) does not match any frame.\r\n"
                "Please review your settings and try again.")
            return
        Go_btn.config(text="Stop", bg='red', fg='white', relief=SUNKEN)
        # Disable all buttons in main window
        button_status_change_except(Go_btn, True)
        win.update()

        if GenerateVideo:
            TargetVideoFilename = video_filename_name.get()
            name, ext = os.path.splitext(TargetVideoFilename)
            if TargetVideoFilename == "":   # Assign default if no filename
                TargetVideoFilename = (
                    "AfterScan-" +
                    datetime.now().strftime("%Y_%m_%d-%H-%M-%S") + ".mp4")
                video_filename_name.delete(0, 'end')
                video_filename_name.insert('end', TargetVideoFilename)
            elif ext == "":
                TargetVideoFilename += ".mp4"
                video_filename_name.delete(0, 'end')
                video_filename_name.insert('end', TargetVideoFilename)
            elif os.path.isfile(os.path.join(TargetDir, TargetVideoFilename)):
                error_msg = (TargetVideoFilename + " already exist in target "
                             "folder. Overwrite?")
                if not tk.messagebox.askyesno("Error!", error_msg):
                    return
        if GenerateVideo and not VideoEncodingDoNotWarnAgain:
            tk.messagebox.showwarning(
                "Video encoding warning",
                "\r\nVideo encoding progress is NOT displayed in the user "
                "interface, only at the end of the encoding (which can take "
                "hours for long films). \r\n"
                "Please check in the console if required, progress reported "
                "by FFmpeg is displayed there. ")

        ConvertLoopRunning = True

        if not skip_frame_regeneration.get():
            win.after(1, frame_generation_loop)
        else:
            win.after(1, video_generation_phase)


def generation_exit():
    global win
    global ConvertLoopExitRequested
    global ConvertLoopRunning
    global Go_btn, save_bg, save_fg

    ConvertLoopExitRequested = False  # Reset flags
    ConvertLoopRunning = False
    Go_btn.config(text="Start", bg=save_bg, fg=save_fg, relief=RAISED)
    # Enable all buttons in main window
    button_status_change_except(0, False)
    win.update()


def frame_generation_loop():
    global s8_template
    global draw_capture_label
    global PerformStabilization
    global ConvertLoopExitRequested
    global save_bg, save_fg
    global Go_btn
    global Exit_btn
    global CropTopLeft, CropBottomRight
    global TargetDir
    global video_writer
    global pipe_ffmpeg
    global cmd_ffmpeg
    global IsWindows
    global ffmpeg_preset
    global TargetVideoFilename
    global CurrentFrame, StartFrame
    global ffmpeg_out, ffmpeg_process
    global stop_event, stop_event_lock
    global FrameFilenameOutputPattern
    global FirstAbsoluteFrame, FramesToEncode

    if CurrentFrame >= StartFrame + FramesToEncode:
        if GenerateVideo:
            win.after(1, video_generation_phase)
        else:
            generation_exit()
        return

    if ConvertLoopExitRequested:  # Stop button pressed
        generation_exit()
        return

    # Get current file
    file = SourceDirFileList[CurrentFrame]
    # read image
    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)

    if PerformStabilization:
        img = stabilize_image(img, StabilizeTopLeft, StabilizeBottomRight)
    if PerformCropping:
        img = crop_image(img, CropTopLeft, CropBottomRight)

    display_image(img)

    logging.debug("Display image: %s, target size: (%i, %i), "
                  "CurrentFrame %i", file,
                  img.shape[1], img.shape[0], CurrentFrame)

    if os.path.isdir(TargetDir):
        target_file = os.path.join(TargetDir, os.path.basename(file))
        cv2.imwrite(target_file, img)

    frame_slider.set(CurrentFrame + FirstAbsoluteFrame)

    CurrentFrame += 1

    win.after(1, frame_generation_loop)


def video_generation_phase():
    global s8_template
    global draw_capture_label
    global PerformStabilization
    global ConvertLoopExitRequested
    global save_bg, save_fg
    global Go_btn
    global Exit_btn
    global CropTopLeft, CropBottomRight
    global TargetDir
    global video_writer
    global pipe_ffmpeg
    global cmd_ffmpeg
    global IsWindows
    global ffmpeg_preset
    global TargetVideoFilename
    global CurrentFrame, StartFrame
    global ffmpeg_out, ffmpeg_process
    global stop_event, stop_event_lock
    global FrameFilenameOutputPattern
    global FirstAbsoluteFrame, FramesToEncode

    # Check for special cases first
    if FramesToEncode == 0:
        tk.messagebox.showwarning(
            "No frames match range to generate video",
            "Video cannot be generated.\r\n"
            "No frames in target folder match the specified range.\r\n"
            "Please review your settings and try again.")
    elif not valid_generated_frame_range():
        tk.messagebox.showwarning(
            "Frames missing",
            "Video cannot be generated.\r\n"
            "Not all frames in specified range exist in target folder to "
            "allow video generation.\r\n"
            "Please regenerate frames making sure option "
            "\'Skip Frame regeneration\' is not selected, and try again.")
    else:
        # Cannot interrupt while generating video (FFmpeg running)
        Go_btn.config(state=DISABLED)
        logging.debug(
            "First filename in list: %s, extracted number: %s",
            os.path.basename(SourceDirFileList[0]), FirstAbsoluteFrame)
        stop_event = threading.Event()
        stop_event_lock = threading.Lock()

        ffmpeg_progress_thread = threading.Thread(
            target=display_ffmpeg_progress)
        ffmpeg_progress_thread.daemon = True
        ffmpeg_progress_thread.start()
        win.update()

        # Cannot call popen with a list in windows. Seems it was a bug
        # already in 2018: https://bugs.python.org/issue32764
        if IsWindows or True:
            cmd_ffmpeg = (FfmpegBinName
                          + ' -y'
                          + ' -f image2'
                          + ' -start_number ' + str(StartFrame +
                                                 FirstAbsoluteFrame)
                          + ' -framerate ' + str(VideoFps)
                          + ' -i "'
                          + os.path.join(TargetDir,
                                         FrameFilenameOutputPattern)
                          + '"')
            if FramesToEncode > 0:
                cmd_ffmpeg += (' -frames:v' + str(FramesToEncode))
            cmd_ffmpeg += (' -an'
                           + ' -vcodec libx264'
                           + ' -preset ' + ffmpeg_preset.get()
                           + ' -crf 18'
                           + ' -aspect 4:3'
                           + ' -pix_fmt yuv420p'
                           + ' '
                           + '"' + os.path.join(
                               TargetDir,
                               TargetVideoFilename) + '"')
            logging.debug("Generated ffmpeg command: %s", cmd_ffmpeg)
            ffmpeg_generation_succeeded = sp.call(cmd_ffmpeg) == 0
        else:
            cmd_ffmpeg = [FfmpegBinName,
                          '-y',
                          '-loglevel', 'error',
                          '-stats',
                          '-flush_packets', '1',
                          '-f', 'image2',
                          '-start_number', str(StartFrame +
                                               FirstAbsoluteFrame),
                          '-framerate', str(VideoFps),
                          '-i',
                          os.path.join(TargetDir,
                                       FrameFilenameOutputPattern)]
            if FramesToEncode > 0:
                cmd_ffmpeg += ['-frames:v', str(FramesToEncode)]
            cmd_ffmpeg += ['-an',  # no audio
                           '-vcodec', 'libx264',
                           '-preset', ffmpeg_preset.get(),
                           '-crf', '18',
                           '-pix_fmt', 'yuv420p',
                           os.path.join(TargetDir,
                                        TargetVideoFilename)]

            logging.debug("Generated ffmpeg command: %s", cmd_ffmpeg)
            ffmpeg_process = sp.Popen(cmd_ffmpeg, stderr=sp.STDOUT,
                                      stdout=sp.PIPE,
                                      universal_newlines=True)
            ffmpeg_generation_succeeded = ffmpeg_process.wait() == 0

        stop_event.set()
        ffmpeg_progress_thread.join()

        # And display results
        if ffmpeg_generation_succeeded:
            tk.messagebox.showinfo(
                "Video generation by ffmpeg has ended",
                "\r\nVideo encoding has finalized successfully. "
                "You can find your video in the target folder, "
                "as stated below\r\n" +
                os.path.join(TargetDir, TargetVideoFilename))
        else:
            tk.messagebox.showinfo(
                "FFMPEG encoding failed",
                "\r\nVideo generation by FFMPEG has failed\r\nPlease "
                "check the logs to determine what the problem was.")

    generation_exit()  # Restore all setigns to normal


def get_current_dir_file_list():
    global SourceDir
    global SourceDirFileList
    global FrameFilenameInputPattern
    global FirstAbsoluteFrame
    global frame_slider

    SourceDirFileList = sorted(list(glob(os.path.join(
        SourceDir,
        FrameFilenameInputPattern))))
    FirstAbsoluteFrame = int(
        ''.join(list(filter(str.isdigit,
                            os.path.basename(SourceDirFileList[0])))))
    LastAbsoluteFrame = FirstAbsoluteFrame + len(SourceDirFileList)-1
    frame_slider.config(from_=FirstAbsoluteFrame, to=LastAbsoluteFrame)


def init_display():
    global SourceDir
    global CurrentFrame
    global SourceDirFileList
    global StabilizeTopLeft, StabilizeBottomRight

    # Get first file
    savedir = os.getcwd()
    if SourceDir == "":
        tk.messagebox.showerror("Error!",
                                "Please specify source and target folders.")
        return
    else:
        extended_stabilization_checkbox.config(state=NORMAL)

    os.chdir(SourceDir)
    file = SourceDirFileList[CurrentFrame]

    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)

    display_image(img)

    # Initizalize default values for perforation search area,
    # as they are relative to image size
    # Get image dimensions first
    width = img.shape[1]
    height = img.shape[0]
    # Default values are needed before the stabilization search area
    # has been defined, therefore we initialized them here
    if StabilizeTopLeft == (0, 0) and StabilizeBottomRight == (0, 0):
        if (ExtendedStabilization):
            StabilizeTopLeft = (0, 0)
            StabilizeBottomRight = (round(width * 0.25), height)
        else:
            StabilizeTopLeft = (0, round(height * 0.30))
            StabilizeBottomRight = (round(width * 0.2), round(height * 0.70))


def scale_display_update():
    global win
    global FrameScaleRefreshDone, FrameScaleRefreshPending
    global CurrentFrame

    file = SourceDirFileList[CurrentFrame]
    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
    display_image(img)
    FrameScaleRefreshDone = True
    if FrameScaleRefreshPending:
        FrameScaleRefreshPending = False
        win.after(100, scale_display_update)


def select_scale_frame(selected_frame):
    global win
    global SourceDir
    global CurrentFrame
    global SourceDirFileList
    global FirstAbsoluteFrame
    global FrameScaleRefreshDone, FrameScaleRefreshPending

    if not ConvertLoopRunning:  # Do not refresh during conversion loop
        frame_slider.focus()
        CurrentFrame = int(selected_frame) - FirstAbsoluteFrame
        if FrameScaleRefreshDone:
            FrameScaleRefreshDone = False
            FrameScaleRefreshPending = False
            win.after(5, scale_display_update)
        else:
            FrameScaleRefreshPending = True


def load_config_data():
    global ConfigData
    global ConfigDataFilename
    global LastSessionDate
    global SourceDir, TargetDir
    global folder_frame_source_dir, folder_frame_target_dir
    global VideoFps, video_fps_dropdown_selected
    global PatternFilename, pattern_filename
    global frame_filename_pattern_name
    global FrameFilenameInputPattern
    global VideoEncodingDoNotWarnAgain

    # Check if persisted data file exist: If it does, load it
    if os.path.isfile(ConfigDataFilename):
        persisted_data_file = open(ConfigDataFilename)
        ConfigData = json.load(persisted_data_file)
        persisted_data_file.close()

    for item in ConfigData:
        logging.info("%s=%s", item, str(ConfigData[item]))

    if 'SourceDir' in ConfigData:
        SourceDir = ConfigData["SourceDir"]
        # If directory in configuration does not exist, set current working dir
        if not os.path.isdir(SourceDir):
            SourceDir = ""
        folder_frame_source_dir.delete(0, 'end')
        folder_frame_source_dir.insert('end', SourceDir)
        get_current_dir_file_list()
    if 'TargetDir' in ConfigData:
        TargetDir = ConfigData["TargetDir"]
        # If directory in configuration does not exist, set current working dir
        if not os.path.isdir(TargetDir):
            TargetDir = ""
        folder_frame_target_dir.delete(0, 'end')
        folder_frame_target_dir.insert('end', TargetDir)
    if 'LastSessionDate' in ConfigData:
        LastSessionDate = eval(ConfigData["LastSessionDate"])
    if 'VideoFps' in ConfigData:
        VideoFps = ConfigData["VideoFps"]
        video_fps_dropdown_selected.set(VideoFps)
    if 'FrameFilenameInputPattern' in ConfigData:
        FrameFilenameInputPattern = ConfigData["FrameFilenameInputPattern"]
        frame_filename_input_pattern_name
        frame_filename_input_pattern_name.delete(0, 'end')
        frame_filename_input_pattern_name.insert('end',
                                                 FrameFilenameInputPattern)
    if 'VideoEncodingDoNotWarnAgain' in ConfigData:
        VideoEncodingDoNotWarnAgain = ConfigData["VideoEncodingDoNotWarnAgain"]

    if ExpertMode:
        if 'PatternFilename' in ConfigData:
            PatternFilename = ConfigData["PatternFilename"]
            pattern_filename.delete(0, 'end')
            pattern_filename.insert('end', PatternFilename)
            display_pattern(PatternFilename)


def afterscan_postprod_init():
    global win
    global TopWinX
    global TopWinY
    global WinInitDone
    global SourceDir
    global LogLevel
    global draw_capture_label
    global PreviewWidth, PreviewHeight
    global preview_factor
    global ExpertMode

    # Initialize logging
    log_path = os.path.dirname(__file__)
    if log_path == "":
        log_path = os.getcwd()
    log_file_fullpath = log_path + "/AfterScan.debug.log"
    logging.basicConfig(
        level=LogLevel,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file_fullpath),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info("Log file: %s", log_file_fullpath)

    win = Tk()  # Create main window, store it in 'win'

    # Get screen size
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    # Set dimensions of UI elements adapted to screen size
    if screen_height >= 1080:
        preview_factor = 0.5
        PreviewWidth = 700
        PreviewHeight = 525
    else:
        preview_factor = 0.25
        PreviewWidth = 560
        PreviewHeight = 420
    app_width = PreviewWidth + 320 + 30
    app_height = PreviewHeight + 25
    if ExpertMode:
        app_height += 75

    win.title('AfterScan')  # setting title of the window
    win.geometry('1080x700')  # setting the size of the window
    win.geometry('+50+50')  # setting the position of the window
    # Prevent window resize
    win.minsize(app_width, app_height)
    win.maxsize(app_width, app_height)

    win.update_idletasks()

    # Set default font size
    default_font = tkFont.nametofont("TkDefaultFont")
    default_font.configure(size=10)

    # Get Top window coordinates
    TopWinX = win.winfo_x()
    TopWinY = win.winfo_y()

    WinInitDone = True

    # Create a frame to add a border to the preview
    preview_border_frame = Frame(win, width=PreviewWidth, height=PreviewHeight,
                                 bg='dark grey')
    preview_border_frame.grid(row=0, column=0, padx=5, pady=5, sticky=N)
    # Also a label to draw images
    draw_capture_label = tk.Label(preview_border_frame)

    logging.debug("AfterScan initialized")


def build_ui():
    global win
    global SourceDir, TargetDir
    global folder_frame_source_dir, folder_frame_target_dir
    global PerformStabilization, perform_stabilization
    global PerformCropping, perform_cropping, cropping_btn
    global GenerateVideo, generate_video
    global from_current_frame, StartFromCurrentFrame
    global frames_to_encode_spinbox, frames_to_encode, FramesToEncode
    global save_bg, save_fg
    global source_folder_btn, target_folder_btn
    global perform_stabilization_checkbox
    global perform_cropping_checkbox, Crop_btn
    global Go_btn
    global Exit_btn
    global video_fps_dropdown_selected
    global video_fps_dropdown, video_fps_label, video_filename_name
    global ffmpeg_preset
    global ffmpeg_preset_rb1, ffmpeg_preset_rb2, ffmpeg_preset_rb3
    global skip_frame_regeneration
    global pattern_filename
    global pattern_canvas
    global ExpertMode
    global generate_video_checkbox
    global extended_stabilization, extended_stabilization_checkbox
    global frame_filename_pattern_name
    global FrameFilenameInputPattern
    global FrameSelected
    global frame_slider

    # Frame for standard widgets
    regular_frame = Frame(win, width=320, height=450)
    regular_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky=N)

    # Frame for top section of standard widgets
    regular_top_section_frame = Frame(regular_frame, width=50, height=50)
    regular_top_section_frame.pack(side=TOP, padx=2, pady=2, anchor=W)

    # Create frame to display current frame and selection buttons
    picture_frame = LabelFrame(regular_top_section_frame, text='Current frame',
                               width=26, height=8)
    picture_frame.pack(side=LEFT, padx=2, pady=2)

    FrameSelected = IntVar()
    frame_slider = Scale(picture_frame, orient=HORIZONTAL, from_=0, to=0,
                         variable=FrameSelected, command=select_scale_frame,
                         font=("Arial", 16))
    frame_slider.pack(side=BOTTOM)

    # Application start button
    Go_btn = Button(regular_top_section_frame, text="Start", width=8, height=3,
                    command=start_convert, activebackground='green',
                    activeforeground='white', wraplength=80)
    Go_btn.pack(side=LEFT, padx=2, pady=2)

    # Application Exit button
    Exit_btn = Button(regular_top_section_frame, text="Exit", width=6,
                      height=3, command=exit_app, activebackground='red',
                      activeforeground='white', wraplength=80)
    Exit_btn.pack(side=LEFT, padx=2, pady=2)

    # Create frame to select source and target folders
    folder_frame = LabelFrame(regular_frame, text='Folder selection', width=50,
                              height=8)
    folder_frame.pack(side=TOP, padx=2, pady=2, anchor=W)

    source_folder_frame = Frame(folder_frame)
    source_folder_frame.pack(side=TOP)
    folder_frame_source_dir = Entry(source_folder_frame, width=36,
                                    borderwidth=1, font=("Arial", 8))
    folder_frame_source_dir.pack(side=LEFT)
    source_folder_btn = Button(source_folder_frame, text='Source', width=6,
                               height=1, command=set_source_folder,
                               activebackground='green',
                               activeforeground='white', wraplength=80,
                               font=("Arial", 8))
    source_folder_btn.pack(side=LEFT)

    target_folder_frame = Frame(folder_frame)
    target_folder_frame.pack(side=TOP)
    folder_frame_target_dir = Entry(target_folder_frame, width=36,
                                    borderwidth=1, font=("Arial", 8))
    folder_frame_target_dir.pack(side=LEFT)
    target_folder_btn = Button(target_folder_frame, text='Target', width=6,
                               height=1, command=set_target_folder,
                               activebackground='green',
                               activeforeground='white', wraplength=80,
                               font=("Arial", 8))
    target_folder_btn.pack(side=LEFT)

    save_bg = source_folder_btn['bg']
    save_fg = source_folder_btn['fg']

    folder_bottom_frame = Frame(folder_frame)
    folder_bottom_frame.pack(side=BOTTOM, ipady=2)

    frame_filename_pattern_frame = Frame(folder_frame)
    frame_filename_pattern_frame.pack(side=TOP)
    frame_filename_pattern_label = Label(frame_filename_pattern_frame,
                                         text='Frame input filename pattern:',
                                         font=("Arial", 8))
    frame_filename_pattern_label.pack(side=LEFT, anchor=W)
    frame_filename_pattern_name = Entry(frame_filename_pattern_frame, width=16,
                                        borderwidth=1, font=("Arial", 8))
    frame_filename_pattern_name.pack(side=LEFT, anchor=W)
    frame_filename_pattern_name.delete(0, 'end')
    frame_filename_pattern_name.insert('end', FrameFilenameInputPattern)
    frame_filename_pattern_btn = Button(
        frame_filename_pattern_frame,
        text='Set', width=2, height=1,
        command=set_frame_pattern_filename_folder,
        activebackground='green',
        activeforeground='white',
        wraplength=80, font=("Arial", 8))
    frame_filename_pattern_btn.pack(side=LEFT)

    # Define post-processing area
    postprocessing_frame = LabelFrame(regular_frame,
                                      text='Frame post-processing',
                                      width=50, height=8)
    postprocessing_frame.pack(side=TOP, padx=2, pady=2, anchor=W)
    postprocessing_row = 0

    # Check box to select start from current frame
    from_current_frame = tk.BooleanVar(value=StartFromCurrentFrame)
    from_current_frame_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Start from current frame',
        variable=from_current_frame, onvalue=True, offvalue=False,
        command=from_current_frame_selection, width=20)
    from_current_frame_checkbox.grid(row=postprocessing_row, column=0,
                                     columnspan=2, sticky=W)
    postprocessing_row += 1

    # Spinbox to select number of frames to process
    frames_to_encode_label = tk.Label(postprocessing_frame,
                                      text='Number of frames to encode:',
                                      width=25)
    frames_to_encode_label.grid(row=postprocessing_row, column=0,
                                columnspan=2, sticky=W)
    frames_to_encode = tk.StringVar(value=str(FramesToEncode))
    frames_to_encode_selection_aux = postprocessing_frame.register(
        frames_to_encode_selection)
    frames_to_encode_spinbox = tk.Spinbox(
        postprocessing_frame,
        command=(frames_to_encode_selection_aux, '%d'), width=8,
        textvariable=frames_to_encode, from_=0, to=50000)
    frames_to_encode_spinbox.grid(row=postprocessing_row, column=2, sticky=W)
    frames_to_encode_selection('down')
    postprocessing_row += 1

    # Checkbox to select extended hole search area (for films with bad synchro)
    extended_stabilization = tk.BooleanVar(value=ExtendedStabilization)
    extended_stabilization_checkbox = tk.Checkbutton(
        postprocessing_frame,
        text='Extended stabilization (bad sync films)',
        variable=extended_stabilization, onvalue=True, offvalue=False,
        command=extended_stabilization_selection, width=32)
    extended_stabilization_checkbox.grid(row=postprocessing_row, column=0,
                                         columnspan=3, sticky=W)
    extended_stabilization_checkbox.config(state=DISABLED)
    postprocessing_row += 1

    # Check box to do cropping or not
    perform_cropping = tk.BooleanVar(value=PerformCropping)
    perform_cropping_checkbox = tk.Checkbutton(
        postprocessing_frame, text='Crop', variable=perform_cropping,
        onvalue=True, offvalue=False, command=perform_cropping_selection,
        width=4)
    perform_cropping_checkbox.grid(row=postprocessing_row, column=0, sticky=W)
    perform_cropping_checkbox.config(state=DISABLED)
    cropping_btn = Button(postprocessing_frame, text='Image crop area',
                          width=24, height=1, command=select_cropping_area,
                          activebackground='green', activeforeground='white',
                          wraplength=120, font=("Arial", 8))
    cropping_btn.grid(row=postprocessing_row, column=1, columnspan=2, sticky=W)
    postprocessing_row += 1

    # Check box to generate video or not
    generate_video = tk.BooleanVar(value=GenerateVideo)
    generate_video_checkbox = tk.Checkbutton(postprocessing_frame,
                                             text='Video',
                                             variable=generate_video,
                                             onvalue=True, offvalue=False,
                                             command=generate_video_selection,
                                             width=5)
    generate_video_checkbox.grid(row=postprocessing_row, column=0, sticky=W)
    generate_video_checkbox.config(state=NORMAL if ffmpeg_installed and
                                   PerformCropping else DISABLED)
    # Check box to skip frame regeneration
    skip_frame_regeneration = tk.BooleanVar(value=False)
    skip_frame_regeneration_cb = tk.Checkbutton(
        postprocessing_frame, text='Skip Frame regeneration',
        variable=skip_frame_regeneration, onvalue=True, offvalue=False,
        width=20)
    skip_frame_regeneration_cb.grid(row=postprocessing_row, column=1,
                                    columnspan=2, sticky=W)
    skip_frame_regeneration_cb.config(state=NORMAL if ffmpeg_installed
                                      else DISABLED)
    postprocessing_row += 1

    # Video filename
    video_filename_label = Label(postprocessing_frame, text='Video filename:',
                                 font=("Arial", 8))
    video_filename_label.grid(row=postprocessing_row, column=0, sticky=W)
    video_filename_name = Entry(postprocessing_frame, width=32, borderwidth=1,
                                font=("Arial", 8))
    video_filename_name.grid(row=postprocessing_row, column=1, columnspan=2,
                             sticky=W)
    video_filename_name.delete(0, 'end')
    video_filename_name.insert('end', TargetVideoFilename)
    video_filename_name.config(state=DISABLED)
    postprocessing_row += 1

    # Drop down to select FPS
    # Dropdown menu options
    fps_list = [
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
    video_fps_frame = Frame(postprocessing_frame)
    video_fps_frame.grid(row=postprocessing_row, column=0, sticky=W)
    video_fps_label = Label(video_fps_frame, text='FPS:')
    video_fps_label.pack(side=LEFT, anchor=W)
    video_fps_label.config(state=DISABLED)
    video_fps_dropdown = OptionMenu(video_fps_frame,
                                    video_fps_dropdown_selected, *fps_list,
                                    command=set_fps)
    video_fps_dropdown.pack(side=LEFT, anchor=E)
    video_fps_dropdown.config(state=DISABLED)
    ffmpeg_preset_frame = Frame(postprocessing_frame)
    ffmpeg_preset_frame.grid(row=postprocessing_row, column=1, columnspan=2,
                             sticky=W)
    ffmpeg_preset = StringVar()
    ffmpeg_preset_rb1 = Radiobutton(ffmpeg_preset_frame,
                                    text="Best quality (slow)",
                                    variable=ffmpeg_preset, value='veryslow')
    ffmpeg_preset_rb1.pack(side=TOP, anchor=W)
    ffmpeg_preset_rb1.config(state=DISABLED)
    ffmpeg_preset_rb2 = Radiobutton(ffmpeg_preset_frame, text="Medium",
                                    variable=ffmpeg_preset, value='medium')
    ffmpeg_preset_rb2.pack(side=TOP, anchor=W)
    ffmpeg_preset_rb2.config(state=DISABLED)
    ffmpeg_preset_rb3 = Radiobutton(ffmpeg_preset_frame,
                                    text="Fast (low quality)",
                                    variable=ffmpeg_preset, value='veryfast')
    ffmpeg_preset_rb3.pack(side=TOP, anchor=W)
    ffmpeg_preset_rb3.config(state=DISABLED)
    ffmpeg_preset.set('medium')
    postprocessing_row += 1

    postprocessing_bottom_frame = Frame(postprocessing_frame, width=30)
    postprocessing_bottom_frame.grid(row=postprocessing_row, column=0)

    # Set focus tab order
    AfterScan_widgets = [frame_slider,
                         Go_btn,
                         Exit_btn,
                         folder_frame_source_dir,
                         source_folder_btn,
                         folder_frame_target_dir,
                         target_folder_btn,
                         frame_filename_pattern_name,
                         frame_filename_pattern_btn,
                         from_current_frame_checkbox,
                         frames_to_encode_spinbox,
                         extended_stabilization_checkbox,
                         perform_cropping_checkbox,
                         cropping_btn,
                         generate_video_checkbox,
                         skip_frame_regeneration_cb,
                         video_filename_name,
                         video_fps_dropdown,
                         ffmpeg_preset_rb1,
                         ffmpeg_preset_rb2,
                         ffmpeg_preset_rb3]
    for aw in AfterScan_widgets:
        aw.lift()
    frame_slider.focus()

    if ExpertMode:
        # Frame for expert widgets
        expert_frame = Frame(win, width=900, height=100)
        expert_frame.grid(row=1, column=0, padx=5, pady=5, sticky=W)

        # Stabilization details (in non-expert mode default values are OK)
        # Pattern file selection
        stabilize_frame = LabelFrame(expert_frame, text='Stabilize details',
                                     width=26, height=8, font=("Arial", 7))
        stabilize_frame.pack(side=LEFT, anchor=N)
        pattern_filename = Entry(stabilize_frame, width=38, borderwidth=1,
                                 font=("Arial", 7))
        # Only if file does exists, add it to edit box
        if os.path.isfile(PatternFilename):
            pattern_filename.delete(0, 'end')
            pattern_filename.insert('end', PatternFilename)
        pattern_filename.grid(row=0, column=0, columnspan=2, sticky=W)
        pattern_filename_btn = Button(stabilize_frame, text='Pattern', width=6,
                                      height=1, command=get_pattern_file,
                                      activebackground='green',
                                      activeforeground='white', wraplength=80,
                                      font=("Arial", 7))
        pattern_filename_btn.grid(row=0, column=2, sticky=W)

        # Check box to do stabilization or not
        perform_stabilization = tk.BooleanVar(value=PerformStabilization)
        perform_stabilization_checkbox = tk.Checkbutton(
            stabilize_frame, text='Stabilize', variable=perform_stabilization,
            onvalue=True, offvalue=False, width=7, font=("Arial", 7),
            command=perform_stabilization_selection)
        perform_stabilization_checkbox.grid(row=1, column=0, sticky=W)
        # Initially the stabilization checkbox was disabled by default, until
        # the area was defined. However, since the default values calculated by
        # the app are good enough, we remove this dependency. Furthermore, the
        # whole stabilizatino settings will be moved to the expert area (for
        # special cases only)
        stabilization_btn = Button(stabilize_frame,
                                   text='Sprocket hole search area',
                                   width=34, height=1, font=("Arial", 7),
                                   command=select_stabilization_area,
                                   activebackground='green',
                                   activeforeground='white', wraplength=120)
        stabilization_btn.grid(row=1, column=1, columnspan=2, sticky=W)

        # Create canvas to display pattern image
        pattern_canvas = Canvas(stabilize_frame, width=22, height=22,
                                bg='black')
        pattern_canvas.grid(row=0, column=3, sticky=N, padx=5)
        display_pattern(PatternFilename)


def main(argv):
    global LogLevel, LoggingMode
    global s8_template
    global VideoEncodingDoNotWarnAgain
    global ExpertMode
    global FfmpegBinName
    global IsWindows, IsLinux
    global PatternFilename

    LoggingMode = "warning"

    s8_template = cv2.imread(PatternFilename, 0)

    opts, args = getopt.getopt(argv, "hel:")

    for opt, arg in opts:
        if opt == '-l':
            LoggingMode = arg
        elif opt == '-e':
            ExpertMode = True
        elif opt == '-h':
            print("AfterScan")
            print("  -l <log mode>  Set log level:")
            print("      <log mode> = [DEBUG|INFO|WARNING|ERROR]")
            print("  -e             Enable expert mode")
            exit()

    LogLevel = getattr(logging, LoggingMode.upper(), None)
    if not isinstance(LogLevel, int):
        raise ValueError('Invalid log level: %s' % LogLevel)

    afterscan_postprod_init()

    ffmpeg_installed = False
    if platform.system() == 'Windows':
        IsWindows = True
        FfmpegBinName = 'C:\\ffmpeg\\bin\\ffmpeg.exe'
        AltFfmpegBinName = 'ffmpeg.exe'
    elif platform.system() == 'Linux':
        IsLinux = True
        FfmpegBinName = 'ffmpeg'
        AltFfmpegBinName = 'ffmpeg'

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

    load_config_data()

    # Display video encoding warnign if not previously declined
    if not VideoEncodingDoNotWarnAgain:
        video_encoding_warning()
    # Disable a few items that shoul dbe not operational withous source folder
    if len(SourceDir) == 0:
        Go_btn.config(state=DISABLED)
        cropping_btn.config(state=DISABLED)
        frame_slider.config(state=DISABLED)

    init_display()

    # Main Loop
    win.mainloop()  # running the loop that works as a trigger


if __name__ == '__main__':
    main(sys.argv[1:])
