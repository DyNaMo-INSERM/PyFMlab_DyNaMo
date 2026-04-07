    #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 18:07:01 2024

@author: vip
"""
from .parseHS3header import parseHS3header
from nptdms import TdmsFile



def loadHS3file(filepath, UFF):
    """
    Load both .dat metadata and the two Force‐Curve channels
    ('Piezo' and 'Deflection') into the supplied UFF object.

    Parameters
    ----------
    filepath : str
        Full path to the .tdms HS3 file.
    UFF : uff.UFF
        A pre‐constructed UFF object to hold metadata + data.
    
    Returns
    -------
    UFF : uff.UFF
        The same UFF object, now with:
          - UFF.filemetadata[...]  (header + channel arrays)
          - a few flags (found_vDeflection, file_type, ...)
    """
    # 1) First, parse the .dat metadata
    filemetadata = parseHS3header(filepath)  
    
    # 3) Populate UFF.filemetadata
    UFF.filemetadata          = filemetadata
    
    # 4) The flags and keys you asked for
    UFF.filemetadata['found_vDeflection']      = True
    UFF.filemetadata['height_channel_key']     = 'Piezo'
    UFF.filemetadata['deflection_channel_key'] = 'Deflection'
    
    
    UFF.filemetadata['isFV']     = False
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




    