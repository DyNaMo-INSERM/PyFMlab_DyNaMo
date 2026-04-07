# File containing the function loadNANOSCcurve,
# used to load the data of force curves from NANOSCOPE files.

import numpy as np
from struct import unpack


from ..utils.forcecurve import ForceCurve
from ..utils.segment import Segment

from afmformats.formats.fmt_igor import load_igor
import pathlib
from igor2 import binarywave

def loadIBWcurve(header, idx=0):
    """
    Function used to load the data of a single force curve from an ibw file.

            Parameters:
                    idx (int): Index of the force curve.
                    header (dict): Dictionary containing ibw file metadata.
            
            Returns:
                    force_curve (utils.forcecurve.ForceCurve): ForceCurve object containing the loaded data.
    """
    
    file_name = header['Entry_filename']
    filepath = header['file_path']
    force_curve = ForceCurve(idx, file_name)

    dslist = load_igor(filepath)
    data = dslist[0]['data']

    index_start_retract = np.argmin(data['height (measured)'])
    index_end_retract = len(data['height (measured)']) -1
    index_start_approach = 0
    index_end_approach = index_start_retract -1

    # spring constant comes in N/m in the raw data
    force = data['force']  # newton
    height_measured = data['height (measured)']*-1  # m
    height_piezo = data['height (piezo)']*-1 # m
    deflection = data['force'] / header['spring constant']  # m

    # Generate time channel from .ibw metadata
    # How much the sampling rate was reduced compared to maximum
    # 1 - you kept all points
    # 2 - only every 2nd point kept
    # the force decimation should be taken from the metadata as I have been doing for ARDF
    # the function from afmformats is not extracting the force_decimation
    # could be a improvement for the future
    force_decimation = 1
    n_pts_per_sec = float(header['rate approach'])
    real_sampling_rate = n_pts_per_sec / force_decimation  # in Hz
    sampling_interval = 1 / real_sampling_rate
    time = np.arange(len(force)) * sampling_interval  # seconds

    appsegment = Segment(file_name, '0', 'Approach')
    retsegment = Segment(file_name, '1', 'Retract')


    # Assign data and metadata for Approach segment.
    appsegment.segment_formated_data = {
        'height': height_measured[index_start_approach:index_end_approach], 
        'vDeflection': deflection[index_start_approach:index_end_approach],
        'time': time[index_start_approach:index_end_approach]
        }
    appsegment.nb_point = len(deflection[index_start_approach:index_end_approach])
    appsegment.force_setpoint_mode = 0
    appsegment.nb_col = len(list(appsegment.segment_formated_data.keys()))
    appsegment.force_setpoint = 0
    appsegment.velocity = float(header['speed approach'])
    appsegment.sampling_rate = float(header['rate approach'])
    appsegment.z_displacement = float(header['z range'])

    # Assing data and metadata for Retract segment.
    retsegment.segment_formated_data = {
        'height': height_measured[index_start_retract:index_end_retract],
        'vDeflection': deflection[index_start_retract:index_end_retract],
        'time': time[index_start_retract:index_end_retract] - time[index_start_retract]
        }
    retsegment.nb_point = len(deflection[index_start_retract:index_end_retract])
    retsegment.force_setpoint_mode = 0
    retsegment.nb_col = len(retsegment.segment_formated_data.keys())
    retsegment.force_setpoint = 0
    retsegment.velocity = float(header['speed retract'])
    retsegment.sampling_rate = float(header['rate retract'])
    retsegment.z_displacement = float(header['z range'])


    force_curve.extend_segments.append(('0', appsegment))
    force_curve.retract_segments.append(('1', retsegment))

    return force_curve




