
"""
Created on Mon Aug 18 17:14:08 2025

@author: yogehs
"""

# File containing the loadJPK h5curve function,
# used to load single force curves from JPK h5 file .

import numpy as np

from ..utils.forcecurve import ForceCurve
from ..utils.segment import Segment
from ..constants import JPK_SETPOINT_MODE
from .utils_h5readcurve import _get_matching_data_set
from .parsejpkh5header import decode_byte_string, properties_section
import h5py
import matplotlib.pyplot as plt


def read_from_metadata(
    segment: h5py.Group, ds_name: str
):
    dataset = segment["meta-data"][ds_name]
    return np.asarray(dataset).flatten()

def loadJPKh5curve(file_metadata, curve_index):
    """
    Function used to load the data of a single force curve from a JPK file.

            Parameters:
                    file_metadata (dict): Dictionary containing the file metadata.
                    curve_index (int): Index of curve to load.

            Returns:
                    force_curve (utils.forcecurve.ForceCurve): ForceCurve object containing the loaded data.
    """
    # curve_properties = file_metadata['curve_properties']

    file_id = file_metadata['Entry_filename']
    file_path = file_metadata['file_path']
    top_group = file_metadata['top_group']

    height_channel_key = file_metadata['height_channel_key']
    found_vDeflection = file_metadata['found_vDeflection']

    force_curve = ForceCurve(curve_index, file_id)

    curve_indices = file_metadata["Entry_tot_nb_curve"] - 1

    index = 1 if curve_indices == 0 else 3
    # opening the file
    h5file = h5py.File(file_path, 'r')

    h5file_top = h5file[top_group]
    segment_meta = file_metadata['segment_meta']

    datasets = [segment_meta[i]['name'] for i in segment_meta]
    segments_h5 = [[h5file_top[f"{d}/"], d] for d in datasets]
    for seg_id in range(len(segments_h5)):
        segment_formated_data = {}

        seg_group, seg_type = segments_h5[seg_id]
        segment_duration = read_from_metadata(
            seg_group, "duration")[curve_index]
        segment_num_points = read_from_metadata(
            seg_group, "num-points")[curve_index]

        # TODO: or to be read from the file
        segment_formated_data["time"] = np.linspace(
            0, segment_duration, segment_num_points, endpoint=False)

        # Transform Height data
        if height_channel_key is not None:

            group, raw_data_all = _get_matching_data_set(
                seg_group, height_channel_key)
            raw_data = np.asarray(
                raw_data_all[curve_index, :segment_num_points])
            encode_atts = properties_section(
                group.attrs, "net-encoder.scaling")
            # conversion_factors = file_metadata["channel_properties"][height_channel_key]

            conversion_factors = {key: decode_byte_string(value)
                                  for key, value in encode_atts.items()}

            if conversion_factors['type'] == 'linear':
                values = conversion_factors['multiplier'] * \
                    raw_data + conversion_factors['offset']
            else:
                print("[!] No encoders found check JPK's script")

            segment_formated_data[height_channel_key] = -1*values

        else:
            print("[!] No valid height channel found!")

        # Transform vDeflection data
        if found_vDeflection:

            group, raw_data_all = _get_matching_data_set(
                seg_group, 'VDeflection')
            raw_data = np.asarray(
                raw_data_all[curve_index, :segment_num_points])
            encode_atts = properties_section(
                group.attrs, "net-encoder.scaling")
            conversion_factors = {key: decode_byte_string(value)
                                  for key, value in encode_atts.items()}

            if conversion_factors['type'] == 'linear':
                values = conversion_factors['multiplier'] * \
                    raw_data + conversion_factors['offset']

                if conversion_factors['unit.unit'] == 'N':
                    # this is to get teh vdeflection in V from N
                    k_sens_in_si = file_metadata['spring_const_Nbym'] * \
                        file_metadata['defl_sens_nmbyV'] * 1e-09
                    values = values/k_sens_in_si
            else:
                print("[!] No encoders found check JPK's script")

            segment_formated_data['vDeflection'] = values

            # conversion_factors = file_metadata["channel_properties"][vDeflection_channel_key]

        else:
            print("[!] No valid vDeflection channel found!")

        # TODO mutiple segments of the same type
        # TODO pause and modulation

        segment = Segment(file_id, seg_id, seg_type)
        segment.segment_formated_data = segment_formated_data
        # TODO do i need to store raw data?
        segment.segment_raw_data = segment_formated_data
        # TODO what is this segment metadata
        segment.segment_metadata = segment_meta[seg_id]
        segment.segment_metadata["duration"] = segment_duration
        segment.segment_metadata["baseline_measured"] = False
        # TODO what is this JPK_SETPOINT_MODE
        segment.force_setpoint_mode = JPK_SETPOINT_MODE

        segment.nb_point = segment_num_points
        segment.nb_col = len(segment_formated_data.keys())
        segment.force_setpoint = file_metadata["force_setpoint"]

        segment.velocity = float(segment_meta[seg_id]["environment.feedback-mode.approach-feedback-settings.velocity"])
        segment.sampling_rate = segment.nb_point / \
             segment.segment_metadata["duration"]
        #TODO move this to parse
        segment_meta[seg_id]["ramp_size"] = float(segment_meta[seg_id]['settings.segment-settings.z-end'])-float(segment_meta[seg_id]['settings.segment-settings.z-start'])
        segment.z_displacement = segment.segment_metadata["ramp_size"]
        if segment.segment_type == "Extend":
            force_curve.extend_segments.append(
                (int(segment.segment_id), segment))
            # storing z at setpoint
            force_curve.z_at_setpoint = segment.segment_formated_data[height_channel_key][-1]
        elif segment.segment_type == "Retract":

            force_curve.retract_segments.append(
                (int(segment.segment_id), segment))

        elif segment.segment_type == "Pause":
            force_curve.pause_segments.append(
                (int(segment.segment_id), segment))
        elif segment.segment_type == "Modulation":
            force_curve.modulation_segments.append(
                (int(segment.segment_id), segment))
    h5file.close()

    return force_curve
