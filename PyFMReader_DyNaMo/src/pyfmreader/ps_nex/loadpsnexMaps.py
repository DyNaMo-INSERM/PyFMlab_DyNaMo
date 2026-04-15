# from pyfmreader import loadfile

# internal
import matplotlib.pyplot as plt 
from nptdms import TdmsFile #from nptdms import tdms  # pip install nptdms
import pandas as pd
import os 
import shutil
# import seaborn as sns
import glob
import numpy as np
# import time

import re
from datetime import datetime
from pathlib import Path
import seaborn as sns
# from sympy import false

import tifffile as tiff

from pyfmreader import loadfile
from pyfmreader.ps_nex.parseTDMS import grab_tdms


def find_psnex_map_folders(root_directory):
    """
    Find all folders that start with 'psnex_map_' in the specified directory.
    Will not recursively search inside directories that already match the pattern.
    
    Parameters:
    -----------
    root_directory : str
        Root directory where to start the search
        
    Returns:
    --------
    list
        A list of paths to folders matching the pattern
    """
    matching_folders = []
    
    # Walk through directory tree
    for root, dirs, _ in os.walk(root_directory):
        # Find directories in current level that match the pattern
        matched_dirs = [d for d in dirs if d.startswith('psnex_map_')]
        
        # Add full paths to matching folders
        for matched_dir in matched_dirs:
            matching_folders.append(os.path.join(root, matched_dir))
            
        # Remove matching directories from dirs to prevent os.walk from recursing into them
        # This modifies dirs in-place which affects os.walk's traversal
        dirs[:] = [d for d in dirs if not d.startswith('psnex_map_')]
    
    return matching_folders

def generate_xy_map_positions(map_x_pix=32, map_y_pix=32):
    """
    Generate X and Y positions for a 2D map and corresponding curve indices.

    This function creates arrays representing the x and y positions for each point
    in a 2D map grid, as well as a sequential curve index array.
    
    Parameters
    ----------
    map_x_pix : int, optional
        Number of pixels in the x direction. Default is 32.
    map_y_pix : int, optional
        Number of pixels in the y direction. Default is 32.
        
    Returns
    -------
    x_pos_1d : numpy.ndarray
        1D array of x positions with shape (map_x_pix * map_y_pix,)
    y_pos_1d : numpy.ndarray
        1D array of y positions with shape (map_x_pix * map_y_pix,)
    curve_index : numpy.ndarray
        1D array of sequential indices from 0 to (map_x_pix * map_y_pix - 1)
    """  
    # create me an array from 0 to 32 with step 1, then concatenate them into 1D array
    x_pos_arr = []
    y_pos_arr = []
    for i in range(0, map_x_pix, 1):
        x_arr = np.arange(0, map_x_pix, 1)
        y_arr = np.full(map_y_pix , i)
        x_pos_arr.append(x_arr)
        y_pos_arr.append(y_arr)

    # After the loop, concatenate all arrays into one 1D array
    x_pos_1d = np.concatenate(x_pos_arr)
    y_pos_1d = np.concatenate(y_pos_arr)
    curve_index = np.arange(0,map_x_pix * map_y_pix,1)
    print(f"Shape of x_pos_1d: {x_pos_1d.shape}")
    print(f"Shape of y_pos_1d: {y_pos_1d.shape}")

    return x_pos_1d, y_pos_1d, curve_index

def check_map_indice_integrity(df_map, map_x_pix = 32, map_y_pix = 32):
    """
    Validates the integrity of df_map's 'curve_index' column in a DataFrame representing a pixel map.
    This function checks whether the 'curve_index' values in `df_map` match the expected sequence
    for a map of size `map_x_pix` by `map_y_pix`. It detects missing or duplicated indices by
    comparing the DataFrame's 'curve_index' column to a generated range of expected indices.

    Parameters
    ----------
    df_map : pandas.DataFrame
        DataFrame containing a 'curve_index' column to be validated.
    map_x_pix : int, optional
        Number of pixels along the x-axis of the map (default is 32).
    map_y_pix : int, optional
        Number of pixels along the y-axis of the map (default is 32).
    Returns
    -------
    error : bool
        True if missing or duplicated indices are found, False otherwise.
    mismatch_indices : numpy.ndarray
        Array of indices where mismatches occur between expected and actual 'curve_index' values.
    Prints
    ------
    If mismatches are found, prints the number of mismatched indices and the first 10 mismatch indices.
    Checks df_map's 'curve_index' for missing or duplicated values.
    if missing or duplicate found, prints the number of mismatches and their indices.
        
    """
    error = False
    # check if df_map has any missing values
    curve_index = np.arange(0,map_x_pix * map_y_pix,1)
    # df_map = df_map.sort_values(by='curve_index')
    curve_index_data = df_map['curve_index']


# check per index if equal
    is_equal = curve_index == curve_index_data
    if not np.all(is_equal):
    # print("There are missing or duplicated curve_index values.")
    # Find the indices where the values are not equal
        mismatch_indices = np.where(~is_equal)[0]
        print(f"{len(mismatch_indices)} Mismatched indices:", mismatch_indices[:10])
        error = True
    else:
        mismatch_indices = np.array([])
        print("All curve_index values are valid.")  

    return error, mismatch_indices

def get_map_parameters(map_path, **kwargs):
    """
    Extract mapping parameters from one TDMS file in a map directory.
    
    Parameters:
    -----------
    map_path : str
        Path to the directory containing TDMS files
    kwargs : dict
        Optional overrides for map_x_pix and map_y_pix
    
    Returns:
    --------
    dict
        Dictionary containing mapping parameters:
        - map_x_step, map_y_step: Step sizes in V
        - map_x_init, map_y_init: Initial positions in V
        - map_x_pix, map_y_pix: Map dimensions in pixels
        - x_sens_um, y_sens_um, z_sens_um: Sensitivities in um/V
    
    tdms_files : list
        List of TDMS files found in the directory
    """

    # Get TDMS files
    _, tdms_files = grab_tdms(map_path)
    
    # Load the second file (first file sometimes gives errors due to 0kb size)
    psnex_file = loadfile(tdms_files[1])
    metadata = psnex_file.filemetadata
    
    # Get mapping parameters
    map_x_init = metadata.get("mapping_X_initial_pos_V", 0.0)
    map_y_init = metadata.get("mapping_Y_initial_pos_V", 0.0)
    map_x_step = metadata.get("mapping_X_step_size_V", 0.0)
    map_y_step = metadata.get("mapping_Y_step_size_V", 0.0)
    map_x_cur = metadata.get("X_cur_position_V", 0.0)
    map_y_cur = metadata.get("Y_cur_position_V", 0.0)
    try:
        map_x_pix = metadata.get('mapping_X_pixels', None)
        map_y_pix = metadata.get('mapping_Y_pixels', None)
    except:
        print('mapping_X_pixels or mapping_Y_pixels not found in metadata, estimating map dimensions')


    # Allow kwargs to override pixel dimensions
    if 'map_x_pix' in kwargs:
        map_x_pix = kwargs['map_x_pix']
    if 'map_y_pix' in kwargs:
        map_y_pix = kwargs['map_y_pix']
    
    # Get sensitivities
    z_stage_sens_nm = metadata['curve_properties']['0'][0].get('z_stage_sensitivity', 6000.0)
    x_sens_nm = metadata.get('system_X_piezo_sensitivity_(nm/V)', 5685.0)
    y_sens_nm = metadata.get('system_Y_piezo_sensitivity_(nm/V)', 3960.0)
    
    # Convert to micrometers
    x_sens_um = x_sens_nm / 1000
    y_sens_um = y_sens_nm / 1000
    z_sens_um = z_stage_sens_nm / 1000
    
    # Create parameter dictionary
    params = {
        'map_x_init': map_x_init,
        'map_y_init': map_y_init,
        'map_x_step': map_x_step, 
        'map_y_step': map_y_step,
        'map_x_pix': map_x_pix,
        'map_y_pix': map_y_pix,
        'map_x_cur': map_x_cur,
        'map_y_cur': map_y_cur, 
        'x_sens_um': x_sens_um,
        'y_sens_um': y_sens_um,
        'z_sens_um': z_sens_um,
        'map_path': map_path,
    }
    
    return params, tdms_files

def find_csv_files(directory_path, checkAllFolders=False):
    """
    Find all CSV files in the specified directory.
    If checkAllFolders is True, search recursively in all subfolders.

    Parameters:
    -----------
    directory_path : str
        Path to the directory where CSV files will be searched.
    checkAllFolders : bool, optional
        If True, search recursively in all subfolders. Default is False.

    Returns:
    --------
    list
        A list of paths to CSV files found in the directory.
        Returns an empty list if no CSV files are found.

    Examples:
    ---------
    >>> files = find_csv_files('/path/to/directory')
    >>> print(files)
    ['/path/to/directory/file1.csv', '/path/to/directory/file2.csv']
    """
    if checkAllFolders:
        # Recursively search for CSV files in all subfolders
        csv_files = glob.glob(os.path.join(directory_path, '**', '*.csv'), recursive=True)
    else:
        # Only search for CSV files in the first level of the directory
        csv_files = glob.glob(os.path.join(directory_path, '*.csv'))

    if not csv_files:
        print("No CSV files found in", directory_path)
    else:
        print(f"Found {len(csv_files)} CSV files:")
        for file in csv_files:
            print(f"  - {os.path.basename(file)}")

    return csv_files

def save_map_as_tiff(array_um, px_um_x, px_um_y, out_path, title=None, unit="um"):
    """
    Saves a 2D array as a TIFF image with ImageJ-compatible metadata.

    Parameters
    ----------
    array_um : array-like, dict, or DataFrame
        2D array (Y, X), or a dictionary/DataFrame with 2D data.
    px_um_x : float
        Pixel size in micrometers along the X axis.
    px_um_y : float
        Pixel size in micrometers along the Y axis.
    out_path : str
        Output file path for the TIFF image.
    title : str, optional
        Title or description to include in the metadata. Default is None.
    unit : str, optional
        Unit of measurement for the image (default is "um").

    Raises
    ------
    ValueError
        If the input array is not 2D.

    Notes
    -----
    - The TIFF image is saved with 32-bit float precision.
    - ImageJ metadata is included for compatibility.
    - The resolution is set based on the pixel size.
    - The output directory is created if it does not exist.
    """
    # Handle dictionary or DataFrame input
    if isinstance(array_um, dict):
        # Try to find a 2D array in the dict (commonly 'z_height_um_zero' or 'z_height_um')
        if "z_height_um_zero" in array_um:
            img = np.asarray(array_um["z_height_um_zero"])
        elif "z_height_um" in array_um:
            img = np.asarray(array_um["z_height_um"])
        else:
            raise ValueError("Dictionary input must contain 'z_height_um_zero' or 'z_height_um' key.")
    elif isinstance(array_um, pd.DataFrame):
        # If it's a DataFrame, use its values
        img = array_um.values
    elif hasattr(array_um, "values") and hasattr(array_um, "shape"):
        # Likely a DataFrame
        img = array_um.values
    else:
        img = np.asarray(array_um)

    if img.ndim != 2:
        raise ValueError("array must be 2D (Y, X)")

    ppi_x = 2.54000 / float(px_um_x)   # pixels per inch
    ppi_y = 2.54000 / float(px_um_y)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tiff.imwrite(
        out_path,
        img.astype(np.float32),
        dtype=np.float32,
        imagej=True,
        resolution=(ppi_x, ppi_y),
        metadata={
            "unit": unit,
            "Info": title or "",
            "mode": "AFM",  # Add AFM mode for proper coloring
        },
        photometric="minisblack",
    )
    print("Saved:", out_path)
 
def handle_file_error(fp, rootdir, error_type, move=True):
    """
    Handles file errors by moving the problematic file and its index to an error folder.

    Args:
        fp (str): File path of the problematic file.
        rootdir (str): Root directory where the error folder will be created.
        error_type (str): Type of error encountered.
        move (bool): Whether to move the files to the error folder.

    Returns:
        None
    """
    print(f"{error_type} encountered.")
    error_folder = os.path.join(rootdir, 'error_file')
    if not os.path.exists(error_folder):
        os.makedirs(error_folder)
    indexfile = fp + '_index'
    if move:
        shutil.move(fp, os.path.join(error_folder, os.path.basename(fp)))
        shutil.move(indexfile, os.path.join(error_folder, os.path.basename(indexfile)))
    print(os.path.basename(fp))

