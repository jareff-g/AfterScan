#!/usr/bin/env python
"""
afterscan_template_manager - Handles AfterScan template and template list management

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "afterscan_template_manager"
__version__ = "1.0.2"
__data_version__ = "1.0"
__date__ = "2025-12-06"
__version_highlight__ = "Implement facade pattern: Adding TemplateManager Class."
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, ClassVar
import logging
import os
import copy
import hashlib
import cv2 # Keep the OpenCV import here, as the logic is tied to it
import tkinter as tk # Needed for the messagebox in check_default_template_consistency

# --- 1. Template Data Class ---

@dataclass
class Template:
    """
    Represents a single loaded image template and its associated metadata.
    This is now a dataclass, but its creation is handled by a Factory Method 
    to manage the heavy I/O/CV dependency (cv2.imread).
    """
    # Core Data Fields (will be populated on creation)
    name: str
    filename: str
    type: str
    position: Tuple[int, int]
    scale: float = 1.0
    size: Tuple[int, int] = field(default=(0, 0))
    scaled_position: Tuple[int, int] = field(default=(0, 0))
    scaled_size: Tuple[int, int] = field(default=(0, 0))
    wb_proportion: float = 0.5

    # Runtime CV/Image Objects (We use Optional[Any] as the type hint for cv2 images)
    template: Optional[Any] = field(default=None, repr=False)
    scaled_template: Optional[Any] = field(default=None, repr=False)
    white_pixel_count: int = 0
    
    # --- Factory Method to handle initialization and I/O ---
    @classmethod
    def create(cls, name: str, filename: str, type: str, position: Tuple[int, int], width: int) -> 'Template':
        """
        Factory method that performs I/O and calculations, then initializes the dataclass.
        """
        # Calculate initial scale
        scale = 1.0 if type == 'custom' else width / 2028
        
        # Instantiate the object with known values
        instance = cls(
            name=name,
            filename=filename,
            type=type,
            position=position,
            scale=scale
        )
        
        # Perform image loading and calculations
        if os.path.isfile(filename):
            instance.template = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
            
            # Use the instance's method to resize
            instance.scaled_template = instance._resize_image(instance.template, instance.scale)
            
            # Calculate metadata
            instance.white_pixel_count = cv2.countNonZero(instance.scaled_template)
            total_pixels = instance.scaled_template.size
            instance.wb_proportion = instance.white_pixel_count / total_pixels if total_pixels > 0 else 0.5
            
            # Set sizes and positions
            instance.size = (instance.template.shape[1], instance.template.shape[0])
            instance.scaled_size = (int(instance.size[0] * instance.scale), int(instance.size[1] * instance.scale))
            instance.scaled_position = (int(instance.position[0] * instance.scale), int(instance.position[1] * instance.scale))
            
            logging.debug(f"Template '{name}' init success. Size: {instance.size}, Scaled: {instance.scaled_size}")
        else:
            logging.warning(f"Template file not found: {filename}")

        return instance


    # --- Methods for internal data manipulation ---

    def refresh(self, width: int):
        """Recalculates scale, position, and resizes the template based on new image width."""
        new_scale = 1.0 if self.type == 'custom' else width / 2028
        
        if self.template is None:
            # Reload image if needed, or if it was missing initially
            self.template = cv2.imread(self.filename, cv2.IMREAD_GRAYSCALE)
            if self.template is None:
                logging.error(f"Failed to load image for refresh: {self.filename}")
                return

        # Update all dependent properties
        self.scale = new_scale
        self.scaled_template = self._resize_image(self.template, self.scale)
        self.white_pixel_count = cv2.countNonZero(self.scaled_template)
        total_pixels = self.scaled_template.size
        self.wb_proportion = self.white_pixel_count / total_pixels if total_pixels > 0 else 0.5
        self.size = (self.template.shape[1], self.template.shape[0])
        self.scaled_size = (int(self.size[0] * self.scale), int(self.size[1] * self.scale))
        self.scaled_position = (int(self.position[0] * self.scale), int(self.position[1] * self.scale))
        logging.debug(f"Template '{self.name}' refreshed. New scale: {self.scale}")

    def _resize_image(self, img: Any, ratio: float) -> Any:
        """Internal helper for image resizing."""
        if img is None:
            return None
        width = int(img.shape[1] * ratio)
        height = int(img.shape[0] * ratio)
        dsize = (width, height)
        return cv2.resize(img, dsize)
    
    def copy(self) -> 'Template':
        """Returns a deep copy of the instance."""
        return copy.deepcopy(self)

# --- 2. Template List Container (Encapsulated) ---

@dataclass
class TemplateList:
    """
    Container for all Template objects. Handles low-level collection management.
    All template manipulation is now managed through the TemplateManager facade.
    """
    templates: Dict[str, Template] = field(default_factory=dict)
    
    # We use Optional[Template] because the template might not be found or be None
    active_template: Optional[Template] = field(default=None, repr=False)
    
    # Image size references (these will be set by the Manager when a frame is loaded)
    img_width: int = 2028
    img_height: int = 1520
    
    # Class attribute: Define the expected state of the default templates
    EXPECTED_HASHES: ClassVar[Dict[str, str]] = {
        'Pattern.S8.jpg': 'dc4b94a14ef3d3dad3fe9d5708b4f2702bed44be2a3ed0aef63e8405301b3562',
        'Pattern.R8.jpg': 'ce7c81572bc0a03b079d655aab10ec16924c8d3b313087bd841cf68a6657fe9a',
        'Pattern_BW.jpg': '4a90371097219e5d5604c00bead6710b694e70b48fe66dbc5c2ce31ceedce4cf',
        'Pattern_WB.jpg': '60d50644f26407503267b763bcc48d7bec88dd6f58bb238cf9bec6ba86938f33',
        'Pattern_Corner_TR.jpg': '5e56a49c029013588646b11adbdc4a223217abfb91423dd3cdde26abbf5dcd9c'
    }

    def add(self, name: str, filename: str, type: str, position: Tuple[int, int]) -> Template:
        """Creates or updates a Template, returning the new/updated instance."""
        key = f"{type}:{name}"
        
        if key in self.templates:
            # If already exists, update it and refresh the scale
            target = self.templates[key]
            target.filename = filename
            target.position = position
            target.refresh(self.img_width)
        else:
            # Create a new template instance using the Factory Method
            target = Template.create(name, filename, type, position, self.img_width)
            self.templates[key] = target
            
        self.active_template = target
        return target

    def get_template_by_key(self, type: str, name: str) -> Optional[Template]:
        """Retrieves a template by its type and name."""
        key = f"{type}:{name}"
        return self.templates.get(key)
        
    def remove(self, template: Template) -> bool:
        """Removes a template instance from the list."""
        key = f"{template.type}:{template.name}"
        if key in self.templates:
            del self.templates[key]
            if template == self.active_template:
                self.active_template = None
            return True
        return False
        
    # --- Consistency Check (Kept here as it uses EXPECTED_HASHES) ---

    @classmethod
    def check_default_template_consistency(cls, templates_dir: str) -> Tuple[bool, str]:
        """Checks if default templates exist and have expected hashes."""
        is_consistent = True
        error_message = ""
        files_missing = []
        files_invalid = []
        
        for jpg, expected in cls.EXPECTED_HASHES.items():
            full_path = os.path.join(templates_dir, jpg)
            
            if not os.path.exists(full_path):
                is_consistent = False
                files_missing.append(jpg)
                continue
                
            try:
                with open(full_path, 'rb') as f:
                    current = hashlib.sha256(f.read()).hexdigest()
                if current != expected:
                    is_consistent = False
                    files_invalid.append(jpg)
            except IOError:
                logging.error(f"Could not read file for hashing: {full_path}")
                is_consistent = False
                files_invalid.append(jpg)
                
        if not is_consistent:
            error_message = "Error when loading template files.\r\n"
            if files_missing:
                error_message += f"Missing files: {', '.join(files_missing)}"
                if files_invalid: error_message += "\r\n"
            if files_invalid:
                error_message += f"Invalid files: {', '.join(files_invalid)}"
            # NOTE: We keep the messagebox for now, but in the final UI, 
            # this should be handled by the UI layer (AfterScanUI)
            tk.messagebox.showerror("Error!", error_message)
            
        return is_consistent, error_message

# --- 3. Template Manager Facade (The UI Interface) ---

@dataclass
class TemplateManager:
    """
    The sole object passed to the UI for all template-related operations.
    It delegates most calls to the encapsulated TemplateList and active Template.
    """
    template_list: TemplateList = field(default_factory=TemplateList)
    
    # --- Factory Method (Initialization) ---
    @classmethod
    def initialize(cls) -> 'TemplateManager':
        """
        Initializes the Manager with an empty TemplateList.
        (No I/O needed since templates are built from external JPEGs.)
        """
        logging.info("TemplateManager initialized with an empty list.")
        return cls(template_list=TemplateList())

    # --- Methods for modifying the collection ---
    
    def add(self, name: str, filename: str, type: str, position: Tuple[int, int]) -> Optional[Template]:
        """Adds a new template or updates an existing one."""
        return self.template_list.add(name, filename, type, position)

    def remove(self, template: Template) -> bool:
        """Removes a specific template instance."""
        return self.template_list.remove(template)

    def set_active_template(self, type: str, name: str) -> bool:
        """Sets the active template by type and name."""
        template = self.template_list.get_template_by_key(type, name)
        if template:
            self.template_list.active_template = template
            return True
        return False
        
    def check_consistency(self, templates_dir: str) -> Tuple[bool, str]:
        """Delegates the file consistency check to the TemplateList."""
        return self.template_list.check_default_template_consistency(templates_dir)

    # --- Methods for querying the entire collection ---

    def get_all_templates(self) -> List[Template]:
        """Returns all managed template instances."""
        return list(self.template_list.templates.values())
        
    def get_template_by_key(self, type: str, name: str) -> Optional[Template]:
        """Returns a specific template instance."""
        return self.template_list.get_template_by_key(type, name)

    def get_template_image_by_key(self, type: str, name: str) -> Optional[Any]:
        """
        Returns the scaled OpenCV image (scaled_template) for a specific 
        template without exposing the Template object itself.
        """
        template = self.get_template_by_key(type, name)
        if template:
            # Safely return the scaled image
            return template.scaled_template
        return None
            
    # --- Methods for querying/manipulating the ACTIVE template ---
    
    @property
    def active_template(self) -> Optional[Template]:
        """Read-only property for the active template instance."""
        return self.template_list.active_template

    def get_active_template_image(self) -> Optional[Any]:
        """Returns the scaled OpenCV image of the active template."""
        if self.active_template:
            return self.active_template.scaled_template
        return None

    def get_active_name(self) -> Optional[str]:
        """Returns the name of the active template."""
        return self.active_template.name if self.active_template else None

    def get_active_filename(self) -> Optional[str]:
        """Returns the filename of the active template."""
        return self.active_template.filename if self.active_template else None

    def get_active_type(self) -> Optional[str]:
        """Returns the type of the active template."""
        return self.active_template.type if self.active_template else None

    def get_active_size(self) -> Optional[str]:
        """Returns the size of the active template."""
        return self.active_template.scaled_size if self.active_template else None

    def get_active_scale(self) -> Optional[str]:
        """Returns the size of the active template."""
        return self.active_template.scale if self.active_template else None

    def get_active_position(self) -> Optional[Tuple[int, int]]:
        """Returns the scaled position of the active template."""
        return self.active_template.scaled_position if self.active_template else None

    def set_active_position(self, scaled_position: Tuple[int, int]):
        """Sets the scaled position and recalculates the original position."""
        if self.active_template:
            t = self.active_template
            t.scaled_position = scaled_position
            t.position = (int(t.scaled_position[0] / t.scale),
                          int(t.scaled_position[1] / t.scale))

    # --- Methods related to scaling (applied globally) ---
    
    def set_scale_and_refresh_all(self, sample_img: Any):
        """
        Updates the reference image size and recalculates scale/positions/sizes 
        for ALL templates in the list.
        """
        if self.template_list.templates and sample_img is not None and len(sample_img.shape) >= 2:
            self.template_list.img_width = sample_img.shape[1]
            self.template_list.img_height = sample_img.shape[0]
            
            for t in self.template_list.templates.values():
                t.refresh(self.template_list.img_width)
            
            logging.info(f"Templates refreshed for new image size: {self.template_list.img_width}x{self.template_list.img_height}")
        elif sample_img is None:
            logging.warning("Cannot set scale: sample_img is None.")
        else:
            logging.warning("Cannot set scale: No templates in list.")