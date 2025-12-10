#!/usr/bin/env python
"""
custom_json_encoder - Custom JSON encoder for AfterScan classes

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "custom_json_encoder"
__version__ = "1.0.0"
__data_version__ = "1.0"
__date__ = "2025-12-10"
__version_highlight__ = "WIP - First version of custom_json_encoder.py. Allow hashing of internal job class"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import json
from datetime import datetime
from dataclasses import asdict
from job_manager import JobEntry
from configuration_manager import ProjectConfigEntry

class AppEncoder(json.JSONEncoder):
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