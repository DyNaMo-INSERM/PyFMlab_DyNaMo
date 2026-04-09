#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 18:14:44 2024

@author: yogehs
"""

import os
from scipy.signal import decimate

# from ..constants import *
from ..constants import *
import traceback
import numpy as np

 
#from .constants import *
from nptdms import TdmsFile #from nptdms import tdms  # pip install nptdms

def contains_word(sentence, word):
    """
    Returns True if 'word' is found in 'sentence', case-insensitive.
    """
    return word.lower() in sentence.lower()

def parsePSNEXsegmentheader(filepath,curve_properties,segment_id, UFF, curve_index=0):
    """
    Function used to load the metadata of each segment for each force curve of a JPK file.

            Parameters:
                    curve_properties (dict): Dictionary containing all the metadata for each force curve in the file.
                    curve_index (int): Dictionary containing metadata from header.properties
                    file_path (str): File extension of psnex file.
                    segment_id (str): Position of the segment in the force curve.
            
            Returns:
                    segment metadata (dict): Dictionary containing all the metadata for each force curve in the file.
    """
    tdms_file_ps_nex = TdmsFile.read_metadata(filepath)  
    
    ## UFF STUFF ONLY
    UFF.filemetadata['height_channel_key'] = tdms_file_ps_nex.groups()[0].channels()[1].name
    UFF.filemetadata['deflection_chanel_key'] = tdms_file_ps_nex.groups()[0].channels()[0].name
    # # Check if deflection is in the channel name
    UFF.filemetadata['found_vDeflection'] = contains_word(UFF.filemetadata['deflection_chanel_key'], 'deflection')
    # UFF.filemetadata['found_vDeflection'] = True
    # # check if zpiezo is in the channel name



    for group in tdms_file_ps_nex.groups():
        ps_nex_meta = (group.properties)

    # Get from Groups
    segment_metadata = {}
    tick_time_s = float(ps_nex_meta.get("instrument_tick_time_(us)"))* 10**-6
    z_stage_sensitivity = float(ps_nex_meta.get('system_Z_stage_piezo_sensitivity_(nm/V)'))
    
    segment_metadata["tick_time_s"] =tick_time_s
    segment_metadata["z_stage_sensitivity"] = z_stage_sensitivity #nm/V

    segment_metadata[f"segment_{segment_id}_type"] =ps_nex_meta.get(f"segment_{segment_id}_type")

    decimation_factor= int(ps_nex_meta.get(f"segment_{segment_id}_dec_factor"))
    segment_metadata[f"segment_{segment_id}_dec_factor"] = decimation_factor
    
    seg_dur_ticks= float(ps_nex_meta.get(f"segment_{segment_id}_duration_(ticks)"))
    segment_metadata[f"segment_{segment_id}_duration_(ticks)"]  = seg_dur_ticks

    segment_metadata[f"segment_{segment_id}_duration"] = seg_dur_ticks * tick_time_s

    segment_metadata[f"segment_{segment_id}_initial_deflection_(V)"] =float(ps_nex_meta.get(f"segment_{segment_id}_initial_deflection_(V)"))
    
    segment_metadata[f"segment_{segment_id}_nb"] = int(ps_nex_meta.get(f"segment_{segment_id}_nb"))

    seg_vel_v_tick = float(ps_nex_meta.get(f"segment_{segment_id}_velocity(V/tick)")) 
    # seg_sr = segment_metadata[f'segment_{segment_id}_sampling_rate_(S/s)']
    seg_dec_factor = segment_metadata[f'segment_{segment_id}_dec_factor']
    segment_metadata[f"segment_{segment_id}_velocity(V/tick)"] = seg_vel_v_tick
    segment_metadata[f"segment_{segment_id}_Z_position_setpoint_trigger_(V)"] = float(ps_nex_meta.get(f"segment_{segment_id}_Z_position_setpoint_trigger_(V)"))
    segment_metadata[f"segment_{segment_id}_zpiezo_control_out"] =ps_nex_meta.get(f"segment_{segment_id}_zpiezo_control_out")
    


    segment_metadata[f"segment_{segment_id}_relative_setpoint_(bool)"] =bool(ps_nex_meta.get(f"segment_{segment_id}_relative_setpoint_(bool)"))
    segment_metadata[f"segment_{segment_id}_sampling_rate_(S/s)"] =float(ps_nex_meta.get(f"segment_{segment_id}_sampling_rate_(S/s)"))
    segment_metadata[f"segment_{segment_id}_setpoint_(V)"] =float(ps_nex_meta.get(f"segment_{segment_id}_setpoint_(V)"))
    segment_metadata[f"segment_{segment_id}_setpoint_on_(bool)"] =bool(ps_nex_meta.get(f"segment_{segment_id}_setpoint_on_(bool)"))
    segment_metadata[f"segment_{segment_id}_setpoint_trigger_channel"] = ps_nex_meta.get(f"segment_{segment_id}_setpoint_trigger_channel")
    
    # seg_vel_v_tick = float(ps_nex_meta.get(f"segment_{segment_id}_velocity(V/tick)")) 
    seg_sr = segment_metadata[f'segment_{segment_id}_sampling_rate_(S/s)']
    # seg_dec_factor = segment_metadata[f'segment_{segment_id}_dec_factor']
    # segment_metadata[f"segment_{segment_id}_velocity(V/tick)"] = seg_vel_v_tick
    # segment_metadata[f"segment_{segment_id}_Z_position_setpoint_trigger_(V)"] = float(ps_nex_meta.get(f"segment_{segment_id}_Z_position_setpoint_trigger_(V)"))
    # segment_metadata[f"segment_{segment_id}_zpiezo_control_out"] =ps_nex_meta.get(f"segment_{segment_id}_zpiezo_control_out")
    
    seg_i_pt_cal = int((seg_dur_ticks * seg_sr * tick_time_s)/seg_dec_factor)

        # for mar's data
    try :
        segment_metadata[f"segment_{segment_id}_nb_points_(points)"] = int(ps_nex_meta.get(f"segment_{segment_id}_nb_points_(points)"))
    except:
        segment_metadata[f"segment_{segment_id}_nb_points_(points)"] = seg_i_pt_cal
 

    # relativ_sr = seg_sr / seg_dec_factor #Hz
    segment_metadata[f"segment_{segment_id}_nb_points_cal"] =seg_i_pt_cal

    # added by Lorenzo june 10 2025
    segment_metadata[f"segment_{segment_id}_initial_deflection_(V)"] = float(ps_nex_meta.get(f"segment_{segment_id}_initial_deflection_(V)"))

    #TODO what is segment baseline 
    segment_metadata["time"] = float(ps_nex_meta.get("time"))

    
    # Parameters always found in the segment header
    segment_metadata["baseline_measured"] = False
    
    # Compute ramp size
    segment_metadata[f"segment_{segment_id}_Z_retract_length_(V)"] =  float(ps_nex_meta.get(f"segment_{segment_id}_Z_retract_length_(V)"))

    # Compute ramp speed
    tick_time_z_loop = UFF.filemetadata["tick_time_z_loop"]
    z_loop_corrrection_factor = UFF.filemetadata.get("tick_time_z_loop_correction_factor", 10)

    tick_time_z_loop /= z_loop_corrrection_factor  # Apply correction factor if available
    z_sens_um_v = z_stage_sensitivity *1e-03 # convert nm/V to um/V
    # vel_sens = (z_sens_um_v / tick_time_z_loop / decimation_factor)
    ramp_speed_um_s = (seg_vel_v_tick / tick_time_z_loop) * z_sens_um_v # um/s
    # print (f'segment_{segment_id}_ramp_speed_um/s: {ramp_speed_um_s:.3g} um/s')
    segment_metadata[f"segment_{segment_id}_ramp_speed_um/s"] = ramp_speed_um_s
    segment_metadata[f"segment_{segment_id}_ramp_speed_nm/s"] = ramp_speed_um_s * 1e3
    segment_metadata[f"segment_{segment_id}_ramp_speed_m/s"] = ramp_speed_um_s * 1e-06
    # print (f'segment_{segment_id}_ramp_speed_nm/s: {segment_metadata[f"segment_{segment_id}_ramp_speed_nm/s"]:.3g} nm/s')

    # segment_metadata[f"segment_{segment_id}_ramp_speed_nm/s"] = float(ps_nex_meta.get(f'segment_{segment_id}_velocity(V/tick)'))*tick_time_s *z_stage_sensitivity
    
    curve_properties[curve_index].update({segment_id: segment_metadata})
    
    return curve_properties




def get_metadata_safe(ps_nex_meta, key, default_value=None, value_type=None, debug=True):
    """
    Safely get metadata value with error handling and type conversion.
    
    Parameters:
        ps_nex_meta: Metadata dictionary
        key: Key to retrieve
        default_value: Value to return if key is missing or conversion fails
        value_type: Type to convert to (float, int, bool, str)
        debug: Whether to print debug messages for missing keys
    
    Returns:
        Retrieved and converted value, or default_value if failed
    """
    try:
        value = ps_nex_meta.get(key)
        if value is None:
            if debug:
                print(f"⚠️  Missing metadata key: '{key}' - using default: {default_value}")
            return default_value
        
        if value_type is not None:
            return value_type(value)
        return value
    except (ValueError, TypeError) as e:
        if debug:
            print(f"⚠️  Error converting '{key}': {e} - using default: {default_value}")
        return default_value

def parsePSNEXheader(filepath, debug=True):
    """
    Function used to load the metadata of a PSNEX file.

            Parameters:
                    filepath (str): UFF object containing the PSNEX file metadata.
                    debug (bool): Enable debug messages for missing metadata
            Returns:
                    file_metadata (dict): Dictionary containing all the file metadata
    """

    tdms_file_ps_nex = TdmsFile.read_metadata(filepath)  

    for group in tdms_file_ps_nex.groups():
        ps_nex_meta = (group.properties)

    file_metadata = {}

    # File stuff 
    file_metadata["file_path"] = filepath
    file_metadata["Entry_filename"] = os.path.basename(filepath)
    file_metadata["file_size_bytes"] = os.path.getsize(filepath)
    
    file_metadata["Entry_date"] = get_metadata_safe(ps_nex_meta, "date", "Unknown", str, debug)
    file_metadata["Entry_tot_nb_curve"] = get_metadata_safe(ps_nex_meta, "number_consecutive_scans", 1, int, debug)

    # Experiment stuff
    file_metadata["Entry_experiment_name"] = get_metadata_safe(ps_nex_meta, "experiment_name", "Unknown", str, debug)
    file_metadata["User"] = get_metadata_safe(ps_nex_meta, "user", "Unknown", str, debug)
    
    # Software version control
    file_metadata["psnex_file_format_version"] = get_metadata_safe(ps_nex_meta, "TDMS_HSFS_file_version", "Unknown", str, debug)
    file_metadata["psnex_software_version"] = get_metadata_safe(ps_nex_meta, "FPGA_SW_version", "Unknown", str, debug)
    
    # Instrument stuff
    file_metadata["Experimental_instrument"] = get_metadata_safe(ps_nex_meta, "instrument", "Unknown", str, debug)
    file_metadata["instrument_clorckrate_(Mhz)"] = get_metadata_safe(ps_nex_meta, "instrument_clorckrate_(Mhz)", 0.0, float, debug)
    file_metadata["instrument_tick_time_(us)"] = get_metadata_safe(ps_nex_meta, "instrument_tick_time_(us)", 0.025, float, debug)
    file_metadata["instrument_tick_time_(s)"] = file_metadata["instrument_tick_time_(us)"] * 10**-6

    file_metadata["instrument_model"] = get_metadata_safe(ps_nex_meta, "instrument_model", "Unknown", str, debug)
    file_metadata["instrument_scanner"] = get_metadata_safe(ps_nex_meta, "instrument_scanner", "Unknown", str, debug)

    # Sample info and user 
    file_metadata['sample_name'] = get_metadata_safe(ps_nex_meta, "sample_name", "Unknown", str, debug)
    file_metadata['sample_species'] = get_metadata_safe(ps_nex_meta, "sample_species", "Unknown", str, debug)
    file_metadata['user'] = get_metadata_safe(ps_nex_meta, "user", "Unknown", str, debug)

    # UFF stuff 
    file_metadata['UFF_code'] = UFF_code
    file_metadata['Entry_UFF_version'] = UFF_version
    file_metadata['num_segments'] = get_metadata_safe(ps_nex_meta, "number_segments", 0, int, debug)

    # Tip stuff 
    file_metadata["tip_half_angle"] = get_metadata_safe(ps_nex_meta, "tip_half_angle_(deg)", 0.0, float, debug)
    file_metadata["tip_geometry"] = get_metadata_safe(ps_nex_meta, "tip_geometry", "Unknown", str, debug)
    file_metadata["tip_height_m"] = get_metadata_safe(ps_nex_meta, "tip_height_(m)", 0.0, float, debug)
    file_metadata["tip_radius_m"] = get_metadata_safe(ps_nex_meta, "tip_radius_(m)", 0.0, float, debug)
    
    # InvOLS 
    file_metadata["invOLS_(nm/V)"] = get_metadata_safe(ps_nex_meta, "invOLS_(nm/V)", 50.0, float, debug)
    file_metadata["defl_sens_nmbyV"] = file_metadata["invOLS_(nm/V)"]

    # Stage sensitivities and gains and angle 
    file_metadata["system_mount_angle_(deg)"] = get_metadata_safe(ps_nex_meta, "system_mount_angle_(deg)", 0.0, float, debug)
    
    axis_arr = ['X', 'Y', 'Z']
    for ax in axis_arr[:2]:
        file_metadata[f"system_{ax}_piezo_gain"] = get_metadata_safe(ps_nex_meta, f"system_{ax}_piezo_gain", 1.0, float, debug)
        file_metadata[f"system_{ax}_piezo_sensitivity_(nm/V)"] = get_metadata_safe(ps_nex_meta, f"system_{ax}_piezo_sensitivity_(nm/V)", 0.0, float, debug)

    # Mapping stuff 
    file_metadata["mapping_bool"] = get_metadata_safe(ps_nex_meta, "mapping_(bool)", False, bool, debug)
    
    if file_metadata["mapping_bool"]:
        file_metadata["mapping_index"] = get_metadata_safe(ps_nex_meta, "mapping_index", 0, int, debug)
        file_metadata["mapping_position_X"] = get_metadata_safe(ps_nex_meta, "mapping_position_row", 0, int, debug)
        file_metadata["mapping_position_Y"] = get_metadata_safe(ps_nex_meta, "mapping_position_column", 0, int, debug)
 
        file_metadata["X_cur_position_V"] = get_metadata_safe(ps_nex_meta, "mapping_next_position_row", 0.0, float, debug)
        file_metadata["Y_cur_position_V"] = get_metadata_safe(ps_nex_meta, "mapping_next_position_column", 0.0, float, debug)
        file_metadata["mapping_X_initial_pos_V"] = get_metadata_safe(ps_nex_meta, "mapping_X_initial_position_(V)", 0.0, float, debug)
        file_metadata["mapping_Y_initial_pos_V"] = get_metadata_safe(ps_nex_meta, "mapping_Y_initial_position_(V)", 0.0, float, debug)
        file_metadata["mapping_X_step_size_V"] = get_metadata_safe(ps_nex_meta, "mapping_X_step_size_(V)", 0.0, float, debug)
        file_metadata["mapping_Y_step_size_V"] = get_metadata_safe(ps_nex_meta, "mapping_Y_step_size_(V)", 0.0, float, debug)
    
        file_metadata["X_closed_loop_bool"] = get_metadata_safe(ps_nex_meta, "X_closed_loop_(bool)", False, bool, debug)
        file_metadata["Y_closed_loop_bool"] = get_metadata_safe(ps_nex_meta, "Y_closed_loop_(bool)", False, bool, debug)
        file_metadata["Z_closed_loop_bool"] = get_metadata_safe(ps_nex_meta, "Z_closed_loop_(bool)", False, bool, debug)

        for ax in axis_arr[:2]:
            if file_metadata[f"{ax}_closed_loop_bool"]:
                file_metadata[f"{ax}_position_(V)"] = get_metadata_safe(ps_nex_meta, f"{ax}_position_(V)", 0.0, float, debug)
                file_metadata[f"{ax}_vel_(V/tick)"] = get_metadata_safe(ps_nex_meta, f"{ax}_vel_(V/tick)", 0.0, float, debug)
        
    # Cantilever calibration stuff
    file_metadata["cantilever_Acoefficient_GCI_(nN.s^1.3/m)"] = get_metadata_safe(ps_nex_meta, "cantilever_Acoefficient_GCI_(nN.s^1.3/m)", 0.0, float, debug)
    file_metadata["cantilever_model"] = get_metadata_safe(ps_nex_meta, "cantilever_model", "Unknown", str, debug)
    file_metadata["cantilever_shape"] = get_metadata_safe(ps_nex_meta, "cantilever_shape", "Unknown", str, debug)
    
    file_metadata["cantilever_resonance_frequency_air_calib_(Hz)"] = get_metadata_safe(ps_nex_meta, "cantilever_resonance_frequency_air_calib_(Hz)", 0.0, float, debug)
    file_metadata["cantilever_resonance_frequency_calib_(Hz)"] = get_metadata_safe(ps_nex_meta, "cantilever_resonance_frequency_calib_(Hz)", 0.0, float, debug)
    file_metadata["cantilever_spring_constant_calib_N/m"] = get_metadata_safe(ps_nex_meta, "cantilever_spring_constant_calib_(N/m)", 0.0, float, debug)
    file_metadata["cantilever_spring_constant_calib_pN/nm"] = 10**3 * file_metadata["cantilever_spring_constant_calib_N/m"]
    
    file_metadata["spring_const_Nbym"] = file_metadata["cantilever_spring_constant_calib_N/m"]
    file_metadata["cantilever_spring_constant_nominal_(N/m)"] = get_metadata_safe(ps_nex_meta, "cantilever_spring_constant_nominal_(N/m)", 0.0, float, debug)
    file_metadata["cantilever_quality_factor"] = get_metadata_safe(ps_nex_meta, "cantilever_quality_factor", 0.0, float, debug)
    
    return file_metadata