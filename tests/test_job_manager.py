import os
import json
import logging
import sys
from typing import Dict, Any

# Ensure we can import the manager (assuming it's in the same directory)
from configuration_manager import ConfigurationManager, GlobalConfig, ProjectConfigEntry
from job_manager import JobManager, JobEntry, JobQueue

def main():
    manager = JobManager.initialize()
    
    print(f"The Current Working Directory is: {os.getcwd()}")

    # 1. Create jobs
    config1 = ProjectConfigEntry(project_name="Batch_1", source_dir="/in/1")
    config2 = ProjectConfigEntry(project_name="Batch_2", source_dir="/in/2")
    
    job1 = manager.create_new_job_entry("FirstRun", config1)
    job2 = manager.create_new_job_entry("SecondRun", config2)
    
    manager.add_job(job1)
    manager.add_job(job2)
    
    # 2. Update status of a job (The main app would handle which job to update)
    # Let's say the main app sends 'FirstRun' to be processed
    job_to_process = manager.get_job("FirstRun")
    if job_to_process and not job_to_process.done:
        print(f"Processing: {job_to_process.job_name} from {job_to_process.project.source_dir}")
        manager.mark_job_done(job_to_process.job_name, success=True)
    
    # 3. Save to file
    temp_file = "temp_job_list.json"
    manager.save_to_file(temp_file)
    
    # 4. Create a new manager and load from file
    new_manager = JobManager.initialize()
    new_manager.load_from_file(temp_file)
    
    print("\nJobs loaded into new manager:")
    for job_name, job_entry in new_manager.get_all_jobs().items():
        print(f" - {job_name}: Done={job_entry.done}, Source={job_entry.project.source_dir}")

    # Clean up (optional)
    if os.path.exists(temp_file):
        os.remove(temp_file)

if __name__ == '__main__':
    main()        