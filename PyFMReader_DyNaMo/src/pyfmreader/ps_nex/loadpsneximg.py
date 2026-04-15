"""
Created on Thu Apr 7 10:56:00 2026

@author: Lorenzo

derived from the JPK file img. Still need to improve this
"""

# import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
# from pyfmreaderpsnex import loadfile
# from pyfmreaderpsnex.ps_nex.parseTDMS import grab_tdms
import numpy as np
import shutil
# from pyfmreader.ps_nex.parseTDMS import grab_tdms
# from pyfmreader import loadfile
import pyfmreader.ps_nex.loadpsnexMaps as maps

import os
import glob

# As for 20/07/2022 these are the accepted channels for
# JPK files. This routine has a lot of hard coded values
# i.e: offset to search for the conversion factors, that are
# susceptible to breaking if the format is modified in any way.
valid_channels = [
    'Baseline', 'Height(measured)', 'SlopeFit', 'Adhesion', 'Height'
]

valid_scalings = [
    'Force', 'volts', 'Calibrated height', 'Nominal height'
]

height_channels = [
    'Height(measured)', 'Height'
]

valid_height_scalings = [
    'Calibrated height', 'Nominal height'
]

valid_vars_channels = [
    'Baseline', 'SlopeFit', 'Adhesion'
]

valid_vars_scalings = [
    'Force', 'volts'
]


def loadPSNEXimg(UFF):
    """
    Function used to load the piezo image from a PS-NEX file.

            Parameters:
                    UFF (uff.UFF): UFF object containing the PS-NEX file metadata.
            
            Returns:
                    piezoimg (np.array): 2D array containing the piezo image.
    """
    piezoimg, data = None, None
    return piezoimg, data



def createPSNEXimgcsv(UFF):
    """
    Function used to create a CSV map file, if it does not already exist, from a PS-NEX file. If Map
    file already exists, it will not be overwritten. Function will check the force curve files in the 
    directory path of the current PS-NEX file. The CSV fill will be placed in the same directory.

            Parameters:
                    UFF (uff.UFF): UFF object containing the PS-NEX file metadata.
            
            Returns:
                    piezoimg (np.array): 2D array containing the piezo image.
    """
    # for testing purposes
    CSVfile = False

    filepath = UFF.filemetadata['file_path']
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} does not exist.")
    
    if UFF.filemetadata['mapping_bool']:
        print("This is a psnex mapping file! ")



    # pattern = os.path.join(filepath, 'psnex_map__*')
    directory = os.path.dirname(filepath)
    print (f"directory: {directory}")
    # files = [f for f in glob.glob(pattern) if not f.endswith('.zip')]
    files = [f for f in glob.glob(os.path.join(directory, '*.tdms')) if f.endswith('.tdms')]

    # if actual map path was given, use that
    if files == []:
        # if no files were found, check if the directory is a valid path
        files.append(filepath)
    
    data = maps.load_map_file_square_tdms_v2(directory)
    experiment_name = UFF.filemetadata['Entry_experiment_name']

    if not experiment_name:
        experiment_name = ''

    # Construct the CSV filename
    csv_filename = os.path.join(directory, f"{os.path.basename(directory)}_{experiment_name}.csv")
    print(csv_filename)


    # Save the DataFrame to CSV with 6 significant digits
    data.to_csv(csv_filename, index=False, float_format='%.6g')
    csv_filepath = csv_filename
    
    piezoimg = np.array(data['Z_height_um_zero']).reshape((UFF.filemetadata['num_y_pixels'], UFF.filemetadata['num_x_pixels']))
    print('done')
    return piezoimg , data