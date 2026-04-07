
from struct import unpack
from itertools import groupby
import numpy as np
from nptdms import TdmsFile

from ..utils.forcecurve import ForceCurve
from ..utils.segment import Segment


def loadHS3curve(file_metadata, curve_index=0):
    """
    Load the single force‐curve segments from an HS3 file into a ForceCurve object.

    Parameters
    ----------
    file_metadata : dict
        Must contain:
          - 'file_path'
          - 'height_channel_key'   (== 'Piezo')
          - 'deflection_channel_key' (== 'Deflection')
          - 'Piezo_data', 'Deflection_data'   (numpy arrays)
          - 'approach_points', 'dwell_points', 'retract_points'
          - 'reading_sample_rate_Hz'
    curve_index : int
        Only one curve per HS3 file; unused but kept for signature compatibility.

    Returns
    -------
    force_curve : ForceCurve
    """
    file_id               = file_metadata['file_id']
    height_channel_key    = file_metadata['height_channel_key']
    deflection_channel_key= file_metadata['deflection_channel_key']
    fs                    = file_metadata['reading_sample_rate_Hz']
    dt                    = 1.0 / fs

    tdms_file_hs3 = TdmsFile.open(file_metadata['file_path'])
    
    height_v = tdms_file_hs3['Force Curve'][height_channel_key][:]
    deflection = tdms_file_hs3['Force Curve'][deflection_channel_key][:]
    sensitivity_nm_per_V = file_metadata['sensitivity_nm_per_V']
    piezo_gain = file_metadata['piezo_gain']
    height_m = height_v * sensitivity_nm_per_V * piezo_gain * -1e-9  # convert to meters
    #height_m =np.flip(height_m)

    # how many points in each segment?
    n_app  = int(file_metadata['approach_points'])
    n_con  = int(file_metadata['dwell_points'])
    n_ret  = int(file_metadata['retract_points'])

    # 5) Build ForceCurve
    force_curve = ForceCurve(curve_index, file_id)

    # sanity check
    total = n_app + n_con + n_ret
    assert total == len(height_m), \
        f"Expected total {total} samples, got {len(height_m)}"
    # segment durations in ms
    S1 = file_metadata['S1_ms']
    S2 = file_metadata['S2_ms']
    S3 = file_metadata['S3_ms']
    S4 = file_metadata['S4_ms']
    S5 = file_metadata['S5_ms']
    # decimation factors
    dec_app = file_metadata['dec_factor_approach']
    dec_con = file_metadata['dec_factor_contact']
    dec_ret = file_metadata['dec_factor_retract']

    V1 = file_metadata['V1']
    V3 = file_metadata['V3']
    V5 = file_metadata['V5']
    # 6) Define the time boundaries in seconds
    t_app_end = (S1 + S2) * 1e-3
    t_con_end = t_app_end + S3 * 1e-3
    t_ret_end = t_con_end + (S4 + S5) * 1e-3

    # 7) Define segments
    segments = [
        ('App', 0,       n_app,    0.0,      t_app_end),
        ('Con', n_app,   n_app+n_con, t_app_end, t_con_end),
        ('Ret', n_app+n_con, n_app+n_con+n_ret, t_con_end, t_ret_end),
    ]

    # 8) Loop over segments
    for segment_id, (seg_type, start, end, t0, t1) in enumerate(segments):
        seg = Segment(file_id, segment_id, seg_type)

        # time vector for this segment
        times = np.linspace(0, t1-t0, end - start, endpoint=False)

        # formatted data
        seg.segment_formated_data = {
            'time': times,
            height_channel_key: height_m[start:end],
            'vDeflection': deflection[start:end]
        }

        # minimal metadata for HS3
        seg.segment_metadata = {
            f"segment_{segment_id}_nb_points_cal": end - start,
            f"segment_{segment_id}_duration_(s)": t1 - t0,
            f"segment_{segment_id}_sampling_rate_(Hz)": fs / (dec_app if seg_type=='App'
                                                            else dec_con if seg_type=='Con'
                                                            else dec_ret),
            'baseline_measured' : False
        }

        seg.nb_point = end - start
        seg.nb_col   = len(seg.segment_formated_data)
        

        
        seg.force_setpoint = V3
        
        seg.sampling_rate = seg.segment_metadata[f"segment_{segment_id}_sampling_rate_(Hz)"]
        seg.z_displacement = height_m[end-1]-height_m[start]
        seg.velocity =  seg.z_displacement/times[-1]


        # assign into correct list
        if seg_type == 'App':
            force_curve.extend_segments.append((segment_id, seg))
        elif seg_type == 'Con':
            force_curve.pause_segments.append((segment_id, seg))
        elif seg_type == 'Ret':
            force_curve.retract_segments.append((segment_id, seg))
        else:
            force_curve.modulation_segments.append((segment_id, seg))

    return force_curve