def extract_map_parameters(tdms_files, impulse_xy_v=1, estimate_xy=True):
    """
    Extracts mapping parameters from a list of TDMS files.

    Args:
        tdms_files (list): List of TDMS file paths.
        impulse_xy_v (float): Impulse voltage for XY calculation.
        estimate_xy (bool): Whether to estimate XY positions.

    Returns:
        dict: Dictionary containing extracted parameters.
        int: map_x_pix (estimated square size)
        int: map_y_pix (estimated square size)
    """
    from pyfmreader import loadfile 
    # from pyfmreader.ps_nex.parseTDMS import grab_tdms
    z_setpoint_trig_v_list = []
    mapping_index_list = []
    map_x_index_list = []
    map_y_index_list = []
    file_id_list = []
    # map_x_pos_v_list = []
    # map_y_pos_v_list = []
    z_stage_sens_nm_V = None
    x_sens_nm = None
    y_sens_nm = None
    x_sens_um = None
    y_sens_um = None
   
    estimated_square = int(np.ceil(np.sqrt(len(tdms_files))))
    if estimated_square * estimated_square == len(tdms_files):
        map_x_pix = estimated_square
        map_y_pix = estimated_square
    else:
        # round up to the nearest integer
        map_x_pix = int(np.ceil(np.sqrt(len(tdms_files)))) 
        map_y_pix = map_x_pix
    print(f'# of files analyzed: {len(tdms_files)}, closest shape: {map_x_pix} x {map_y_pix}')


    for files in tdms_files:
        try:
            psnex_file = loadfile(files)
            metadata = psnex_file.filemetadata
            z_setpoint_trig_v = metadata['curve_properties']['0'][0]['segment_0_Z_position_setpoint_trigger_(V)']
            mapping_index = metadata['mapping_index']
            file_id = metadata['Entry_filename']
            try:
                map_x_index = metadata['mapping_position_row']
                map_y_index = metadata['mapping_position_col']

                map_x_init= metadata["mapping_X_initial_pos_V"]
                map_y_init= metadata["mapping_Y_initial_pos_V"]

                map_x_step = metadata["mapping_X_step_size_V"]
                map_y_step = metadata["mapping_Y_step_size_V"]

                # map_x_cur = metadata["X_cur_position_V"]
                # map_y_cur = metadata["Y_cur_position_V"]
            except Exception:
                map_x_index = metadata['mapping_position_X']
                map_y_index = metadata['mapping_position_Y']

                map_x_init= metadata["mapping_X_initial_pos_V"]
                map_y_init= metadata["mapping_Y_initial_pos_V"]

                map_x_step = metadata["mapping_X_step_size_V"]
                map_y_step = metadata["mapping_Y_step_size_V"]

                # map_x_cur = metadata["X_cur_position_V"]
                # map_y_cur = metadata["Y_cur_position_V"]

            if z_stage_sens_nm_V is None:
                z_stage_sens_nm_V = metadata['curve_properties']['0'][0]['z_stage_sensitivity']
            if x_sens_nm is None:
                x_sens_nm = metadata['system_X_piezo_sensitivity_(nm/V)']
            if y_sens_nm is None:
                y_sens_nm = metadata['system_Y_piezo_sensitivity_(nm/V)']
            if x_sens_um is None:
                x_sens_um = x_sens_nm / 1000
            if y_sens_um is None:
                y_sens_um = y_sens_nm / 1000

            z_setpoint_trig_v_list.append(float(z_setpoint_trig_v))
            mapping_index_list.append(mapping_index)
            map_x_index_list.append(map_x_index)
            map_y_index_list.append(map_y_index)
            file_id_list.append(file_id)
            # map_x_pos_v_list.append(map_x_pos_v)
            # map_y_pos_v_list.append(map_y_pos_v)
        except Exception as e:
            print(f"Error loading file {files}: {e}")
            z_setpoint_trig_v_list.append(np.nan)
            mapping_index_list.append(np.nan)
            map_x_index_list.append(np.nan)
            map_y_index_list.append(np.nan)
            file_id_list.append(np.nan)   
            handle_file_error(files, os.path.dirname(files), e, move=True)
            # map_x_pos_v_list.append(np.nan)
            # map_y_pos_v_list.append(np.nan)


    print (f' map metadata: map_x_step: {map_x_step}, map_y_step: {map_y_step}, map_x_init: {map_x_init}, map_y_init: {map_y_init}')
    print (f' x_sens (um/V): {x_sens_um}, y_sens (um/V): {y_sens_um}, z_sens (um/V): {z_stage_sens_nm_V / 1000}, z_setpoint_trig (V): {z_setpoint_trig_v}')

    z_height_um_list = [z * z_stage_sens_nm_V * 1e-3 for z in z_setpoint_trig_v_list]

    if estimate_xy:
        x_pos_um_list = [x * x_sens_um * impulse_xy_v for x in map_x_index_list]
        y_pos_um_list = [y * y_sens_um * impulse_xy_v for y in map_y_index_list]
    # else:
    #     x_pos_um_list = [x * x_sens_um * impulse_xy_v for x in map_x_pos_v_list]
    #     y_pos_um_list = [y * y_sens_um * impulse_xy_v for y in map_y_pos_v_list]


    data = {
        'filepath': tdms_files,
        'file_id': file_id_list,
        'z_height_v': z_setpoint_trig_v_list,
        'curve_index': mapping_index_list,
        'x_index': map_x_index_list,
        'y_index': map_y_index_list,
        # 'x_pos_v': map_x_pos_v_list,
        # 'y_pos_v': map_y_pos_v_list,
        'z_height_um': z_height_um_list,
        # 'z_height_um_zero': map_test_um_zeroed,
        'x_pos_um': x_pos_um_list,
        'y_pos_um': y_pos_um_list,
    }
    return data, map_x_pix, map_y_pix

def checkMapFileNULL(directory, CSVfile=True):
    """
    Checks the map directory for TDMS files that are empty and moves them to an error folder.
    Additionally, processes valid files to extract metadata and generate a CSV log file.
    Args:
        directory (str): The path to the directory containing the map files to be checked.
        CSVfile (bool, optional): A flag indicating whether to generate a CSV log file 
                                  with metadata from the processed files. Defaults to True.

    Returns:
        pd.DataFrame: A DataFrame containing metadata and analysis results for the processed files.
        
    """
    from pyfmreader import loadfile 
    from pyfmreader.ps_nex.parseTDMS import grab_tdms
    # Check if the directory is a valid path
    pattern = os.path.join(directory, 'psnex_map__*')
    # files = [f for f in glob.glob(pattern) if not f.endswith('.zip')]
    files = [f for f in glob.glob(pattern) if not (f.endswith('.zip') or f.endswith('.csv'))]
    move = True
    # if actual map path was given, use that
    if files == []:
        # if no files were found, check if the directory is a valid path
        files.append(directory)
    for rootdir in files[:]:
        print(f"processing file : {rootdir}")
        # _,all_files,filenames = find_directories_with_file_type(rootdir,'.tdms')
        _, all_files = grab_tdms(rootdir)

        df_point_log = pd.DataFrame()

        # with concurrent.futures.ProcessPoolExecutor() as executor:
        #     # loaded_files = executor.map(load_single_file, files_to_load)
        #     futures = [executor.submit(load_single_file, filepath) for filepath in files_to_load]
        #     for future in concurrent.futures.as_completed(futures):
        #         loaded_files.append(future.result())
        #         count+=1
        #         progress_callback.emit(count)

        # tp_file = []
        for fp in all_files:
            # print(f'now analyzing {fp}')
            try :
                #loading and updating params for hertz
                file = loadfile(fp)
                filemetadata = file.filemetadata
                #closed_loop = filemetadata['z_closed_loop']
                # file_deflection_sensitivity = filemetadata['defl_sens_nmbyV']  # nm/V
                # file_spring_constant = filemetadata['spring_const_Nbym']  # N/m
                height_channel = filemetadata['height_channel_key']
                #force_set_point = filemetadata["force_setpoint"]
                deflection_sensitivity = filemetadata['defl_sens_nmbyV'] / 1e9  # m/V
                # spring_constant = file_spring_constant
            
                curve_properties = filemetadata['curve_properties']
                # tick_time_s = filemetadata['instrument_tick_time_(s)']# 2* 10**-6
                tick_time_s = filemetadata['tick_time_z_loop']# 2* 10**-6

                force_curve = file.getcurve(0)
                # Preprocess curve
                force_curve.preprocess_force_curve(deflection_sensitivity, height_channel)
                tdms_file_ps_nex_file = TdmsFile.open(fp)
                tdms_groups = tdms_file_ps_nex_file.groups() 
                tdms_psnex_fc = tdms_groups[0]
                
                deflection = tdms_psnex_fc[height_channel][:]
                total_len = len(deflection)
                stored_arr =[]
                cal_arr = []

                # for i, segment in force_curve.get_segments():
                #     temp_seg_dict = curve_properties[str(0)][i]
                #     seg_i_pt_cal = temp_seg_dict[f"segment_{i}_nb_points_cal"]
                #     seg_i_pt_stored = temp_seg_dict[f"segment_{i}_nb_points_(points)"]
                #     stored_arr.append(seg_i_pt_stored)
                #     cal_arr.append(seg_i_pt_cal)

                #     segment_duration = temp_seg_dict[f"segment_{i}_duration_(ticks)"]*tick_time_s
                #     if i ==0:
                #         set_pt_z_pos_V = temp_seg_dict[f"segment_{i}_Z_position_setpoint_trigger_(V)"]
                #     print(f"segment duration {segment_duration}, \n numb of point cal (ticks, dec, sampling rate {seg_i_pt_cal}, num pts stored per segment {seg_i_pt_stored}")
                # Extract retract segment data
                # relative_SR = filemetadata['relative_sr']

                for segid, segment in force_curve.get_segments():
                    temp_seg_dict = curve_properties[str(0)][segid]
                    if segment.segment_type in ('Approach', 'App'):
                        seg_i_pt_cal = temp_seg_dict[f"segment_{segid}_nb_points_cal"]
                        seg_i_pt_stored = temp_seg_dict[f"segment_{segid}_nb_points_(points)"]
                        stored_arr.append(seg_i_pt_stored)
                        cal_arr.append(seg_i_pt_cal)

                        segment_duration = temp_seg_dict[f"segment_{segid}_duration_(ticks)"]*tick_time_s
                        # segment_duration = temp_seg_dict[f"segment_{segid}_duration_(ticks)"]*tick_time_s
                        
                        # only if approach
                        set_pt_z_pos_V = temp_seg_dict[f"segment_{segid}_Z_position_setpoint_trigger_(V)"]
                        print(f"segment duration {segment_duration}, \n numb of point cal (ticks, dec, sampling rate {seg_i_pt_cal}, num pts stored per segment {seg_i_pt_stored}")
                    elif segment.segment_type in ('Retract', 'Ret'):
                        # ret_piezo = -segment.zheight
                        # ret_deflection = -segment.vdeflection * K
                        # relative_SR_ret = relative_SR[segid]
                        # vel_ret_um_s = segment.velocity * 1e-03  # Convert from nm to um/s
                        # time_ret = np.arange(len(ret_piezo)) * relative_SR_ret 
                        seg_i_pt_cal = temp_seg_dict[f"segment_{segid}_nb_points_cal"]
                        seg_i_pt_stored = temp_seg_dict[f"segment_{segid}_nb_points_(points)"]
                        stored_arr.append(seg_i_pt_stored)
                        cal_arr.append(seg_i_pt_cal)
                        segment_duration = temp_seg_dict[f"segment_{segid}_duration_(ticks)"]*tick_time_s
                        print(f"segment duration {segment_duration}, \n numb of point cal (ticks, dec, sampling rate {seg_i_pt_cal}, num pts stored per segment {seg_i_pt_stored}")

                temp_dict = {
                                "filepath":fp,
                                "total_len":total_len,
                                "total_len_cal_tick":sum(cal_arr),
                                "diff_cal":total_len-sum(cal_arr),
                                "diff_store":total_len-sum(stored_arr),
                                "total_len_stored_point":sum(stored_arr),
                                "store_nbpts_app" :stored_arr[0],
                                "store_nbpts_ret" :stored_arr[1],
                                "cal_nbpts_app" :cal_arr[0],
                                "cal_nbpts_ret" :cal_arr[1],
                                "set_pt_z_pos_V":set_pt_z_pos_V    
                            }

                df_temp = pd.DataFrame(temp_dict,index = [0])
                df_point_log = pd.concat([df_point_log,df_temp],ignore_index=True)
                print ('df_point log made')

            except Exception as e:
                handle_file_error(fp, rootdir, e, move=True)
                    
        results_folder = os.path.join(rootdir, 'results')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
            if CSVfile:
                df_point_log.to_csv(os.path.join(results_folder, 'df_point_log.csv'), index=False)
        return df_point_log
    
