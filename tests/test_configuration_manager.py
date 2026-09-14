import os
import json
import logging
import sys
from typing import Dict, Any

# Ensure we can import the manager (assuming it's in the same directory)
from configuration_manager import ConfigurationManager, GlobalConfig, ProjectConfigEntry

# --- File Constants ---
NEW_CONFIG_PATH = "afterscan.json"
LEGACY_GLOBAL_PATH = "AfterScan.json"
LEGACY_PROJECTS_PATH = "AfterScan-projects.json"
BACKUP_EXT = ".bak" # Extension for archived, migrated files
EXTRA_LEGACY_EXT = ".legacy" # Extension for bootstrapping files

# --- Debug and Logging Setup ---
def setup_logging():
    """Sets up basic logging to show debug info."""
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(levelname)s: %(message)s')

# --- I/O Helpers ---

def create_legacy_files(file_path: str, data: Dict[str, Any]):
    """
    Creates a single file for the migration scenario.
    (Kept as a general utility for other potential test setup, 
    but not used for bootstrapping .legacy files anymore).
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    logging.debug(f"Created file: {file_path}")

def ensure_legacy_source_files_exist():
    """
    Checks that the permanent *.legacy files exist. If they are missing, 
    the application is terminated as the test cannot proceed without them.
    
    The application will NOT create these files using sample data.
    """
    missing_files = []
    
    global_legacy_path = LEGACY_GLOBAL_PATH + EXTRA_LEGACY_EXT
    projects_legacy_path = LEGACY_PROJECTS_PATH + EXTRA_LEGACY_EXT
    
    if not os.path.exists(global_legacy_path):
        missing_files.append(global_legacy_path)

    if not os.path.exists(projects_legacy_path):
        missing_files.append(projects_legacy_path)

    if missing_files:
        logging.critical(
            "CRITICAL ERROR: Cannot run test. The following required permanent *.legacy source files are missing: "
        )
        for f in missing_files:
            logging.critical(f"- {f}")
        logging.critical(
            "Please create these files manually using the intended legacy configuration data to proceed with the test."
        )
        sys.exit(1)
    
    logging.info("Required permanent *.legacy source files found.")


def cleanup_files():
    """
    Deletes all generated and migrated config files (.json and .bak).
    The original .legacy files are RETAINED for multiple test runs.
    """
    paths_to_cleanup = [
        LEGACY_GLOBAL_PATH, 
        LEGACY_PROJECTS_PATH,
        # Also clean up the backups
        LEGACY_GLOBAL_PATH + BACKUP_EXT,
        LEGACY_PROJECTS_PATH + BACKUP_EXT,
        # *** NOTE: .legacy files are intentionally left here for repeated testing. ***
    ]
    for path in paths_to_cleanup:
        if os.path.exists(path):
            os.remove(path)
            logging.info(f"Cleaned up file: {path}")

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Helper to safely load a JSON file or return empty dict if not found."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading {file_path}: {e}")
        return {}
        
def pre_check_legacy_files():
    """
    Checks for legacy files with the EXTRA_LEGACY_EXT and copies their content 
    to the standard legacy file names if the standard files don't exist.
    This allows bootstrapping a fresh install from a .legacy file.
    """
    for legacy_path in [LEGACY_GLOBAL_PATH, LEGACY_PROJECTS_PATH]:
        extra_legacy_path = legacy_path + EXTRA_LEGACY_EXT
        
        # 1. Check if the standard legacy file already exists (e.g., AfterScan.json)
        if os.path.exists(legacy_path):
            logging.debug(f"Standard legacy file exists: {legacy_path}. Skipping copy from {EXTRA_LEGACY_EXT}.")
            continue
            
        # 2. Check if the file with the extra extension exists (e.g., AfterScan.json.legacy)
        if os.path.exists(extra_legacy_path):
            logging.warning(f"Found {EXTRA_LEGACY_EXT} file. Copying content to standard name: {legacy_path}")
            try:
                # Basic file copy: read all content from .legacy file and write to standard name
                with open(extra_legacy_path, 'r') as source_f:
                    content = source_f.read()
                with open(legacy_path, 'w') as dest_f:
                    dest_f.write(content)
                logging.info(f"Successfully copied content from {extra_legacy_path} to {legacy_path}.")
            except Exception as e:
                logging.error(f"Failed to copy {extra_legacy_path} content to {legacy_path}: {e}")


# --- Configuration Orchestrator (Implements the Migration Plan) ---

def orchestrate_loading(manager: ConfigurationManager):
    """
    Implements the backward-compatibility file loading strategy:
    1. Try new file.
    2. If missing, try legacy files.
    """
    
    if os.path.exists(NEW_CONFIG_PATH):
        logging.info(">>> STEP 1: Found NEW unified config file. Loading directly.")
        manager.load_configuration(NEW_CONFIG_PATH)
        return

    # --- Legacy Fallback Path ---
    
    if os.path.exists(LEGACY_GLOBAL_PATH) or os.path.exists(LEGACY_PROJECTS_PATH):
        logging.warning(">>> STEP 2: NEW config file missing. Starting LEGACY MIGRATION.")
        
        # Load data from the two legacy sources
        global_data = load_json_file(LEGACY_GLOBAL_PATH)
        projects_data = load_json_file(LEGACY_PROJECTS_PATH)
        
        # Merge, migrate keys, and load into the manager
        manager.migrate_legacy_data(global_data, projects_data)
        
        # Mark manager as dirty to ensure save on exit occurs
        manager.global_config.is_dirty = True
        
        # CRITICAL: Rename/archive legacy files after successful in-memory load
        try:
            # We must check if the file still exists before attempting to rename/move it, 
            # as it might have been only one of the two that triggered the load.
            if os.path.exists(LEGACY_GLOBAL_PATH):
                os.rename(LEGACY_GLOBAL_PATH, LEGACY_GLOBAL_PATH + BACKUP_EXT)
            if os.path.exists(LEGACY_PROJECTS_PATH):
                os.rename(LEGACY_PROJECTS_PATH, LEGACY_PROJECTS_PATH + BACKUP_EXT)
            logging.info(f"Legacy files successfully loaded and renamed to *{BACKUP_EXT}. Ready to save to new format.")
        except Exception as e:
             logging.error(f"Failed to rename legacy files: {e}. Migration successful, but cleanup failed.")
        
        return

    # Default path if no config files exist
    logging.info(">>> STEP 3: No config files found. Starting with default settings.")
    manager.global_config.is_dirty = True # Always mark dirty on default start


def main():
    setup_logging()
    
    # --- Test 1: Simulate Migration from Legacy Files ---
    
    # 1. SETUP: ENSURE the permanent *.legacy source files exist, or terminate.
    ensure_legacy_source_files_exist()

    # 2. CLEANUP: Remove any temporary files from previous runs (.json and .bak).
    cleanup_files() 
    
    print("\n--- Test 1: Starting Migration from verified .legacy source files ---")
    
    # 3. PRE-CHECK: This copies the content from the .legacy files to the standard names (AfterScan.json).
    pre_check_legacy_files()
    
    config_manager = ConfigurationManager.initialize()
    
    # 4. LOAD & MIGRATE: Orchestrator loads the newly created standard files, performs migration, and renames them to .bak.
    orchestrate_loading(config_manager)
    
    # 5. VERIFY: Check for migration and merge
    print("\n--- Verification of Loaded Data (Post-Migration) ---")
    
    # Check Global Config
    g_config = config_manager.get_global_config()
    logging.debug(f"Global App Version (Legacy): {g_config.version}")
    
    # Check Project Entries
    print("\n--- Verifying Project Entry Migration ---")
    project_path = "/home/juan/V\u00eddeos/Captures/Eddie-Sample 2"
    config_manager.set_active_project(project_path)
    #config_manager.set_video_resolution('this is not a resolution!!!!!!')
    p_entry = config_manager.get_project_config(project_path)
    
    # CRITICAL: Check for successful key migration (ActiveTemplateName -> active_template_name)
    logging.debug(f"Project Name: {p_entry.project_name}")
    logging.debug(f"Source dir (Migrated Key): {p_entry.source_dir}")
    # CRITICAL: Check for successful deletion of deprecated key (it should not exist)
    if not hasattr(p_entry, 'LegacyDeprecatedSetting'):
        logging.debug("LegacyDeprecatedSetting was successfully excluded/deleted.")
    
    # 6. SAVE: Save the result to the NEW unified file (afterscan.json)
    print("\n--- Saving to Unified File (Simulating App Exit) ---")
    config_manager.save_configuration(NEW_CONFIG_PATH)
    
    
    print("\n--- Test 2: Simulate Loading from NEW Unified File ---")
    
    # Reset manager and load the new file we just created
    new_manager = ConfigurationManager.initialize()
    orchestrate_loading(new_manager)
    
    # Check Global Config from new file
    new_g_config = new_manager.get_global_config()
    logging.debug(f"New Global App Version: {new_g_config.version} (Should be 0.9.0)")
    
    # Check Project Entries from new file
    new_p_entry = new_manager.get_project_config(project_path)
    logging.debug(f"New Project source dir: {new_p_entry.source_dir}")
    
    print("\n--- Test Complete ---")
    cleanup_files() # Final cleanup (leaves .legacy files intact)

if __name__ == '__main__':
    main()