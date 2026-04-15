    #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  7 18:07:01 2025

@author: Lorenzo villanueva 
"""

from .parseHS3header import parseHS3header

def loadHS3file(filepath, UFF):
    """
    Function used to load the metadata of a PS_nex file.

            Parameters:
                    filepath (str): Path to the PS_nex file.
                    UFF (uff.UFF): UFF object to load the metadata into.
            
            Returns:
                    UFF (uff.UFF): UFF object containing the loaded metadata.
    """
    UFF.filemetadata = parseHS3header(filepath)
    # UFF.filemetadata['tick_time_z_loop'] = 2e-06 # 500khz
    # UFF.filemetadata['tick_time_z_loop_correction_factor'] = 10  # July 31 2025. Added by Lorenzo. apparently, there is a insconsistency
    UFF.filemetadata["num_segments"] = 3 # constant for hs3 files 
    
    # Required metadata flags for UI
    UFF.filemetadata['found_vDeflection'] = True
    UFF.filemetadata['isFV'] = False
    # UFF.filemetadata['num_x_pixels'] = 32
    # UFF.filemetadata['num_y_pixels'] = 32
    # UFF.filemetadata['scan_size_x'] = 0
    # UFF.filemetadata['scan_size_y'] = 0
    UFF.filemetadata['file_type'] = 'HS3.tdms'

    return UFF
























# def loadHS3file(filepath, UFF):
#     """
#     Function used to load the metadata of a PS_nex file.

#             Parameters:
#                     filepath (str): Path to the PS_nex file.
#                     UFF (uff.UFF): UFF object to load the metadata into.
            
#             Returns:
#                     UFF (uff.UFF): UFF object containing the loaded metadata.
#     """
#     UFF.filemetadata = parseHS3header(filepath)
#     #UFF.isFV = UFF.filemetadata["mapping_bool"]
#     #key for the channel of ht and defleciton

#     UFF.filemetadata['found_vDeflection'] = True
#     UFF.filemetadata['height_channel_key'] = "Zpiezo stage (V)"
#     UFF.filemetadata['deflection_chanel_key'] = "Deflection (V)"
#     curve_properties = {}

#     curve_indices =  UFF.filemetadata["Entry_tot_nb_curve"] 

#     index = 1 if curve_indices == 0 else 3

#     # for i in range( UFF.filemetadata["num_segments"] ):
#     #     if index == 3:
#     #         #curve_id = segment_group[0].split("/")[1]
#     #         curve_id =  UFF.filemetadata["curve_id"] 
#     #     else:
#     #         curve_id = '0'
#     #     segment_id = i
#     #     if not curve_id in curve_properties.keys():
#     #         curve_properties.update({curve_id:{}})

#        # curve_properties = parsePSNEXsegmentheader(filepath,curve_properties, segment_id,curve_id )

#     #UFF.filemetadata['curve_properties'] = curve_properties
#     UFF.filemetadata['isFV'] = False
#     UFF.filemetadata['file_type'] = 'HS3.tdms'

#     return UFF




    