def remove_nan_and_get_indices(input_list):
    nan_indices = [i for i, x in enumerate(input_list) if np.isnan(x)]
    cleaned_list = [x for x in input_list if not np.isnan(x)]
    return cleaned_list, nan_indices

def load_map_file_square_tdms (directory, key = 'z_height_um'):
    """
    Loads a square map from a directory containing TDMS files, extracts mapping parameters,
    processes Z-position data, and returns a dictionary of map data and map dimensions.

    Parameters
    ----------
    directory : str
        Path to the directory containing TDMS files for the map.

    Returns
    -------
    df_dict : dict
        Dictionary containing map data columns such as 'z_height_um', 'curve_index', etc.
    map_x_pix : int
        Number of pixels along the X-axis (width) of the map.
    map_y_pix : int
        Number of pixels along the Y-axis (height) of the map.
    params : dict
        Dictionary containing mapping parameters such as step sizes, initial positions, sensitivities, and map dimensions.

    Notes
    -----
    - The function loads each TDMS file, extracts Z-position contact data, and handles corrupt files by inserting NaN.
    - The Z-position data is reshaped and zeroed for topographical analysis.
    - The returned dictionary can be used for further visualization or analysis.
    """

    # from pyfmreader import loadfile
    from pyfmreader.ps_nex.parseTDMS import grab_tdms
    # Grab TDMS files 
    _, tdms_files = grab_tdms(directory)

    # Open each force curve in the map and read the Zposition contact. If file is corrupt, NaN will be placed
    data, map_x_pix, map_y_pix = extract_map_parameters(tdms_files, impulse_xy_v=0.1, estimate_xy=True)

    # get mapping parameters
    params = get_map_parameters(directory)   

    # write map_x_pix and map_y_pix to params
    params[0]['map_x_pix'] = map_x_pix
    params[0]['map_y_pix'] = map_y_pix

    # Convert the dictionary to a DataFrame
    df = pd.DataFrame(data)


    # Sort the dataframe
    df_sorted = df.sort_values(by='curve_index')
    z_height_um_sorted = df_sorted['z_height_um'].values

    # create

    # check if reshape for square is possible with amount of data
    if len(z_height_um_sorted) != map_x_pix * map_y_pix:
        print(f"Warning: Data length {len(z_height_um_sorted)} does not match expected size {map_x_pix * map_y_pix}. Adjusting map dimensions.")
        estimated_square = int(np.ceil(np.sqrt(len(z_height_um_sorted))))
        if estimated_square * estimated_square == len(z_height_um_sorted):
            map_x_pix = estimated_square
            map_y_pix = estimated_square
        else:
            # check difference between estimated square and actual data length
            diff = len(z_height_um_sorted) - (map_x_pix * map_y_pix)

            # fill in NaN to make it fit
            if diff < 0:
                z_height_um_sorted = np.append(z_height_um_sorted, [np.nan]*np.abs(diff))
                print(f'Added {np.abs(diff)} NaN values to fit the shape.')
            elif diff > 0:
                z_height_um_sorted = z_height_um_sorted[:diff]
                print(f'Removed {np.abs(diff)} values to fit the shape.')

            # map_x_pix = int(np.ceil(np.sqrt(len(z_height_um_sorted)))) + 1
            # map_y_pix = map_x_pix
            print(f'Adjusted shape: {map_x_pix} x {map_y_pix}')

    # create copy of dataframe and increase size to fit the new shape if needed
    df_sorted_new = df_sorted.reindex(range(map_x_pix * map_y_pix))
    df_sorted_new = df_sorted_new.sort_values(by='curve_index')

    try :
        # z_pos_2d = np.reshape(z_height_um_sorted, (map_x_pix, map_y_pix)) 

        # Mirror flip the 2D array along the vertical axis
        # z_pos_2d_flipped = np.flip(z_pos_2d, axis=1)
        z_param = df_sorted_new['z_height_um'].values

        # zero height to represent the actual height since the height is calculated as the approach 
        map_test_um_zeroed = -z_param + np.nanmax(z_param) # # Fixed version - ignores NaN: map_test_um_zeroed = -z_param + z_param.max().max()
        # error occurs here when the pixels are not the same due to the added nan's to the dataframe.
        df_sorted_new['z_height_um_zero'] = map_test_um_zeroed.flatten()
    except Exception as e:
        print(f"Could not calculate z_height_um_zero: {e}, missing z_height_um column?")
        

    df_dict = {col: df_sorted_new[col].to_numpy() for col in df_sorted_new.columns}
    # convert df_dict to pandas dataframe
    df_dict = pd.DataFrame(df_dict)

    return df_dict, map_x_pix, map_y_pix, params

def load_map_file_square_tdms_v2 (directory) :
    """
    Loads a square map from a directory containing TDMS files, extracts mapping parameters,
    processes Z-position data, and returns a DataFrame of map data.

    Parameters
    ----------
    directory : str
        Path to the directory containing TDMS files for the map.

    Returns
    -------
    df_sorted : pandas.DataFrame
        DataFrame containing map data columns such as 'z_height_um', 'curve_index', etc.

    Raises
    ------
    Exception
        If a TDMS file cannot be loaded or its metadata cannot be parsed, an error message is printed and NaN values are inserted.

    Notes
    -----
    - The function loads each TDMS file, extracts Z-position contact data, and handles corrupt files by inserting NaN.
    - The Z-position data is reshaped and zeroed for topographical analysis.
    - The returned DataFrame can be used for further visualization or analysis.
    """
    from pyfmreader import loadfile
    from pyfmreader.ps_nex.parseTDMS import grab_tdms
    # Grab TDMS files 
    _, tdms_files = grab_tdms(directory)
    # Initialize lists to store the parameters
    z_setpoint_trig_v_list = []
    mapping_index_list = []
    map_x_index_list = []
    map_y_index_list = []
    filepaths = []
    # map_x_pos_v_list = []
    # map_y_pos_v_list = []
    impulse_xy_v = 0.1
    estimate_xy = True

    # Open each force curve in the map and read the Zposition contact. If file is corrupt, NaN will be placed
    for files in tdms_files:
        # start_time = time.time()  # Start timing
        try:
            psnex_file = loadfile(files)  # load the file
            # Get metadata and force curve object
            metadata = psnex_file.filemetadata
           
            z_setpoint_trig_v = metadata['curve_properties']['0'][0]['segment_0_Z_position_setpoint_trigger_(V)']
            mapping_index = metadata['mapping_index']
            try: 
                #OLD MAP VERSION    
                map_x_index = metadata['mapping_position_row']
                map_y_index = metadata['mapping_position_col']
            except:
                map_x_index = metadata['mapping_position_X']
                map_y_index = metadata['mapping_position_Y']
            # map_x_pos_v = metadata['X_cur_position_V']
            # map_y_pos_v = metadata['Y_cur_position_V']
        
            # Z height contact and setpoint
            # z_setpoint_trig_v  = metadata['curve_properties']['0'][0]['segment_0_Z_position_setpoint_trigger_(V)']
            
            # Get sensitivities if not already loaded
            if 'z_stage_sens_nm_V' not in locals():
                z_stage_sens_nm_V = metadata['curve_properties']['0'][0]['z_stage_sensitivity']
            if 'x_sens_nm' not in locals():
                x_sens_nm = metadata['system_X_piezo_sensitivity_(nm/V)']
            if 'y_sens_nm' not in locals():
                y_sens_nm = metadata['system_Y_piezo_sensitivity_(nm/V)']
            if 'x_sens_um' not in locals():
                x_sens_um = x_sens_nm / 1000
            if 'y_sens_um' not in locals():
                y_sens_um = y_sens_nm / 1000
            
            # Append the parameters to the lists
            z_setpoint_trig_v_list.append(float(z_setpoint_trig_v))
            mapping_index_list.append(mapping_index)
            map_x_index_list.append(map_x_index)
            map_y_index_list.append(map_y_index)
            filepaths.append(files)
            # map_x_pos_v_list.append(map_x_pos_v)
            # map_y_pos_v_list.append(map_y_pos_v)
        except Exception as e:
            print(f"Error loading file {files}: {e}")
            # Append NaN to the lists if there is an error
            z_setpoint_trig_v_list.append(np.nan)
            mapping_index_list.append(np.nan)
            map_x_index_list.append(np.nan)
            map_y_index_list.append(np.nan)
            filepaths.append(files)
            # map_x_pos_v_list.append(np.nan)
            # map_y_pos_v_list.append(np.nan)
        # end_time = time.time()  # End timing
        # iteration_time = end_time - start_time
        # print(f"Time for iteration: {iteration_time:.4f} seconds")

    z_height_um_list = [z * z_stage_sens_nm_V * 1e-3 for z in z_setpoint_trig_v_list]

    if estimate_xy:
        x_pos_um_list = [x * x_sens_um * impulse_xy_v for x in map_x_index_list]
        y_pos_um_list = [y * y_sens_um * impulse_xy_v for y in map_y_index_list]
    # else:
    #     x_pos_um_list = [x * x_sens_um * impulse_xy_v for x in map_x_pos_v_list]
    #     y_pos_um_list = [y * y_sens_um * impulse_xy_v for y in map_y_pos_v_list]



    estimated_square = np.sqrt(len(tdms_files))
    print (f'# of files analyzed: {len(tdms_files)}, square root is : {estimated_square}')
    map_x_pix = int(estimated_square)
    map_y_pix = int(estimated_square)

    data = {
    'filepaths' : filepaths,
    'curve_index': mapping_index_list,
    'x_index': map_x_index_list,
    'y_index': map_y_index_list,
    # 'x_pos_v': map_x_pos_v_list,
    # 'y_pos_v': map_y_pos_v_list,
    'z_height_um': z_height_um_list,
    'z_height_v': z_setpoint_trig_v_list,
    # 'z_height_um_zero': map_test_um_zeroed,
    'x_pos_um': x_pos_um_list,
    'y_pos_um': y_pos_um_list, 
    }

    # Convert the dictionary to a DataFrame
    df = pd.DataFrame(data)


    # Sort the dataframe
    df_sorted = df.sort_values(by='curve_index')
    x_pos_um_sorted = df_sorted['x_pos_um'].values
    y_pos_um_sorted = df_sorted['y_pos_um'].values
    z_height_um_sorted = df_sorted['z_height_um'].values

    # Get final data files
    x_axis = x_pos_um_sorted[:map_x_pix].round(1)
    y_axis = np.reshape(y_pos_um_sorted, (map_x_pix, map_y_pix))[:,0].round(1)
    z_pos_2d = np.reshape(z_height_um_sorted, (map_x_pix, map_y_pix)) 


    # Mirror flip the 2D array along the vertical axis
    z_pos_2d_flipped = np.flip(z_pos_2d, axis=1)

    # zero height to represent the actual height since the height is calculated as the approach 
    map_test_um_zeroed = -z_pos_2d_flipped + z_pos_2d_flipped.max().max()
    df_sorted['z_height_um_zero'] = map_test_um_zeroed.flatten()

    # df_dict = {col: df_sorted[col].to_numpy() for col in df_sorted.columns}
    
    return df_sorted

