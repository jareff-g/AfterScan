#!/usr/bin/env python
"""
frame_list - Handles AfterScan frame lists and related status tracking.

Licensed under a MIT LICENSE.

More info in README.md file
"""

import logging
from afterscan_config import AfterScanConfig
from afterscan_status import AfterScanStatus
import os
import cv2

class FrameList:
    """Class to manage frame lists and related status tracking for AfterScan."""

    afterscan_status: AfterScanStatus
    general_config: AfterScanConfig

    # Film frames (in/out) file vars
    frame_input_filename_pattern_list_jpg: str = "picture-?????.jpg"
    hdr_input_filename_pattern_list_jpg: str = "picture-?????.3.jpg"   # In HDR mode, use 3rd frame as guide
    legacy_hdr_input_filename_pattern_list_jpg: str = "hdrpic-?????.3.jpg"   # In legacy HDR mode, use 3rd frame as guide
    frame_input_filename_pattern_list_png: str = "picture-?????.png"
    hdr_input_filename_pattern_list_png: str = "picture-?????.3.png"   # In HDR mode, use 3rd frame as guide
    legacy_hdr_input_filename_pattern_list_png: str = "hdrpic-?????.3.png"   # In legacy HDR mode, use 3rd frame as guide
    frame_input_filename_pattern: str = "picture-%05d.%s"   # HDR frames using standard filename (2/12/2023)
    frame_hdr_input_filename_pattern: str = "picture-%05d.%1d.%s"   # HDR frames using standard filename (2/12/2023)
    frame_output_filename_pattern: str = "picture_out-%05d.%s"
    title_output_filename_pattern: str = "picture_out(title)-%05d.%s"
    frame_output_filename_pattern_for_ffmpeg: str = "picture_out-%05d."
    title_output_filename_pattern_for_ffmpeg: str = "picture_out(title)-%05d."
    frame_check_output_filename_pattern: str = "picture_out-?????.%s"  # Req. for ffmpeg gen.
    hdr_set_input_filename_pattern: str = "hdrpic-%05d.%1d.%s"   # Req. to fetch each HDR frame set
    hdr_files_only: bool = False   # No HDR by default. Updated when building file list from input folder
    merge_mertens = None
    align_mtb = None

    source_dir: str = ''
    target_dir: str = ''
    source_dir_file_list: list = []
    target_dir_file_list: list = []
    film_type: str = 'S8'
    frame_fill_type: str = 'fake'
    file_type_out: str = 'jpg'


    def __init__(self, general_config: AfterScanConfig, afterscan_status: AfterScanStatus):
        self.general_config = general_config
        self.afterscan_status = afterscan_status
        self.frames = []  # List of frame file paths
        self.current_index = 0  # Current frame index

    def set_source_dir(self, source_dir):
        self.source_dir = source_dir

    def set_target_dir(self, target_dir):
        self.target_dir = target_dir

    def load_current_frame_image(self):
        # If HDR mode, pick the lightest frame to select rectangle
        file3 = os.path.join(self.general_config.source_dir, self.frame_hdr_input_filename_pattern % (self.afterscan_status.current_frame + 1, 2, self.afterscan_status.file_type))
        if os.path.isfile(file3):  # If hdr frames exist, add them
            file = file3
        else:
            file = self.source_dir_file_list[self.afterscan_status.current_frame]
        return cv2.imread(file, cv2.IMREAD_UNCHANGED)

    def get_source_dir_file_list(self):
        global frame_width, frame_height
        global SourceDirFileList
        global CurrentFrame
        """ delete_this
        global first_absolute_frame, last_absolute_frame
        global CropBottomRight
        """
        global frame_slider
        global area_select_image_factor, screen_height
        global frames_target_dir
        global HdrFilesOnly
        global file_type, file_type_out
        global FrameSync_Images_Factor
        global frame_height, frame_width
        global general_config, project_config_entry

        if not os.path.isdir(general_config.source_dir):
            tk.messagebox.showerror("Error!",
                                    "Source folder does not exist. "
                                    "Please specify a different one and try again")
            frames_target_dir.delete(0, 'end')
            return 0

        # Try first with standard scan filename template
        SourceDirFileList_jpg = list(glob(os.path.join(
            general_config.source_dir,
            FrameInputFilenamePatternList_jpg)))
        if len(SourceDirFileList_jpg) == 0:     # Only try to read if there are no JPG at all
            SourceDirFileList_png = list(glob(os.path.join(
                general_config.source_dir,
                FrameInputFilenamePatternList_png)))
            SourceDirFileList = sorted(SourceDirFileList_png)
            file_type_out = 'png'  # If we have png files in the input, we default to png for the output
        else:
            SourceDirFileList = sorted(SourceDirFileList_jpg)
            file_type_out = 'jpg'

        SourceDirHdrFileList_jpg = list(glob(os.path.join(
            general_config.source_dir,
            HdrInputFilenamePatternList_jpg)))
        SourceDirHdrFileList_png = list(glob(os.path.join(
            general_config.source_dir,
            HdrInputFilenamePatternList_png)))
        SourceDirHdrFileList = sorted(SourceDirHdrFileList_jpg + SourceDirHdrFileList_png)
        if len(SourceDirHdrFileList_png) != 0:
            file_type_out = 'png'   # If we have png files in the input, we default to png for the output
        elif len(SourceDirHdrFileList_jpg) != 0:
            file_type_out = 'jpg'

        SourceDirLegacyHdrFileList_jpg = list(glob(os.path.join(
            general_config.source_dir,
            LegacyHdrInputFilenamePatternList_jpg)))
        SourceDirLegacyHdrFileList_png = list(glob(os.path.join(
            general_config.source_dir,
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
            return 0
        else:
            HdrFilesOnly = NumLegacyHdrFiles > NumFiles

        # Sanity check for CurrentFrame
        if CurrentFrame >= len(SourceDirFileList):
            CurrentFrame = 0

        # Extract frame number from filename
        temp = re.findall(r'\d+', os.path.basename(SourceDirFileList[0]))
        numbers = list(map(int, temp))
        project_config_entry.first_absolute_frame = numbers[0]
        project_config_entry.last_absolute_frame = project_config_entry.first_absolute_frame + len(SourceDirFileList)-1
        frame_slider.config(from_=0, to=len(SourceDirFileList)-1)
        refresh_current_frame_ui_info(CurrentFrame, project_config_entry.first_absolute_frame)

        # In order to determine template dimensons, no not take the first frame, as often
        # it is not so good. Take a frame 10% ahead in the set
        sample_frame = int(len(SourceDirFileList) * 0.1)
        aux_image = cv2.imread(SourceDirFileList[sample_frame], cv2.IMREAD_UNCHANGED)
        # Set frame dimensions in global variable, for use everywhere
        frame_width = aux_image.shape[1]
        frame_height = aux_image.shape[0]
        template_list.set_scale(aux_image)    # frame_width set by get_source_dir_file_list

        return len(SourceDirFileList)


def get_target_dir_file_list(self):

    if not os.path.isdir(self.target_dir):
        return

    self.target_dir_file_list = sorted(list(glob(os.path.join(
        self.target_dir, frame_check_output_filename_pattern % self.file_type_out))))
    logging.debug(f"{len(self.target_dir_file_list)} files read in target folder {self.target_dir}.")
