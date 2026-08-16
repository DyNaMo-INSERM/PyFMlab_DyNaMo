# File containing the function loadARDFfile, 
# used to load the metadata of ARDF files (Asylum Research devices)

from .parseARDFheader import parseARDFheader
from .loadARDFimg import loadARDFimg
import numpy as np
def loadARDFfile(filepath, UFF):
    """
    Function used to load the metadata of an ARDF forcemap file.

            Parameters:
                    filepath (str): File path to the ARDF file.
                    UFF (uff.UFF): UFF object to load the metadata into.
            
            Returns:
                    UFF (uff.UFF): UFF object containing the loaded metadata.
    """
    UFF.filemetadata = parseARDFheader(filepath)
    UFF.isFV = True
    UFF.piezoimg = loadARDFimg(UFF.filemetadata)
    shape = UFF.piezoimg.shape
    rows, cols = shape[0], shape[1]
    curve_coords = np.arange(cols*rows).reshape((cols, rows))
    UFF.imagedata = {'coordinate':curve_coords}
    return UFF
