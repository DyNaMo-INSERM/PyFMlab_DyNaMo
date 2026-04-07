# File containing the function loadARDFimg,
# used to load the piezo image from ARDF files.

import itertools
from struct import unpack
import numpy as np

def loadARDFimg(header):
    """
    Function used to load the piezo image from a NANOSCOPE file.

            Parameters:
                    header (dict): Dictionary containing the file metadata.
            
            Returns:
                    piezoimg (np.array): 2D array containing the piezo image.
    """
    
    piezoimg = header['y'][:, :, 0]

    return piezoimg