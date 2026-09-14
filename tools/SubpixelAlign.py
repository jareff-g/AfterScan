#!/usr/bin/env python
"""
SubpixelAlign - Function to perform subpixel alignment

Preliminary tests did not show significant differences in alignment quality


Licensed under a MIT LICENSE.

More info in README.md file

!!! This code does not work. It assumes consecutive images in consecutive calls, which is not the case !!!

"""

__author__ = 'Juan Remirez de Esparza'
__copyright__ = "Copyright 2022-25, Juan Remirez de Esparza"
__credits__ = ["Juan Remirez de Esparza"]
__license__ = "MIT"
__module__ = "SubpixelAlign"
__version__ = "1.0.7"
__date__ = "2025-11-20"
__version_highlight__ = "First revision"
__maintainer__ = "Juan Remirez de Esparza"
__email__ = "jremirez@hotmail.com"
__status__ = "Development"

import cv2
import numpy as np

class FrameAligner:
    """
    Clase para realizar la alineación subpixelar de fotogramas, 
    manteniendo el estado del fotograma anterior y el índice para 
    asegurar la continuidad.
    """
    def __init__(self):
        """
        Inicializa las variables de estado persistente.
        """
        # Variables persistentes (de estado)
        self.previous_frame_idx = None
        self.previous_bw_left_stripe = None # Almacenamos en gris para eficiencia
        self.accumulated_shift = (0.0, 0.0) # Para futura estabilización absoluta

    def subpixel_align(self, frame_idx: int, image: np.ndarray, left_stripe: np.ndarray) -> np.ndarray:
        """
        Alinea el 'image' actual con respecto al fotograma anterior usando 
        cv2.phaseCorrelate y devuelve la imagen alineada.

        Args:
            frame_idx: Índice del fotograma actual (int).
            image: Imagen actual (numpy.ndarray, BGR a color).
            left_stripe: Fragmento (ROI) de la imagen actual (BGR) usado para la correlación.
        Returns:
            La imagen actual alineada (numpy.ndarray).
        """
        
        # El left stripe actual se convierte a gris para el cálculo del shift
        #bw_left_stripe = cv2.cvtColor(left_stripe, cv2.COLOR_BGR2GRAY)
        if len(left_stripe.shape) == 3:
             bw_left_stripe = cv2.cvtColor(left_stripe, cv2.COLOR_BGR2GRAY)
        else:
             # Si ya es gris (2D), úsalo directamente.
             bw_left_stripe = left_stripe
        
        aligned_image = image.copy() # Usaremos esta copia para el output

        if frame_idx > 0: # No hay alineación para el primer fotograma
            
            # --- VERIFICACIÓN DE CONTINUIDAD ---
            # Asegura que estamos comparando el fotograma N con el N-1
            if self.previous_bw_left_stripe is not None and self.previous_frame_idx == frame_idx - 1:
                
                # 1. Preparación de entradas (normalización a float32)
                # src1 es la imagen actual (target)
                src1 = bw_left_stripe.astype(np.float32) / 255.0
                # src2 es la imagen anterior (reference)
                src2 = self.previous_bw_left_stripe.astype(np.float32) / 255.0
                
                # --- VERIFICACIÓN DE DEBUGGING (Añadir temporalmente) ---
                if src1.ndim != 2 or src2.ndim != 2:
                    raise Exception(f"PhaseCorrelate Input Error: Ambos src deben ser 2D (escala de grises). src1 dims: {src1.ndim}, src2 dims: {src2.ndim}")
                # --------------------------------------------------------
                
                # 2. Correlación de Fase
                shift, _ = cv2.phaseCorrelate(src1, src2)
                dx = shift[0]
                dy = shift[1]

                # 3. Aplicar Transformación (Warping)
                M = np.float32([[1, 0, dx], [0, 1, dy]])
                rows, cols = image.shape
                
                # Aplicamos el shift (dx, dy) al fotograma original a color
                aligned_image = cv2.warpAffine(image, M, (cols, rows))
                
                # Opcional: Acumular el shift (para estabilización global)
                # self.accumulated_shift = (self.accumulated_shift[0] + dx, 
                #                           self.accumulated_shift[1] + dy)
            
            else:
                print(f"Advertencia: Salto detectado en frame {frame_idx}. Reiniciando referencia.")

        # --- ACTUALIZACIÓN DEL ESTADO (PERSISTENCIA) ---
        self.previous_frame_idx = frame_idx
        # Almacenamos el fotograma actual (ya alineado si no era el primero) como la nueva referencia (gris)
        self.previous_bw_left_stripe = bw_left_stripe.copy() 
        
        return aligned_image