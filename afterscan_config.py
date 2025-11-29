#!/usr/bin/env python
"""
afterscan_config - Handles AfterScan configuration and metadata.

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "afterscan_config"
__version__ = "1.0.0"
__data_version__ = "1.0"
__date__ = "2025-11-24"
__version_highlight__ = "Isolate AfterScan configuration in dedicated class"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import json
from dataclasses import dataclass, field, asdict
import os
from typing import Optional
from afterscan_template_manager import Template, TemplateList

@dataclass
class AfterScanConfig:
    # Atributos antiguos
    anonymous_uuid: str = ""
    enable_popups: bool = False
    enable_soundtrack: bool = False
    ffmpeg_hqdn3d: str = "8:6:4:3"
    ffmpeg_bin_name: str = "ffmpeg"
    general_config_date: str = ""
    detect_minor_mismatches: bool = False
    job_list_filename: str = ""
    default_job_list_filename: str = ""
    default_job_list_filename_legacy: str = ""
    last_consent_date: str = ""
    left_stripe_width_proportion: float = 0.25
    popup_pos: str = ""
    precise_template_match: bool = False
    source_dir: str = ""
    template_popup_window_pos: str = ""
    user_consent: str = "yes"
    version: str = ""
    window_pos: str = ""
    script_dir: str = ""

    # --- Calculated Path Attributes (New) ---
    # NOTE: You don't need 'general_config_filename' here if you pass it into the method,
    # but defining it here is cleaner if you want to store it in the instance.
    general_config_filename: str = "" 
    
    project_settings_filename: str = ""
    project_settings_backup_filename: str = ""
    project_config_basename: str = "AfterScan-project.json" # Static basename
    project_config_filename: str = ""
    
    temp_dir: str = ""
    logs_dir: str = ""
    resources_dir: str = ""
    soundtrack_file_path: str = ""
    
    hole_template_filename_r8: str = ""
    hole_template_filename_s8: str = ""
    hole_template_filename_custom: str = ""
    hole_template_filename_corner: str = ""
    hole_template_filename_bw: str = ""
    hole_template_filename_wb: str = ""
    hole_template_filename: str = ""
    
    # --- Calculated State Attributes (New) ---
    copy_templates_from_temp: bool = False
    sound_file_available: bool = False
    project_config_from_file: bool = True
    project_name: str = "No Project"
    job_list_hash: Optional[str] = None # None is a fine default
    template_list: list["Template"] = None # None is a fine default. Template set as string to avoid circular import dependency
    left_stripe_width_pixels: int = 100

    # --- Retrieve config from json file keeping backward compatibility with legacy names ---
    @classmethod
    def from_json(cls, json_path: str):
        """
        Load configuration from a JSON file, safely handling missing, 
        empty, or corrupted files.
        """
        
        # 1. Check if the file exists
        if not os.path.exists(json_path):
            print(f"Warning: Config file '{json_path}' not found. Returning default configuration.")
            return cls() # Returns instance with default values
            
        # 2. Check if the file is empty (size 0)
        if os.path.getsize(json_path) == 0:
            print(f"Warning: Config file '{json_path}' is empty. Returning default configuration.")
            return cls() 
        # 3. Attempt to load the JSON content
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON in '{json_path}': {e}. Returning default configuration.")
            return cls()

        # --- Compatibility and Deserialization Logic ---
        # 4. Handle Old Key Names (your original compatibility logic goes here)
        if 'anonymous_uuid' not in data and 'AnonymousUuid' in data:
            data['anonymous_uuid'] = data.pop('AnonymousUuid')
        if 'enable_popups' not in data and 'EnablePopups' in data:
            data['enable_popups'] = data.pop('EnablePopups')
        if 'enable_soundtrack' not in data and 'EnableSoundtrack' in data:
            data['enable_soundtrack'] = data.pop('EnableSoundtrack')
        if 'ffmpeg_hqdn3d' not in data and 'FFmpegHqdn3d' in data:
            data['ffmpeg_hqdn3d'] = data.pop('FFmpegHqdn3d')
        if 'ffmpeg_bin_name' not in data and 'FfmpegBinName' in data:
            data['ffmpeg_bin_name'] = data.pop('FfmpegBinName')
        if 'general_config_date' not in data and 'GeneralConfigDate' in data:
            data['general_config_date'] = data.pop('GeneralConfigDate')
        if 'detect_minor_mismatches' not in data and 'HighSensitiveBadFrameDetection' in data:
            data['detect_minor_mismatches'] = data.pop('HighSensitiveBadFrameDetection')
        if 'job_list_filename' not in data and 'JobListFilename' in data:
            data['job_list_filename'] = data.pop('JobListFilename')
        if 'last_consent_date' not in data and 'LastConsentDate' in data:
            data['last_consent_date'] = data.pop('LastConsentDate')
        if 'left_stripe_width_proportion' not in data and 'LeftStripeWidth' in data:
            data['left_stripe_width_proportion'] = data.pop('LeftStripeWidth')
        if 'popup_pos' not in data and 'PopupPos' in data:
            data['popup_pos'] = data.pop('PopupPos')
        if 'precise_template_match' not in data and 'PreciseTemplateMatch' in data:
            data['precise_template_match'] = data.pop('PreciseTemplateMatch')
        if 'source_dir' not in data and 'SourceDir' in data:
            data['source_dir'] = data.pop('SourceDir')
        if 'template_popup_window_pos' not in data and 'TemplatePopupWindowPos' in data:
            data['template_popup_window_pos'] = data.pop('TemplatePopupWindowPos')
        if 'user_consent' not in data and 'UserConsent' in data:
            data['user_consent'] = data.pop('UserConsent')
        if 'version' not in data and 'Version' in data:
            data['version'] = data.pop('Version')
        if 'window_pos' not in data and 'WindowPos' in data:
            data['window_pos'] = data.pop('WindowPos')
        # 5. Tolerant Deserialization (using dict.get for safety)
        # We use dict.get(key, default_value) to avoid errors if the key is missing
        return cls(
            anonymous_uuid=data.get('anonymous_uuid', ""),
            enable_popups=data.get('enable_popups', False),
            enable_soundtrack=data.get('enable_soundtrack', False),
            ffmpeg_hqdn3d=data.get('ffmpeg_hqdn3d', "8:6:4:3"),
            ffmpeg_bin_name=data.get('ffmpeg_bin_name', "ffmpeg"),
            general_config_date=data.get('general_config_date', ""),
            detect_minor_mismatches=data.get('detect_minor_mismatches', False),
            job_list_filename=data.get('job_list_filename', ""),
            last_consent_date=data.get('last_consent_date', ""),
            left_stripe_width_proportion=data.get('left_stripe_width_proportion', 0.25),
            popup_pos=data.get('popup_pos', ""),
            precise_template_match=data.get('precise_template_match', False),
            source_dir=data.get('source_dir', ""),
            template_popup_window_pos=data.get('template_popup_window_pos', ""),
            user_consent=data.get('user_consent', "yes"),
            version=data.get('version', ""),
            window_pos=data.get('window_pos', "")
        )
    

    @staticmethod
    def sort_nested_json(data):
        """Sorts keys in nested dictionaries recursively."""
        if isinstance(data, dict):
            return {k: AfterScanConfig.sort_nested_json(data[k]) for k in sorted(data)}
        elif isinstance(data, list):
            return [AfterScanConfig.sort_nested_json(item) for item in data]
        else:
            return data


    def to_json(self, json_path: str):
        """Serializes AfterScanConfig instance to a JSON file with sorted keys."""
        
        # 1. Convert instance to dictionary
        data_dict = asdict(self)
        
        # 2. Apply the recursive sorting
        sorted_data = AfterScanConfig.sort_nested_json(data_dict) 
        
        # 3. Save the sorted dictionary to JSON
        try:
            with open(json_path, 'w') as f:
                json.dump(sorted_data, f, indent=4) 
            print(f"Configuration saved to: {json_path}")
        except Exception as e:
            print(f"Error saving configuration to {json_path}: {e}")


    # --- Helper Method (already defined in your class) ---
    def _ensure_directory_exists(self, path):
        """Creates a directory if it does not exist."""
        if not os.path.exists(path):
            os.mkdir(path)


    def initialize_environment_paths(self, config_file_path: str):
        """
        Called after __init__ to perform environment setup (path construction and directory creation).
        Note: self.script_dir MUST be set before calling this method.
        """
        self.script_dir = os.path.split(config_file_path)[0]  

        if not self.script_dir:
            # Fallback or initialization error check
            raise ValueError("Script directory must be set before path construction.")            #"""Builds all dependent paths and ensures necessary directories exist."""
        
        # Assig configuration path for internal reference
        self.general_config_filename = config_file_path

        # 1. build patchs depending on self.script_dir
        self.temp_dir = os.path.join(self.script_dir, "temp")

        #general_config_filename = os.path.join(self.script_dir, "AfterScan.json")         
        self.project_settings_filename = os.path.join(self.script_dir, "AfterScan-projects.json")
        self.project_settings_backup_filename = os.path.join(self.script_dir, "AfterScan-projects.json.bak")
        self.project_config_basename = "AfterScan-project.json"
        self.project_config_filename = ""
        self.project_config_from_file = True
        self.project_name = "No Project"
        self.default_job_list_filename_legacy = os.path.join(self.script_dir, "AfterScan_job_list.json")
        self.default_job_list_filename = os.path.join(self.script_dir, "AfterScan.joblist.json")
        self.job_list_filename = self.default_job_list_filename
        self.job_list_hash = None    # To determine if job list has changed since loaded
        self.temp_dir = os.path.join(self.script_dir, "temp")
        self._ensure_directory_exists(self.temp_dir)
        self.logs_dir = os.path.join(self.script_dir, "Logs")
        self._ensure_directory_exists(self.logs_dir)
        self.copy_templates_from_temp = False
        self.resources_dir = os.path.join(self.script_dir, "Resources")
        if not os.path.exists(self.resources_dir):
            os.mkdir(self.resources_dir)
            self.copy_templates_from_temp = True
        # Soundtrack
        self.soundtrack_file_path = os.path.join(self.script_dir, "projector-loop.mp3")
        if os.path.isfile(self.soundtrack_file_path):
            self.sound_file_available = True
        else:
            self.sound_file_available = False

        self.template_list = None
        self.hole_template_filename_r8 = os.path.join(self.script_dir, "Pattern.R8.jpg")
        self.hole_template_filename_s8 = os.path.join(self.script_dir, "Pattern.S8.jpg")
        self.hole_template_filename_custom = os.path.join(self.script_dir, "Pattern.custom.jpg")
        self.hole_template_filename_corner = os.path.join(self.script_dir, "Pattern_Corner_TR.jpg")
        self.hole_template_filename_bw = os.path.join(self.script_dir, "Pattern_BW.jpg")
        self.hole_template_filename_wb = os.path.join(self.script_dir, "Pattern_WB.jpg")
        self.hole_template_filename = self.hole_template_filename_s8