
"""
Created on Mon Aug 18 18:26

@author: yogehs
"""
from .parsejpkh5header import parsejpkh5_header
from .jpkh5piezoimg import loadJPKimg_h5


def loadJPKh5file(filepath, UFF):
    """
    Function used to load the metadata of a PS_nex file.

            Parameters:
                    filepath (str): Path to the PS_nex file.
                    UFF (uff.UFF): UFF object to load the metadata into.

            Returns:
                    UFF (uff.UFF): UFF object containing the loaded metadata.
    """
    UFF.filemetadata = parsejpkh5_header(filepath)
    UFF.isFV = bool(UFF.filemetadata["force_volume"])

    UFF.filemetadata['found_vDeflection'] = True
    UFF.filemetadata['height_channel_key'] = "Height"
    UFF.filemetadata['deflection_chanel_key'] = "VDeflection"
    UFF.imagedata = loadJPKimg_h5(UFF.filemetadata)

    curve_properties = {}

    curve_indices = UFF.filemetadata["Entry_tot_nb_curve"]

    '''
        index = 1 if curve_indices == 0 else 3

        for i in range( UFF.filemetadata["Recording_number_segment"] ):
            if index == 3:
                #curve_id = segment_group[0].split("/")[1]
                curve_id =  UFF.filemetadata["curve_id"] 
            else:
                curve_id = '0'
            segment_id = i
            if not curve_id in curve_properties.keys():
                curve_properties.update({curve_id:{}})

            curve_properties =  UFF.filemetadata["segment_meta"][0] 

        UFF.filemetadata['curve_properties'] = curve_properties

    '''

    return UFF
