
import os
import re

from ..constants import UFF_code, UFF_version
from .read_ardf import read_ardf_metadata 

def parseARDFheader(filepath):
    """
    Function used to load the metadata of an ARDF file.

            Parameters:
                    filepath (str): Path to the ARDF file.
            
            Returns:
                    header (dict): Dictionary containing the ARDF file metadata.
    """
    header = {}
    
    header["file_path"] = filepath
    header["Entry_filename"] = os.path.basename(filepath)
    header["file_size_bytes"] = os.path.getsize(filepath)
    header["file_type"] = filepath.split(os.extsep)[-1]
    header['UFF_code'] = UFF_code
    header['Entry_UFF_version'] = UFF_version

    file_struct = read_ardf_metadata(filepath)

    header.update(file_struct)

    nlines = header['y'].shape[0]
    npoints = header['y'].shape[1]
    all_positions_ardf = []

    for line in range(nlines):
                for point in range(npoints):
                    all_positions_ardf.append([line, point])
    
    header['all_positions_ardf'] = all_positions_ardf
    header['Entry_tot_nb_curve'] = len(all_positions_ardf)

    # Needed to avoid errors in the GUI
    header['height_channel_key'] = 'height'
    header["defl_sens_nmbyV"] = float(file_struct['Notes']['InvOLS']) * 1e9
    header["spring_const_Nbym"] = float(file_struct['Notes']['SpringConstant']) # unit N/m
    
    
    return header