def load_df_file_csv(map_path, params=None, flipAxis=True, zmin=None, zmax=None, save_svg=False, svg_path=None):
    """
    Loads a CSV file of an already analyzed map that was loaded into a dataframe.
    If a params dictionary is provided (from get_map_parameters), it overrides relevant parameters.

    Parameters
    ----------
    map_path : str
        Path to the CSV file containing the map data.
    params : dict, optional
        Dictionary containing mapping parameters (from get_map_parameters).
    flipAxis : bool, optional
        Whether to flip the aspect ratio of the axes (default is True).
    zmin : float or None, optional
        Minimum Z value for colormap scaling. If None, uses minimum from data.
    zmax : float or None, optional
        Maximum Z value for colormap scaling. If None, uses maximum from data.
    save_svg : bool, optional
        Whether to save the heatmap as an SVG file (default is False).
    svg_path : str, optional
        Full path where the SVG file should be saved. If None and save_svg is True,
        saves to current directory with name derived from map_path.

    Returns
    -------
    map_test_um_zeroed : pandas.Series or numpy.ndarray
        Zeroed Z-axis values in micrometers.
    x_axis : numpy.ndarray
        X-axis values in micrometers.
    y_axis : numpy.ndarray
        Y-axis values in micrometers.
    """
    print(f'Analyzing map: {map_path}')
    map_test = pd.read_csv(map_path)

    # Internal defaults
    defaults = {
        'z_sens_um': 6,
        'x_sens_um': 5.685,
        'y_sens_um': 3.960,
        'map_x_step': 0.14,
        'map_y_step': 0.14,
        'map_x_pix': 32,
        'map_y_pix': 32
    }

    # Override defaults with params if provided
    if params is not None:
        for k in defaults:
            if k in params:
                defaults[k] = params[k]

    z_sens_um = defaults['z_sens_um']
    x_sens_um = defaults['x_sens_um']
    y_sens_um = defaults['y_sens_um']
    dx_v = defaults['map_x_step']
    dy_v = defaults['map_y_step']
    map_x_pix = defaults['map_x_pix']
    map_y_pix = defaults['map_y_pix']

    try:
        z_height_arr_v = map_test['z_height_um_zero']
    except Exception as e:
        print(f"Error loading z_height_um_zero from CSV: {e}")
        z_height_arr_v = map_test['z_height_um']

    map_test_um = z_height_arr_v * z_sens_um
    map_test_um_zeroed = -map_test_um + map_test_um.max().max()
    x_axis = (np.arange(map_x_pix) * dx_v * x_sens_um).round(1)
    y_axis = (np.arange(map_y_pix) * dy_v * y_sens_um).round(1)

    # Define the z-axis range for the colormap
    z_min = zmin if zmin is not None else map_test_um_zeroed.min().min()
    z_max = zmax if zmax is not None else map_test_um_zeroed.max().max()
    vmin = z_min
    vmax = z_max

    z_pos_2d = np.reshape(map_test_um_zeroed, (map_x_pix, map_y_pix))

    fig, ax = plt.subplots(figsize=(20, 10))
    a = sns.heatmap(z_pos_2d, xticklabels=x_axis, yticklabels=y_axis, ax=ax, cmap="YlOrBr", vmin=vmin, vmax=vmax)
    a.invert_yaxis()
    xy_axis = -1 if flipAxis else 1
    a.set_aspect((y_sens_um / x_sens_um) ** (xy_axis * 1))
    print(f'y_sens_um: {y_sens_um}, x_sens_um: {x_sens_um}')
    a.set_xlabel('X axis (um)', fontsize=20)
    a.set_ylabel('Y axis (um)', fontsize=20)
    colorbar = a.collections[0].colorbar
    colorbar.set_label('Z axis (um)', fontsize=18)
    colorbar.ax.yaxis.label.set_rotation(90)
    _ = plt.xticks(ticks=np.arange(0, len(x_axis), 5), labels=x_axis[::5].round(2), rotation=45, fontsize=18)
    _ = plt.yticks(ticks=np.arange(0, len(y_axis), 5), labels=y_axis[::5].round(2), rotation=0, fontsize=18)
    colorbar.ax.tick_params(labelsize=20)
    filename = os.path.basename(map_path)
    a.set_title(f'Heatmap: {filename}', fontsize=20)
    ax.minorticks_on()
    ax.tick_params(axis='both', which='minor', length=4, color='black')
    fig.patch.set_alpha(0.0)
    ax.minorticks_on()
    ax.tick_params(axis='both', which='minor', length=4, color='black')

    # Save SVG if requested
    if save_svg and svg_path:
        try:
            output_path = svg_path
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(map_path))[0]
                output_path = os.path.join(os.getcwd(), f"{base_name}.svg")
            fig.savefig(output_path, format='svg', bbox_inches='tight', transparent=True)
            print(f"Saved SVG to: {output_path}")
        except Exception as e:
            print(f"Error saving SVG: {e}")

    return map_test_um_zeroed, x_axis, y_axis

def load_2d_map_file_csv(map_path, params=None, flipAxis=True, zmin=None, zmax=None, save_svg=False, svg_path=None, lastColFirst=False, cmap="YlOrBr"):
    """
    Opens a CSV file containing a 2D map of data representing a topographical map.
    Args:
        map_path (str): The path to the CSV file containing the map data.
        params (dict, optional): Dictionary from get_map_parameters to override axis sensitivities and steps.
        flipAxis (bool): If True, flips the Y axis to match the expected orientation.
        zmin (float, optional): Minimum value for the Z axis in the heatmap.
        zmax (float, optional): Maximum value for the Z axis in the heatmap.
        save_svg (bool, optional): Whether to save the heatmap as an SVG file (default is False).
        svg_path (str, optional): Full path where the SVG file should be saved. If None and save_svg is True,
            saves to current directory with name derived from map_path.
        lastColFirst (bool, optional): If True, move the last column to the first position.

    Returns:
        pd.DataFrame: A DataFrame containing the processed map data.
        np.ndarray: The X axis values in micrometers.
        np.ndarray: The Y axis values in micrometers.
    """
    print(f'Analyzing map: {map_path}')
    map_test = pd.read_csv(map_path, header=None)

    # Default parameters
    defaults = {
        'z_sens_um': 6,
        'x_sens_um': 5.685,
        'y_sens_um': 3.960,
        'map_x_step': 0.14,
        'map_y_step': 0.14,
        'map_x_pix': map_test.shape[1],
        'map_y_pix': map_test.shape[0]
    }

    # Override defaults with params if provided
    if params is not None:
        for k in defaults:
            if k in params:
                defaults[k] = params[k]

    z_sens_um = defaults['z_sens_um']
    x_sens_um = defaults['x_sens_um']
    y_sens_um = defaults['y_sens_um']
    dx_v = defaults['map_x_step']
    dy_v = defaults['map_y_step']
    map_x_pix = defaults['map_x_pix']
    map_y_pix = defaults['map_y_pix']

    # Convert values
    map_test_um = map_test * z_sens_um
    map_test_um_zeroed = -map_test_um + map_test_um.max().max()
    x_axis = (np.arange(map_x_pix) * dx_v * x_sens_um).round(1)
    y_axis = (np.arange(map_y_pix) * dy_v * y_sens_um).round(1)

    # Define the z-axis range for the colormap
    z_min = zmin if zmin is not None else map_test_um_zeroed.min().min()
    z_max = zmax if zmax is not None else map_test_um_zeroed.max().max()
    vmin = z_min
    vmax = z_max

    # Flip 2D array along vertical axis
    map_test_um_zeroed = np.flip(map_test_um_zeroed.values, axis=1)

    # If lastColFirst is True, move the first column to the last position
    if lastColFirst:
        map_test_um_zeroed = np.roll(map_test_um_zeroed, shift=-1, axis=1)

    fig, ax = plt.subplots(figsize=(20, 10))
    a = sns.heatmap(map_test_um_zeroed, xticklabels=x_axis.round(2), yticklabels=y_axis.round(2), ax=ax, cmap=cmap, vmin=vmin, vmax=vmax)
    a.invert_yaxis()
    xy_axis = -1 if flipAxis else 1
    a.set_aspect((x_sens_um / y_sens_um) ** xy_axis)
    print(f'y_sens_um: {y_sens_um}, x_sens_um: {x_sens_um}')
    a.set_xlabel('X axis (um)', fontsize=20)
    a.set_ylabel('Y axis (um)', fontsize=20)
    colorbar = a.collections[0].colorbar
    colorbar.set_label('Z axis (um)', fontsize=18)
    colorbar.ax.yaxis.label.set_rotation(90)
    _ = plt.xticks(ticks=np.arange(0, len(x_axis), 5), labels=x_axis[::5].round(2), rotation=45, fontsize=18)
    _ = plt.yticks(ticks=np.arange(0, len(y_axis), 5), labels=y_axis[::5].round(2), rotation=0, fontsize=18)
    colorbar.ax.tick_params(labelsize=20)
    filename = os.path.basename(map_path)
    a.set_title(f'Heatmap: {filename}', fontsize=20)
    ax.minorticks_on()
    ax.tick_params(axis='both', which='minor', length=4, color='black')
    fig.patch.set_alpha(0.0)

    # Save SVG if requested
    if save_svg and svg_path:
        try:
            output_path = svg_path
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(map_path))[0]
                output_path = os.path.join(os.getcwd(), f"{base_name}.svg")
            fig.savefig(output_path, format='svg', bbox_inches='tight', transparent=True)
            print(f"Saved SVG to: {output_path}")
        except Exception as e:
            print(f"Error saving SVG: {e}")

    return map_test_um_zeroed, x_axis, y_axis

