# File containing the function loadNANOSCcurve,
# used to load the data of force curves from NANOSCOPE files.

import numpy as np
from struct import unpack

from .get_ardf_data import extract_ardf_data

from ..utils.forcecurve import ForceCurve
from ..utils.segment import Segment

def loadARDFcurve(header, idx):
    """
    Function used to load the data of a single force curve from an ARDF file.

            Parameters:
                    idx (int): Index of the force curve.
                    header (dict): Dictionary containing all ARDF file metadata.
            
            Returns:
                    force_curve (utils.forcecurve.ForceCurve): ForceCurve object containing the loaded data.
    """
    
    file_name = header['Entry_filename']
    filepath = header['file_path']
    force_curve = ForceCurve(idx, file_name)
    curve_indices = header['all_positions_ardf']

    line, point = header['all_positions_ardf'][idx]

    ardf_data = extract_ardf_data(header["file_path"], line, point, 1, header)

    # The list needs cleaning because it contains null bytes -> \x00 at the end
    clean_channel_list = [s.rstrip('\x00') for s in header['channelList'][0]]
    
    # Removes the tail of 0s in the array (it is an artifact from parsing ARDF files)
    last_nonzero_piezo = np.nonzero(ardf_data['y'][:, clean_channel_list.index('ZSnsr')])[0][-1]
    channel_data_piezo = (ardf_data['y'][:, clean_channel_list.index('ZSnsr')][:last_nonzero_piezo + 1])
    last_nonzero_deflection = np.nonzero(ardf_data['y'][:, clean_channel_list.index('Defl')])[0][-1]
    channel_data_deflection = ardf_data['y'][:, clean_channel_list.index('Defl')][:last_nonzero_deflection + 1]

    # Generate time channel from .ARDF metadata
    # How much the sampling rate was reduced compared to maximum
    # 1 - you kept all points
    # 2 - only every 2nd point kept
    force_decimation = float(header['Notes']['ForceDecimation'])
    n_pts_per_sec = float(header['Notes']['NumPtsPerSec'])
    real_sampling_rate = n_pts_per_sec / force_decimation  # in Hz
    sampling_interval = 1 / real_sampling_rate
    time = np.arange(len(channel_data_deflection)) * sampling_interval

    # Indexes indicating when approach, retraction and baseline start, repectively
    pnt_list = [ardf_data['pnt0'], ardf_data['pnt1'], ardf_data['pnt2']]

    appsegment = Segment(file_name, '0', 'Approach')
    retsegment = Segment(file_name, '1', 'Retract')


    # Assign data and metadata for Approach segment.
    appsegment.segment_formated_data = {
        'height': channel_data_piezo[pnt_list[0]:pnt_list[1]], 
        'vDeflection': channel_data_deflection[pnt_list[0]:pnt_list[1]],
        'time': time[pnt_list[0]:pnt_list[1]]
        }
    appsegment.nb_point = len(channel_data_deflection[pnt_list[0]:pnt_list[1]])
    appsegment.force_setpoint_mode = header['Notes']['TriggerType']
    appsegment.nb_col = len(list(appsegment.segment_formated_data.keys()))
    appsegment.force_setpoint = 0
    appsegment.velocity = float(header['Notes']['ApproachVelocity'])
    appsegment.sampling_rate = float(header['Notes']['NumPtsPerSec'])
    appsegment.z_displacement = float(header['Notes']['ExtendZ'])

    # Assing data and metadata for Retract segment.
    retsegment.segment_formated_data = {
        'height':channel_data_piezo[pnt_list[1]+1:len(channel_data_deflection)],
        'vDeflection': channel_data_deflection[pnt_list[1]+1:len(channel_data_deflection)],
        'time': time[pnt_list[1]+1:len(channel_data_deflection)]- time[pnt_list[1]]
        }
    retsegment.nb_point = len(channel_data_deflection[pnt_list[1]+1:len(channel_data_deflection)])
    retsegment.force_setpoint_mode = header['Notes']['TriggerType']
    retsegment.nb_col = len(retsegment.segment_formated_data.keys())
    retsegment.force_setpoint = 0
    retsegment.velocity = float(header['Notes']['RetractVelocity'])
    retsegment.sampling_rate = float(header['Notes']['NumPtsPerSec'])
    retsegment.z_displacement = float(header['Notes']['RetractZ'])


    force_curve.extend_segments.append(('0', appsegment))
    force_curve.retract_segments.append(('1', retsegment))

    return force_curve




