
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  7 18:07:01 2025
Edited on : Apr 7 2026

@author: Lorenzo Villanueva
"""
# File containing the loadPSNEXcurve function,

import numpy as np
from nptdms import TdmsFile

from ..utils.forcecurve import ForceCurve
from ..utils.segment import Segment
from scipy.stats import linregress
 

def calculate_velocity(displacement_um, rel_time):
    """
    Calculate the average velocity from displacement_um and time arrays using linear regression.

    Parameters:
        displacement_um (np.ndarray): Displacement values (in micrometers).
        rel_time (np.ndarray): Time values (in seconds).

    Returns:
        float: Average velocity (slope) in µm/s.
    """
    displacement_um = -displacement_um * 1e6  # Convert to micrometers (for compatibility with previous code)
    # deriv_displacement = np.gradient(displacement_um, rel_time)
    slope, intercept, _, _, _= linregress(rel_time, displacement_um)
    return slope


def loadHS3curve(file_metadata, curve_index=0, bool_correct_overshoot=False):
    """
    Function used to load the data of a single force curve from a HS3 file.

            Parameters:
                    file_metadata (dict): Dictionary containing the file metadata.
                    curve_index (int): Index of curve to load.
                    bool_correct_overshoot (bool): Flag indicating whether to correct overshoot.

            Returns:
                    force_curve (utils.forcecurve.ForceCurve): ForceCurve object containing the loaded data.
    """
    file_id = file_metadata['file_path']
    # curve_properties = file_metadata['curve_properties']
    # height_channel_key = file_metadata['height_channel_key']
    # deflection_chanel_key = file_metadata['deflection_chanel_key']
    tdms_file = TdmsFile.open(file_metadata['file_path'])  # alternative TdmsFile.read(path1+fname[ibead])
    main_group = tdms_file.groups()[0].name

    channels = tdms_file[main_group].channels()
    i = 0 
    channel_dict = {}
    channel_names_dict = {}
    for channel in channels:
        channel_dict[channel.name] = tdms_file[main_group][channel.name][:]  
        channel_names_dict[i] = tdms_file[main_group][channel.name].name
        i += 1

    # dt = tdms_file[main_group][channel_names_dict[0]].properties["wf_increment"]
    # time_s = tdms_file[main_group][channel_names_dict[0]].time_track()


    force_curve = ForceCurve(curve_index, file_id)

    # curve_indices = file_metadata["Entry_tot_nb_curve"] 
    # num_segment = file_metadata['num_segments']

    # Always load all segments initially
    num_segment_arr = [0, 1, 2]
    
    z_piezo_sens_m = file_metadata['invOLS_nm_per_V'] * 1e-9
    deflection = channel_dict['Deflection']
    height = channel_dict['Piezo'] * z_piezo_sens_m

    dec_app = file_metadata['dec_factor_approach']
    dec_con = file_metadata['dec_factor_contact']
    dec_ret = file_metadata['dec_factor_retract']

    app_ms = file_metadata['S1_ms'] + file_metadata['S2_ms']
    con_ms = file_metadata['S3_ms']
    ret_ms = file_metadata['S4_ms'] + file_metadata['S5_ms']

    dec_arr = np.array([dec_app, dec_con, dec_ret])
    seg_arr = np.array([app_ms, con_ms, ret_ms]) * 1e-3

    SR = file_metadata['reading_sample_rate_Hz']
    rel_SR = SR / dec_arr
    file_metadata['relative_sr'] = dec_arr / SR
    sizes_per_seg = (rel_SR * seg_arr).astype(int)
    start_indices = np.concatenate(([0], np.cumsum(sizes_per_seg[:-1])))
    end_indices = start_indices + sizes_per_seg
    rel_period = 1 / rel_SR

    length_deflection = len(deflection)
    if end_indices[-1] != length_deflection:
        end_indices[-1] = length_deflection
    file_metadata['final_nb_points'] = np.cumsum(sizes_per_seg[:-1])

    # Find maximum deflection for overshoot correction (like PSNEX)
    max_deflection_index = np.nanargmax(deflection)

    for idx in range(len(num_segment_arr)):
        segment_id = num_segment_arr[idx]
        start_pos, end_pos = start_indices[idx], end_indices[idx]

        segment_type = "App" if segment_id == 0 else "Ret" if segment_id == 2 else "Con" if segment_id == 1 else "Modulation"

        # Apply overshoot correction to approach segment (like PSNEX)
        if segment_type == "App" and bool_correct_overshoot:
            if max_deflection_index < end_pos and max_deflection_index >= start_pos:
                # Adjust approach segment to end at max deflection
                end_pos = max_deflection_index
                # Adjust subsequent indices if retract segment exists
                if idx + 1 < len(num_segment_arr):
                    start_indices[idx + 1] = max_deflection_index + 1

        # Skip contact segment if doing overshoot correction
        if segment_type == "Con" and bool_correct_overshoot:
            continue

        segment_formated_data = {}
        segment_formated_data['time'] = np.arange(end_pos - start_pos) * rel_period[idx]
        segment_formated_data['Piezo'] = -height[start_pos:end_pos]
        segment_formated_data['vDeflection'] = -deflection[start_pos:end_pos]

        segment = Segment(file_id, segment_id, segment_type)
        segment.segment_formated_data = segment_formated_data
        segment.nb_point = end_pos - start_pos
        segment.nb_col = len(segment_formated_data.keys())

        segment.velocity = -calculate_velocity(segment_formated_data['Piezo'], segment_formated_data["time"])
        segment.zheight = segment_formated_data['Piezo'][-1] if len(segment_formated_data['Piezo']) > 0 else 0
        segment.vdeflection = segment_formated_data['vDeflection'][-1] if len(segment_formated_data['vDeflection']) > 0 else 0
        segment.sampling_rate = rel_SR[idx]
        segment.z_displacement = height[-1]
        segment.force = deflection[start_pos:end_pos] * file_metadata['defl_sens_nmbyV'] * 1e-09 * file_metadata['spring_const_Nbym']

        if segment_type == "App":
            force_curve.extend_segments.append((int(segment.segment_id), segment))
        elif segment_type == "Ret":
            force_curve.retract_segments.append((int(segment.segment_id), segment))
        elif segment_type == "Con":
            force_curve.pause_segments.append((int(segment.segment_id), segment))
        elif segment_type == "Modulation":
            force_curve.modulation_segments.append((int(segment.segment_id), segment))

    return force_curve

