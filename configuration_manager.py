#!/usr/bin/env python
"""
configuration_manager - Handles AfterScan projects configuration and metadata.

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
__date__ = "2025-12-06"
__version_highlight__ = "Isolate AfterScan project + general configuration in dedicated manager class (using Facade pattern)"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

from dataclasses import dataclass, field, fields, asdict
from typing import Dict, Any, List
import copy
import logging
import os 
import json 
from datetime import datetime

# Handle migration from old JSON names (CamelCase) to new ones (snake_case)
# --- Constants for Key Migration ---
KEY_TO_DELETE = "__DELETE_KEY_FROM_CONFIG__"

# --- Key Migration Map ---
# Maps old (legacy/camelCase) keys to new (snake_case) keys or to KEY_TO_DELETE.
KEY_MIGRATION_MAP = {
    # General config keys
    'HighSensitiveBadFrameDetection': 'detect_minor_mismatches',
    'EnablePopups': 'enable_rectangle_popup',
    'EnableSoundtrack': 'enable_soundtrack',
    'FfmpegBinName': 'ffmpeg_bin_name',
    'FFmpegHqdn3d': 'ffmpeg_hqdn_3d',
    'GeneralConfigDate': 'last_config_save_date',
    'LastConsentDate': 'last_consent_date',
    'PopupPos': 'popup_pos',
    'PreciseTemplateMatch': 'precise_template_match',
    'SourceDir': 'source_dir',
    'TemplatePopupWindowPos': 'template_popup_window_pos',
    'UserConsent': 'user_consent',
    'Version': 'version',
    'WindowPos': 'window_pos',
    'AnonymousUuid': 'anonymous_uuid',
    'JobListFilename': 'job_list_filename',
    # Project config keys
    'FillBorders': KEY_TO_DELETE,
    'FillBordersThickness': KEY_TO_DELETE,
    'FillBordersMode': KEY_TO_DELETE,
    'FakeFillType': KEY_TO_DELETE,
    'StabilizationShift': KEY_TO_DELETE,
    'SourceDir': 'source_dir',
    'TargetDir': 'target_dir',
    'VideoTargetDir': 'video_target_dir',
    'CurrentFrame': 'current_frame',
    'EncodeAllFrames': 'encode_all_frames',
    'FrameFrom': 'frame_from',
    'FrameTo': 'frame_to',
    'FramesToEncode': 'frames_to_encode',
    'FilmType': 'film_type',
    'RotationAngle': 'rotation_angle',
    'StabilizationThreshold': 'stabilization_threshold',
    'LowContrastCustomTemplate': 'low_contrast_custom_template',
    'ExtendedStabilization': 'extended_stabilization',
    'CustomTemplateDefined': 'custom_template_defined',
    'CustomTemplateName': 'custom_template_name',
    'CustomTemplateExpectedPos': 'custom_template_expected_pos',
    'CustomTemplateFilename': 'custom_template_filename',
    'PerformCropping': 'perform_cropping',
    'PerformDenoise': 'perform_denoise',
    'PerformSharpness': 'perform_sharpness',
    'PerformGammaCorrection': 'perform_gamma_correction',
    'GammaCorrectionValue': 'gamma_correction_value',
    'CropRectangle': 'crop_rectangle',
    'Force_4/3': 'force_4_3',
    'Force_16/9': 'force_16_9',
    'FrameFillType': 'frame_fill_type',
    'GenerateVideo': 'generate_video',
    'VideoFilename': 'video_filename',
    'VideoTitle': 'video_title',
    'SkipFrameRegeneration': 'skip_frame_regeneration',
    'FFmpegPreset': 'ffmpeg_preset',
    'PerformStabilization': 'perform_stabilization',
    'StabilizationShiftY': 'stabilization_shift_y',
    'StabilizationShiftX': 'stabilization_shift_x',
    'PerformRotation': 'perform_rotation',
    'VideoFps': 'video_fps',
    'VideoResolution': 'video_resolution',
    'CurrentBadFrameIndex': 'current_bad_frame_index',
    'UserDefinedLeftStripeWidthProportion': 'user_defined_left_stripe_width_proportion',
    'ProjectConfigDate': 'project_config_date',
    'HighSensitiveBadFrameDetection': 'precise_template_match',
    'PreciseTemplateMatch': 'precise_template_match'
}


# --- 1. Global Configuration (The new structure) ---

@dataclass
class GlobalConfig:
    """
    Stores global, application-wide settings.
    
    CRITICAL: Fields must now be explicitly marked with metadata={'do_serialize': True} 
    to be included in the saved configuration file.
    """

    # Application Metadata (PERSISTENT FIELDS)
    # Global Configuration Items
    anonymous_uuid: str = field(default="", metadata={'do_serialize': True})
    detect_minor_mismatches: bool = field(default=False, metadata={'do_serialize': True})
    enable_popups: bool = field(default=False, metadata={'do_serialize': True})
    enable_soundtrack: bool = field(default=False, metadata={'do_serialize': True})
    ffmpeg_hqdn_3d: str = field(default="8:6:4:3", metadata={'do_serialize': True})
    ffmpeg_bin_name: str = field(default="ffmpeg", metadata={'do_serialize': True})
    general_config_date: str = field(default="", metadata={'do_serialize': True})
    job_list_filename: str = field(default="", metadata={'do_serialize': True})
    last_consent_date: str = field(default="", metadata={'do_serialize': True})
    popup_pos: str = field(default="", metadata={'do_serialize': True})
    precise_template_match: bool = field(default=False, metadata={'do_serialize': True})
    source_dir: str = field(default="", metadata={'do_serialize': True})    # Even if this is part of the project configuration, since it is the key to retrieve each specific project, needs to be in general_config
    template_popup_window_pos: str = field(default="", metadata={'do_serialize': True})
    user_consent: str = field(default="yes", metadata={'do_serialize': True})
    version: str = field(default="", metadata={'do_serialize': True})
    window_pos: str = field(default="", metadata={'do_serialize': True})
    
    # --- NON-PERSISTENT FIELD (Default behavior: NOT serialized) ---
    # Since it lacks the 'do_serialize' metadata, it will be skipped.
    # Extra attributes, no need to persist but dataclass will persist
    left_stripe_width_proportion: float = field(default=0.25)
    default_job_list_filename: str = field(default="")
    default_job_list_filename_legacy: str = field(default="")
    script_dir: str = field(default="")

    # --- Calculated Path Attributes (New) ---
    # NOTE: You don't need 'general_config_filename' here if you pass it into the method,
    # but defining it here is cleaner if you want to store it in the instance.
    general_config_filename: str = field(default="")
    
    project_settings_filename: str = field(default="")
    project_settings_backup_filename: str = field(default="")
    project_config_basename: str = field(default="AfterScan-project.json") # Static basename
    project_config_filename: str = field(default="")
    
    temp_dir: str = field(default="")
    logs_dir: str = field(default="")
    resources_dir: str = field(default="")
    soundtrack_file_path: str = field(default="")
    
    hole_template_filename_r8: str = field(default="")
    hole_template_filename_s8: str = field(default="")
    hole_template_filename_custom: str = field(default="")
    hole_template_filename_corner: str = field(default="")
    hole_template_filename_bw: str = field(default="")
    hole_template_filename_wb: str = field(default="")
    hole_template_filename: str = field(default="")
    
    # --- Calculated State Attributes (New) ---
    copy_templates_from_temp: bool = field(default=False)
    sound_file_available: bool = field(default=False)
    project_config_from_file: bool = field(default=True)
    project_name: str = field(default="No Project")
    job_list_hash: Optional[str] = field(default=None) # None is a fine default
    template_list: list["Template"] = field(default=None) # None is a fine default. Template set as string to avoid circular import dependency
    left_stripe_width_pixels: int = field(default=100)

    # Helper methods for GlobalConfig
    def copy(self) -> 'GlobalConfig':
        """Returns a deep copy of the instance."""
        return copy.deepcopy(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalConfig':
        """Creates a GlobalConfig instance from a dictionary, filtering invalid keys."""
        valid_fields = {f.name for f in fields(cls)}
        # When loading, we still accept all valid field names, regardless of 'do_serialize' status
        filtered_data = {key: value for key, value in data.items() if key in valid_fields}
        return cls(**filtered_data)


# --- 2. Single Project Configuration Entry ---
@dataclass
class ProjectConfigEntry:
    """
    Represents the configuration settings for a single project directory.
    Fields must be explicitly marked with metadata={'do_serialize': True} to be persisted.
    """
    # PERSISTENT FIELDS
    project_name: str = field(default="Default Project", metadata={'do_serialize': True})
    active_template_type: str = field(default="default", metadata={'do_serialize': True})
    active_template_name: str = field(default="Pattern.S8", metadata={'do_serialize': True})
    custom_template_expected_pos: List[int] = field(default_factory=lambda: [0, 0], metadata={'do_serialize': True})
    custom_template_expected_size: List[int] = field(default_factory=lambda: [200, 200], metadata={'do_serialize': True})
    crop_rectangle: List[int] = field(default_factory=list, metadata={'do_serialize': True}) 
    is_template: bool = field(default=False, metadata={'do_serialize': True})
    job_list: List[Dict[str, Any]] = field(default_factory=list, metadata={'do_serialize': True})

    # --- NON-PERSISTENT FIELD (Default behavior: NOT serialized) ---
    # Since it lacks the 'do_serialize' metadata, it will be skipped.
    cache_id: str = field(default="") 

    def copy(self) -> 'ProjectConfigEntry':
        """Returns a deep copy of the instance."""
        return copy.deepcopy(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfigEntry':
        """
        Creates an instance from a dictionary, filtering invalid keys 
        to ensure forward/backward compatibility.
        """
        valid_fields = {f.name for f in fields(cls)}
        filtered_data = {key: value for key, value in data.items() if key in valid_fields}
        return cls(**filtered_data)

    def log_fields(self):
        """Logs all field contents for debugging."""
        logging.debug("--- Debugging ProjectConfigEntry Contents ---")
        config_dict = asdict(self)
        for key, value in config_dict.items():
            logging.debug("%s = %s", key, str(value))
        logging.debug("----------------------------------------------")

# --- 3. The Configuration Manager Facade ---
@dataclass
class ConfigurationManager:
    """
    The Facade that manages both global and project-specific configurations.
    This is the single object the main application should rely on for all settings.
    """
    # ConfigurationManager fields themselves don't need 'do_serialize' unless 
    # they were intended to be saved as part of a larger container, but 
    # we handle them explicitly in _to_dict_recursive for the top-level structure.
    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    entries: Dict[str, ProjectConfigEntry] = field(default_factory=dict)
    
    @classmethod
    def initialize(cls) -> 'ConfigurationManager':
        """Initializes the Manager, loading global settings if available."""
        logging.info("ConfigurationManager initialized.")
        return cls()
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the entire ConfigurationManager object to a dictionary,
        excluding fields not marked with metadata={'do_serialize': True}.
        """
        return self._to_dict_recursive(self)
        
    def _to_dict_recursive(self, obj: Any) -> Any:
        """
        Custom recursive serialization function that respects the 'do_serialize'
        metadata flag.
        """
        if isinstance(obj, dict):
            # Recursively handle dictionaries (e.g., self.entries)
            return {k: self._to_dict_recursive(v) for k, v in obj.items()}
        
        if isinstance(obj, list):
            # Recursively handle lists (e.g., job_list)
            return [self._to_dict_recursive(item) for item in obj]
        
        # Check if the object is one of our configuration dataclasses
        if isinstance(obj, (ConfigurationManager, GlobalConfig, ProjectConfigEntry)):
            data = {}
            for field_info in fields(obj):
                
                # CRITICAL: Check the metadata flag. Only serialize if explicitly marked True.
                if not field_info.metadata.get('do_serialize', False):
                    
                    # Special exception: If the object is ConfigurationManager itself, 
                    # we must explicitly include global_config and entries, 
                    # as they form the top-level structure.
                    is_manager_field = isinstance(obj, ConfigurationManager) and field_info.name in ('global_config', 'entries')
                    
                    if not is_manager_field:
                        continue # Skip fields not marked for serialization (default behavior)
                
                # Get the value and serialize it recursively
                value = getattr(obj, field_info.name)
                data[field_info.name] = self._to_dict_recursive(value)
            return data
        
        # Return primitives and non-dataclass objects unchanged
        return obj


    # --- Private Migration Helper ---
    def _migrate_keys(self, obj: Any) -> Any:
        """
        Recursively checks keys in dictionaries within a structure (dict or list) 
        and converts legacy keys using the KEY_MIGRATION_MAP. Keys mapped to 
        KEY_TO_DELETE are removed.
        """
        if isinstance(obj, dict):
            new_dict = {}
            for old_key, value in obj.items():
                # Recursively process the value first
                new_value = self._migrate_keys(value)
                
                # Determine the target key (rename or delete)
                new_key = KEY_MIGRATION_MAP.get(old_key, old_key)
                
                if new_key == KEY_TO_DELETE:
                    logging.debug(f"Deleting deprecated key: '{old_key}'")
                    continue # Skip adding this pair to new_dict
                    
                if new_key != old_key:
                    logging.debug(f"Migrating key: '{old_key}' -> '{new_key}'")
                    
                new_dict[new_key] = new_value
            return new_dict
            
        elif isinstance(obj, list):
            # Recursively process items in a list
            return [self._migrate_keys(item) for item in obj]
            
        else:
            # Base case: return primitives unchanged
            return obj

    # --- Project-Specific Accessors ---

    def get_active_config(self, current_source_dir: str) -> ProjectConfigEntry:
        """
        Retrieves the configuration entry matching the current source directory 
        from the registry, or returns a brand new default configuration if not found.
        """
        if current_source_dir in self.entries:
            logging.debug(f"Project config found for directory: {current_source_dir}. Returning copy.")
            
            # CRITICAL: Return a deep copy to ensure the active config is independent.
            active_config = self.entries[current_source_dir].copy()
            
        else:
            logging.info(f"No existing project config found for '{current_source_dir}'. Creating default entry.")
            active_config = ProjectConfigEntry()
            
        return active_config
        
    def save_active_config(self, current_source_dir: str, config: ProjectConfigEntry):
        """
        Updates the registry with the current configuration entry (in-memory).
        Actual disk I/O (to_json) is a separate future step.
        """
        self.entries[current_source_dir] = config.copy()
        logging.debug(f"Saved active project config for directory: {current_source_dir}")

    # --- Global Config Accessors (Simple pass-through) ---
    
    def get_global_config(self) -> GlobalConfig:
        """Returns a copy of the global configuration."""
        return self.global_config.copy()
        
    def update_global_config(self, config: GlobalConfig):
        """Updates the internal global configuration instance."""
        self.global_config = config.copy()
        logging.debug("Global configuration updated.")

    # --- Placeholder for I/O methods ---
    
    def load_all(self, global_file_path: str, project_file_path: str): 
        """
        Placeholder demonstrating the load and migration sequence.
        Supports the new dictionary format and the simplified legacy list format.
        """
        logging.info(f"Attempting to load config from {project_file_path}")
        try:
            # --- SIMULATION OF RAW LOADED DATA (Legacy list format, with removed header) ---
            # NOTE: Index 0 is now GlobalConfig, Index 1 is Project Entries
            raw_data = [
                {'log_level': 'INFO', 'ui_theme': 'Dark'}, # Index 0: Global Config 
                { # Index 1: Project Entries
                    '/some/old/path': {
                        'project_name': 'Legacy List Project',
                        'ActiveTemplateName': 'Pattern.Super8', 
                        'LegacyDeprecatedSetting': True, 
                        'job_list': [
                            {'id': 1, 'CropRectangle': [50, 50, 150, 150]}, 
                        ]
                    }
                }
            ]
            # ----------------------------------------------------
            
            # 1. Migrate keys immediately on the raw data structure
            migrated_data = self._migrate_keys(raw_data)
            
            # 2. Determine the source format and normalize data into a dictionary structure
            if isinstance(migrated_data, list):
                logging.warning("Loading legacy list-based configuration file structure (Header removed).")
                normalized_data = {}
                
                # Assume list is now [GlobalConfig, Entries]
                if len(migrated_data) >= 1:
                    normalized_data['global_config'] = migrated_data[0]
                if len(migrated_data) >= 2:
                    normalized_data['entries'] = migrated_data[1]
                
            elif isinstance(migrated_data, dict):
                logging.debug("Loading modern dictionary-based configuration file structure.")
                normalized_data = migrated_data
            else:
                raise ValueError("Unsupported configuration file format: must be a list or dictionary.")

            # 3. Use the normalized dictionary to populate the manager properties
            
            # Global Config
            global_data = normalized_data.get('global_config', {})
            self.global_config = GlobalConfig.from_dict(global_data)
            
            # Project Entries
            for path, entry_data in normalized_data.get('entries', {}).items():
                self.entries[path] = ProjectConfigEntry.from_dict(entry_data)
                
            logging.info("Configuration loaded and migrated successfully.")
            
        except FileNotFoundError:
            logging.warning(f"Configuration file not found at {project_file_path}. Starting with defaults.")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            
    # def save_all(self, global_file_path: str, project_file_path: str):
    #     # Implementation note: This would save self.to_dict() which now excludes the header
    #     with open(project_file_path, 'w') as f:
    #         json.dump(self.to_dict(), f, indent=4)