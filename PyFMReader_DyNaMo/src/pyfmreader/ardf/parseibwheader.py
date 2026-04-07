import os
import re

from ..constants import UFF_code, UFF_version
from afmformats.formats.fmt_igor import load_igor
import pathlib
from igor2 import binarywave


def parseIBWheader(filepath):
    """
    Function used to load the metadata of an ibw file.

            Parameters:
                    filepath (str): Path to the ibw file.
            
            Returns:
                    header (dict): Dictionary containing the ibw file metadata.
    """
    header = {}
    
    header["file_path"] = filepath
    header["Entry_filename"] = os.path.basename(filepath)
    header["file_size_bytes"] = os.path.getsize(filepath)
    header["file_type"] = filepath.split(os.extsep)[-1]
    header['UFF_code'] = UFF_code
    header['Entry_UFF_version'] = UFF_version

    dslist = load_igor(filepath)
    parameters = dslist[0]['metadata']


    header.update(parameters)

    # Needed to avoid errors in the GUI
    header['height_channel_key'] = 'height'
    header["defl_sens_nmbyV"] = float(parameters['sensitivity']) * 1e9
    header["spring_const_Nbym"] = float(parameters['spring constant']) # unit N/m
    
    
    return header