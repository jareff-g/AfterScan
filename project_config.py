#!/usr/bin/env python
"""
project_config - Handles AfterScan projects configuration and metadata.

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "project_config"
__version__ = "1.0.0"
__data_version__ = "1.0"
__date__ = "2025-11-24"
__version_highlight__ = "Isolate AfterScan project configuration in dedicated class"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import json
from dataclasses import dataclass, field, asdict, fields
import os
from typing import List, Optional, Dict, Any
from afterscan_template_manager import Template, TemplateList
import copy
import logging

@dataclass
class ProjectHeader:
    code_version: str = "1.0"
    data_version: str = "1.0"
    save_date: str = "" # Set before saving

@dataclass
class ProjectConfigEntry:
    source_dir: str = ""
    target_dir: str = ""
    video_target_dir: str = ""
    film_type: str = "S8"
    perform_cropping: bool = False
    perform_sharpness: bool = False
    perform_denoise: bool = False
    perform_gamma_correction: bool = False
    generate_video: bool = False
    video_fps: str = "18"
    current_frame: int = 0
    encode_all_frames: bool = True
    frames_to_encode: str = "All"
    stabilization_threshold: float = 220.0
    perform_stabilization: bool = False
    skip_frame_regeneration: bool = False
    video_filename: str = ""
    video_title: str = ""
    fill_borders: bool = False
    fill_borders_thickness: int = 5
    fill_borders_mode: str = "smear"
    frame_fill_type: str = "none"
    frame_from: int = 0
    frame_to: int = 0
    low_contrast_custom_template: bool = False
    extended_stabilization: bool = False
    stabilization_shift_x: int = 0
    stabilization_shift_y: int = 0
    rotation_angle: str = "0.0"
    custom_template_defined: bool = False
    custom_template_expected_pos: List[int] = field(default_factory=lambda: (0, 0))
    custom_template_filename: str = ""
    gamma_correction_value: float = 1.0
    crop_rectangle: List[List[int]] = field(default_factory=lambda: [[0, 0], [0, 0]])
    force_4_3: bool = False
    force_16_9: bool = False
    ffmpeg_preset: str = "veryfast"
    perform_rotation: bool = False
    video_resolution: str = ""
    current_bad_frame_index: int = -1

    """
    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectConfigEntry':
        return cls(**data)
    """

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectConfigEntry':
        """
        Create an instance of ProjectConfigEntry from a dictionary,
        filtering out any invalid/legacy keys that might exist in the JSON file.
        """
        # 1. Get the names of all valid fields defined in the class
        #    This acts as the expected "schema".
        valid_fields = {f.name for f in fields(cls)}
        
        # 2. Filter the input dictionary
        #    We only keep key-value pairs where the key exists in the schema.
        filtered_data = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }

        # 3. Destructure the filtered dictionary, now safe, into the constructor.
        #    If keys are missing, dataclasses will use the default values defined.
        return cls(**filtered_data)

    def copy(self) -> 'ProjectConfigEntry':
        """
        Returns a deep copy of the current ProjectConfigEntry instance.
        The new instance is completely independent of the original, including 
        mutable fields (like job_list) which are fully duplicated.
        """
        return copy.deepcopy(self)

    def log_fields(self):
        """
        Converts the current dataclass instance to a dictionary and logs 
        all its contents at the DEBUG level.
        
        This method replaces your previous external loop.
        """
        # 1. Use asdict(self) to convert the instance into a standard dictionary
        project_config_dict = asdict(self)
        
        logging.debug("--- Debugging ProjectConfigEntry Contents ---")
        
        # 2. Iterate over the resulting dictionary items
        for key, value in project_config_dict.items():
            # Log key and value
            logging.debug("%s = %s", key, str(value))
            
        logging.debug("----------------------------------------------")


@dataclass
class ProjectRegistry:
    header: ProjectHeader = field(default_factory=ProjectHeader)
    
    # Stores all individual projects, keyed by their folder path (string)
    projects: Dict[str, ProjectConfigEntry] = field(default_factory=dict)

    @staticmethod
    def convert_keys_to_snake_case(camel_dict: dict) -> dict:
        """Recursively converts keys from CamelCase to snake_case."""
        import re
        snake_dict = {}
        
        for key, value in camel_dict.items():
            # Regex to insert an underscore before any capital letter followed by a lowercase letter
            snake_key = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
            
            # Recursively handle nested dictionaries/lists (important if project config is deep)
            if isinstance(value, dict):
                value = ProjectRegistry.convert_keys_to_snake_case(value)
            elif isinstance(value, list):
                value = [ProjectRegistry.convert_keys_to_snake_case(item) if isinstance(item, dict) else item for item in value]
                
            snake_dict[snake_key] = value
            
        return snake_dict

    # --- The Custom Methods ---
    @classmethod
    def from_json(cls, json_path: str):
        """
        Load configuration from a JSON file, safely handling missing, 
        empty, or corrupted files.
        """
        
        # 1. Check if the file exists
        if not os.path.exists(json_path):
            print(f"Warning: Project config file '{json_path}' not found. Returning default project configuration.")
            return cls() # Returns instance with default values
            
        # 2. Check if the file is empty (size 0)
        if os.path.getsize(json_path) == 0:
            print(f"Warning: Project config file '{json_path}' is empty. Returning default project configuration.")
            return cls() 
        # 3. Attempt to load the JSON content
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON in '{json_path}': {e}. Returning default project configuration.")
            return cls()

        # --- Step 4.1: Check for the NEW structure ---
        if "header" in data or "projects" in data:
            print("Loading NEW project file structure.")
            
            # New structure: Data is already separated by keys
            header_data = data.get("header", {})
            projects_data = data.get("projects", {})
            
        # --- Step 4.2: Handle the OLD (Anonymous) structure ---
        else:
            # Loading OLD (anonymous) project file structure. UPGRADING
            print("Debugging: Type of 'data' before popping:", type(data)) # <-- ADD THIS LINE            
            # 4.2.1. Extract the Header data using the existing snake_case keys (using pop to remove them)
            header_data = {
                "code_version": data[0].pop("code_version"),
                "data_version": data[0].pop("data_version"),
                "save_date": data[0].pop("save_date")
            }
            
            # 4.2.2. The remainder of the dictionary is the anonymous project data
            projects_data = data[1]

            # projects_data now holds the remaining anonymous dict: {path: {CamelCaseConfig}, ...}
            temp_projects_data = {}
            
            # 4.2.3. Iterate through each project's data dictionary for conversion
            for path, project_dict_camel_case in projects_data.items():
                # Apply the conversion function to the project's configuration dictionary
                project_dict_snake_case = cls.convert_keys_to_snake_case(project_dict_camel_case)
                temp_projects_data[path] = project_dict_snake_case
                
            projects_data = temp_projects_data

            """ Code for manual conversion from CamelCase to snake_case, in case it will be needed (deleted otherwise -> delete_this)
            # --- Compatibility and Deserialization Logic ---
            # 4. Handle Old Key Names (your original compatibility logic goes here)
            if 'source_dir' not in data and 'SourceDir' in data:
                data['source_dir'] = data.pop('SourceDir')
            if 'target_dir' not in data and 'TargetDir' in data:
                data['target_dir'] = data.pop('TargetDir')
            if 'video_target_dir' not in data and 'VideoTargetDir' in data:
                data['video_target_dir'] = data.pop('VideoTargetDir')
            if 'film_type' not in data and 'FilmType' in data:
                data['film_type'] = data.pop('FilmType')
            if 'perform_cropping' not in data and 'PerformCropping' in data:
                data['perform_cropping'] = data.pop('PerformCropping')
            if 'perform_sharpness' not in data and 'PerformSharpness' in data:
                data['perform_sharpness'] = data.pop('PerformSharpness')
            if 'perform_denoise' not in data and 'PerformDenoise' in data:
                data['perform_denoise'] = data.pop('PerformDenoise')
            if 'perform_gamma_correction' not in data and 'PerformGammaCorrection' in data:
                data['perform_gamma_correction'] = data.pop('PerformGammaCorrection')
            if 'generate_video' not in data and 'GenerateVideo' in data:
                data['generate_video'] = data.pop('GenerateVideo')
            if 'video_fps' not in data and 'VideoFps' in data:
                data['video_fps'] = data.pop('VideoFps')
            if 'current_frame' not in data and 'CurrentFrame' in data:
                data['current_frame'] = data.pop('CurrentFrame')
            if 'encode_all_frames' not in data and 'EncodeAllFrames' in data:
                data['encode_all_frames'] = data.pop('EncodeAllFrames')
            if 'frames_to_encode' not in data and 'FramesToEncode' in data:
                data['frames_to_encode'] = data.pop('FramesToEncode')
            if 'stabilization_threshold' not in data and 'StabilizationThreshold' in data:
                data['stabilization_threshold'] = data.pop('StabilizationThreshold')
            if 'perform_stabilization' not in data and 'PerformStabilization' in data:
                data['perform_stabilization'] = data.pop('PerformStabilization')
            if 'video_filename' not in data and 'VideoFilename' in data:
                data['video_filename'] = data.pop('VideoFilename')
            if 'video_title' not in data and 'VideoTitle' in data:
                data['video_title'] = data.pop('VideoTitle')
            if 'fill_borders' not in data and 'FillBorders' in data:
                data['fill_borders'] = data.pop('FillBorders')
            if 'fill_borders_thickness' not in data and 'FillBordersThickness' in data:
                data['fill_borders_thickness'] = data.pop('FillBordersThickness')
            if 'fill_borders_mode' not in data and 'FillBordersMode' in data:
                data['fill_borders_mode'] = data.pop('FillBordersMode')
            if 'frame_fill_type' not in data and 'FrameFillType' in data:
                data['frame_fill_type'] = data.pop('FrameFillType')
            if 'frame_from' not in data and 'FrameFrom' in data:
                data['frame_from'] = data.pop('FrameFrom')
            if 'frame_to' not in data and 'FrameTo' in data:
                data['frame_to'] = data.pop('FrameTo')
            if 'low_contrast_custom_template' not in data and 'LowContrastCustomTemplate' in data:
                data['low_contrast_custom_template'] = data.pop('LowContrastCustomTemplate')
            if 'extended_stabilization' not in data and 'ExtendedStabilization' in data:
                data['extended_stabilization'] = data.pop('ExtendedStabilization')
            if 'stabilization_shift_x' not in data and 'StabilizationShiftX' in data:
                data['stabilization_shift_x'] = data.pop('StabilizationShiftX')
            if 'stabilization_shift_y' not in data and 'StabilizationShiftY' in data:
                data['stabilization_shift_y'] = data.pop('StabilizationShiftY')
            if 'rotation_angle' not in data and 'RotationAngle' in data:
                data['rotation_angle'] = data.pop('RotationAngle')
            if 'custom_template_defined' not in data and 'CustomTemplateDefined' in data:
                data['custom_template_defined'] = data.pop('CustomTemplateDefined')
            if 'custom_template_expected_pos' not in data and 'CustomTemplateExpectedPos' in data:
                data['custom_template_expected_pos'] = data.pop('CustomTemplateExpectedPos')
            if 'custom_template_filename' not in data and 'CustomTemplateFilename' in data:
                data['custom_template_filename'] = data.pop('CustomTemplateFilename')
            if 'gamma_correction_value' not in data and 'GammaCorrectionValue' in data:
                data['gamma_correction_value'] = data.pop('GammaCorrectionValue')
            if 'crop_rectangle' not in data and 'CropRectangle' in data:
                data['crop_rectangle'] = data.pop('CropRectangle')
            if 'force_4_3' not in data and 'Force_4/3' in data:
                data['force_4_3'] = data.pop('Force_4/3')
            if 'force_16_9' not in data and 'Force_16/9' in data:
                data['force_16_9'] = data.pop('Force_16/9')
            if 'ffmpeg_preset' not in data and 'FFmpegPreset' in data:
                data['ffmpeg_preset'] = data.pop('FFmpegPreset')
            if 'perform_rotation' not in data and 'PerformRotation' in data:
                data['perform_rotation'] = data.pop('PerformRotation')
            if 'video_resolution' not in data and 'VideoResolution' in data:
                data['video_resolution'] = data.pop('VideoResolution')
            if 'current_bad_frame_index' not in data and 'CurrentBadFrameIndex' in data:
                data['current_bad_frame_index'] = data.pop('CurrentBadFrameIndex')
            """
        # 5. Tolerant Deserialization (using dict.get for safety)
        # We use dict.get(key, default_value) to avoid errors if the key is missing
        """ Code for manual conversion from CamelCase to snake_case, in case it will be needed (deleted otherwise -> delete_this)
        return cls(
            source_dir=data.get('source_dir', ""),
            target_dir=data.get('target_dir', ""),
            video_target_dir=data.get('video_target_dir', ""),
            film_type=data.get('film_type', "S8"),
            perform_cropping=data.get('perform_cropping', False),
            perform_sharpness=data.get('perform_sharpness', False),
            perform_denoise=data.get('perform_denoise', False),
            generate_video=data.get('generate_video', False),
            video_fps=data.get('video_fps', "18"),
            current_frame=data.get('current_frame', 0),
            encode_all_frames=data.get('encode_all_frames', True),
            frames_to_encode=data.get('frames_to_encode', "All"),
            stabilization_threshold=data.get('stabilization_threshold', 220.0),
            perform_stabilization=data.get('perform_stabilization', False),
            skip_frame_regeneration=data.get('skip_frame_regeneration', False),
            video_filename=data.get('video_filename', ""),
            video_title=data.get('video_title', ""),
            fill_borders=data.get('fill_borders', False),
            fill_borders_thickness=data.get('fill_borders_thickness', 5),
            fill_borders_mode=data.get('fill_borders_mode', "smear"),
            frame_fill_type=data.get('frame_fill_type', "none"),
            frame_from=data.get('frame_from', 0),
            frame_to=data.get('frame_to', 0),
            low_contrast_custom_template=data.get('low_contrast_custom_template', False),
            extended_stabilization=data.get('extended_stabilization', False),
            stabilization_shift_x=data.get('stabilization_shift_x', 0),
            stabilization_shift_y=data.get('stabilization_shift_y', 0),
            rotation_angle=data.get('rotation_angle', "0.0"),
            custom_template_defined=data.get('custom_template_defined', False),
            custom_template_expected_pos=data.get('custom_template_expected_pos', (0, 0)),
            custom_template_filename=data.get('custom_template_filename', ""),
            gamma_correction_value=data.get('gamma_correction_value', 1.0),
            crop_rectangle=data.get('crop_rectangle', [[0, 0], [0, 0]]),
            force_4_3=data.get('force_4_3', False),
            force_16_9=data.get('force_16_9', False),
            ffmpeg_preset=data.get('ffmpeg_preset', "veryfast"),
            perform_rotation=data.get('perform_rotation', False),
            video_resolution=data.get('video_resolution', ""),
            current_bad_frame_index=data.get('current_bad_frame_index', -1)
        )
        """
        # --- Step 6: Deserialize and Return (Common Logic) ---

        # 1. The dictionaries in projects_data now have snake_case keys.
        projects_dict = {}
        for path, project_data in projects_data.items():
            # ProjectConfigEntry.from_dict expects snake_case keys
            projects_dict[path] = ProjectConfigEntry.from_dict(project_data) 
            
        return cls(header=header_data, projects=projects_dict)

    def to_json(self, json_path: str):
        """
        Serializes the ProjectRegistry instance to a JSON file.
        This method permanently upgrades the file format to use the 'header' and 
        'projects' keys.
        """
        # 1. Convert the entire nested structure (header and projects) to a dictionary.
        # This will produce the new, structured format.
        data_dict = asdict(self)
        
        # 2. Sort the keys for consistency and readability.
        sorted_data = self.sort_nested_json(data_dict) 
        
        # 3. Write the sorted dictionary to the JSON file, ensuring data integrity.
        # We write to a temporary file first to prevent leaving an empty file 
        # if the write operation fails (similar to what happened before).
        temp_path = json_path + ".tmp"
        
        try:
            with open(temp_path, 'w') as f:
                json.dump(sorted_data, f, indent=4) 
            
            # 4. If successful, replace the original file with the temporary one.
            os.replace(temp_path, json_path)
            print(f"Project settings saved successfully to: {json_path}")

        except Exception as e:
            print(f"ERROR: Failed to save project settings to {json_path}. Exception: {e}")
            # Clean up the temporary file if it still exists
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get_active_config(self, current_source_dir: str) -> 'ProjectConfigEntry':
        """
        Retrieves the configuration entry matching the current source directory 
        from the registry, or returns a default configuration if not found.
        """
        
        # 1. Check if the current source directory exists as a key in the entries
        if current_source_dir in self.projects:
            logging.debug(f"Configuration found for directory: {current_source_dir}")
            
            # 2. Extract the stored instance
            stored_entry = self.projects[current_source_dir]
            
            # 3. Return a deep copy of the stored entry. 
            #    This is CRITICAL: it ensures any modifications to the active_config 
            #    do not change the data stored in the project_registry until saved.
            active_config = stored_entry.copy()
            
        else:
            logging.info(f"No existing configuration found for '{current_source_dir}'. Creating default entry.")
            
            # If no entry is found, create a brand new default instance.
            active_config = ProjectConfigEntry() 
            
            # Optionally, you might initialize the project_name here:
            # active_config.project_name = current_source_dir.split('/')[-1] # Example
            
        return active_config