# def loadHS3curve(file_metadata, curve_index=0):
#     """
#     Load the single force‐curve segments from an HS3 file into a ForceCurve object.

#     Parameters
#     ----------
#     file_metadata : dict
#         Must contain:
#           - 'file_path'
#           - 'height_channel_key'   (== 'Piezo')
#           - 'deflection_channel_key' (== 'Deflection')
#           - 'Piezo_data', 'Deflection_data'   (numpy arrays)
#           - 'approach_points', 'dwell_points', 'retract_points'
#           - 'reading_sample_rate_Hz'
#     curve_index : int
#         Only one curve per HS3 file; unused but kept for signature compatibility.

#     Returns
#     -------
#     force_curve : ForceCurve
#     """
#     file_id               = file_metadata['file_id']
#     height_channel_key    = file_metadata['height_channel_key']
#     deflection_channel_key= file_metadata['deflection_channel_key']
#     fs                    = file_metadata['reading_sample_rate_Hz']
#     dt                    = 1.0 / fs

#     tdms_file_hs3 = TdmsFile.open(file_metadata['file_path'])
    
#     height_v = tdms_file_hs3['Force Curve'][height_channel_key][:]
#     deflection = tdms_file_hs3['Force Curve'][deflection_channel_key][:]
#     sensitivity_nm_per_V = file_metadata['sensitivity_nm_per_V']
#     piezo_gain = file_metadata['piezo_gain']
#     height_m = height_v * sensitivity_nm_per_V * piezo_gain * 1e-9  # convert to meters
    
#     # how many points in each segment?
#     n_app  = int(file_metadata['approach_points'])
#     n_con  = int(file_metadata['dwell_points'])
#     n_ret  = int(file_metadata['retract_points'])

#     # build ForceCurve
#     force_curve = ForceCurve(curve_index, file_id)

#     # cumulative indices
#     idx_app_end = n_app
#     idx_con_end = n_app + n_con
#     idx_ret_end = n_app + n_con + n_ret

#     # sanity check
#     assert idx_ret_end == len(height_m), \
#         f"Expected total {idx_ret_end} samples, found {len(height_m)}"

#     # define segments
#     segments = [
#       ('App', 0,        idx_app_end),
#       ('Con', idx_app_end, idx_con_end),
#       ('Ret', idx_con_end, idx_ret_end)
#     ]

#     for segment_id, (seg_type, start, end) in enumerate(segments):
#         seg = Segment(file_id, segment_id, seg_type)

#         # time vector for this segment
#         duration = (end - start) * dt
#         times = np.linspace(0, duration, end - start, endpoint=False)

#         # formatted data
#         seg.segment_formated_data = {
#             'time': times,
#             height_channel_key: height_m[start:end],
#             'vDeflection':       deflection[start:end]
#         }

#         # minimal metadata for HS3—just point counts and sample rate
#         seg.segment_metadata = {
#             f"segment_{segment_id}_nb_points_cal": end - start,
#             f"segment_{segment_id}_duration_(s)": duration,
#             f"segment_{segment_id}_sampling_rate_(Hz)": fs,
#         }

#         seg.nb_point  = end - start
#         seg.nb_col    = len(seg.segment_formated_data)

#         # assign into correct ForceCurve list
#         if seg_type == 'App':
#             force_curve.extend_segments.append((segment_id, seg))
#         elif seg_type == 'Con':
#             force_curve.pause_segments.append((segment_id, seg))
#         elif seg_type == 'Ret':
#             force_curve.retract_segments.append((segment_id, seg))
#         else:
#             force_curve.modulation_segments.append((segment_id, seg))

#     return force_curve



