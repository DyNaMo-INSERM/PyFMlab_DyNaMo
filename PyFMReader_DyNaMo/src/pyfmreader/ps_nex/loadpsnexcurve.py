#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  7 10:55:32 2026

@author: Lorenzo
"""
# File containing the loadPSNEXcurve function,
# used to load single force curves from JPK files.

# from struct import unpack
# from itertools import groupby
import numpy as np
from nptdms import TdmsFile

from ..utils.forcecurve import ForceCurve
from ..utils.segment import Segment

 
#from pyfmreader.utils.forcecurve import ForceCurve
#from pyfmreader.utils.segment import Segment

def loadPSNEXcurve(file_metadata,curve_index = 0, 
                   z_sensor_delay = 0, bool_correct_overshoot = False):
    """
    Function used to load the data of a single force curve from a PSNEX file.

            Parameters:
                    file_metadata (dict): Dictionary containing the file metadata.

                    curve_index (int): Index of curve to load.
                    z_sensor_delay (float): Z sensor delay value.
                    bool_correct_overshoot (bool): Flag indicating whether to correct overshoot.

            Returns:
                    force_curve (utils.forcecurve.ForceCurve): ForceCurve object containing the loaded data.
    """
    file_id = file_metadata['Entry_filename']
    curve_properties = file_metadata['curve_properties']
    height_channel_key = file_metadata['height_channel_key']
    deflection_chanel_key = file_metadata['deflection_chanel_key']
    tdms_file_ps_nex_file = TdmsFile.open(file_metadata['file_path'])  # alternative TdmsFile.read(path1+fname[ibead])
    tick_time_s = file_metadata['instrument_tick_time_(s)']
    #please add it inthe file metadata
    z_stage_sens_m = file_metadata['curve_properties']['0'][0]['z_stage_sensitivity'] *10**-9

    force_curve = ForceCurve(curve_index, file_id)

    # curve_indices = file_metadata["Entry_tot_nb_curve"] 
    # num_segment = file_metadata['num_segments']
    num_segments = file_metadata['num_segments']
    num_segment_arr = np.arange(0,num_segments,1)

    if bool_correct_overshoot:
        # print("Correcting overshoot in the approach segment")
        if len(num_segment_arr) > 2:
            first = num_segment_arr[0]
            last = num_segment_arr[-1]
            num_segment_arr = [first, last]
    #     num_segment_arr = [0,1]
    # else:
    #     print("No overshoot correction in the approach segment")
    #     num_segment_arr = [0,1,2]
    # index = 1 if curve_indices == 0 else 3
    
    tdms_groups = tdms_file_ps_nex_file.groups()  ;    tdms_psnex_fc = tdms_groups[0]
 
    deflection = tdms_psnex_fc[deflection_chanel_key][:]
    height = tdms_psnex_fc[height_channel_key][:]*z_stage_sens_m
    # seg_pos_array =[[0,0]] * len(num_segment_arr)
    #for the offset, and the final time array  
    # t0 = 0;time_fc =  np.array([])

    dec_seg = np.array([
    curve_properties[str(curve_index)][i][f"segment_{i}_dec_factor"]
    for i in num_segment_arr])

    # print (f'decimation: {dec_seg}')

    # dec_factor = 1
    # if dec_seg[0] != 1:
    #     dec_factor = dec_seg[0]
    # print(f"dec_factor: {dec_factor}")
    #TALK TO ENZO, remind him 
    #TODO delays in the system , a bool maybe to trigger this 


    # For calculating per segment
    sizes_seg = np.array([
    curve_properties[str(curve_index)][i][f"segment_{i}_nb_points_cal"]
    for i in num_segment_arr])

    sizes_seg_tick = np.array([
    curve_properties[str(curve_index)][i][f"segment_{i}_duration_(ticks)"]
    for i in num_segment_arr])

    seg_sampling_rate =  np.array([
    curve_properties[str(curve_index)][i][f"segment_{i}_sampling_rate_(S/s)"]
    for i in num_segment_arr])


    tick_sampling_rate_time_s = dec_seg / seg_sampling_rate
    # z_sensor_delay = 1e-3;bool_correct_overshoot = True
    # print (f"z_sensor_delay: {z_sensor_delay}, bool_correct_overshoot: {bool_correct_overshoot} ")

    num_pts_rm = int(z_sensor_delay/tick_sampling_rate_time_s[0])
    # num_pts_rm = 1
    # print(f"points removed : {num_pts_rm}")

    # sr_ticks = (1/seg_sampling_rate)/file_metadata['instrument_tick_time_(s)']
    relative_segment_sampling_rate = ((1 / seg_sampling_rate) * dec_seg)
    relative_SR_ticks = relative_segment_sampling_rate / tick_time_s
    
    file_metadata['relative_sr'] = relative_segment_sampling_rate
    file_metadata['relative_SR_ticks'] = relative_SR_ticks
    final_nb_points = (sizes_seg_tick/relative_SR_ticks).astype(int)
    file_metadata['final_nb_points'] = final_nb_points  

    # print (f'tick_sampling_rate_time_s: {tick_sampling_rate_time_s}, relative_SR: {relative_SR}')
    #replace all zeros in final_nb_points with 1
    final_nb_points[final_nb_points == 0] = 1


    #if segment has zero, fill with 1 and add
    #TODO what the helllis this 
    if z_sensor_delay>0:
        
        num_pts_rm = int(z_sensor_delay/tick_sampling_rate_time_s[0])
        
        #TODO what the helllis this 
        num_pts_rm_time = num_pts_rm- (len(height) - np.sum(sizes_seg))

     
        deflection = deflection[:-num_pts_rm]
        height = height[num_pts_rm:]
    else :
        deflection = deflection[:]
        height = height[:]


    start_indices = np.concatenate(([0], np.cumsum(sizes_seg[:-1])))
    end_indices = start_indices + sizes_seg



    file_metadata['start_indices'] = start_indices
    file_metadata['end_indices'] = end_indices
    file_metadata['numPnts'] = final_nb_points
    #Lorenzo implementation:
    # get segment type contact for final nb points
    if len(num_segment_arr) >= 1:
        num_pts_con = sizes_seg[1]
        # if bool_correct_overshoot:
        #     num_pts_con = sizes_seg[1] - 1
    # deflection = deflection[:-num_pts_rm]
    # height = height[num_pts_rm:]
    # print(f'Deflection Length: {len(deflection)}, Height: {len(height)}')
    #finding the seg_pos_array from max z height 

    # correct start and end indices to match the length of the array of
    # deflection and height array
    length_deflection = len(deflection)
    if end_indices[-1] != length_deflection:
        end_indices[-1] = length_deflection

    


    for idx in range(len(num_segment_arr)):

        start_pos,end_pos = start_indices[idx],end_indices[idx]

        # print(start_pos,end_pos)

        segment_id = num_segment_arr[idx]
        # segment_raw_data = {}
        segment_formated_data = {}
        
        segment_type = curve_properties[str(curve_index)][segment_id][f"segment_{segment_id}_type"]

        # Lorenzo updated
        segment_duration_ticks = curve_properties[str(curve_index)][segment_id][f"segment_{segment_id}_duration_(ticks)"]*tick_time_s

        if segment_duration_ticks < 1:
            segment_duration_ticks = 1
        # else:
        
        segment_duration = curve_properties[str(curve_index)][segment_id][f"segment_{segment_id}_duration_(ticks)"]*tick_time_s
        
        
        
        segment_num_points = curve_properties[str(curve_index)][segment_id][f"segment_{segment_id}_nb_points_cal"]

        # TO DO: Time can be exported, handle this situation.
        #segment_formated_data["time"] = np.linspace(0, segment_duration, segment_num_points, endpoint=False)
        
        # print (f"segment: {segment_type}, segment relative position: {end_pos-start_pos}, segment duration: {segment_duration}")
        segment_formated_data["time"] = np.linspace(0, segment_duration, end_pos-start_pos, endpoint=False)
        #segment_formated_data["time"] = np.linspace(0, segment_duration, segment_num_points, endpoint=False)

        segment_formated_data[height_channel_key] = height[start_pos:end_pos]
        segment_formated_data['vDeflection'] = deflection[start_pos:end_pos]
        segment_formated_data['duration'] = segment_duration

        segment = Segment(file_id, segment_id, segment_type)
        segment.segment_formated_data = segment_formated_data
        
        segment.segment_metadata = curve_properties[str(curve_index)][segment_id]
        #TODO what is the set point mode 
        #segment.force_setpoint_mode = JPK_SETPOINT_MODE
        
        segment.nb_point = segment_num_points
        segment.nb_col = len(segment_formated_data.keys())
    
        segment.force_setpoint = segment.segment_metadata[f"segment_{segment_id}_setpoint_(V)"]
        segment.velocity = segment.segment_metadata[f"segment_{segment_id}_ramp_speed_m/s"]
        
        segment.sampling_rate = segment.segment_metadata[f"segment_{segment_id}_sampling_rate_(S/s)"]
        segment.z_displacement = segment.segment_metadata[f"segment_{segment_id}_Z_retract_length_(V)"]
        
        
        # print(segment.segment_type)
        if segment.segment_type in ["App", "Approach"]:
            #if we overshoot in the approach
            max_height_index = np.nanargmax(deflection)
            if bool_correct_overshoot:
                if max_height_index != end_pos:
                    # Assign max height index to end_indeces
                    end_indices[idx] = max_height_index
                    # Assign max height index to the next element of start index,
                    start_indices[idx+1] = max_height_index + 1
                    # End index of approach would include 
                    end_indices_last_idx = max_height_index 

                    if end_indices_last_idx > length_deflection:
                        end_indices[idx+1] = end_indices_last_idx
                    end_pos = end_indices[idx]
                    
                    segment_formated_data["time"] = np.linspace(0, segment_duration, end_pos-start_pos, endpoint=False)
                    # segment_formated_data["time"] = time_tdms[start_pos:end_pos]-time_tdms[start_pos]
                    segment_formated_data[height_channel_key] = height[start_pos:end_pos]
                    segment_formated_data['vDeflection'] = deflection[start_pos:end_pos]

            force_curve.extend_segments.append((int(segment.segment_id), segment))
                    
            # print("removed overshoot")
        elif segment.segment_type in ["Ret", "Retract"]:
            #TODO rem half points from each time segment for aligning  


            if z_sensor_delay>0 :
                segment_formated_data["time"] = segment_formated_data["time"][:-(num_pts_rm_time)]
            else:
                if bool_correct_overshoot:
                    # print (f'Ret final nb points: {final_nb_points[idx]}, sizes_seg: {sizes_seg}, deflection size: {len(deflection)}')
                    segment_formated_data["time"] = segment_formated_data["time"][:]
                else:

                    segment_formated_data["time"] = segment_formated_data["time"][:]

            force_curve.retract_segments.append((int(segment.segment_id), segment))
        elif segment.segment_type in ["Con", "Contact"]:
            force_curve.pause_segments.append((int(segment.segment_id), segment))
            # print ("Contact entered")
        elif segment.segment_type == "Modulation":
            force_curve.modulation_segments.append((int(segment.segment_id), segment))

        # print(f'start_indices: {start_indices}')
        # print(f'end_indices: {end_indices}')
        # print(f'NumPnts: {final_nb_points}')
        # print ("---------------------")
 
    return force_curve