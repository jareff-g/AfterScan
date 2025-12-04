#!/usr/bin/env python
"""
afterscan_status - Handles AfterScan app global status management.

Licensed under a MIT LICENSE.

More info in README.md file
"""

from dataclasses import dataclass

@dataclass
class AfterScanStatus:
    """
    A dedicated model for holding application-wide, central state variables 
    that control flow and are required by multiple independent subsystems (UI, Factories).
    """
    # Flow control vars
    is_conversion_loop_running: bool = False  # renamed from ConvertLoopRunning in afterScan legacy code
    is_conversion_loop_exit_requested: bool = False  # renamed from ConvertLoopExitRequested in afterScan legacy code
    is_correction_loop_running: bool = False  # renamed from CorrectLoopRunning in afterScan legacy code
    is_batch_job_running: bool = False  # renamed from BatchJobRunning in afterScan legacy code
    is_batch_autostarted: bool = False  # renamed from BatchAutostart in afterScan legacy code
    is_ui_operational: bool = True  # renamed from ui_init_done in AfterScan legacy code

    file_type: str = "jpg"  # This is not in AfterScan project config since it is not user selectable, type is the one of input frames

    # Indexes and other state variables
    current_frame: int = 0  # renamed from CurrentFrame in afterScan legacy code
    
    def start_conversion(self):
        """Sets the flag to indicate the conversion loop is active."""
        self.is_conversion_running = True

    def stop_conversion(self):
        """Sets the flag to indicate the conversion loop has stopped."""
        self.is_conversion_running = False
    
    def request_conversion_exit(self):
        """Sets the flag to request exit from the conversion loop."""
        self.is_conversion_loop_exit_requested = True

    def clear_conversion_exit_request(self):
        """Clears the flag requesting exit from the conversion loop."""
        self.is_conversion_loop_exit_requested = False

    def start_correction(self):
        """Sets the flag to indicate the correction loop is active."""
        self.is_correction_loop_running = True

    def stop_correction(self):
        """Sets the flag to indicate the correction loop has stopped."""
        self.is_correction_loop_running = False
    def start_batch_job(self):
        """Sets the flag to indicate a batch job is active."""
        self.is_batch_job_running = True

    def stop_batch_job(self):
        """Sets the flag to indicate a batch job has stopped."""
        self.is_batch_job_running = False
    def enable_batch_autostart(self):
        """Enables batch autostart."""
        self.is_batch_autostarted = True

    def disable_batch_autostart(self):
        """Disables batch autostart."""
        self.is_batch_autostarted = False

    def set_ui_operational(self, operational: bool):
        """Sets the UI operational status."""
        self.is_ui_operational = operational

    def set_current_frame(self, frame_index: int):
        """Sets the current frame index."""
        self.current_frame = frame_index

    def set_file_type(self, file_type: str):
        """Sets the current file type."""
        self.file_type = file_type
