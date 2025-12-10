#!/usr/bin/env python
"""
job_manager - Handles AfterScan batch job list

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "job_manager"
__version__ = "1.0.5"
__data_version__ = "1.0"
__date__ = "2025-12-10"
__version_highlight__ = "WIP - Settings changes properly propagated to/from current project and job list."
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

from dataclasses import dataclass, field, fields, asdict
from typing import Dict, Any, Optional, List
import uuid
import copy
import logging
import json
import os
import time
from configuration_manager import ProjectConfigEntry, ConfigurationManager



# --- Job Entry (The Value in the Job Map) ---

@dataclass
class JobEntry:
    """Represents a single entry in the batch processing queue."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_name: str = "Unnamed Job" 
    project: ProjectConfigEntry = field(default_factory=ProjectConfigEntry) 
    
    # Job execution status metadata
    description: str = "Batch Job"
    done: bool = False
    attempted: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], job_name_key: str) -> 'JobEntry':
        """Creates a JobEntry instance from snake_case data."""
        valid_fields = {f.name for f in fields(cls)}
        filtered_data = {key: value for key, value in data.items() if key in valid_fields}

        if 'project' in filtered_data:
            pc_data = filtered_data.pop('project')
            filtered_data['project'] = ProjectConfigEntry.from_dict(pc_data)
        
        filtered_data['job_name'] = job_name_key
        
        return cls(**filtered_data)

    def to_dict(self) -> Dict[str, Any]:
        """Converts JobEntry to a snake_case dictionary for persistence."""
        output = asdict(self)
        
        # We keep job_name and project inside the dict structure, 
        # but the caller (JobQueue.to_dict) will use job_name as the top-level key.
        output['project'] = self.project.to_dict()
        
        return output
    
    def get_project(self) -> Optional[ProjectConfigEntry]:
        """Retrieves a job by its name."""
        return self.project

    def get_description(self) -> str:
        """Retrieves a job by its name."""
        return self.description


# --- Job Queue Container (The Top-Level Structure) ---