def compute_time_difference(folder_path: str):
    """
    Computes the time difference between the earliest and latest `.tdms` files in a specified folder,
    based on timestamps extracted from their filenames.

    This function scans all `.tdms` files in the given folder, attempts to extract a timestamp from each
    filename using several predefined patterns, and parses the timestamp into a datetime object.
    It then determines the earliest and latest timestamps and prints the time difference between them
    in the format HH:MM:SS:MS. Files without a recognizable timestamp are skipped.

    Parameters
    ----------
    folder_path : str
        Path to the folder containing `.tdms` files.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with columns:
            - 'filepath': Full path to each `.tdms` file with a recognized timestamp.
            - 'datetime': Corresponding parsed datetime object.
        If fewer than two files with valid timestamps are found, returns an empty DataFrame.

    Notes
    -----
    Supported timestamp patterns in filenames include:
        1. 'YYYYMMDD_HHMMSS.fff' (e.g., '20240614_162642.559')
        2. 'YYYY.MM.DD_HH.MM.SS.ff' (e.g., '2024.06.14_16.26.42.59')
        3. 'YYYY-MM-DDTHH:MM:SS' (e.g., '2024-06-14T16:26:42')
        4. 'YYYYMMDD_HHMMSS' (e.g., '20240614_162642')

    Prints
    ------
        - Number of files processed and matched.
        - Skipped files without recognizable timestamps.
        - Time difference between the earliest and latest file (if at least two matches are found).
    """
    folder = Path(folder_path)
    
    # Define different timestamp patterns to try
    patterns = [
        # Pattern 1: YYYYMMDD_HHMMSS.fff (like in your sample "20240614_162642.559")
        (r"(\d{8}_\d{6}\.\d{3})", "%Y%m%d_%H%M%S.%f"),
        
        # Pattern 2: Original format YYYY.MM.DD_HH.MM.SS.ff
        (r"(\d{4}\.\d{2}\.\d{2}_\d{2}\.\d{2}\.\d{2}\.\d{2})", "%Y.%m.%d_%H.%M.%S.%f"),
        
        # Pattern 3: ISO format YYYY-MM-DDTHH:MM:SS
        (r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", "%Y-%m-%dT%H:%M:%S"),
        
        # Pattern 4: Compact date_time format YYYYMMDD_HHMMSS
        (r"(\d{8}_\d{6})", "%Y%m%d_%H%M%S")
    ]
    
    timestamps = []
    files_processed = 0
    files_matched = 0
    
    for file in folder.glob("*.tdms"):
        files_processed += 1
        matched = False
        
        # Try each pattern until one works
        for pattern_regex, date_format in patterns:
            pattern = re.compile(pattern_regex)
            match = pattern.search(file.name)
            
            if match:
                timestamp_str = match.group(1)
                try:
                    dt = datetime.strptime(timestamp_str, date_format)
                    timestamps.append((file.name, dt))
                    files_matched += 1
                    matched = True
                    break  # Stop after first successful match
                except ValueError:
                    continue  # Try next pattern if datetime parsing fails
        
        if not matched:
            print(f"Skipped: {file.name} (no timestamp matched)")
    
    print(f"Files processed: {files_processed}, matches found: {files_matched}")
    
    if len(timestamps) >= 2:
        timestamps.sort(key=lambda x: x[1])
        t_first = timestamps[0][1]
        t_last = timestamps[-1][1]
        delta = t_last - t_first
        delta_seconds = delta.total_seconds()
        hours, remainder = divmod(delta_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = delta.microseconds // 10000  # Two-digit ms

        print(f"\nTime difference between first and last file HH:MM:SS:MS: "
              f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}:{milliseconds:02}")
        df = pd.DataFrame([(str(folder / fname), dt) for fname, dt in timestamps], columns=["filepath", "datetime"])
        return df
    else:
        print("Not enough files to compute a time difference.")
        return pd.DataFrame(columns=["filename", "datetime"])
    
def analyze_map_dimension(df, map_x_pix, map_y_pix):
    """
    if no map metadata given,
    Analyzes the map data dictionary structure and checks if the data dimensions match expected values.
    
    Parameters:
    ----------
    df : dict
        Dictionary containing map data with various columns including 'z_height_um'
    map_x_pix : int
        Expected width of the map in pixels
    map_y_pix : int
        Expected height of the map in pixels
        
    Returns:
    -------
    int
        Number of values to trim (if any) to make the data fit the expected dimensions,
        or 0 if no trimming is needed
    """
    print(type(df))
    print(f"Dictionary structure: {df.keys()}")
    print(f"Length of df: {len(df)}")  # Number of keys in dictionary
    print(f"Size of z_height_um column: {len(df['z_height_um'])}")  # Number of elements in that column
    print(f"Shape of data: {map_x_pix} x {map_y_pix} = {map_x_pix * map_y_pix}")
    
    # Check if the size matches the expected dimensions
    if map_x_pix * map_y_pix != len(df['z_height_um']):
        print("The size of 'z_height_um' does not match the expected shape.")
        if map_x_pix * map_y_pix < len(df['z_height_um']):
            data_to_trim = len(df['z_height_um']) - (map_x_pix * map_y_pix)
            print(f"Consider trimming {data_to_trim} values from the end of 'z_height_um'.")
            return data_to_trim
        else:
            print("The expected shape is larger than the data size. Consider padding the data.")
            return 0
    else:
        print("Data dimensions match the expected shape.")
        return 0
    
# # import gwyfile
# def save_gwy(array_um, px_um_x, px_um_y, out_path, title="Mechanical map"):
#     """Save data as a native Gwyddion (.gwy) file with full metadata."""
#     # Get dimensions
#     y_res, x_res = array_um.shape
    
#     # Convert to float32
#     data = np.asarray(array_um, dtype=np.float32)
    
#     # Calculate dimensions in meters (required by Gwyddion)
#     x_real_m = float(px_um_x * x_res) * 1e-6
#     y_real_m = float(px_um_y * y_res) * 1e-6
    
#     # Create a DataField with proper calibration
#     datafield = gwyfile.DataField(
#         data=data,
#         xreal=x_real_m,      # width in meters
#         yreal=y_real_m,      # height in meters
#         si_unit_xy="m",      # lateral units
#         si_unit_z="m",       # height units
#         xoff=0.0, yoff=0.0
#     )
    
#     # Create a GWY container and add the datafield
#     container = gwyfile.Container()
#     container["/0/data"] = datafield
#     container["/0/data/title"] = title
#     container["/0/meta/channel"] = "Topography"
    
#     # Save with proper xy and z units
#     for prefix, unit in [("xy", "µm"), ("z", "µm")]:
#         container[f"/0/data/si_unit_{prefix}"] = gwyfile.GwySIUnit(unit)
    
#     # Save to file
#     gwyfile.write(container, out_path)
#     print(f"GWY file saved: {out_path}")


# # Output path for GWY
# gwy_path = os.path.join(out_dir, f"{map_basename}_topography.gwy")

# # Save as GWY
# save_gwy(
#     z_pos_2d_flipped_um_zeroed,
#     px_um_x, px_um_y,
#     gwy_path,
#     title=f"Topography map: {map_basename}"
# )
# create heatmap plot function 
# def create_heatmap(df_map, params=None, flipAxis=True, zmin=None, 
#                    zmax=None, value_key="z_height_um_zero", annot=False, 
#                    lastColFirst=True, correct_indices=False, cmap = "YlOrBr", 
#                    save_svg=False, svg_path=None):
#     """
#     Creates a heatmap plot from map data which can be either a DataFrame or dictionary from load_map_file_square_tdms.
#     Args:
#         df_map (dict or pd.DataFrame): Dictionary with map data from load_map_file_square_tdms or DataFrame with map data.
#         params (dict, optional): Dictionary from get_map_parameters to override axis sensitivities and steps.
#         flipAxis (bool): If True, flips the Y axis to match the expected orientation.
#         zmin (float, optional): Minimum value for the Z axis in the heatmap.
#         zmax (float, optional): Maximum value for the Z axis in the heatmap.
#         value_key (str): Key name in the dictionary for the Z values (default "z_height_um").
#         annot (bool): Whether to annotate the heatmap with values (default is True).
#         lastColFirst (bool): Whether to roll the last column to the first position (default is True).
#         correct_indices (bool): Whether to regenerate indices if integrity check fails (default is False).
#         cmap (str): Colormap to use for the heatmap (default is "YlOrBr").
#         save_svg (bool, optional): Whether to save the heatmap as an SVG file (default is False).
#         svg_path (str, optional): Full path where the SVG file should be saved. If None and save_svg is True,
#             saves to current directory with name derived from input.

#     Returns:
#         pd.DataFrame: A DataFrame containing the processed map data.
#         np.ndarray: The X axis values in micrometers.
#         np.ndarray: The Y axis values in micrometers.
#     """

#     # Check if input is a dictionary from load_map_file_square_tdms
#     if isinstance(df_map, dict):
#         print("Using dictionary from load_map_file_square_tdms")
#         # Create a 2D array from the dictionary data
#         x_indices = df_map['x_index']
#         y_indices = df_map['y_index']

#         # Get dimensions from params or from max indices
#         map_x_pix = params['map_x_pix'] if params and 'map_x_pix' in params else int(np.max(x_indices)) + 1
#         map_y_pix = params['map_y_pix'] if params and 'map_y_pix' in params else int(np.max(y_indices)) + 1

#         print (f'Map dimensions: {map_x_pix} x {map_y_pix}')
#         if correct_indices:
#             # # check map for map integrity 
#             bool_error, _ = check_map_indice_integrity(df_map, map_x_pix, map_y_pix)

#             if bool_error:
#                 x_pos_1d, y_pos_1d, curve_index = generate_xy_map_positions(map_x_pix=map_x_pix, map_y_pix=map_y_pix)
#                 x_indices = x_pos_1d
#                 y_indices = y_pos_1d
#                 print ('Map indices were regenerated due to integrity error')   

#                 # replace curve_index in df_map
#                 df_map['curve_index'] = curve_index
#                 df_map['x_index'] = x_indices
#                 df_map['y_index'] = y_indices   

#         # Use the specified key, fallback to 'z_height_um_zero' if not present
#         if value_key in df_map:
#             z_values = df_map[value_key]
#         # elif 'z_height_um_zero' in df_map:
#         #     z_values = df_map['z_height_um_zero']
#         else:
#             z_values = df_map['z_height_um']

#         # Create empty 2D array and fill with values
#         map_test_um_zeroed = np.zeros((map_y_pix, map_x_pix), dtype=np.float64)
#         # Parse data into the map
#         print (type(map_test_um_zeroed))
#         for i in range(len(z_values)):
#             x_idx = int(x_indices[i])
#             y_idx = int(y_indices[i])
#             if 0 <= x_idx < map_x_pix and 0 <= y_idx < map_y_pix:
#                 if np.isnan(z_values[i]):
#                     map_test_um_zeroed[y_idx, x_idx] = 0
#                 else:
#                     map_test_um_zeroed[y_idx, x_idx] = z_values[i]

#         # get the last column and move it to the first column. Remove this if fixed in the future -LDV
#         if lastColFirst:
#             map_test_um_zeroed = np.roll(map_test_um_zeroed, shift=1, axis=1)

#         # Convert to DataFrame for consistency with the rest of the function
#         df_map_test_um_zeroed = pd.DataFrame(map_test_um_zeroed, dtype=np.float64)
#         map_path = "Dictionary Input"  # Default path name when using Dictionary
#         print (type(df_map_test_um_zeroed))

#     elif isinstance(df_map, pd.DataFrame):
#         # Assume df_map is a DataFrame with at least x_index, y_index, and value_key columns
#         print("Using provided DataFrame for heatmap")
#         x_indices = df_map['x_index'].values
#         y_indices = df_map['y_index'].values

#         # Get dimensions from params or from max indices
#         map_x_pix = params[0]['map_x_pix'] if params and 'map_x_pix' in params else int(np.max(x_indices)) + 1
#         map_y_pix = params[0]['map_y_pix'] if params and 'map_y_pix' in params else int(np.max(y_indices)) + 1

#         print(f'Map dimensions: {map_x_pix} x {map_y_pix}')
#         if correct_indices:
#             bool_error, _ = check_map_indice_integrity(df_map, map_x_pix, map_y_pix)
#             if bool_error:
#                 x_pos_1d, y_pos_1d, curve_index = generate_xy_map_positions(map_x_pix=map_x_pix, map_y_pix=map_y_pix)
#                 x_indices = x_pos_1d
#                 y_indices = y_pos_1d
#                 print('Map indices were regenerated due to integrity error')
#                 df_map['curve_index'] = curve_index
#                 df_map['x_index'] = x_indices
#                 df_map['y_index'] = y_indices

#         # Use the specified key, fallback to 'z_height_um_zero' if not present
#         if value_key in df_map.columns:
#             z_values = df_map[value_key].values
#         else:
#             z_values = df_map['z_height_um'].values

#         # Create empty 2D array and fill with values
#         map_test_um_zeroed = np.zeros((map_y_pix, map_x_pix), dtype=np.float64)
#         for i in range(len(z_values)):
#             x_idx = int(x_indices[i])
#             y_idx = int(y_indices[i])
#             if 0 <= x_idx < map_x_pix and 0 <= y_idx < map_y_pix:
#                 if np.isnan(z_values[i]):
#                     map_test_um_zeroed[y_idx, x_idx] = 0
#                 else:
#                     map_test_um_zeroed[y_idx, x_idx] = z_values[i]

#         if lastColFirst:
#             map_test_um_zeroed = np.roll(map_test_um_zeroed, shift=-1, axis=1)

#         df_map_test_um_zeroed = pd.DataFrame(map_test_um_zeroed, dtype=np.float64)
#         map_path = "DataFrame Input"  # Default path name when using DataFrame
#     else:
#         # Assume df_map is a path to a CSV file
#         map_path = df_map
#         print(f'Loading map from file: {map_path}')


#     # Default parameters
#     defaults = {
#         'z_sens_um': 6,
#         'x_sens_um': 5.685,
#         'y_sens_um': 3.960,
#         'map_x_step': 0.14,
#         'map_y_step': 0.14,
#         'map_x_pix': df_map_test_um_zeroed.shape[0],
#         'map_y_pix': df_map_test_um_zeroed.shape[1]
#     }

#     # Override defaults with params if provided
#     if params is not None:
#         for k in defaults:
#             if k in params:
#                 defaults[k] = params[k]

#     # z_sens_um = defaults['z_sens_um']
#     x_sens_um = defaults['x_sens_um']
#     y_sens_um = defaults['y_sens_um']
#     dx_v = defaults['map_x_step']
#     dy_v = defaults['map_y_step']
#     map_x_pix = defaults['map_x_pix']
#     map_y_pix = defaults['map_y_pix']

#     # Generate axis values
#     x_axis = (np.arange(map_x_pix) * dx_v * x_sens_um).round(1)
#     y_axis = (np.arange(map_y_pix) * dy_v * y_sens_um).round(1)

#     # Define the z-axis range for the colormap
#     z_min = zmin if zmin is not None else df_map_test_um_zeroed.min().min()
#     z_max = zmax if zmax is not None else df_map_test_um_zeroed.max().max()
#     vmin = z_min
#     vmax = z_max

#     # plot the heatmp
#     fig, ax = plt.subplots(figsize=(20, 10))
#     if annot is False:
#         a = sns.heatmap(df_map_test_um_zeroed, xticklabels=x_axis.round(2), yticklabels=y_axis.round(2), ax=ax, cmap=cmap, vmin=vmin, vmax=vmax, annot=annot)
#     else :
#         a = sns.heatmap(df_map_test_um_zeroed, annot = df_map_test_um_zeroed, xticklabels=x_axis.round(2), yticklabels=y_axis.round(2), ax=ax, cmap=cmap, vmin=vmin, vmax=vmax)
#     a.invert_yaxis()
#     xy_axis = -1 if flipAxis else 1
    
#     a.set_aspect((x_sens_um / y_sens_um) ** xy_axis)
    
#     print(f'y_sens_um: {y_sens_um}, x_sens_um: {x_sens_um}')
    
#     a.set_xlabel('X axis (um)', fontsize=20)
#     a.set_ylabel('Y axis (um)', fontsize=20)
#     colorbar = a.collections[0].colorbar
#     colorbar.set_label(f'{value_key}', fontsize=18)
#     colorbar.ax.yaxis.label.set_rotation(90)
#     _ = plt.xticks(ticks=np.arange(0, len(x_axis), 5), labels=x_axis[::5].round(2), rotation=45, fontsize=18)
#     _ = plt.yticks(ticks=np.arange(0, len(y_axis), 5), labels=y_axis[::5].round(2), rotation=0, fontsize=18)
#     colorbar.ax.tick_params(labelsize=20)
#     # filename = os.path.basename(map_path)
#     # a.set_title(f'Heatmap: {filename}', fontsize=20)
#     ax.minorticks_on()
#     ax.tick_params(axis='both', which='minor', length=4, color='black')
#     fig.patch.set_alpha(0.0)

#     # Save SVG if requested
#     if save_svg or svg_path:
#         try:
#             output_path = svg_path
#             if output_path is None:
#                 # Derive filename from input type
#                 if isinstance(map_path, str):
#                     base_name = os.path.splitext(os.path.basename(map_path))[0]
#                 else:
#                     base_name = "heatmap"
#                 output_path = os.path.join(os.getcwd(), f"{base_name}.svg")
#             fig.savefig(output_path, format='svg', bbox_inches='tight', transparent=True)
#             print(f"Saved SVG to: {output_path}")
#         except Exception as e:
#             print(f"Error saving SVG: {e}")

#     return df_map_test_um_zeroed, x_axis, y_axis

def create_heatmap(df_map, params=None, flipAxis=True, zmin=None, 
                   zmax=None, value_key="z_height_um_zero", annot=False, 
                   lastColFirst=True, correct_indices=False, cmap="YlOrBr", 
                   save_svg=False, svg_path=None, nan=False, scale_axis=False,
                   logscale=False):
    """
    Creates a heatmap plot from map data which can be either a DataFrame or dictionary from load_map_file_square_tdms.
    
    Args:
        df_map (dict or pd.DataFrame): Dictionary with map data from load_map_file_square_tdms or DataFrame with map data.
        params (dict, optional): Dictionary from get_map_parameters to override axis sensitivities and steps.
        flipAxis (bool): If True, flips the Y axis to match the expected orientation.
        zmin (float, optional): Minimum value for the Z axis in the heatmap (NOT in log10 if logscale=True).
        zmax (float, optional): Maximum value for the Z axis in the heatmap (NOT in log10 if logscale=True).
        value_key (str): Key name in the dictionary for the Z values (default "z_height_um_zero").
        annot (bool): Whether to annotate the heatmap with values (default is False).
        lastColFirst (bool): Whether to roll the last column to the first position (default is True).
        correct_indices (bool): Whether to regenerate indices if integrity check fails (default is False).
        cmap (str): Colormap to use for the heatmap (default is "YlOrBr").
        save_svg (bool, optional): Whether to save the heatmap as an SVG file (default is False).
        svg_path (str, optional): Full path where the SVG file should be saved.
        nan (bool): If True, set all values outside [zmin, zmax] to NaN (displayed as white).
        scale_axis (bool): If True, use scaled axis values instead of grid indices.
        logscale (bool): If True, apply log10 scaling to the colormap (default is False).

    Returns:
        pd.DataFrame: A DataFrame containing the processed map data. \n
        np.ndarray: The X axis values in micrometers.\n
        np.ndarray: The Y axis values in micrometers.\n
    """
    import matplotlib.colors as mcolors

    # Check if input is a dictionary from load_map_file_square_tdms
    if isinstance(df_map, dict):
        print("Using dictionary from load_map_file_square_tdms")
        x_indices = df_map['x_index']
        y_indices = df_map['y_index']

        map_x_pix = params['map_x_pix'] if params and 'map_x_pix' in params else int(np.max(x_indices)) + 1
        map_y_pix = params['map_y_pix'] if params and 'map_y_pix' in params else int(np.max(y_indices)) + 1

        print(f'Map dimensions: {map_x_pix} x {map_y_pix}')
        if correct_indices:
            bool_error, _ = check_map_indice_integrity(df_map, map_x_pix, map_y_pix)
            if bool_error:
                x_pos_1d, y_pos_1d, curve_index = generate_xy_map_positions(map_x_pix=map_x_pix, map_y_pix=map_y_pix)
                x_indices = x_pos_1d
                y_indices = y_pos_1d
                print('Map indices were regenerated due to integrity error')
                df_map['curve_index'] = curve_index
                df_map['x_index'] = x_indices
                df_map['y_index'] = y_indices

        if value_key in df_map:
            z_values = df_map[value_key]
        else:
            z_values = df_map['z_height_um']

        map_test_um_zeroed = np.zeros((map_y_pix, map_x_pix), dtype=np.float64)
        for i in range(len(z_values)):
            x_idx = int(x_indices[i])
            y_idx = int(y_indices[i])
            if 0 <= x_idx < map_x_pix and 0 <= y_idx < map_y_pix:
                map_test_um_zeroed[y_idx, x_idx] = z_values[i] if not np.isnan(z_values[i]) else (0 if logscale else np.nan)

        if lastColFirst:
            map_test_um_zeroed = np.roll(map_test_um_zeroed, shift=1, axis=1)

        df_map_test_um_zeroed = pd.DataFrame(map_test_um_zeroed, dtype=np.float64)
        map_path = "Dictionary Input"

    elif isinstance(df_map, pd.DataFrame):
        print("Using provided DataFrame for heatmap")
        x_indices = df_map['x_index'].values
        y_indices = df_map['y_index'].values

        map_x_pix = params[0]['map_x_pix'] if params and 'map_x_pix' in params else int(np.max(x_indices)) + 1
        map_y_pix = params[0]['map_y_pix'] if params and 'map_y_pix' in params else int(np.max(y_indices)) + 1

        print(f'Map dimensions: {map_x_pix} x {map_y_pix}')
        if correct_indices:
            bool_error, _ = check_map_indice_integrity(df_map, map_x_pix, map_y_pix)
            if bool_error:
                x_pos_1d, y_pos_1d, curve_index = generate_xy_map_positions(map_x_pix=map_x_pix, map_y_pix=map_y_pix)
                x_indices = x_pos_1d
                y_indices = y_pos_1d
                print('Map indices were regenerated due to integrity error')
                df_map['curve_index'] = curve_index
                df_map['x_index'] = x_indices
                df_map['y_index'] = y_indices

        if value_key in df_map.columns:
            z_values = df_map[value_key].values
        else:
            z_values = df_map['z_height_um'].values

        map_test_um_zeroed = np.zeros((map_y_pix, map_x_pix), dtype=np.float64)
        for i in range(len(z_values)):
            x_idx = int(x_indices[i])
            y_idx = int(y_indices[i])
            if 0 <= x_idx < map_x_pix and 0 <= y_idx < map_y_pix:
                map_test_um_zeroed[y_idx, x_idx] = z_values[i] if not np.isnan(z_values[i]) else (0 if logscale else np.nan)

        if lastColFirst:
            map_test_um_zeroed = np.roll(map_test_um_zeroed, shift=-1, axis=1)

        df_map_test_um_zeroed = pd.DataFrame(map_test_um_zeroed, dtype=np.float64)
        map_path = "DataFrame Input"
    else:
        map_path = df_map
        print(f'Loading map from file: {map_path}')

    # Default parameters
    defaults = {
        'z_sens_um': 6,
        'x_sens_um': 5.685,
        'y_sens_um': 3.960,
        'map_x_step': 0.14,
        'map_y_step': 0.14,
        'map_x_pix': df_map_test_um_zeroed.shape[0],
        'map_y_pix': df_map_test_um_zeroed.shape[1]
    }

    if params is not None:
        for k in defaults:
            if k in params:
                defaults[k] = params[k]

    x_sens_um = defaults['x_sens_um']
    y_sens_um = defaults['y_sens_um']
    dx_v = defaults['map_x_step']
    dy_v = defaults['map_y_step']
    map_x_pix = defaults['map_x_pix']
    map_y_pix = defaults['map_y_pix']

    # Generate axis values
    if scale_axis:
        x_axis = (np.arange(map_x_pix) * dx_v * x_sens_um).round(1)
        y_axis = (np.arange(map_y_pix) * dy_v * y_sens_um).round(1)
        x_labels = x_axis
        y_labels = y_axis
        x_ticklabels = x_axis
        y_ticklabels = y_axis
    else:
        x_labels = np.arange(map_x_pix)
        y_labels = np.arange(map_y_pix)
        x_ticklabels = x_labels
        y_ticklabels = y_labels

    # Prepare data for plotting
    data = df_map_test_um_zeroed.values.copy()
    
    # For logscale, handle zeros and negatives first
    if logscale:
        data[data <= 0] = np.nan
    
    # Handle filtering based on zmin/zmax if nan=True
    if nan:
        if zmin is not None:
            data[data < zmin] = np.nan
        if zmax is not None:
            data[data > zmax] = np.nan
    
    # Apply log10 transformation if requested
    if logscale:
        plot_data = np.log10(data)
        colorbar_label = f'log10({value_key})'
        
        # Define colormap range in log10 space
        if zmin is not None and zmin > 0:
            vmin = np.log10(zmin)
        else:
            vmin = np.nanmin(plot_data)
        
        if zmax is not None and zmax > 0:
            vmax = np.log10(zmax)
        else:
            vmax = np.nanmax(plot_data)
    else:
        plot_data = data
        colorbar_label = f'{value_key}'
        
        # Define colormap range in linear space
        vmin = zmin if zmin is not None else np.nanmin(plot_data)
        vmax = zmax if zmax is not None else np.nanmax(plot_data)
    
    # Convert to DataFrame for plotting
    plot_data = pd.DataFrame(plot_data, dtype=np.float64)

    # Create colormap with bounds and set colors for out-of-range values
    current_cmap = plt.cm.get_cmap(cmap).copy()
    current_cmap.set_bad(color='white')
    
    if zmin is not None:
        current_cmap.set_under(current_cmap(0))
    if zmax is not None:
        current_cmap.set_over(current_cmap(1.0))
    
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax, clip=True)

    # print zmax and zmin of the map data set
    # print z-range of the dataset

    print(f"zmax: {vmax}, zmin: {vmin}")

    # Plot the heatmap
    fig, ax = plt.subplots(figsize=(20, 10))
    if annot is False:
        a = sns.heatmap(
            plot_data,
            xticklabels=x_ticklabels.round(2) if scale_axis else x_ticklabels,
            yticklabels=y_ticklabels.round(2) if scale_axis else y_ticklabels,
            ax=ax, cmap=current_cmap, vmin=vmin, vmax=vmax, annot=annot, norm=norm
        )
    else:
        # Annotate with original values (not log)
        annot_data = df_map_test_um_zeroed if logscale else plot_data
        a = sns.heatmap(
            plot_data,
            annot=annot_data,
            fmt=".2f",
            xticklabels=x_ticklabels.round(2) if scale_axis else x_ticklabels,
            yticklabels=y_ticklabels.round(2) if scale_axis else y_ticklabels,
            ax=ax, cmap=current_cmap, vmin=vmin, vmax=vmax, norm=norm
        )
    
    a.invert_yaxis()
    xy_axis = -1 if flipAxis else 1
    a.set_aspect((x_sens_um / y_sens_um) ** xy_axis)
    print(f'y_sens_um: {y_sens_um}, x_sens_um: {x_sens_um}')

    if scale_axis:
        a.set_xlabel('X axis (um)', fontsize=20)
        a.set_ylabel('Y axis (um)', fontsize=20)
    else:
        a.set_xlabel('X index', fontsize=20)
        a.set_ylabel('Y index', fontsize=20)

    colorbar = a.collections[0].colorbar
    colorbar.set_label(colorbar_label, fontsize=18)
    colorbar.ax.yaxis.label.set_rotation(90)

    # Format colorbar tick labels to remove unnecessary decimals
    if logscale:
        colorbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}' if x == int(x) else f'{x:.0f}'))
    
    
    # _ = plt.xticks(
    #     ticks=np.arange(0, len(x_labels), 5),
    #     labels=x_labels[::5].round(2) if scale_axis else x_labels[::5],
    #     rotation=45, fontsize=18
    # )
    # _ = plt.yticks(
    #     ticks=np.arange(0, len(y_labels), 5),
    #     labels=y_labels[::5].round(2) if scale_axis else y_labels[::5],
    #     rotation=0, fontsize=18
    # )

    _ = plt.xticks(
    ticks=np.arange(0, len(x_labels), 5),
    labels=[f'{x:.0f}' if x == int(x) else f'{x:.0f}' for x in x_labels[::5]] if scale_axis else x_labels[::5],
    rotation=45, fontsize=18
    )
    _ = plt.yticks(
        ticks=np.arange(0, len(y_labels), 5),
        labels=[f'{y:.0f}' if y == int(y) else f'{y:.0f}' for y in y_labels[::5]] if scale_axis else y_labels[::5],
        rotation=0, fontsize=18
    )
    colorbar.ax.tick_params(labelsize=20)
    ax.minorticks_on()
    ax.tick_params(axis='both', which='minor', length=4, color='black')
    fig.patch.set_alpha(0.0)

    # Add scale bar if scale_axis is True
    if scale_axis:
        scalebar_length_um = 10
        px_per_um = 1.0 / (dx_v * x_sens_um)
        scalebar_px = int(scalebar_length_um * px_per_um)
        x_start = map_x_pix - scalebar_px - 2
        y_start = map_y_pix - 2
        ax.hlines(y=y_start, xmin=x_start, xmax=x_start + scalebar_px, colors='k', linewidth=6)
        ax.text(x_start + scalebar_px / 2, y_start + 1, f"{scalebar_length_um} μm",
                ha='center', va='bottom', color='k', fontsize=16, fontweight='bold')

    # Save SVG if requested
    if save_svg:
        try:
            if svg_path is not None:
                new_path = svg_path
            else:
                map_path = params[0]['map_path']
                last_folder_name = os.path.basename(map_path)
                maps_path = os.path.join(map_path, 'maps')
                os.makedirs(maps_path, exist_ok=True)
                new_path = os.path.join(maps_path, last_folder_name + '_heatmap.svg')

            fig.savefig(new_path, format='svg', bbox_inches='tight', transparent=True)
            print(f"Saved SVG to: {new_path}")
        except Exception as e:
            print(f"Error saving SVG: {e}")

    return df_map_test_um_zeroed, x_labels, y_labels


