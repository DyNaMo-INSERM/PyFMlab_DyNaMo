#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 7 10:56:00 2026

@author: Lorenzo
"""
from .parsepsnexheader import parsePSNEXheader, parsePSNEXsegmentheader
import os

def loadPSNEXfile(filepath, UFF):
    """
    Function used to load the metadata of a PS_nex file.

            Parameters:
                    filepath (str): Path to the PS_nex file.
                    UFF (uff.UFF): UFF object to load the metadata into.
            
            Returns:
                    UFF (uff.UFF): UFF object containing the loaded metadata.
    """
    # print(filepath)
    UFF.filemetadata = parsePSNEXheader(filepath)
    UFF.filemetadata['tick_time_z_loop'] = 2e-06 # 500khz
    UFF.filemetadata['tick_time_z_loop_correction_factor'] = 10  # July 31 2025. Added by Lorenzo. apparently, there is a insconsistency

    
    # check if folder name contains psnex_map_
    if 'psnex_map_' in os.path.basename(os.path.dirname(filepath)):
        # print ('detected PS-NEX map folder')
        UFF.filemetadata['isFV'] = True
        # get first file in the folder
        # Grab TDMS files 
        # filepath, _ = grab_tdms(filepath)
    else:
        UFF.filemetadata['isFV'] = False


    curve_properties = {}

    curve_indices =  UFF.filemetadata["Entry_tot_nb_curve"] 

    index = 1 if curve_indices not in [3] else 3

    for i in range( UFF.filemetadata["num_segments"] ):
        if index == 3:
            #curve_id = segment_group[0].split("/")[1]
            curve_id =  UFF.filemetadata["curve_id"] 
        else:
            curve_id = '0'
        segment_id = i
        if not curve_id in curve_properties.keys():
            curve_properties.update({curve_id:{}})

        curve_properties = parsePSNEXsegmentheader(filepath,curve_properties, segment_id, UFF, curve_id)

    UFF.filemetadata['curve_properties'] = curve_properties
    
    #TODO what the hall have you done 
    # UFF.isFV = UFF.filemetadata["mapping_bool"]
    
    # UFF.filemetadata['num_x_pixels'] = 32
    # UFF.filemetadata['num_y_pixels'] = 32
    # UFF.filemetadata['scan_size_x'] = 0
    # UFF.filemetadata['scan_size_y'] = 0
    UFF.filemetadata['file_type'] = 'PSNEX.tdms'

    return UFF


    