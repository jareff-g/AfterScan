"""
****************************************************************************************************************
Class DefineRectangle
Alow user to define a rectangle (for Cropping an dCustom templates) directly on the main canvas

Licensed under a MIT LICENSE.

More info in README.md file
****************************************************************************************************************
"""
__author__ = 'Gemini/Juan Remirez de Esparza'
__copyright__ = "Copyright 2022/25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "Tooltips"
__version__ = "1.0.1"
__date__ = "2025-03-17"
__version_highlight__ = "DefineRectangle - First version"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import tkinter as tk
from PIL import Image, ImageTk

class DefineRectangle:
    def __init__(self, canvas, source_image, aspect_ratio=None):
        self.canvas = canvas
        self.aspect_ratio = aspect_ratio
        self.photo = None
        self.image_id = None
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.rect_coords = [0, 0, 0, 0]
        self.original_image = source_image  # Store the original PIL Image
 
        self.load_and_resize_image()
        self.setup_bindings()

    def load_and_resize_image(self):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        image = self.original_image.copy()  # Create a copy for resizing
        image.thumbnail((canvas_width, canvas_height), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(image)
        if self.image_id:
            self.canvas.itemconfig(self.image_id, image=self.photo)
        else:
            self.image_id = self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def setup_bindings(self):
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Left>", lambda event: self.move_rect(-2, 0))
        self.canvas.bind("<Right>", lambda event: self.move_rect(2, 0))
        self.canvas.bind("<Up>", lambda event: self.move_rect(0, -2))
        self.canvas.bind("<Down>", lambda event: self.move_rect(0, 2))
        self.canvas.bind("<b>", lambda event: self.resize_rect(1.02))
        self.canvas.bind("<s>", lambda event: self.resize_rect(0.98))
        self.canvas.bind("<Configure>", lambda event: self.load_and_resize_image())
        self.canvas.focus_set()

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.photo:
            self.start_x = min(event.x, self.photo.width())

    def on_motion(self, event):
        if self.start_x is not None and self.start_y is not None:
            end_x = event.x
            end_y = event.y
            if self.photo:
                end_x = min(event.x, self.photo.width())

            if self.aspect_ratio:
                width = abs(end_x - self.start_x)
                height = width / self.aspect_ratio
                if end_y < self.start_y:
                    end_y = self.start_y - height
                else:
                    end_y = self.start_y + height

            self.rect_coords = [
                min(self.start_x, end_x),
                min(self.start_y, end_y),
                max(self.start_x, end_x),
                max(self.start_y, end_y),
            ]
            self.redraw_rect()

    def on_release(self, event):
        self.start_x = None
        self.start_y = None

    def redraw_rect(self):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            *self.rect_coords, outline="red"
        )

    def move_rect(self, dx, dy):
        self.rect_coords = [coord + offset for coord, offset in zip(self.rect_coords, [dx, dy, dx, dy])]
        self.redraw_rect()

    def resize_rect(self, scale_factor):
        x1, y1, x2, y2 = self.rect_coords
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        width = (x2 - x1) * scale_factor
        height = (y2 - y1) * scale_factor
        if self.aspect_ratio:
            height = width / self.aspect_ratio
        x1 = center_x - width / 2
        y1 = center_y - height / 2
        x2 = center_x + width / 2
        y2 = center_y + height / 2
        self.rect_coords = [x1, y1, x2, y2]
        self.redraw_rect()

    def draw_initial_rectangle(self, x1, y1, x2, y2):
        """Draws an initial rectangle on the canvas."""
        if self.photo:
            original_width, original_height = self.original_image.size
            image_width = self.photo.width()
            image_height = self.photo.height()

            #Ensure the rectangle is inside the image.
            x1 = int(max(0, min(x1*image_width/original_width, image_width)))
            y1 = int(max(0, min(y1*image_height/original_height, image_height)))
            x2 = int(max(0, min(x2*image_width/original_width, image_width)))
            y2 = int(max(0, min(y2*image_height/original_height, image_height)))

            self.rect_coords = [x1, y1, x2, y2]
            self.redraw_rect()
            ###self.initial_rect_coords = [x1, y1, x2, y2] #store initial rectangle coords

    def get_crop_dimensions(self):
        if not self.original_image:
            return None  # No original image loaded

        original_width, original_height = self.original_image.size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if not self.photo:
            return None

        image_width = self.photo.width()
        image_height = self.photo.height()

        x1, y1, x2, y2 = self.rect_coords

        # Calculate relative coordinates
        relative_x1 = int(x1 / image_width * original_width)
        relative_y1 = int(y1 / image_height * original_height)
        relative_x2 = int(x2 / image_width * original_width)
        relative_y2 = int(y2 / image_height * original_height)

        return (relative_x1, relative_y1, relative_x2, relative_y2)

    def destroy(self):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        if self.image_id:
            self.canvas.delete(self.image_id)
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.canvas.unbind("<Left>")
        self.canvas.unbind("<Right>")
        self.canvas.unbind("<Up>")
        self.canvas.unbind("<Down>")
        self.canvas.unbind("<b>")
        self.canvas.unbind("<s>")
        self.canvas.unbind("<Configure>")
        self.photo = None
        self.original_image = None
        self.rect_coords = [0, 0, 0, 0]
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.image_id = None
        self.canvas = None
        self.aspect_ratio = None

    def wait_for_enter(self):
        self.wait_variable = tk.IntVar()  # Create a Tkinter variable to wait on

        def set_variable(event):
            self.wait_variable.set(1)  # Set the variable when Enter is pressed

        self.canvas.bind("<Return>", set_variable)  # Bind Enter key
        self.canvas.wait_variable(self.wait_variable)  # Wait for the variable to be set
        self.canvas.unbind("<Return>") #Clean up the event bind.
        return self.get_crop_dimensions()