def create_log_heatmap(df_map, params=None, flipAxis=True, 
                       zmin=None, zmax=None, value_key="z_height_um_zero", 
                       annot=True, lastColFirst=True, correct_indices=False, 
                       cmap="YlOrBr", save_svg=False, svg_path=None, 
                       nan=False, scale_axis=False
                       ):
    """
    Creates a heatmap plot from map data with a log10 colormap scaling. If value_key does not exists, default to height key.
    Args:
        df_map (dict or pd.DataFrame): Dictionary with map data from load_map_file_square_tdms or DataFrame with map data.
        params (dict, optional): Dictionary from get_map_parameters to override axis sensitivities and steps.
        flipAxis (bool): If True, flips the Y axis to match the expected orientation.
        zmin (float, optional): Minimum value for the Z axis in the heatmap. Not in LOG10 values
        zmax (float, optional): Maximum value for the Z axis in the heatmap. Not in LOG10 values
        value_key (str): Key name in the dictionary for the Z values (default "z_height_um_zero").
        annot (bool): Whether to annotate the heatmap with values (default is True).
        lastColFirst (bool): Whether to roll the last column to the first position (default is True).
        correct_indices (bool): Whether to regenerate indices if integrity check fails (default is False).
        cmap (str): Colormap to use for the heatmap (default is "YlOrBr").
        save_svg (bool, optional): Whether to save the heatmap as an SVG file (default is False).
        svg_path (str, optional): Full path where the SVG file should be saved. If None and save_svg is True,
            saves to current directory with name derived from input.
        nan (bool): If True, set all values outside [zmin, zmax] to nan before log10. If False, do nothing.
        scale_axis (bool): If True, use scaled axis values instead of grid indices.

    Returns:
        pd.DataFrame: A DataFrame containing the processed map data.
        np.ndarray: The X axis values in micrometers.
        np.ndarray: The Y axis values in micrometers.
    """

    import matplotlib.colors as mcolors

    # Check if input is a dictionary from load_map_file_square_tdms
    if isinstance(df_map, dict):
        print("Using dictionary from load_map_file_square_tdms")
        x_indices = df_map['x_index']
        y_indices = df_map['y_index']
        map_x_pix = params['map_x_pix'] if params and 'map_x_pix' in params else int(np.max(x_indices)) + 1
        map_y_pix = params['map_y_pix'] if params and 'map_y_pix' in params else int(np.max(y_indices)) + 1

        print(f'Map dimensions: {map_x_pix} x {map_y_pix}')
        if correct_indices:
            bool_error, _ = check_map_indice_integrity(df_map, map_x_pix, map_y_pix)
            if bool_error:
                x_pos_1d, y_pos_1d, curve_index = generate_xy_map_positions(map_x_pix=map_x_pix, map_y_pix=map_y_pix)
                x_indices = x_pos_1d
                y_indices = y_pos_1d
                print('Map indices were regenerated due to integrity error')
                df_map['curve_index'] = curve_index
                df_map['x_index'] = x_indices
                df_map['y_index'] = y_indices

        # if value_key is not found, default to 'z_height_um'
        if value_key in df_map:
            z_values = df_map[value_key]
        else:
            z_values = df_map['z_height_um']

        # Create empty 2D array and fill with values
        map_test_um_zeroed = np.zeros((map_y_pix, map_x_pix), dtype=np.float64)
        for i in range(len(z_values)):
            x_idx = int(x_indices[i])
            y_idx = int(y_indices[i])
            if 0 <= x_idx < map_x_pix and 0 <= y_idx < map_y_pix:
                if np.isnan(z_values[i]):
                    map_test_um_zeroed[y_idx, x_idx] = 0
                else:
                    map_test_um_zeroed[y_idx, x_idx] = z_values[i]
        # if the last column is first, shift the last column and move to the start
        if lastColFirst:
            map_test_um_zeroed = np.roll(map_test_um_zeroed, shift=1, axis=1)

        df_map_test_um_zeroed = pd.DataFrame(map_test_um_zeroed, dtype=np.float64)

        print(type(df_map_test_um_zeroed))

    elif isinstance(df_map, pd.DataFrame):
        print("Using provided DataFrame for heatmap")
        x_indices = df_map['x_index'].values
        y_indices = df_map['y_index'].values
        map_x_pix = params[0]['map_x_pix'] if params and 'map_x_pix' in params else int(np.max(x_indices)) + 1
        map_y_pix = params[0]['map_y_pix'] if params and 'map_y_pix' in params else int(np.max(y_indices)) + 1

        print(f'Map dimensions: {map_x_pix} x {map_y_pix}')
        if correct_indices:
            bool_error, _ = check_map_indice_integrity(df_map, map_x_pix, map_y_pix)
            if bool_error:
                x_pos_1d, y_pos_1d, curve_index = generate_xy_map_positions(map_x_pix=map_x_pix, map_y_pix=map_y_pix)
                x_indices = x_pos_1d
                y_indices = y_pos_1d
                print('Map indices were regenerated due to integrity error')
                df_map['curve_index'] = curve_index
                df_map['x_index'] = x_indices
                df_map['y_index'] = y_indices

        if value_key in df_map.columns:
            z_values = df_map[value_key].values
        else:
            z_values = df_map['z_height_um'].values

        map_test_um_zeroed = np.zeros((map_y_pix, map_x_pix), dtype=np.float64)
        for i in range(len(z_values)):
            x_idx = int(x_indices[i])
            y_idx = int(y_indices[i])
            if 0 <= x_idx < map_x_pix and 0 <= y_idx < map_y_pix:
                if np.isnan(z_values[i]):
                    map_test_um_zeroed[y_idx, x_idx] = 0
                else:
                    map_test_um_zeroed[y_idx, x_idx] = z_values[i]

        if lastColFirst:
            map_test_um_zeroed = np.roll(map_test_um_zeroed, shift=-1, axis=1)

        df_map_test_um_zeroed = pd.DataFrame(map_test_um_zeroed, dtype=np.float64)

    else:
        map_path = df_map

    # get parameters from metadata, if not provided, use defaults
    defaults = {
        'z_sens_um': 6,
        'x_sens_um': 5.685,
        'y_sens_um': 3.960,
        'map_x_step': 0.14,
        'map_y_step': 0.14,
        'map_x_pix': df_map_test_um_zeroed.shape[0],
        'map_y_pix': df_map_test_um_zeroed.shape[1]
    }

    if params is not None:
        for k in defaults:
            if k in params:
                defaults[k] = params[k]

    x_sens_um = defaults['x_sens_um']
    y_sens_um = defaults['y_sens_um']
    dx_v = defaults['map_x_step']
    dy_v = defaults['map_y_step']
    map_x_pix = defaults['map_x_pix']
    map_y_pix = defaults['map_y_pix']

    # Axis scaling
    if scale_axis:
        # Use scaled axis values instead of grid indices
        x_axis = (np.arange(map_x_pix) * dx_v * x_sens_um).round(1)
        y_axis = (np.arange(map_y_pix) * dy_v * y_sens_um).round(1)
        x_labels = x_axis
        y_labels = y_axis
        x_ticklabels = x_axis
        y_ticklabels = y_axis
    else:
        # Use grid indices
        x_labels = np.arange(map_x_pix)
        y_labels = np.arange(map_y_pix)
        x_ticklabels = x_labels
        y_ticklabels = y_labels

    # Prepare log10 data, handle zeros, negatives, and filtering
    data = df_map_test_um_zeroed.values.copy()  # Make a copy to avoid modifying original
    
    # Step 2: Set non-positive values to NaN (can't take log of zero or negative)
    data[data <= 0] = np.nan

    # Step 1: Handle filtering based on zmin/zmax if nan=True
    if nan:
        if zmin is not None:
            data[data < zmin] = np.nan
        if zmax is not None:
            data[data > zmax] = np.nan

    # Step 3: Take log10 of the data
    log_data = np.log10(data)

    # Step 4: Define colormap range (in log10 space)
    # Use the log10 of zmin/zmax if provided, otherwise use data range
    if zmin is not None and zmin > 0:
        vmin = np.log10(zmin)
    else:
        vmin = np.nanmin(log_data)

    if zmax is not None and zmax > 0:
        vmax = np.log10(zmax)
    else:
        vmax = np.nanmax(log_data)

    # Step 5: Create a colormap that handles out-of-range values
    current_cmap = plt.cm.get_cmap(cmap).copy()
    current_cmap.set_bad(color='white')  # Keep NaN as white (for actual NaN values)

    # Set out-of-range colors to the colormap extremes
    current_cmap.set_under(current_cmap(0))  # Values below vmin → lowest color
    current_cmap.set_over(current_cmap(1.0))  # Values above vmax → highest color

    # Create normalization with clipping to ensure out-of-range values get colored
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax, clip=True)

    fig, ax = plt.subplots(figsize=(20, 10))
    if annot is False:
        a = sns.heatmap(
            log_data,
            xticklabels=x_ticklabels.round(2) if scale_axis else x_ticklabels,
            yticklabels=y_ticklabels.round(2) if scale_axis else y_ticklabels,
            ax=ax, cmap=current_cmap, vmin=vmin, vmax=vmax, annot=annot,
            norm=norm  # Add normalization here
        )
    else:
        # Annotate with original (not log) values for clarity
        a = sns.heatmap(
            log_data,
            annot=df_map_test_um_zeroed,
            fmt=".2f",
            xticklabels=x_ticklabels.round(2) if scale_axis else x_ticklabels,
            yticklabels=y_ticklabels.round(2) if scale_axis else y_ticklabels,
            ax=ax, cmap=current_cmap, vmin=vmin, vmax=vmax,
            norm=norm  # Add normalization here
        )
    
    a.invert_yaxis()
    xy_axis = -1 if flipAxis else 1
    a.set_aspect((x_sens_um / y_sens_um) ** xy_axis)
    print(f'y_sens_um: {y_sens_um}, x_sens_um: {x_sens_um}')
    a.set_xlabel('X axis (um)' if scale_axis else 'X index', fontsize=20)
    a.set_ylabel('Y axis (um)' if scale_axis else 'Y index', fontsize=20)
    colorbar = a.collections[0].colorbar
    colorbar.set_label(f'log10({value_key})', fontsize=18)
    colorbar.ax.yaxis.label.set_rotation(90)
    _ = plt.xticks(
        ticks=np.arange(0, len(x_labels), 5),
        labels=x_labels[::5].round(2) if scale_axis else x_labels[::5],
        rotation=45, fontsize=18
    )
    _ = plt.yticks(
        ticks=np.arange(0, len(y_labels), 5),
        labels=y_labels[::5].round(2) if scale_axis else y_labels[::5],
        rotation=0, fontsize=18
    )
    colorbar.ax.tick_params(labelsize=20)
    ax.minorticks_on()
    ax.tick_params(axis='both', which='minor', length=4, color='black')
    fig.patch.set_alpha(0.0)

    if save_svg and svg_path:
        try:
            output_path = svg_path
            if output_path is None:
                if isinstance(map_path, str):
                    base_name = os.path.splitext(os.path.basename(map_path))[0]
                else:
                    base_name = "heatmap"
                output_path = os.path.join(os.getcwd(), f"{base_name}.svg")
            fig.savefig(output_path, format='svg', bbox_inches='tight', transparent=True)
            print(f"Saved SVG to: {output_path}")
        except Exception as e:
            print(f"Error saving SVG: {e}")

    return df_map_test_um_zeroed, x_labels, y_labels


