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
__version__ = "1.0.0"
__data_version__ = "1.0"
__date__ = "2025-11-25"
__version_highlight__ = "Dedicated module for template and template list management."
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import hashlib
import cv2
import os
import logging
from typing import Tuple, Dict, Any, ClassVar

class Template:
    def __init__(self, name, filename, type, position, width):
        self.name = name
        self.filename = filename
        self.type = type
        if self.type == 'custom':
            self.scale = 1.0
        else:
            self.scale = width/2028
        self.position = position
        self.scaled_position = (int(self.position[0] * self.scale),
                                int(self.position[1] * self.scale))
        self.size = (0,0)
        if os.path.isfile(filename):
            self.template = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
            self.scaled_template = self.resize_image(self.template, self.scale)
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


    def refresh(self, width):
        if self.type == 'custom':
            self.scale = 1.0
        else:
            self.scale = width/2028
        self.template = cv2.imread(self.filename, cv2.IMREAD_GRAYSCALE)
        self.scaled_template = self.resize_image(self.template, self.scale)
        self.white_pixel_count = cv2.countNonZero(self.scaled_template)
        total_pixels = self.scaled_template.size
        self.wb_proportion = self.white_pixel_count / total_pixels
        self.size = (self.template.shape[1], self.template.shape[0])
        self.scaled_size = (int(self.size[0] * self.scale),
                            int(self.size[1] * self.scale))
        self.scaled_position = (int(self.position[0] * self.scale),
                                int(self.position[1] * self.scale))
        logging.debug(f"Init Template {self.type}, size: {self.size}, scaled size: {self.scaled_size}")


    def resize_image(self, img, ratio):
        # Calculate the proportional size of original image
        width = int(img.shape[1] * ratio)
        height = int(img.shape[0] * ratio)

        dsize = (width, height)

        # resize image
        return cv2.resize(img, dsize)



class TemplateList:
    """Manages template filenames, hashes, and validation."""
        
    # Class attribute: Define the expected state of the default templates
    # Dictionary format: { filename: expected_hash }
    EXPECTED_HASHES = {
        'Pattern.S8.jpg': 'dc4b94a14ef3d3dad3fe9d5708b4f2702bed44be2a3ed0aef63e8405301b3562',
        'Pattern.R8.jpg': 'ce7c81572bc0a03b079d655aab10ec16924c8d3b313087bd841cf68a6657fe9a',
        'Pattern_BW.jpg': '4a90371097219e5d5604c00bead6710b694e70b48fe66dbc5c2ce31ceedce4cf',
        'Pattern_WB.jpg': '60d50644f26407503267b763bcc48d7bec88dd6f58bb238cf9bec6ba86938f33',
        'Pattern_Corner_TR.jpg': '5e56a49c029013588646b11adbdc4a223217abfb91423dd3cdde26abbf5dcd9c'
    }

    def __init__(self):
        self.templates = []
        self.active_template = None  # Initialize active_element to None
        self.img_width = 2028
        self.img_height = 1520

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
            t.refresh(self.img_width)
            target = t
        else:
            target = Template(name, filename, type, position, self.img_width)
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

    def set_scale(self, sample_img):
        # If new image size is different, Update all scaled templates and positions
        # Size reference 2028x1520
        # Probably we could call t.refresh instead of the following code, but let's keep it as is for now
        self.img_width = sample_img.shape[1]
        self.img_height = sample_img.shape[0]
        """
        new_scale = img_width/2028
        """
        for t in self.templates:
            t.refresh(self.img_width)
            """
            if t.type != 'custom' and new_scale != t.scale:
                t.scale = new_scale
                t.scaled_position = (int(t.position[0] * new_scale),
                                    int(t.position[1] * new_scale))
                t.scaled_template = resize_image(t.template, new_scale)
                t.scaled_size = (int(t.size[0] * new_scale),
                                int(t.size[1] * new_scale))
            """

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

    @classmethod
    def check_default_template_consistency(cls, templates_dir: str) -> Tuple[bool, str]:
        is_consistent = True
        error_message = ""
        files_missing = []
        files_invalid = []
        for jpg, expected in cls.EXPECTED_HASHES.items():
            if not os.path.exists(os.path.join(templates_dir, jpg)):
                is_consistent = False
                files_missing.append(jpg)
                continue
            with open(os.path.join(templates_dir, jpg), 'rb') as f:
                current = hashlib.sha256(f.read()).hexdigest()
            if current != expected:
                is_consistent = False
                files_invalid.append(jpg)
        if not is_consistent:
            error_message = "Error when loading template files.\r\n"
            if len(files_missing) > 0:
                error_message += f"Missing files: {', '.join(files_missing)}"
                if len(files_invalid) > 0:
                    error_message += "\r\n"
            if len(files_invalid) > 0:
                error_message += f"Invalid files: {', '.join(files_invalid)}"
            error_message += f"\r\nPlease install the correct template files for AfterScan {__version__} and try again."
            tk.messagebox.showerror("Error!", error_message)
        return is_consistent, error_message