@dataclass
class JobQueue:
    """A type-safe container for all batch jobs: {job_name: JobEntry, ...}."""
    job_map: Dict[str, JobEntry] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, Any]]) -> 'JobQueue':
        """
        Constructs the JobQueue from a dictionary of jobs.
        Keys of 'data' are job names, values are snake_case JobEntry content.
        """
        instance = cls()
        
        for job_name, job_data in data.items():
            try:
                job_entry = JobEntry.from_dict(job_data, job_name_key=job_name)
                instance.job_map[job_name] = job_entry
            except Exception as e:
                logging.warning(f"Failed to load job '{job_name}': {e}. Skipping.")
                continue
                
        return instance

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Converts the queue to a dictionary for file storage (snake_case data)."""
        output_data: Dict[str, Dict[str, Any]] = {}
        
        for job_name, job_entry in self.job_map.items():
            # Use job_name as the key, and JobEntry's data as the value
            output_data[job_name] = job_entry.to_dict()
            
        return output_data
        
    def add_job(self, job: JobEntry):
        """Adds or updates a job using its name as the key."""
        self.job_map[job.job_name] = job
        
    def get_job(self, job_name: str) -> Optional[JobEntry]:
        """Retrieves a job by its name."""
        return self.job_map.get(job_name)

    def delete_job(self, job_name: str):
        """Retrieves a job by its name."""
        self.job_map.pop(job_name)

    def job_exists(self, job_name: str) -> bool:
        """Checks if a job with the given name exists."""
        return job_name in self.job_map

# --- Job Manager Facade ---

@dataclass
class JobManager:
    """
    Facade for managing the JobQueue and handling dedicated joblist file I/O.
    """
    job_queue: JobQueue = field(default_factory=JobQueue)

    @classmethod
    def initialize(cls) -> 'JobManager':
        """
        Factory method to initialize the JobManager with an empty queue.
        """
        logging.info("JobManager initialized.")
        return cls()
      
    # --- Persistence Methods (Dedicated Job File) ---

    def load_from_file(self, filepath: str) -> bool:
        """Loads a dedicated 'joblist-only' JSON file and replaces the active queue."""
        if not os.path.exists(filepath):
            logging.error(f"Cannot load jobs: File not found at '{filepath}'")
            return False

        try:
            with open(filepath, 'r') as f:
                raw_data = json.load(f)

            migrated_data = ConfigurationManager.migrate_keys(raw_data)
            
            # The raw_data must be in the format {job_name: job_data_dict (snake_case)}
            if not isinstance(migrated_data, dict):
                 logging.error(f"File content is invalid: expected dictionary structure.")
                 return False

            # Create a new JobQueue from the loaded data
            new_queue = JobQueue.from_dict(migrated_data)
            self.job_queue = new_queue
            
            logging.info(f"Successfully loaded {len(self.job_queue.job_map)} jobs from '{filepath}'")
            return True
            
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from '{filepath}'. File may be corrupt.")
            return False
        except Exception as e:
            logging.error(f"General error loading job queue from '{filepath}': {e}")
            return False

    def save_to_file(self, filepath: str) -> bool:
        """Saves the active job queue to a dedicated 'joblist-only' JSON file."""
        try:
            # Get data in the file format (job names as keys, snake_case data as values)
            output_data = self.job_queue.to_dict()
            
            # NOTE ON CASE CONVERSION: 
            # If the output file *must* use CamelCase, you must apply the 
            # snake_to_camel conversion here before dumping to JSON.
            
            with open(filepath, 'w') as f:
                json.dump(output_data, f, indent=4)
                
            logging.info(f"Successfully saved {len(output_data)} jobs to '{filepath}'")
            return True
            
        except Exception as e:
            logging.error(f"Error saving job queue to '{filepath}': {e}")
            return False

    # --- Job Manipulation Methods ---
    
    def create_new_job_entry(self, name: str, description: str, config: ProjectConfigEntry) -> JobEntry:
        """Creates and returns a new JobEntry instance."""
        # Use a deep copy of the config to ensure mutations on the job object don't affect 
        # the original config object outside this manager, if any.
        return JobEntry(
            job_name=name,
            description=description,
            project=copy.deepcopy(config),
            done=False,
            attempted=False
        )

    def add_job(self, job: JobEntry):
        """Adds or updates a job in the queue."""
        self.job_queue.add_job(job)
        logging.info(f"Job added/updated: {job.job_name}")

    def get_job(self, job_name: str) -> Optional[JobEntry]:
        """Retrieves a job by name."""
        return self.job_queue.get_job(job_name)
        
    def delete_job(self, job_name: str):
        """Deletes a job by name."""
        return self.job_queue.delete_job(job_name)
        
    def job_exists(self, job_name: str) -> bool:
        """Checks if a job with the given name exists."""
        return self.job_queue.job_exists(job_name)

    def mark_job_done(self, job_name: str, success: bool = True):
        """Updates the status of a job."""
        job = self.get_job(job_name)
        if job:
            job.done = success
            job.attempted = True
            logging.debug(f"Job '{job_name}' marked as done. Success: {success}")
        else:
            logging.debug(f"Could not find job '{job_name}' to update done status.")

    def is_job_done(self, job_name: str):
        """Retrieves the status of a job."""
        job = self.get_job(job_name)
        if not job:
            logging.debug(f"Could not find job '{job_name}' to retrieve done status.")
        return job.done if job else False

    def mark_job_attempted(self, job_name: str, success: bool = True):
        """Updates the status of a job."""
        job = self.get_job(job_name)
        if job:
            job.attempted = True
            logging.debug(f"Job '{job_name}' marked as attempted. Success: {success}")
        else:
            logging.debug(f"Could not find job '{job_name}' to update attempted status.")

    def is_job_attempted(self, job_name: str):
        """Retrieves the status of a job."""
        job = self.get_job(job_name)
        if not job:
            logging.debug(f"Could not find job '{job_name}' to retrieve attempted status.")
        return job.attempted if job else False

    def get_all_jobs(self) -> Dict[str, JobEntry]:
        """Returns the complete job map."""
        return self.job_queue.job_map

    def set_jobs_map(self, new_map: Dict[str, JobEntry]):
        """Replaces the internal job map with a new one."""
        self.job_queue.job_map = new_map