def process_map_and_create_heatmap(map_path, annot = False, **heatmap_kwargs):
    """
    Processes a map directory containing CSV and TDMS files, loads map data, and creates a heatmap.

    Steps performed:
        1. Searches for CSV files in the specified directory.
        2. Loads map parameters from the directory.
        3. Loads and zeroes a 2D map from the first CSV file found (if any).
        4. Loads map data from TDMS files in square format.
        5. Creates a heatmap using the loaded map data and parameters.

    Args:
        map_path (str): Path to the directory containing map files (CSV and TDMS).
        **heatmap_kwargs: Additional keyword arguments to pass to the `create_heatmap` function.

    Returns:
        tuple:
            - map_test_um_zeroed (np.ndarray): The zeroed 2D map from TDMS data.
            - map_test_um_zeroed_csv (np.ndarray or None): The zeroed 2D map loaded from CSV, or None if not found.
            - x_axis (np.ndarray): The x-axis values of the map.
            - y_axis (np.ndarray): The y-axis values of the map.
            - df_maps (dict): The map data loaded from the TDMS files.
            - params (dict): The parameters loaded from the map directory.

    Raises:
        FileNotFoundError: If no CSV files are found in the specified directory.
    """
    csvBool = True
    
    # Find CSV files in the specified directory
    csv_files = find_csv_files(map_path)
    params, tdms_files = get_map_parameters(map_path)

    data, map_x_pix, map_y_pix = extract_map_parameters(tdms_files=tdms_files, estimate_xy=True)

    if params['map_x_pix'] or params['map_y_pix'] == None:
        params['map_x_pix'] = map_x_pix
        params['map_y_pix'] = map_y_pix


    if csv_files is None or len(csv_files) == 0:    
        csvBool = False 
        print(f"Process_map_and_create_heatmap: No CSV files found in directory: {map_path}")
    

    # Get the first CSV file found (if any)
    if csvBool:
        map_path_csv = csv_files[0]
        print(map_path_csv)
        map_test_um_zeroed_csv, x_axis, y_axis = load_2d_map_file_csv(map_path_csv, params)
    else:
        map_test_um_zeroed_csv, x_axis, y_axis = None, None, None
    

    # map_test_um_zeroed, x_axis, y_axis = load_2d_map_file_csv(map_path_csv, params)
    try: 
        dic_maps, _, _, _ = load_map_file_square_tdms(map_path)

    except Exception as e:
        print(f"Process_map_and_create_heatmap: Error loading TDMS files: {e}")

        # dic_maps = None
        # params = None 
    
    try: 
        if dic_maps is None:
            print ("Process_map_and_create_heatmap: No valid map data loaded from TDMS files.")
        else: 
            # replace nan with 0 for all columns
            # dic_maps = dic_maps.fillna(0)
            map_test_um_zeroed, x_axis, y_axis = create_heatmap(dic_maps, params, annot=annot, **heatmap_kwargs)
    except Exception as e:
        print(f"Process_map_and_create_heatmap: Error creating heatmap from TDMS data: {e}")
        map_test_um_zeroed = None
        x_axis = None
        y_axis = None
    
    return map_test_um_zeroed, map_test_um_zeroed_csv, x_axis, y_axis, dic_maps, params

