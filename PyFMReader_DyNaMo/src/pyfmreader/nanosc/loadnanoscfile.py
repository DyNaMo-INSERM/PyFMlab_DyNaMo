# File containing the function loadNANOSCfile, 
# used to load the metadata of NANOSCOPE files.

from .parsenanoscheader import parseNANOSCheader
from .loadnanoscimg import loadNANOSCimg
import numpy as np

def loadNANOSCfile(filepath, UFF):
    """
    Function used to load the metadata of a NANOSCOPE file.

            Parameters:
                    filepath (str): File path to the NANOSCOPE file.
                    UFF (uff.UFF): UFF object to load the metadata into.
            
            Returns:
                    UFF (uff.UFF): UFF object containing the loaded metadata.
    """
    UFF.filemetadata = parseNANOSCheader(filepath)
    UFF.isFV = bool(UFF.filemetadata['force_volume'])
    if UFF.isFV:
        UFF.piezoimg = loadNANOSCimg(UFF.filemetadata)
        shape = UFF.piezoimg.shape
        rows, cols = shape[0], shape[1]
        curve_coords = np.arange(cols*rows).reshape((cols, rows))
        UFF.imagedata = {'coordinate':curve_coords}

    return UFF
