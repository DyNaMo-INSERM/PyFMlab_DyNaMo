# File containing the function loadARDFfile, 
# used to load the metadata of ARDF files (Asylum Research devices)

from .parseibwheader import parseIBWheader

def loadIBWfile(filepath, UFF):
    """
    Function used to load the metadata of an ibw file.

            Parameters:
                    filepath (str): File path to the ibw file.
                    UFF (uff.UFF): UFF object to load the metadata into.
            
            Returns:
                    UFF (uff.UFF): UFF object containing the loaded metadata.
    """
    UFF.filemetadata = parseIBWheader(filepath)
    UFF.filemetadata['file_type'] = '.ibw'
    UFF.isFV = False
    return UFF