# Create a function to generate histograms with a consistent filter
def create_filtered_histogram(df, keys, filter_range=(0, 4000), bins=50, figsize=(14, 10)):
    """
    Create a grid of subplots of histograms for the given keys with a consistent filter
    
    Parameters:
    df (DataFrame): The dataframe to plot
    keys (list): List of column names to plot
    filter_range (tuple): Min and max values to filter (applied to all plots)
    bins (int): Number of bins for the histograms
    figsize (tuple): Figure size
    """
    # Calculate number of rows and columns for the subplot grid
    n_plots = len(keys)
    n_cols = min(3, n_plots)  # Maximum 3 columns
    n_rows = (n_plots + n_cols - 1) // n_cols  # Ceiling division
    
    # Create a figure with a dynamic grid of subplots
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    
    # Handle case of single subplot (axes is not an array)
    if n_plots == 1:
        axes = np.array([axes])
    
    # Convert to 1D array for easier indexing
    axes = np.array(axes).flatten()
    
    # Get min and max values for each key for display purposes
    stats = {}
    for key in keys:
        # Calculate statistics with the same filter range as the plots
        filtered_data = df[key][(df[key] > filter_range[0]) & (df[key] < filter_range[1])]
        stats[key] = {
            'min': filtered_data.min(),
            'max': filtered_data.max(),
            'median': filtered_data.median(),
            'mean': filtered_data.mean()
        }
    # Create filtered dataframe (same filter range for all plots)
    filtered_df = df.copy()
    
    # Loop through the keys and create histograms
    for i, key in enumerate(keys):
        # Further filter for each plot (but with same range)
        plot_df = filtered_df[(filtered_df[key] > filter_range[0]) & (filtered_df[key] < filter_range[1])]
        
        # Create histogram
        sns.histplot(plot_df[key], bins=bins, kde=True, ax=axes[i])
        
        # Set titles and labels
        axes[i].set_title(f"Histogram of {key}")
        axes[i].set_xlabel(f"{key} (Pa)")
        axes[i].set_ylabel("Frequency")
        axes[i].grid(True)
        
        # Add stats as text
        axes[i].text(0.05, 0.95, 
                   f"Min: {stats[key]['min']:.2f}\nMax: {stats[key]['max']:.2f}\n" +
                   f"Mean: {stats[key]['mean']:.2f}\nMedian: {stats[key]['median']:.2f}",
                   transform=axes[i].transAxes, 
                   fontsize=10,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    # Hide any unused subplots
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    
    plt.tight_layout()
    plt.show()

# # Example usage - select any 4 columns to display
# keys_to_plot = ['hertz_E', 'ting_E0', 'ting_betaE']
# create_filtered_histogram(df, keys_to_plot, filter_range=(0, 4000), bins=50)

# You can change the keys and filter range as needed:
# keys_to_plot = ['ting_E0', 'hertz_E', 'hertz_Rsquared', 'ting_Rsquared'] 
# create_filtered_histogram(df, keys_to_plot, filter_range=(0, 2000))

def create_scatter_comparison(dataframes, keys_to_plot, 
                              filter_range=(0, 4000), figsize=(15, 10), bins=50):
    """
    Create histogram plots to compare values across different dataframes with the same style as create_filtered_histogram.
    
    Parameters:
    dataframes (list): List of tuples containing (dataframe, label) for each dataframe to compare
    keys_to_plot (list): List of column names to plot
    filter_range (tuple): Min and max values to filter (applied to all plots)
    figsize (tuple): Figure size for the plot
    bins (int): Number of bins for the histograms
    """
    # Calculate number of rows and columns for the subplot grid
    n_plots = len(keys_to_plot)
    n_cols = min(3, n_plots)  # Maximum 3 columns
    n_rows = (n_plots + n_cols - 1) // n_cols  # Ceiling division
    
    # Create figure
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    
    # Convert to 1D array for easier indexing
    if n_plots == 1:
        axes = np.array([axes])
    axes = np.array(axes).flatten()
    
    # Generate colors for different datasets
    colors = plt.cm.tab10(np.linspace(0, 1, len(dataframes)))
    
    for i, key in enumerate(keys_to_plot):
        # Plot each dataset
        for j, (df, label) in enumerate(dataframes):
            # Check if the key exists in this dataframe
            if key in df.columns:
                # Filter the data
                filtered_data = df[key][(df[key] > filter_range[0]) & (df[key] < filter_range[1])]
                
                if not filtered_data.empty:
                    # Plot histogram for this dataset
                    sns.histplot(
                        filtered_data, 
                        ax=axes[i], 
                        kde=True, 
                        color=colors[j], 
                        bins=bins,
                        alpha=0.6, 
                        label=f"{label}"
                    )
                    
                    # Calculate statistics for the filtered data
                    stats = {
                        'min': filtered_data.min(),
                        'max': filtered_data.max(),
                        'mean': filtered_data.mean(),
                        'median': filtered_data.median()
                    }
                    
                    # Position the stats text based on dataset index
                    text_y = 0.95 - (j * 0.2)  # Adjust vertical position for each dataset
                    if text_y > 0.1:  # Ensure text stays in visible area
                        axes[i].text(
                            0.05, text_y, 
                            f"{label}:\nMin: {stats['min']:.2f}\nMax: {stats['max']:.2f}\n" +
                            f"Mean: {stats['mean']:.2f}\nMedian: {stats['median']:.2f}",
                            transform=axes[i].transAxes, 
                            fontsize=10,
                            verticalalignment='top',
                            bbox=dict(boxstyle='round', facecolor=colors[j], alpha=0.2)
                        )
        
        # Set titles and labels
        axes[i].set_title(f"Histogram of {key}")
        axes[i].set_xlabel(f"{key} (Pa)")
        axes[i].set_ylabel("Frequency")
        axes[i].grid(True)
        axes[i].legend(loc='upper right')
    
    # Hide any unused subplots
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    
    plt.tight_layout()
    plt.show()
    
    return fig, axes
