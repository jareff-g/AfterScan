#!/usr/bin/env python
"""
GenerateHashes - Create SHA256 hashes for reference images

This utility generates SHA256 hashes for a set of reference images used in the AfterScan tool.

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "AfterScan"
__version__ = "1.0.0"
__data_version__ = "1.0"
__date__ = "2025-11-23"
__version_highlight__ = "First revision of GenerateHashes utility included in Github repository"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import hashlib
import os
import cv2

EXPECTED_HASHES = {
    'Pattern.S8.jpg': 'sha256_hash_1',
    'Pattern.R8.jpg': 'sha256_hash_1',
    #'Pattern.R8T.jpg': 'sha256_hash_2',
    #'Pattern.R8B.jpg': 'sha256_hash_2',
    'Pattern_BW.jpg': 'sha256_hash_3',
    'Pattern_WB.jpg': 'sha256_hash_4',
    'Pattern_Corner_TR.jpg': 'sha256_hash_5'
}

for jpg in EXPECTED_HASHES.keys():
    with open(jpg, 'rb') as f:
        print(f"'{jpg}': '{hashlib.sha256(f.read()).hexdigest()}',")
