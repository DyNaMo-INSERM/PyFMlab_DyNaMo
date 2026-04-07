# File containing the function loadARDFfile, 
# used to load the metadata of ARDF files (Asylum Research devices)

from .parseARDFheader import parseARDFheader

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
    UFF.filemetadata['file_type'] = 'ARDF'
    UFF.isFV = bool(UFF.filemetadata['file_type'])
    return UFF
