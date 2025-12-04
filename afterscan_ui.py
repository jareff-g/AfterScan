#!/usr/bin/env python
"""
afterscan_ui - Handles AfterScan user interface.

Licensed under a MIT LICENSE.

More info in README.md file
"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "afterscan_ui"
__version__ = "1.0.0"
__data_version__ = "1.0"
__date__ = "2025-12-01"
__version_highlight__ = "Isolate AfterScan UI in a dedicated class"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from typing import Union, Optional
from tkinter import Frame, LabelFrame, Label, Button, Entry, Canvas, Scale, Radiobutton, LEFT, TOP, RIGHT, BOTTOM, EW, W, E, NORMAL, SUNKEN, RAISED, HORIZONTAL
import webbrowser
from PIL import Image, ImageTk
import logging
import time
from tooltip import Tooltips
from afterscan_status import AfterScanStatus
from afterscan_config import AfterScanConfig
from project_config import AfterScanConfigRegistry, AfterScanConfigEntry
from frame_list import FrameList
import os
import sys

    
class AfterScanUI:
    # TK widget vars
    win: tk.Tk = None
    general_config: AfterScanConfig = None
    project_registry: AfterScanConfigRegistry = None
    project_config_entry: AfterScanConfigEntry = None
    afterscan_status: AfterScanStatus = None
    menu_bar: tk.Menu = None
    file_menu: tk.Menu = None
    help_menu: tk.Menu = None
    font_size: int = 11
    left_area_frame: Frame = None
    border_frame: LabelFrame = None
    draw_capture_canvas: Canvas = None
    frame_slider: Scale = None
    as_tooltips: Tooltips = None
    right_area_frame: Frame = None
    regular_top_section_frame: Frame = None
    frame_frame: LabelFrame = None
    selected_frame_number: Label = None
    selected_frame_index: Label = None
    selected_frame_time: Label = None
    app_status_label: Label = None
    Exit_btn: Button = None
    Go_btn: Button = None
    folder_frame: LabelFrame = None
    source_folder_frame: Frame = None
    frames_source_dir: Entry = None
    source_folder_btn: Button = None
    target_folder_frame: Frame = None
    frames_target_dir: Entry = None
    target_folder_btn: Button = None
    folder_bottom_frame: Frame = None
    postprocessing_frame: LabelFrame = None
    film_type_S8_rb: Radiobutton = None
    film_type_R8_rb: Radiobutton = None


    # TK variables
    frame_selected: tk.IntVar = None
    film_type: tk.StringVar = None

    # Other global attributes
    # Preview dimensions (4/3 format) vars
    big_size = True
    preview_width = 700
    preview_height = 525
    preview_ratio = 1  # Defined globally for homogeneity, to be calculated once per project

    # UI colors
    save_bg: str = None
    save_fg: str = None

    # Global status vars, UI specific
    frame_scale_refresh_pending: bool = False
    hole_search_area_adjustment_pending: bool = False

    # Detect whether 'requests' can be imported or not
    _requests_loaded: bool = False
    _requests_module: Optional[object] = None


    ####################
    # 1 - Dunder methods
    ####################

    def __init__(self, master, general_config, project_registry):
        self.win = master

        # --- Dependency Check ---
        try:
            import requests # Attempt the import inside the method
            self._requests_loaded = True
            # Optional: Store the imported module itself if needed later
            self._requests_module = requests 
        except ImportError:
            self._requests_loaded = False
            self._requests_module = None
        # ------------------------

        # 1. Own the core model (your finished classes)
        self.general_config = general_config
        self.project_registry = project_registry 
        self.project_config_entry = self.project_registry.get_active_config(self.general_config.source_dir)
        self.afterscan_status = AfterScanStatus()
        self.frame_list = FrameList(self.general_config, self.afterscan_status)

        self.as_tooltips = Tooltips(self.font_size)

        # 2. Instantiate and store references to all managers/factories (To be done later)
        # These will be created but not fully initialized yet
        #self.rectangle_manager = None
        #self.video_factory = None
        # ...
        
        # 3. Begin building the UI
        self._build_layout()    

    ######################
    # 2 - Public interface
    ######################

    ########################
    # 3 - UI/Event Callbacks
    ########################

    ################################
    # 4 - Protected/Internal Helpers
    ################################

    def _exit_app(self):  # Exit Application
        global win
        global active_threads
        global frame_encoding_event, frame_encoding_queue, num_threads

        # Terminate threads
        # frame_encoding_event.set()
        for i in range(0, num_threads):
            frame_encoding_queue.put((END_TOKEN, 0))
            logging.debug("Inserting end token to encoding queue")

        while active_threads > 0:
            win.update()
            logging.debug(f"Waiting for threads to exit, {active_threads} pending")
            time.sleep(0.2)

        """ delete_this
        save_general_config()
        save_project_config()
        """
        self.general_config.to_json(self.general_config.script_dir)
        self.project_registry.save_config_entry(
            source_dir=self.general_config.source_dir,
            config_to_save=self.project_config_entry
        )
        self.project_registry.to_json(self.general_config.project_settings_filename)
        """ to be completed: Class required for job list management
        save_job_list()
        """
        win.destroy()

    # Validation function for different widgets
    def _validate_entry_length(self, P, widget_name):
        max_lengths = {
            "video_filename": 100,  # First Entry widget (Tkinter auto-names widgets)
            "video_title": 200,   # Second Entry widget
        }

        max_length = max_lengths.get(widget_name.split(".")[-1], 10)  # Default to 10 if not found
        if len(P) > max_length:
            tk.messagebox.showerror("Error!",
                                f"Maximum length for this field is {max_length}")
            return 
        return len(P) <= max_length
    

    def _save_named_job_list(self):
        pass
        """ to be completed
        global general_config
        global job_list, job_list_hash
        start_dir = os.path.split(general_config.job_list_filename)[0]  
        aux_file = filedialog.asksaveasfilename(
            initialdir=start_dir,
            defaultextension=".json",
            initialfile=general_config.job_list_filename,
            filetypes=[("Joblist JSON files", "*.joblist.json"), ("JSON files", "*.json")],
            title="Select file to save job list")
        if len(aux_file) > 0:
            job_list_hash = generate_dict_hash(job_list)
            # Remove only the exact suffix if present
            if not aux_file.endswith(".joblist.json"):
                # Remove .json or .joblist if they exist separately
                aux_file = aux_file.removesuffix(".json").removesuffix(".joblist")
                # Append the correct suffix
                aux_file = f"{aux_file}.joblist.json"
            with open(aux_file, 'w+') as f:
                json.dump(job_list, f, indent=4)
            general_config.job_list_filename = aux_file
            display_window_title()
    """

    def _load_named_job_list(self):
        pass
        """ to be completed
        global general_config
        global job_list, job_list_hash

        aux_hash = generate_dict_hash(job_list)
        if job_list_hash != aux_hash:   # Current job list modified since loaded
            if tk.messagebox.askyesno(
                "Save job list?",
                "Current lob list contains unsaved changes.\r\n"
                "Do you want to save them before loading the new job list?\r\n"):
                save_named_job_list()
        start_dir = os.path.split(general_config.job_list_filename)[0]  
        aux_file = filedialog.askopenfilename(
            initialdir=start_dir,
            defaultextension=".json",
            filetypes=[("Joblist JSON files", "*.joblist.json"), ("JSON files", "*.json")],
            title="Select file to retrieve job list")
        if len(aux_file) > 0:
            load_job_list(aux_file)
            general_config.job_list_filename = aux_file
            job_list_hash = generate_dict_hash(job_list)
            display_window_title()
        """


    def _get_consent(self, force = False):
        # Check reporting consent
        if self._requests_loaded:
            if force or self.general_config.user_consent == None or self.general_config.last_consent_date == None or (self.general_config.user_consent == 'no' and (datetime.today()-self.general_config.last_consent_date).days >= 60):
                consent = tk.messagebox.askyesno(
                    "AfterScan User Count",
                    "Help us count AfterScan users anonymously? Reports versions to track usage. No personal data is collected, just an anonymous hash plus AfterScan versions."
                )
                self.general_config.last_consent_date = datetime.today().isoformat()  # Update last consent date
                self.general_config.user_consent = "yes" if consent else "no"


    # Scale related functions
    def _scale_display_update(self, update_filters=True, offset_x = 0, offset_y = 0):
        if self.afterscan_status.current_frame >= len(self.frame_list.source_dir_file_list):
            return
        img = self.frame_list.load_current_frame_image()
        if img is None:
            self.frame_scale_refresh_done = True
            logging.error(
                "Error reading frame %i, skipping", self.afterscan_status.current_frame)
        else:
            if self.hole_search_area_adjustment_pending:
                self.hole_search_area_adjustment_pending = False
                define_template_search_area(img)
            if not frame_scale_refresh_pending:
                if perform_rotation.get():
                    img = rotate_image(img)
                # If FrameSync editor opened, call stabilize_image even when not enabled just to display FrameSync images. Image would not be stabilized
                if perform_stabilization.get() or FrameSync_Viewer_opened: 
                    img = stabilize_image(CurrentFrame, img, img, offset_x, offset_y)[0]
                if update_filters:  # Only when changing values in UI, not when moving from frame to frame
                    if perform_denoise.get():
                        img = denoise_image(img)
                    if perform_sharpness.get():
                        # Sharpness code taken from https://www.educative.io/answers/how-to-sharpen-a-blurred-image-using-opencv
                        sharpen_filter = np.array([[-1, -1, -1],
                                                [-1, 9, -1],
                                                [-1, -1, -1]])
                        # applying kernels to the input image to get the sharpened image
                        img = cv2.filter2D(img, -1, sharpen_filter)
            if perform_gamma_correction.get():  # Unconditionalyl done GC if enabled, otherwise it might be confusing
                img = gamma_correct_image(img, float(gamma_correction_str.get()))
            if perform_cropping.get():
                img = crop_image(img, project_config_entry.crop_rectangle[0], project_config_entry.crop_rectangle[1])
            else:
                img = even_image(img)
            if img is not None and not img.size == 0:   # Just in case img is not well generated
                display_image(img)
            if frame_scale_refresh_pending:
                frame_scale_refresh_pending = False
                win.after(100, self._scale_display_update, update_filters) # If catching up after too many frames refreshed, las one do the refresh with filters
            else:
                frame_scale_refresh_done = True

    def _select_scale_frame(self, selected_frame):
        if int(selected_frame) >= len(self.frame_list.source_dir_file_list):
            selected_frame = str(len(self.frame_list.source_dir_file_list) - 1)
        if not self.afterscan_status.is_conversion_loop_running and not self.afterscan_status.is_batch_job_running:  # Do not refresh during conversion loop
            frame_slider.focus()
            CurrentFrame = int(selected_frame)
            self.project_config_entry.current_frame = CurrentFrame
            refresh_current_frame_ui_info(CurrentFrame, self.project_config_entry.first_absolute_frame)
            if frame_scale_refresh_done:
                frame_scale_refresh_done = False
                self.frame_scale_refresh_pending = False
                if self.afterscan_status.is_ui_operational:
                    win.after(5, self._scale_display_update, False)
            else:
                self.frame_scale_refresh_pending = True


    def _process_scale_value(event):
        """
        This function is called ONLY when the left mouse button (Button 1)
        is released on the Scale widget.
        """
        # Get the current value from the scale widget
        select_scale_frame(frame_slider.get())
    

    def _on_paste_all_entries(self, event, entry):
        try:
            entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            logging.warning("No selection to delete")


    def _set_frames_source_folder(self):

        # Write project data before switching project
        self.project_registry.to_json(self.general_config.project_settings_filename)
        
        aux_dir = filedialog.askdirectory(
            initialdir=self.general_config.source_dir,
            title="Select folder with captured images to process")

        if not aux_dir or aux_dir == "" or aux_dir == ():
            return
        elif self.project_config_entry.target_dir == aux_dir:
            tk.messagebox.showerror(
                "Error!",
                "Source folder cannot be the same as target folder.")
            return
        else:
            self.win.config(cursor="watch")  # Set cursor to hourglass
            self.afterscan_status.is_ui_operational = False
            self.general_config.source_dir = aux_dir
            self.frames_source_dir.delete(0, 'end')
            self.frames_source_dir.insert('end', self.general_config.source_dir)
            self.frames_source_dir.after(100, self.frames_source_dir.xview_moveto, 1)
            # Create a project id (folder name) for the stats logging below
            # Replace any commas by semi colon to avoid problems when generating csv by AfterScanAnalysis
            self.project_config_entry.project_name = os.path.split(self.general_config.source_dir)[-1].replace(',', ';')

        ''' delete_this - Load current project config (matching source dir)
        #load_project_config()
        '''
        project_config_entry = self.project_registry.get_active_config(general_config.source_dir)

        ''' delete_this
        decode_project_config()  # Needs first_absolute_frame defined
        apply_project_settings()
        '''
        refresh_ui_with_config_values()

        # If not defined in project, create target folder inside source folder
        if TargetDir == '':
            TargetDir = os.path.join(general_config.source_dir, 'out')
            if not os.path.isdir(TargetDir):
                os.mkdir(TargetDir)
            get_target_dir_file_list()
            frames_target_dir.delete(0, 'end')
            frames_target_dir.insert('end', TargetDir)
            frames_target_dir.after(100, frames_target_dir.xview_moveto, 1)
            set_project_defaults()
            project_config_entry.target_dir = TargetDir

        # Enable Start and Crop buttons, plus slider, once we have files to handle
        cropping_btn.config(state=NORMAL)
        frame_slider.config(state=NORMAL)
        Go_btn.config(state=NORMAL)
        frame_slider.set(CurrentFrame)

        init_display()
        widget_status_update(NORMAL)
        FrameSync_Viewer_popup_update_widgets(NORMAL)
        ui_init_done = True
        win.config(cursor="")  # Reset cursor to standard arrow


    def _set_frames_target_folder(self):
        global general_config, project_config_entry
        global TargetDir
        global frames_target_dir

        aux_dir = filedialog.askdirectory(
            initialdir=TargetDir,
            title="Select folder where to store generated frames")

        if not aux_dir or aux_dir == "" or aux_dir == ():
            return
        elif aux_dir == general_config.source_dir:
            tk.messagebox.showerror(
                "Error!",
                "Target folder cannot be the same as source folder.")
            return
        else:
            TargetDir = aux_dir
            get_target_dir_file_list()
            frames_target_dir.delete(0, 'end')
            frames_target_dir.insert('end', TargetDir)
            frames_target_dir.after(100, frames_target_dir.xview_moveto, 1)
            set_project_defaults()
            project_config_entry.target_dir = TargetDir

def set_film_type(self):
    global film_type, template_list
    global project_config_entry

    # To be completed: access template class from UI class
    if template_list.set_active(film_type.get(), film_type.get()):
        project_config_entry.film_type = film_type.get()
        debug_template_refresh_template()
        logging.debug(f"Setting {film_type.get()} template as active")
        video_fps_dropdown_selected.set('18' if film_type.get() == 'S8' else '16')
        return True
    else:
        tk.messagebox.showerror(
            "Default template could not be set",
            "Error while reverting back to standard template after disabling custom.")
        return False


    def _build_layout(self):
        """ delete_this
        global win
        global frames_source_dir, frames_target_dir, video_target_dir, video_target_dir_str
        global perform_cropping, cropping_btn
        global perform_denoise, perform_denoise_checkbox
        global perform_sharpness, perform_sharpness_checkbox
        global perform_gamma_correction_checkbox, gamma_correction_spinbox
        global generate_video, generate_video_checkbox
        global encode_all_frames, encode_all_frames_checkbox
        global frames_to_encode_str, frames_to_encode, frames_to_encode_label
        global save_bg, save_fg
        global source_folder_btn, target_folder_btn
        global perform_stabilization, perform_stabilization_checkbox
        global stabilization_threshold_spinbox, stabilization_threshold_str
        global stabilization_threshold_match_label
        global perform_rotation, perform_rotation_checkbox, rotation_angle_label
        global rotation_angle_spinbox, rotation_angle_str
        global custom_stabilization_btn, stabilization_threshold_label, low_contrast_custom_template_checkbox
        global perform_cropping_checkbox, Crop_btn
        global perform_gamma_correction, gamma_correction_str
        global force_4_3_crop_checkbox, force_4_3_crop
        global force_16_9_crop_checkbox, force_16_9_crop
        global Go_btn
        global Exit_btn
        global video_fps_dropdown_selected, skip_frame_regeneration_cb
        global video_fps_dropdown, video_fps_label, video_filename_name, video_filename_str, video_title_name, video_title_str
        global resolution_dropdown, resolution_label, resolution_dropdown_selected
        global video_target_folder_btn, video_filename_label, video_title_label
        global ffmpeg_preset
        global ffmpeg_preset_rb1, ffmpeg_preset_rb2, ffmpeg_preset_rb3
        global skip_frame_regeneration
        global frame_slider, selected_frame_time, CurrentFrame, frame_selected, selected_frame_number, selected_frame_index
        global film_type
        global job_list_treeview, job_list_listbox_disabled
        global app_status_label
        global PreviewWidth, PreviewHeight
        global left_area_frame
        global draw_capture_canvas
        global custom_ffmpeg_path
        global start_batch_btn, add_job_btn, delete_job_btn, rerun_job_btn
        global film_type_S8_rb, film_type_R8_rb
        global frame_from_str, frame_to_str, frame_from_entry, frame_to_entry, frames_separator_label
        global suspend_on_joblist_end
        global frame_fill_type
        global extended_stabilization, extended_stabilization_checkbox
        global RotationAngle
        global suspend_on_completion
        global perform_fill_none_rb, perform_fill_fake_rb, perform_fill_dumb_rb
        global ExpertMode
        global BigSize, self.font_size
        global template_list
        global low_contrast_custom_template
        global display_template_popup_btn
        global stabilization_shift_y_value, stabilization_shift_label, stabilization_shift_y_spinbox
        global stabilization_shift_x_value, stabilization_shift_x_spinbox
        global video_play_btn
        global general_config, project_config_entry
        """

        # Menu bar
        self.menu_bar = tk.Menu(self.win)
        self.win.config(menu=self.menu_bar)
        
        # Register max length validation function
        vcmd = (win.register(self._validate_entry_length), "%P", "%W")  # Pass widget name (%W)

        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu, font=("Arial", self.font_size))
        self.file_menu.add_command(label="Save job list", command=self._save_named_job_list, font=("Arial", self.font_size))
        self.file_menu.add_command(label="Load job list", command=self._load_named_job_list, font=("Arial", self.font_size))
        self.file_menu.add_separator()  # Optional divider
        self.file_menu.add_command(label="Exit", command=self._exit_app, font=("Arial", self.font_size))
        # Help Menu
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu, font=("Arial", self.font_size))
        self.help_menu.add_command(label="User Guide", font=("Arial", self.font_size), 
                            command=lambda: webbrowser.open("https://github.com/jareff-g/AfterScan/wiki/AfterScan-user-interface-description"))
        self.help_menu.add_command(label="Discord Server", font=("Arial", self.font_size), 
                            command=lambda: webbrowser.open("https://discord.gg/r2UGkH7qg2"))
        self.help_menu.add_command(label="AfterScan Wiki", font=("Arial", self.font_size), 
                            command=lambda: webbrowser.open("https://github.com/jareff-g/AfterScan/wiki"))
        if self.general_config.user_consent == "no":
            self.help_menu.add_command(label="Report AfterScan usage", font=("Arial", self.font_size), 
                                command=lambda: self._get_consent(True))
        self.help_menu.add_command(label="About AfterScan", font=("Arial", self.font_size), 
                            command=lambda: webbrowser.open("https://github.com/jareff-g/AfterScan/wiki/AfterScan:-8mm,-Super-8-film-post-scan-utility"))

        # Create a frame to add a border to the preview
        self.left_area_frame = Frame(self.win)
        self.left_area_frame.pack(side=LEFT, padx=5, pady=5, anchor='N')
        # Create a LabelFrame to act as a border
        self.border_frame = tk.LabelFrame(self.left_area_frame, bd=2, relief=tk.GROOVE)
        self.border_frame.pack(expand=True, fill="both", padx=5, pady=5)
        # Create the canvas
        self.draw_capture_canvas = Canvas(self.border_frame, bg='dark grey', width=self.preview_width, height=self.preview_height)
        self.draw_capture_canvas.pack(side=TOP, anchor=N)
        # Initialize canvas image (to avoid multiple use of create_image)
        #Create an empty photoimage
        self.draw_capture_canvas.image = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), master=self.draw_capture_canvas) #create a transparent 1x1 image.
        # Ensure the draw_capture_canvas object keeps a direct reference to the image.
        self.draw_capture_canvas.image_id = self.draw_capture_canvas.create_image(0, 0, anchor=tk.NW, image=self.draw_capture_canvas.image)
        # New scale under canvas 
        self.frame_selected = tk.IntVar(master=self.win)
        self.frame_slider = Scale(self.border_frame, orient=HORIZONTAL, from_=0, to=0, showvalue=False,
                            variable=self.frame_selected, highlightthickness=1,
                            length=self.preview_width, takefocus=1, font=("Arial", self.font_size))
        self.frame_slider.bind("<ButtonRelease-1>", process_scale_value)
        self.frame_slider.bind("<KeyRelease>", process_scale_value)
        self.frame_slider.pack(side=BOTTOM, pady=4)
        self.frame_slider.set(self.project_config_entry.current_frame)
        self.as_tooltips.add(self.frame_slider, "Browse around frames to be processed")

        # Frame for standard widgets to the right of the preview
        self.right_area_frame = Frame(self.win)
        #right_area_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky=N)
        self.right_area_frame.pack(side=LEFT, padx=5, pady=5, anchor=N)

        # Frame for top section of standard widgets ******************************
        self.regular_top_section_frame = Frame(self.right_area_frame)
        self.regular_top_section_frame.pack(side=TOP, padx=2, pady=2)

        # Create frame to display current frame and slider
        self.frame_frame = LabelFrame(self.regular_top_section_frame, text='Current frame',
                                width=35, height=10, font=("Arial", self.font_size-2))
        self.frame_frame.grid(row=1, column=0, sticky='nsew')

        self.selected_frame_number = Label(self.frame_frame, width=12, text='Number:', font=("Arial", self.font_size))
        self.selected_frame_number.pack(side=TOP, pady=2)
        self.as_tooltips.add(self.selected_frame_number, "Frame number, as stated in the filename")

        self.selected_frame_index = Label(self.frame_frame, width=12, text='Index:', font=("Arial", self.font_size))
        self.selected_frame_index.pack(side=TOP, pady=2)
        self.as_tooltips.add(self.selected_frame_index, "Sequential frame index, from 1 to n")

        self.selected_frame_time = Label(self.frame_frame, width=12, text='Time:', font=("Arial", self.font_size))
        self.selected_frame_time.pack(side=TOP, pady=2)
        self.as_tooltips.add(self.selected_frame_time, "Time in the source film where this frame is located")

        # Application status label
        self.app_status_label = Label(self.regular_top_section_frame, width=46 if self.big_size else 46, borderwidth=2,
                                relief="groove", text='Status: Idle',
                                highlightthickness=1, font=("Arial", self.font_size))
        self.app_status_label.grid(row=2, column=0, columnspan=3, pady=5, sticky=EW)

        # Application Exit button
        self.Exit_btn = Button(self.regular_top_section_frame, text="Exit", width=10,
                        height=5, command=self._exit_app, activebackground='red',
                        activeforeground='white', wraplength=80, font=("Arial", self.font_size))
        self.Exit_btn.grid(row=0, column=1, rowspan=2, padx=10, sticky='nsew')

        self.as_tooltips.add(self.Exit_btn, "Exit AfterScan")

        # Application start button
        self.Go_btn = Button(self.regular_top_section_frame, text="Start", width=12, height=5,
                        command=self.start_convert, activebackground='green',
                        activeforeground='white', wraplength=80, font=("Arial", self.font_size))
        self.Go_btn.grid(row=0, column=2, rowspan=2, sticky='nsew')

        self.as_tooltips.add(self.Go_btn, "Start post-processing using current settings")

        # Add AfterScan Logo
        self.win.update_idletasks()

        
        # Display AfterScan logo in frame window
        try:
            logo_image = Image.open(os.path.join(self.general_config.script_dir, "AfterScan_logo.jpeg"))  # Replace with your logo file name
        except FileNotFoundError as e:
            logo_image = None
            logging.warning(f"Could not find AfterScan logo file: {e}")
        if logo_image != None:
            # Resize the image (e.g., to 50% of its original size)
            ratio = self.frame_frame.winfo_width() / logo_image.width
            new_width = int(logo_image.width * ratio)
            new_height = int(logo_image.height * ratio)
            resized_logo = logo_image.resize((new_width, new_height), Image.LANCZOS) #use LANCZOS for high quality resizing.
            # Convert to PhotoImage
            logo_image = ImageTk.PhotoImage(resized_logo, master=self.draw_capture_canvas)
            if logo_image:
                logo_label = tk.Label(self.regular_top_section_frame, image=logo_image)

                # Delete reference to previous image, if any
                aux_image = None
                if hasattr(logo_label, 'image'):
                    aux_image = logo_label.image
                logo_label.image = logo_image  # Keep a reference!
                if aux_image:
                    del aux_image
                logo_label.grid(row=0, column=0, sticky='nsew')

        # Create frame to select source and target folders *******************************
        self.folder_frame = LabelFrame(self.right_area_frame, text='Folder selection', width=30,
                                height=8, font=("Arial", self.font_size-2))
        self.folder_frame.pack(padx=2, pady=2, ipadx=5, expand=True, fill="both")

        self.source_folder_frame = Frame(self.folder_frame)
        self.source_folder_frame.pack(side=TOP)
        self.frames_source_dir = Entry(self.source_folder_frame, width=34 if self.big_size else 34,
                                        borderwidth=1, font=("Arial", self.font_size))
        self.frames_source_dir.pack(side=LEFT)
        self.frames_source_dir.delete(0, 'end')
        self.frames_source_dir.insert('end', self.general_config.source_dir)
        self.frames_source_dir.after(100, self.frames_source_dir.xview_moveto, 1)
        self.frames_source_dir.bind('<<Paste>>', lambda event, entry=self.frames_source_dir: self._on_paste_all_entries(event, entry))

        self.as_tooltips.add(self.frames_source_dir, "Directory where the source frames are located")

        self.source_folder_btn = Button(self.source_folder_frame, text='Source', width=6,
                                height=1, command=set_source_folder,
                                activebackground='green',
                                activeforeground='white', wraplength=80, font=("Arial", self.font_size))
        self.source_folder_btn.pack(side=LEFT)

        self.as_tooltips.add(self.source_folder_btn, "Selects the directory where the source frames are located")

        self.target_folder_frame = Frame(self.folder_frame)
        self.target_folder_frame.pack(side=TOP)
        self.frames_target_dir = Entry(self.target_folder_frame, width=34 if self.big_size else 34,
                                        borderwidth=1, font=("Arial", self.font_size))
        self.frames_target_dir.pack(side=LEFT)
        self.frames_target_dir.bind('<<Paste>>', lambda event, entry=self.frames_target_dir: self._on_paste_all_entries(event, entry))
        
        self.as_tooltips.add(self.frames_target_dir, "Directory where generated frames will be stored")

        self.target_folder_btn = Button(self.target_folder_frame, text='Target', width=6,
                                height=1, command=set_frames_target_folder,
                                activebackground='green',
                                activeforeground='white', wraplength=80, font=("Arial", self.font_size))
        self.target_folder_btn.pack(side=LEFT)
        self.as_tooltips.add(self.target_folder_btn, "Selects the directory where the generated frames will be stored")

        self.save_bg = self.source_folder_btn['bg']
        self.save_fg = self.source_folder_btn['fg']

        self.folder_bottom_frame = Frame(self.folder_frame)
        self.folder_bottom_frame.pack(side=BOTTOM, ipady=2)

        # Define post-processing area *********************************************
        self.postprocessing_frame = LabelFrame(self.right_area_frame,
                                        text='Frame post-processing',
                                        width=40, height=8, font=("Arial", self.font_size-2))
        self.postprocessing_frame.pack(padx=2, pady=2, ipadx=5, expand=True, fill="both")
        postprocessing_row = 0
        self.postprocessing_frame.grid_columnconfigure(0, weight=1)
        self.postprocessing_frame.grid_columnconfigure(1, weight=1)
        self.postprocessing_frame.grid_columnconfigure(2, weight=1)

        # Radio buttons to select R8/S8. Required to select adequate pattern, and match position
        self.film_type = tk.StringVar(master=self.win)
        self.film_type_S8_rb = Radiobutton(self.postprocessing_frame, text="Super 8", variable=self.film_type, command=set_film_type,
                                    width=11 if self.big_size else 11, value='S8', font=("Arial", self.font_size))
        self.film_type_S8_rb.grid(row=postprocessing_row, column=0, sticky=W)
        self.as_tooltips.add(self.film_type_S8_rb, "Handle as Super 8 film")
        self.film_type_R8_rb = Radiobutton(self.postprocessing_frame, text="Regular 8", variable=self.film_type, command=set_film_type,
                                    width=11 if self.big_size else 11, value='R8', font=("Arial", self.font_size))
        self.film_type_R8_rb.grid(row=postprocessing_row, column=1, sticky=W)
        self.as_tooltips.add(film_type_R8_rb, "Handle as 8mm (Regular 8) film")
        self.film_type.set(self.project_config_entry.film_type)
        postprocessing_row += 1

        # Check box to select encoding of all frames
        encode_all_frames = tk.BooleanVar(master=win, value=False)
        encode_all_frames_checkbox = tk.Checkbutton(
            postprocessing_frame, text='Encode all frames',
            variable=encode_all_frames, onvalue=True, offvalue=False,
            command=encode_all_frames_selection, width=14, font=("Arial", self.font_size))
        encode_all_frames_checkbox.grid(row=postprocessing_row, column=0,
                                            columnspan=3, sticky=W)
        as_tooltips.add(encode_all_frames_checkbox, "If selected, all frames in source folder will be encoded")
        postprocessing_row += 1

        # Entry to enter start/end frames
        frames_to_encode_label = tk.Label(postprocessing_frame,
                                        text='Frame range:',
                                        width=12, font=("Arial", self.font_size))
        frames_to_encode_label.grid(row=postprocessing_row, column=0, columnspan=2, sticky=W)
        frame_from_str = tk.StringVar(master=win, value=str(from_frame))
        frame_from_entry = Entry(postprocessing_frame, textvariable=frame_from_str, width=5, borderwidth=1, font=("Arial", self.font_size))
        frame_from_entry.grid(row=postprocessing_row, column=1, sticky=W)
        frame_from_entry.config(state=NORMAL)
        frame_from_entry.bind("<Double - Button - 1>", update_frame_from)
        frame_from_entry.bind("<Button - 2>", update_frame_from)
        frame_from_entry.bind('<<Paste>>', lambda event, entry=frame_from_entry: self._on_paste_all_entries(event, entry))
        as_tooltips.add(frame_from_entry, "First frame to be processed, if not encoding the entire set")
        frame_to_str = tk.StringVar(master=win, value=str(from_frame))
        frames_separator_label = tk.Label(postprocessing_frame, text='to', width=2, font=("Arial", self.font_size))
        frames_separator_label.grid(row=postprocessing_row, column=1)
        frame_to_entry = Entry(postprocessing_frame, textvariable=frame_to_str, width=5, borderwidth=1, font=("Arial", self.font_size))
        frame_to_entry.grid(row=postprocessing_row, column=1, sticky=E)
        frame_to_entry.config(state=NORMAL)
        frame_to_entry.bind("<Double - Button - 1>", update_frame_to)
        frame_to_entry.bind("<Button - 2>", update_frame_to)
        frame_to_entry.bind('<<Paste>>', lambda event, entry=frame_to_entry: self._on_paste_all_entries(event, entry))
        as_tooltips.add(frame_to_entry, "Last frame to be processed, if not encoding the entire set")

        postprocessing_row += 1

        # Check box to do rotate image
        perform_rotation = tk.BooleanVar(master=win, value=False)
        perform_rotation_checkbox = tk.Checkbutton(
            postprocessing_frame, text='Rotate image:',
            variable=perform_rotation, onvalue=True, offvalue=False, width=11,
            command=perform_rotation_selection, font=("Arial", self.font_size))
        perform_rotation_checkbox.grid(row=postprocessing_row, column=0,
                                            columnspan=1, sticky=W)
        perform_rotation_checkbox.config(state=NORMAL)
        as_tooltips.add(perform_rotation_checkbox, "Rotate generated frames")

        # Spinbox to select rotation angle
        rotation_angle_str = tk.StringVar(master=win, value=str(0))
        #rotation_angle_selection_aux = postprocessing_frame.register(rotation_angle_selection)
        rotation_angle_spinbox = tk.Spinbox(
            postprocessing_frame,
            command=rotation_angle_selection, width=5,
            textvariable=rotation_angle_str, from_=-5, to=5,
            format="%.1f", increment=0.1, font=("Arial", self.font_size))
        rotation_angle_spinbox.grid(row=postprocessing_row, column=1, sticky=W)
        rotation_angle_spinbox.bind("<FocusOut>", rotation_angle_spinbox_focus_out)
        as_tooltips.add(rotation_angle_spinbox, "Angle to use when rotating frames")
        #rotation_angle_selection('down')
        rotation_angle_label = tk.Label(postprocessing_frame,
                                        text='°',
                                        width=1, font=("Arial", self.font_size))
        rotation_angle_label.grid(row=postprocessing_row, column=1)
        rotation_angle_label.config(state=NORMAL)
        postprocessing_row += 1

        ### Stabilization controls
        # Custom film perforation template
        custom_stabilization_btn = Button(postprocessing_frame,
                                        text='Define custom template',
                                        width=18, height=1,
                                        command=select_custom_template,
                                        activebackground='green',
                                        activeforeground='white', font=("Arial", self.font_size))
        custom_stabilization_btn.config(relief=SUNKEN if template_list.get_active_type() == 'Custom' else RAISED)
        custom_stabilization_btn.grid(row=postprocessing_row, column=0, columnspan=2, padx=5, pady=5, sticky=W)
        as_tooltips.add(custom_stabilization_btn,
                    "Define a custom template for this project (vs the automatic template defined by AfterScan)")

        low_contrast_custom_template = tk.BooleanVar(master=win, value=False)
        low_contrast_custom_template_checkbox = tk.Checkbutton(
            postprocessing_frame, text='Low contrast helper',
            variable=low_contrast_custom_template, onvalue=True, offvalue=False, width=16,
            command=low_contrast_custom_template_selection, font=("Arial", self.font_size))
        low_contrast_custom_template_checkbox.grid(row=postprocessing_row, column=1,
                                            columnspan=2, sticky=E)
        as_tooltips.add(low_contrast_custom_template_checkbox, "Activate when defining a custom template using a low contrast frame")

        postprocessing_row += 1

        # Check box to do stabilization or not
        perform_stabilization = tk.BooleanVar(master=win, value=False)
        perform_stabilization_checkbox = tk.Checkbutton(
            postprocessing_frame, text='Stabilize',
            variable=perform_stabilization, onvalue=True, offvalue=False, width=7,
            command=perform_stabilization_selection, font=("Arial", self.font_size))
        perform_stabilization_checkbox.grid(row=postprocessing_row, column=0,
                                            columnspan=1, sticky=W)
        as_tooltips.add(perform_stabilization_checkbox, "Stabilize generated frames. Sprocket hole is used as common reference, it needs to be clearly visible")
        # Label to display the match level of current frame to template
        stabilization_threshold_match_label = Label(postprocessing_frame, width=4, borderwidth=1, relief='sunken', font=("Arial", self.font_size))
        stabilization_threshold_match_label.grid(row=postprocessing_row, column=0, sticky=E)
        as_tooltips.add(stabilization_threshold_match_label, "Dynamically displays the match quality of the sprocket hole template. Green is good, orange acceptable, red is bad")

        # Extended search checkbox (replace radio buttons for fast/precise stabilization)
        extended_stabilization = tk.BooleanVar(master=win, value=False)
        extended_stabilization_checkbox = tk.Checkbutton(
            postprocessing_frame, text='Extend',
            variable=extended_stabilization, onvalue=True, offvalue=False, width=6,
            command=extended_stabilization_selection, font=("Arial", self.font_size))
        #extended_stabilization_checkbox.grid(row=postprocessing_row, column=1, columnspan=1, sticky=W)
        extended_stabilization_checkbox.forget()
        as_tooltips.add(extended_stabilization_checkbox, "Extend the area where AfterScan looks for sprocket holes. In some cases this might help")

        # Stabilization shift: Since film might not be centered around hole(s) this gives the option to move it up/down
        # Spinbox for gamma correction
        stabilization_shift_label = tk.Label(postprocessing_frame, text='Offset X/Y:',
                                            width=14, font=("Arial", self.font_size))
        stabilization_shift_label.grid(row=postprocessing_row, column=1, columnspan=1, sticky=E)

        stabilization_shift_x_value = tk.IntVar(master=win, value=0)
        stabilization_shift_x_spinbox = tk.Spinbox(postprocessing_frame, width=3, command=select_stabilization_shift_x,
            textvariable=stabilization_shift_x_value, from_=-150, to=150, increment=-5, font=("Arial", self.font_size))
        stabilization_shift_x_spinbox.grid(row=postprocessing_row, column=2, sticky=W)
        as_tooltips.add(stabilization_shift_x_spinbox, "Allows to shift the frame left or right after stabilization "
                                    "(to compensate for films where the frame is not centered around the hole/holes)")
        stabilization_shift_x_spinbox.bind("<FocusOut>", select_stabilization_shift_x)

        stabilization_shift_y_value = tk.IntVar(master=win, value=0)
        stabilization_shift_y_spinbox = tk.Spinbox(postprocessing_frame, width=3, command=select_stabilization_shift_y,
            textvariable=stabilization_shift_y_value, from_=-150, to=150, increment=-5, font=("Arial", self.font_size))
        stabilization_shift_y_spinbox.grid(row=postprocessing_row, column=2, sticky=E)
        as_tooltips.add(stabilization_shift_y_spinbox, "Allows to shift the frame up or down after stabilization "
                                    "(to compensate for films where the frame is not centered around the hole/holes)")
        stabilization_shift_y_spinbox.bind("<FocusOut>", select_stabilization_shift_y)

        postprocessing_row += 1

        ### Cropping controls
        # Check box to do cropping or not
        cropping_btn = Button(postprocessing_frame, text='Define crop area',
                            width=12, height=1, command=select_cropping_area,
                            activebackground='green', activeforeground='white',
                            wraplength=120, font=("Arial", self.font_size))
        cropping_btn.grid(row=postprocessing_row, column=0, sticky=E)
        as_tooltips.add(cropping_btn, "Open popup window to define the cropping rectangle")

        perform_cropping = tk.BooleanVar(master=win, value=False)
        perform_cropping_checkbox = tk.Checkbutton(
            postprocessing_frame, text='Crop', variable=perform_cropping,
            onvalue=True, offvalue=False, command=perform_cropping_selection,
            width=4, font=("Arial", self.font_size))
        perform_cropping_checkbox.grid(row=postprocessing_row, column=1, sticky=W)
        as_tooltips.add(perform_cropping_checkbox, "Crop generated frames to the user-defined limits ('Define crop area' button)")

        force_4_3_crop = tk.BooleanVar(master=win, value=False)
        force_4_3_crop_checkbox = tk.Checkbutton(
            postprocessing_frame, text='4:3', variable=force_4_3_crop,
            onvalue=True, offvalue=False, command=force_4_3_selection,
            width=4, font=("Arial", self.font_size))
        force_4_3_crop_checkbox.grid(row=postprocessing_row, column=1, sticky=E)
        as_tooltips.add(force_4_3_crop_checkbox, "Enforce 4:3 aspect ratio when defining the cropping rectangle")

        force_16_9_crop = tk.BooleanVar(master=win, value=False)
        force_16_9_crop_checkbox = tk.Checkbutton(
            postprocessing_frame, text='16:9', variable=force_16_9_crop,
            onvalue=True, offvalue=False, command=force_16_9_selection,
            width=4, font=("Arial", self.font_size))
        force_16_9_crop_checkbox.grid(row=postprocessing_row, column=2, sticky=W)
        as_tooltips.add(force_16_9_crop_checkbox, "Enforce 16:9 aspect ratio when defining the cropping rectangle")

        postprocessing_row += 1

        # Check box to perform denoise
        perform_denoise = tk.BooleanVar(master=win, value=False)
        perform_denoise_checkbox = tk.Checkbutton(
            postprocessing_frame, text='Denoise', variable=perform_denoise,
            onvalue=True, offvalue=False, command=perform_denoise_selection,
            font=("Arial", self.font_size))
        perform_denoise_checkbox.grid(row=postprocessing_row, column=0, sticky=W)
        as_tooltips.add(perform_denoise_checkbox, "Apply denoise algorithm (using OpenCV's 'fastNlMeansDenoisingColored') to the generated frames")

        # Check box to perform sharpness
        perform_sharpness = tk.BooleanVar(master=win, value=False)
        perform_sharpness_checkbox = tk.Checkbutton(
            postprocessing_frame, text='Sharpen', variable=perform_sharpness,
            onvalue=True, offvalue=False, command=perform_sharpness_selection,
            font=("Arial", self.font_size))
        perform_sharpness_checkbox.grid(row=postprocessing_row, column=1, sticky=W)
        as_tooltips.add(perform_sharpness_checkbox, "Apply sharpen algorithm (using OpenCV's 'filter2D') to the generated frames")

        # Check box to do gamma correction
        perform_gamma_correction = tk.BooleanVar(master=win, value=False)
        perform_gamma_correction_checkbox = tk.Checkbutton(
            postprocessing_frame, text='GC:', variable=perform_gamma_correction, command=perform_gamma_correction_selection,
            onvalue=True, offvalue=False, font=("Arial", self.font_size))
        perform_gamma_correction_checkbox.grid(row=postprocessing_row, column=2, sticky=W)
        perform_gamma_correction_checkbox.config(state=NORMAL)
        as_tooltips.add(perform_gamma_correction_checkbox, "Apply gamma correction to the generated frames")

        # Spinbox for gamma correction
        gamma_correction_str = tk.StringVar(master=win, value="2.2")
        gamma_correction_spinbox = tk.Spinbox(postprocessing_frame, width=3, command=select_gamma_correction_value,
            textvariable=gamma_correction_str, from_=0.1, to=4, format="%.1f", increment=0.1, font=("Arial", self.font_size))
        gamma_correction_spinbox.grid(row=postprocessing_row, column=2, sticky=E)
        as_tooltips.add(gamma_correction_spinbox, "Gamma correction value (default is 2.2, has to be greater than zero)")
        # Bind focus-out event to enforce the minimum value
        gamma_correction_spinbox.bind("<FocusOut>", gamma_enforce_min_value)

        postprocessing_row += 1

        # This checkbox enables 'fake' frame completion when, due to stabilization process, part of the frame is lost at the
        # top or at the bottom. It is named 'fake' because to fill in the missing part, a fragment of the previous or next
        # frame is used. Not perfect, but better than leaving the missing part blank, as it would happen without this.
        # Also, for this to work the cropping rectangle should encompass the full frame, top to bottom.
        # And yes, in theory we could pick the missing fragment of the same frame by picking the picture of the
        # next/previous frame, BUT it is not given that it will be there, as the next/previous frame might have been
        # captured without the required part.
        frame_fill_type = tk.StringVar(master=win)
        perform_fill_none_rb = Radiobutton(postprocessing_frame, text='No frame fill',
                                        variable=frame_fill_type, value='none', font=("Arial", self.font_size))
        perform_fill_none_rb.grid(row=postprocessing_row, column=0, sticky=W)
        as_tooltips.add(perform_fill_none_rb, "Badly aligned frames will be left with the missing part of the image black after stabilization")
        perform_fill_fake_rb = Radiobutton(postprocessing_frame, text='Fake fill',
                                        variable=frame_fill_type, value='fake', font=("Arial", self.font_size))
        perform_fill_fake_rb.grid(row=postprocessing_row, column=1, sticky=W)
        as_tooltips.add(perform_fill_fake_rb, "Badly aligned frames will have the missing part of the image completed with a fragment of the next/previous frame after stabilization")
        perform_fill_dumb_rb = Radiobutton(postprocessing_frame, text='Dumb fill',
                                        variable=frame_fill_type, value='dumb', font=("Arial", self.font_size))
        perform_fill_dumb_rb.grid(row=postprocessing_row, column=2, sticky=W)
        as_tooltips.add(perform_fill_dumb_rb, "Badly aligned frames will have the missing part of the image filled with the adjacent pixel row after stabilization")
        frame_fill_type.set('fake')

        postprocessing_row += 1

        # Define video generating area ************************************
        video_frame = LabelFrame(right_area_frame,
                                text='Video generation',
                                width=30, height=8, font=("Arial", self.font_size-2))
        video_frame.pack(padx=2, pady=2, ipadx=5, expand=True, fill="both")
        video_row = 0
        video_frame.grid_columnconfigure(0, weight=1)
        video_frame.grid_columnconfigure(1, weight=1)
        video_frame.grid_columnconfigure(2, weight=1)

        # Check box to generate video or not
        generate_video = tk.BooleanVar(master=win, value=False)
        generate_video_checkbox = tk.Checkbutton(video_frame,
                                                text='Video',
                                                variable=generate_video,
                                                onvalue=True, offvalue=False,
                                                command=generate_video_selection,
                                                width=5, font=("Arial", self.font_size))
        generate_video_checkbox.grid(row=video_row, column=0, sticky=W, padx=5)
        generate_video_checkbox.config(state=NORMAL if ffmpeg_installed
                                    else DISABLED)
        as_tooltips.add(generate_video_checkbox, "Generate an MP4 video, once all frames have been processed")

        # Check box to skip frame regeneration
        skip_frame_regeneration = tk.BooleanVar(master=win, value=False)
        skip_frame_regeneration_cb = tk.Checkbutton(
            video_frame, text='Skip Frame regeneration',
            variable=skip_frame_regeneration, onvalue=True, offvalue=False,
            width=20, font=("Arial", self.font_size))
        skip_frame_regeneration_cb.grid(row=video_row, column=1,
                                        columnspan=2, sticky=W, padx=5)
        skip_frame_regeneration_cb.config(state=NORMAL if ffmpeg_installed
                                        else DISABLED)
        as_tooltips.add(skip_frame_regeneration_cb, "If frames have ben already generated in a previous run, and you want to only generate the vieo, check this one")

        video_row += 1

        # Video target folder
        video_target_dir_str = tk.StringVar(master=win)
        video_target_dir = Entry(video_frame, textvariable=video_target_dir_str, width=30, borderwidth=1, font=("Arial", self.font_size))
        video_target_dir.grid(row=video_row, column=0, columnspan=2, sticky=W, padx=5)
        video_target_dir.bind('<<Paste>>', lambda event, entry=video_target_dir: self._on_paste_all_entries(event, entry))
        as_tooltips.add(video_target_dir, "Directory where the generated video will be stored")

        video_target_folder_btn = Button(video_frame, text='Target', width=6,
                                height=1, command=set_video_target_folder,
                                activebackground='green',
                                activeforeground='white', wraplength=80, font=("Arial", self.font_size))
        video_target_folder_btn.grid(row=video_row, column=2, columnspan=2, sticky=W, padx=5)
        as_tooltips.add(video_target_folder_btn, "Selects directory where the generated video will be stored")
        video_row += 1

        # Video filename
        video_filename_str = tk.StringVar(master=win)
        video_filename_label = Label(video_frame, text='Video filename:', font=("Arial", self.font_size))
        video_filename_label.grid(row=video_row, column=0, sticky=W, padx=5)
        video_filename_name = Entry(video_frame, textvariable=video_filename_str, name="video_filename", 
                                    validate="key", validatecommand=vcmd,
                                    width=26 if self.big_size else 26, borderwidth=1, font=("Arial", self.font_size))
        video_filename_name.grid(row=video_row, column=1, columnspan=2, sticky=W, padx=5)
        video_filename_name.bind('<<Paste>>', lambda event, entry=video_filename_name: self._on_paste_all_entries(event, entry))
        as_tooltips.add(video_filename_name, "Filename of video to be created")

        video_row += 1

        # Video title (add title at the start of the video)
        video_title_str = tk.StringVar(master=win)
        video_title_label = Label(video_frame, text='Video title:', font=("Arial", self.font_size))
        video_title_label.grid(row=video_row, column=0, sticky=W, padx=5)
        video_title_name = Entry(video_frame, textvariable=video_title_str, name="video_title", 
                                validate="key", validatecommand=vcmd,
                                width=26 if self.big_size else 26, borderwidth=1, font=("Arial", self.font_size))
        video_title_name.grid(row=video_row, column=1, columnspan=2, sticky=W, padx=5)
        video_title_name.bind('<<Paste>>', lambda event, entry=video_title_name: self._on_paste_all_entries(event, entry))
        as_tooltips.add(video_title_name, "Video title. If entered, a simple title sequence will be generated at the start of the video, using a sequence randomly selected from the same video, running at half speed")

        video_row += 1

        # Drop down to select FPS
        # Dropdown menu options
        fps_list = [
            "8",
            "9",
            "16",
            "16.67",
            "18",
            "24",
            "25",
            "29.97",
            "30",
            "48",
            "50"
        ]

        # datatype of menu text
        video_fps_dropdown_selected = tk.StringVar(master=win)

        # initial menu text
        video_fps_dropdown_selected.set("18")

        # Create FPS Dropdown menu
        video_fps_frame = Frame(video_frame)
        video_fps_frame.grid(row=video_row, column=0, sticky=W)
        video_fps_label = Label(video_fps_frame, text='FPS:', font=("Arial", self.font_size))
        video_fps_label.pack(side=LEFT, anchor=W, padx=5)
        video_fps_label.config(state=DISABLED)
        video_fps_dropdown = OptionMenu(video_fps_frame,
                                        video_fps_dropdown_selected, *fps_list,
                                        command=set_fps)
        video_fps_dropdown.config(takefocus=1, font=("Arial", self.font_size))
        video_fps_dropdown.pack(side=LEFT, anchor=E, padx=5)
        video_fps_dropdown.config(state=DISABLED)
        as_tooltips.add(video_fps_dropdown, "Number of frames per second (FPS) of the video to be generated. Usually Super8 goes at 18 FPS, and Regular 8 at 16 FPS, although some cameras allowed to use other speeds (faster for smoother movement, slower for extended play time)")

        # Create FFmpeg preset options
        ffmpeg_preset_frame = Frame(video_frame)
        ffmpeg_preset_frame.grid(row=video_row, column=1, columnspan=2, sticky=W, padx=5)
        ffmpeg_preset = tk.StringVar(master=win)
        ffmpeg_preset_rb1 = Radiobutton(ffmpeg_preset_frame,
                                        text="Best quality (slow)",
                                        variable=ffmpeg_preset, value='veryslow', font=("Arial", self.font_size))
        ffmpeg_preset_rb1.pack(side=TOP, anchor=W, padx=5)
        ffmpeg_preset_rb1.config(state=DISABLED)
        as_tooltips.add(ffmpeg_preset_rb1, "Best quality, but very slow encoding. Maps to the same ffmpeg option")

        ffmpeg_preset_rb2 = Radiobutton(ffmpeg_preset_frame, text="Medium",
                                        variable=ffmpeg_preset, value='medium', font=("Arial", self.font_size))
        ffmpeg_preset_rb2.pack(side=TOP, anchor=W, padx=5)
        ffmpeg_preset_rb2.config(state=DISABLED)
        as_tooltips.add(ffmpeg_preset_rb2, "Compromise between quality and encoding speed. Maps to the same ffmpeg option")
        ffmpeg_preset_rb3 = Radiobutton(ffmpeg_preset_frame,
                                        text="Fast (low quality)",
                                        variable=ffmpeg_preset, value='veryfast', font=("Arial", self.font_size))
        ffmpeg_preset_rb3.pack(side=TOP, anchor=W, padx=5)
        ffmpeg_preset_rb3.config(state=DISABLED)
        as_tooltips.add(ffmpeg_preset_rb3, "Faster encoding speed, lower quality (but not so much IMHO). Maps to the same ffmpeg option")
        ffmpeg_preset.set('medium')
        video_row += 1

        # Drop down to select resolution
        # datatype of menu text
        resolution_dropdown_selected = tk.StringVar(master=win)

        # initial menu text
        resolution_dropdown_selected.set("1920x1440 (1080P)")

        # Create resolution Dropdown menu
        resolution_frame = Frame(video_frame)
        resolution_frame.grid(row=video_row, column=0, columnspan= 2, sticky=W)
        resolution_label = Label(resolution_frame, text='Resolution:', font=("Arial", self.font_size))
        resolution_label.pack(side=LEFT, anchor=W, padx=5)
        resolution_label.config(state=DISABLED)
        resolution_dropdown = OptionMenu(resolution_frame,
                                        resolution_dropdown_selected, *resolution_dict.keys(),
                                        command=set_resolution)
        resolution_dropdown.config(takefocus=1, font=("Arial", self.font_size))
        resolution_dropdown.pack(side=LEFT, anchor=E, padx=5)
        resolution_dropdown.config(state=DISABLED)
        as_tooltips.add(resolution_dropdown, "Resolution to be used when generating the video")

        # Create button to play the video
        video_play_btn = Button(video_frame, text='▶', width=8,
                                height=1, command=play_video,
                                activebackground='green',
                                activeforeground='white', wraplength=80, font=("Arial", self.font_size))
        video_play_btn.grid(row=video_row, column=2, sticky=E, padx=5)
        as_tooltips.add(video_play_btn, "Play the generated video")

        video_row += 1

        # Extra (expert) area ***************************************************
        if ExpertMode:
            extra_frame = LabelFrame(right_area_frame,
                                    text='Expert options',
                                    width=50, height=8, font=("Arial", self.font_size-2))
            extra_frame.pack(padx=5, pady=5, ipadx=5, ipady=5, expand=True, fill="both")
            extra_frame.grid_columnconfigure(0, weight=1)
            extra_frame.grid_columnconfigure(1, weight=1)
            extra_row = 0

            # Check box to display misaligned frame monitor/editor
            display_template_popup_btn = Button(extra_frame,
                                                text='FrameSync Editor',
                                                command=FrameSync_Viewer_popup,
                                                width=15, font=("Arial", self.font_size))
            display_template_popup_btn.config(relief=SUNKEN if FrameSync_Viewer_opened else RAISED)
            display_template_popup_btn.grid(row=extra_row, column=0, padx=5, sticky="nsew")
            ### extra_frame.grid_columnconfigure(0, weight=1)
            as_tooltips.add(display_template_popup_btn, "Display popup window with dynamic debug information.Useful for developers only")

            # Settings button, at the bottom of top left area
            options_btn = Button(extra_frame, text="Settings", command=cmd_settings_popup, width=15,
                                relief=RAISED, font=("Arial", self.font_size), name='options_btn')
            options_btn.widget_type = "general"
            options_btn.grid(row=extra_row, column=1, padx=5, sticky="nsew")
            as_tooltips.add(options_btn, "Set AfterScan options.")
            extra_row += 1

            # Spinbox to select stabilization threshold - Ignored, to be removed in the future
            stabilization_threshold_label = tk.Label(extra_frame,
                                                    text='Threshold:',
                                                    width=11, font=("Arial", self.font_size))
            #stabilization_threshold_label.grid(row=extra_row, column=1, columnspan=1, sticky=E)
            stabilization_threshold_label.grid_forget()
            stabilization_threshold_str = tk.StringVar(master=win, value=str(StabilizationThreshold))
            stabilization_threshold_selection_aux = extra_frame.register(
                stabilization_threshold_selection)
            stabilization_threshold_spinbox = tk.Spinbox(
                extra_frame,
                command=(stabilization_threshold_selection_aux, '%d'), width=6,
                textvariable=stabilization_threshold_str, from_=0, to=255, font=("Arial", self.font_size))
            #stabilization_threshold_spinbox.grid(row=extra_row, column=2, sticky=W)
            stabilization_threshold_spinbox.grid_forget()
            stabilization_threshold_spinbox.bind("<FocusOut>", stabilization_threshold_spinbox_focus_out)
            as_tooltips.add(stabilization_threshold_spinbox, "Threshold value to isolate the sprocket hole from the rest of the image while definint the custom template")

            extra_row += 1

        # Define job list area ***************************************************
        # Replace listbox with treeview
        # Define style for labelframe
        style = ttk.Style()
        style.configure("TLabelframe.Label", font=("Arial", self.font_size-2))
        # Create a frame to hold Treeview and scrollbars
        job_list_frame = ttk.LabelFrame(left_area_frame,
                                text='Job List',
                                width=50, height=8)
        job_list_frame.pack(side=TOP, padx=2, pady=2, anchor=W)

        # Create Treeview with a single column
        job_list_treeview = ttk.Treeview(job_list_frame, columns=("description"))

        # Define style for headings
        style.configure("Treeview.Heading", font=("Arial", self.font_size, "bold")) #Change header font.

        # Define the single column
        name_width = 130 if ForceSmallSize else 200
        description_width = 250 if ForceSmallSize else 340
        job_list_treeview.heading("#0", text="Name")
        job_list_treeview.heading("description", text="Description")
        job_list_treeview.column("#0", anchor="w", width=name_width, minwidth=name_width, stretch=tk.NO)
        job_list_treeview.column("description", anchor="w", width=description_width, minwidth=1400, stretch=tk.NO)

        # job listbox scrollbars
        job_list_listbox_scrollbar_y = ttk.Scrollbar(job_list_frame, orient="vertical", command=job_list_treeview.yview)
        job_list_treeview.configure(yscrollcommand=job_list_listbox_scrollbar_y.set)
        job_list_listbox_scrollbar_y.grid(row=0, column=1, sticky=NS)
        job_list_listbox_scrollbar_x = ttk.Scrollbar(job_list_frame, orient="horizontal", command=job_list_treeview.xview)
        job_list_treeview.configure(xscrollcommand=job_list_listbox_scrollbar_x.set)
        job_list_listbox_scrollbar_x.grid(row=1, column=0, columnspan=1, sticky=EW)

        # Layout
        job_list_treeview.grid(column=0, row=0, padx=5, pady=2, ipadx=5)

        # Define tags for different row colors
        job_list_treeview.tag_configure("pending", foreground="black")
        job_list_treeview.tag_configure("ongoing", foreground="blue")
        job_list_treeview.tag_configure("done", foreground="green")
        job_list_treeview.tag_configure("joblist_font", font=("Arial", self.font_size))

        # Bind the keys to be used alog
        job_list_treeview.bind("<Delete>", job_list_delete_current)
        job_list_treeview.bind("<Return>", job_list_load_current)
        job_list_treeview.bind("<KP_Enter>", job_list_load_current)
        job_list_treeview.bind("<Double - Button - 1>", job_list_load_current)
        job_list_treeview.bind("r", job_list_rerun_current)
        job_list_treeview.bind('<<ListboxSelect>>', job_list_process_selection)
        job_list_treeview.bind("u", job_list_move_up)
        job_list_treeview.bind("d", job_list_move_down)
        job_list_listbox_disabled = False   # to prevent processing clicks on listbox, as disabling it will prevent checkign status of each job
        
        # Define job list button area
        job_list_btn_frame = Frame(job_list_frame,
                                width=50, height=8)
        job_list_btn_frame.grid(row=0, column=2, padx=2, pady=2, sticky=W)

        # Add job button
        add_job_btn = Button(job_list_btn_frame, text="Add job", width=12, height=1,
                        command=job_list_add_current, activebackground='green',
                        activeforeground='white', wraplength=100, font=("Arial", self.font_size))
        add_job_btn.pack(side=TOP, padx=2, pady=2)
        as_tooltips.add(add_job_btn, "Add to job list a new job using the current settings defined on the right area of the AfterScan window")

        # Delete job button
        delete_job_btn = Button(job_list_btn_frame, text="Delete job", width=12, height=1,
                        command=job_list_delete_selected, activebackground='green',
                        activeforeground='white', wraplength=100, font=("Arial", self.font_size))
        delete_job_btn.pack(side=TOP, padx=2, pady=2)
        as_tooltips.add(delete_job_btn, "Delete currently selected job from list")

        # Rerun job button
        rerun_job_btn = Button(job_list_btn_frame, text="Rerun job", width=12, height=1,
                        command=job_list_rerun_selected, activebackground='green',
                        activeforeground='white', wraplength=100, font=("Arial", self.font_size))
        rerun_job_btn.pack(side=TOP, padx=2, pady=2)
        as_tooltips.add(rerun_job_btn, "Toggle 'run' state of currently selected job in list")

        # Start processing job button
        start_batch_btn = Button(job_list_btn_frame, text="Start batch", width=12, height=1,
                        command=start_processing_job_list, activebackground='green',
                        activeforeground='white', wraplength=100, font=("Arial", self.font_size))
        start_batch_btn.pack(side=TOP, padx=2, pady=2)
        as_tooltips.add(start_batch_btn, "Start processing jobs in list")

        # Suspend on end checkbox
        # suspend_on_joblist_end = tk.BooleanVar(master=win, value=False)
        # suspend_on_joblist_end_cb = tk.Checkbutton(
        #     job_list_btn_frame, text='Suspend on end',
        #     variable=suspend_on_joblist_end, onvalue=True, offvalue=False,
        #     width=13)
        # suspend_on_joblist_end_cb.pack(side=TOP, padx=2, pady=2)

        suspend_on_completion_label = Label(job_list_btn_frame, text='Suspend on:', font=("Arial", self.font_size))
        suspend_on_completion_label.pack(side=TOP, anchor=W, padx=2, pady=2)
        suspend_on_completion = tk.StringVar(master=win)
        suspend_on_batch_completion_rb = Radiobutton(job_list_btn_frame, text="Job completion",
                                    variable=suspend_on_completion, value='job_completion', font=("Arial", self.font_size))
        suspend_on_batch_completion_rb.pack(side=TOP, anchor=W, padx=2, pady=2)
        as_tooltips.add(suspend_on_batch_completion_rb, "Suspend computer when all jobs in list have been processed")
        suspend_on_job_completion_rb = Radiobutton(job_list_btn_frame, text="Batch completion",
                                    variable=suspend_on_completion, value='batch_completion', font=("Arial", self.font_size))
        suspend_on_job_completion_rb.pack(side=TOP, anchor=W, padx=2, pady=2)
        as_tooltips.add(suspend_on_batch_completion_rb, "Suspend computer when current job being processed is complete")
        no_suspend_rb = Radiobutton(job_list_btn_frame, text="No suspend",
                                    variable=suspend_on_completion, value='no_suspend', font=("Arial", self.font_size))
        no_suspend_rb.pack(side=TOP, anchor=W, padx=2, pady=2)
        as_tooltips.add(suspend_on_batch_completion_rb, "Do not suspend when done")

        suspend_on_completion.set("no_suspend")

        postprocessing_bottom_frame = Frame(video_frame, width=30)
        postprocessing_bottom_frame.grid(row=video_row, column=0)
