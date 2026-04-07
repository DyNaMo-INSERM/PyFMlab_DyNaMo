#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 18:14:44 2024

@author: yogehs
"""

import os
from scipy.signal import decimate

from ..constants import *

 
#from .constants import *
from nptdms import TdmsFile #from nptdms import tdms  # pip install nptdms

def parsePSNEXheader(filepath):
    """
    Function used to load the metadata of a PSNEX file.

            Parameters:
                    filepath (str): UFF object containing the PSNEX file metadata.
            Returns:
                    file_metadata (dict): Dictionary containing all the file metadata
    """

    tdms_file_ps_nex = TdmsFile.read_metadata(filepath)  

    for group in tdms_file_ps_nex.groups():
        ps_nex_meta = (group.properties)

    file_metadata = {}

    #file stuff 
    file_metadata["file_path"] = filepath
    file_metadata["Entry_filename"] = os.path.basename(filepath)
    file_metadata["file_size_bytes"] = os.path.getsize(filepath)
    file_metadata["file_id"] = ps_nex_meta["filename"]
    file_metadata["Entry_date"] = ps_nex_meta.get("date")
    file_metadata["Entry_tot_nb_curve"] = int(ps_nex_meta.get("number_consecutive_scans"))
    #Software version control
    file_metadata["psnex_file_format_version"] = ps_nex_meta.get("TDMS_HSFS_file_version")
    file_metadata["psnex_software_version"] = ps_nex_meta.get("FPGA_SW_version")
    
    #instrument stuff
    file_metadata["Experimental_instrument"] = ps_nex_meta.get("instrument")
    file_metadata["instrument_clorckrate_(Mhz)"] = float(ps_nex_meta.get("instrument_clorckrate_(Mhz)"))
    file_metadata["instrument_tick_time_(us)"] = float(ps_nex_meta.get("instrument_tick_time_(us)"))
    file_metadata["instrument_tick_time_(s)"] = file_metadata["instrument_tick_time_(us)"]* 10**-6

    file_metadata["instrument_model"] = ps_nex_meta.get("instrument_model")
    file_metadata["instrument_scanner"] = ps_nex_meta.get("instrument_scanner")
    file_metadata["instrument_model"] = ps_nex_meta.get("instrument_model")

    #sample info and user 
    file_metadata['sample_name'] = ps_nex_meta.get("sample_name")
    file_metadata['sample_species'] = ps_nex_meta.get("sample_species")
    file_metadata['user'] = ps_nex_meta.get("user")

    #UFF stuff 
    file_metadata['UFF_code'] = UFF_code
    file_metadata['Entry_UFF_version'] = UFF_version
    file_metadata['num_segments'] = int(ps_nex_meta.get("number_segments"))

    #tip stuff 
    file_metadata["tip_half_angle"] = float(ps_nex_meta.get("tip_half_angle_(deg)"))
    file_metadata["tip_geometry"] = ps_nex_meta.get("tip_geometry")
    file_metadata["tip_height_m"] = float(ps_nex_meta.get("tip_height_(m)"))
    file_metadata["tip_radius_m"] = float(ps_nex_meta.get("tip_radius_(m)"))
    #invols 
    
    file_metadata["invOLS_(nm/V)"] = float(ps_nex_meta.get("invOLS_(nm/V)"))
    file_metadata["defl_sens_nmbyV"] = float(ps_nex_meta.get("invOLS_(nm/V)"))


    #stage sentivities and gains and angle 
    file_metadata["system_mount_angle_(deg)"] = float(ps_nex_meta.get("system_mount_angle_(deg)"))
    axis_arr = ['X','Y','Z']
    for ax in axis_arr[:2]:
        print(ps_nex_meta.get(f"system_{ax}_piezo_gain"))
        file_metadata[f"system_{ax}_piezo_gain"] = float(ps_nex_meta.get(f"system_{ax}_piezo_gain"))
        file_metadata[f"system_{ax}_piezo_sensitivity_(nm/V)"] = float(ps_nex_meta.get(f"system_{ax}_piezo_sensitivity_(nm/V)"))

    #mapping stuff 
    file_metadata["force_volume"] = bool(ps_nex_meta.get("mapping_(bool)"))

    if file_metadata["force_volume"]:
        #TODO: add map size and num of pixels 
        file_metadata['num_x_pixels'] = 0
        file_metadata['num_y_pixels'] = 0
        #in the scan size needs to be in m
        file_metadata['scan_size_x'] = 0
        file_metadata['scan_size_y'] = 0


        file_metadata["X_closed_loop_bool"] = bool(ps_nex_meta.get("X_closed_loop_(bool)"))
        
        file_metadata["Y_closed_loop_bool"] = bool(ps_nex_meta.get("Y_closed_loop_(bool)"))
        file_metadata["Z_closed_loop_bool"] = bool(ps_nex_meta.get("Z_closed_loop_(bool)"))
        for ax in axis_arr[:2]:
            if file_metadata[f"{ax}_closed_loop_bool"]:
                file_metadata[f"{ax}_position_(V)"] = float(ps_nex_meta.get(f"{ax}_position_(V)"))
                file_metadata[f"{ax}_vel_(V/tick)"] =float(ps_nex_meta.get(f"{ax}_vel_(V/tick)"))
        
        
    #cant calib stuff
    file_metadata["cantilever_Acoefficient_GCI_(nN.s^1.3/m)"] = float(ps_nex_meta.get("cantilever_Acoefficient_GCI_(nN.s^1.3/m)"))
    file_metadata["cantilever_model"] = ps_nex_meta.get("cantilever_model")
    file_metadata["cantilever_shape"] = ps_nex_meta.get("cantilever_shape")
    
    
    file_metadata["cantilever_resonance_frequency_air_calib_(Hz)"] = float(ps_nex_meta.get("cantilever_resonance_frequency_air_calib_(Hz)"))
    file_metadata["cantilever_resonance_frequency_calib_(Hz)"] = float(ps_nex_meta.get("cantilever_resonance_frequency_calib_(Hz)"))
    file_metadata["cantilever_spring_constant_calib_N/m"] = float(ps_nex_meta.get("cantilever_spring_constant_calib_(N/m)"))
    file_metadata["cantilever_spring_constant_calib_pN/nm"] = 10**3*float(ps_nex_meta.get("cantilever_spring_constant_calib_(N/m)"))
    
    file_metadata["spring_const_Nbym"] = float(ps_nex_meta.get("cantilever_spring_constant_calib_(N/m)"))

    file_metadata["cantilever_spring_constant_nominal_(N/m)"] = float(ps_nex_meta.get("cantilever_spring_constant_nominal_(N/m)"))
    file_metadata["cantilever_quality_factor"] = float(ps_nex_meta.get("cantilever_quality_factor"))
    return file_metadata

def parsePSNEXsegmentheader(filepath,curve_properties,segment_id,curve_index=0):
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

    for group in tdms_file_ps_nex.groups():
        ps_nex_meta = (group.properties)

    segment_metadata = {}
    tick_time_s = float(ps_nex_meta.get("instrument_tick_time_(us)"))* 10**-6
    z_stage_sensitivity = float(ps_nex_meta.get('system_Z_stage_piezo_sensitivity_(nm/V)'))
    segment_metadata["tick_time_s"] =float(ps_nex_meta.get("instrument_tick_time_(us)"))* 10**-6
    segment_metadata["z_stage_sensitivity"] =float(ps_nex_meta.get('system_Z_stage_piezo_sensitivity_(nm/V)'))

    segment_metadata[f"segment_{segment_id}_type"] =ps_nex_meta.get(f"segment_{segment_id}_type")

    segment_metadata[f"segment_{segment_id}_dec_factor"] = int(ps_nex_meta.get(f"segment_{segment_id}_dec_factor"))
    
    segment_metadata[f"segment_{segment_id}_duration_(ticks)"] = float(ps_nex_meta.get(f"segment_{segment_id}_duration_(ticks)"))
    segment_metadata[f"segment_{segment_id}_initial_deflection_(V)"] =float(ps_nex_meta.get(f"segment_{segment_id}_initial_deflection_(V)"))
    
    segment_metadata[f"segment_{segment_id}_nb"] = int(ps_nex_meta.get(f"segment_{segment_id}_nb"))
    segment_metadata[f"segment_{segment_id}_nb_points_(points)"] =float(ps_nex_meta.get(f"segment_{segment_id}_nb_points_(points)"))
 
    segment_metadata[f"segment_{segment_id}_relative_setpoint_(bool)"] =bool(ps_nex_meta.get(f"segment_{segment_id}_relative_setpoint_(bool)"))
    segment_metadata[f"segment_{segment_id}_sampling_rate_(S/s)"] =float(ps_nex_meta.get(f"segment_{segment_id}_sampling_rate_(S/s)"))
    segment_metadata[f"segment_{segment_id}_setpoint_(V)"] =float(ps_nex_meta.get(f"segment_{segment_id}_setpoint_(V)"))
    segment_metadata[f"segment_{segment_id}_setpoint_on_(bool)"] =bool(ps_nex_meta.get(f"segment_{segment_id}_setpoint_on_(bool)"))
    segment_metadata[f"segment_{segment_id}_setpoint_trigger_channel"] = ps_nex_meta.get(f"segment_{segment_id}_setpoint_trigger_channel")
    segment_metadata[f"segment_{segment_id}_velocity(V/tick)"] = float(ps_nex_meta.get(f"segment_{segment_id}_velocity(V/tick)"))
    segment_metadata[f"segment_{segment_id}_Z_position_setpoint_trigger_(V)"] = float(ps_nex_meta.get(f"segment_{segment_id}_Z_position_setpoint_trigger_(V)"))
    segment_metadata[f"segment_{segment_id}_zpiezo_control_out"] =ps_nex_meta.get(f"segment_{segment_id}_zpiezo_control_out")
    seg_i_pt_cal = int((segment_metadata[f"segment_{segment_id}_duration_(ticks)"]*segment_metadata[f'segment_{segment_id}_sampling_rate_(S/s)']*tick_time_s)/segment_metadata[f'segment_{segment_id}_dec_factor'])
    segment_metadata[f"segment_{segment_id}_nb_points_cal"] =seg_i_pt_cal


    #TODO what is segment baseline 
    
    segment_metadata["time"] = float(ps_nex_meta.get("time"))

    
    # Parameters always found in the segment header
    segment_metadata["baseline_measured"] = False
    
    # Compute ramp size
    segment_metadata[f"segment_{segment_id}_Z_retract_length_(V)"] =  float(ps_nex_meta.get(f"segment_{segment_id}_Z_retract_length_(V)"))

    # Compute ramp speed
    segment_metadata[f"segment_{segment_id}_ramp_speed_nm/s"] = float(ps_nex_meta.get(f'segment_{segment_id}_velocity(V/tick)'))*tick_time_s *z_stage_sensitivity

    curve_properties[curve_index].update({segment_id: segment_metadata})
    
    return curve_properties
