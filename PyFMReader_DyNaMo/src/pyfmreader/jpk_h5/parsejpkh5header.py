#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 27 18:48:18 2025

@author: yogehs
"""

import sys
from ..constants import UFF_version, UFF_code, default_delay, default_angle, multiplier_default
from ..constants import offset_default, boolean_default, num_segments_default, scaling_factor
import h5py
import os
import re
from typing import Any, Iterator, NoReturn, cast, Union, Dict

import numpy as np


def canonicalize_segment_name(name: str) -> str:
    """Transform e.g. 'extend-spm' to 'Extend'."""
    return re.sub(r"-spm$", "", name).capitalize()


def get_attributes_matching(
    section_pattern: str, attrs: h5py.AttributeManager
) -> dict[str, Any]:
    """Get attributes matching a prefix and strip that prefix away.

    The result is a dict {stripped_key: value}.
    See also properties_section().

    """
    map = {}
    for full_key, value in attrs.items():
        if re.search(section_pattern, full_key):
            key = re.sub(section_pattern + r"\.", "", full_key)
            map[key] = decode_byte_string(value)
    return map


def decode_byte_string(value: Any) -> Any:
    """Decode attribute values (which are byte strings) to strings and sanitize.

    Leave attributes of any other type alone.

    """
    if isinstance(value, bytes):
        string = value.decode("utf-8")
    elif isinstance(value, str):
        string = value
    else:
        return value

    # Expand Java-style '\u' unicode points
    while True:
        m = re.search(
            r"""
            ^
            (?P<pre>.*)
            \\u(?P<hex>[0-9a-fA-F]{4})
            (?P<post> .*)
            $""",
            string,
            flags=re.VERBOSE,
        )
        if m:
            char = chr(int(m.group("hex"), base=16))
            string = f"{m.group('pre')}{char}{m.group('post')}"
        else:
            break
    return string


def read_clean_attrs(h5obj, verbose=True):
    """
    Converts attributes of an HDF5 group or dataset to a clean Python dict.

    Parameters:
    - h5obj: h5py.Group or h5py.Dataset
    - verbose: if True, prints warnings for unusual types

    Returns:
    - A cleaned dict of attributes
    """
    clean_attrs = {}

    for key, val in h5obj.attrs.items():
        # Convert bytes to str
        if isinstance(val, bytes):
            clean_attrs[key] = val.decode('utf-8')

        # Convert NumPy scalars to Python scalars
        elif hasattr(val, 'item'):
            clean_attrs[key] = val.item()

        # If array-like (e.g., numpy arrays), convert to list
        elif isinstance(val, (np.ndarray, list, tuple)):
            clean_attrs[key] = val.tolist()

        else:
            clean_attrs[key] = val
            if verbose:
                print(f"⚠️  Attribute '{key}' has unusual type: {type(val)}")
    # pyperclip.copy(clean_attrs)

    return clean_attrs


def properties_section(properties: dict[str, Any], prefix: str) -> dict[str, Any]:
    r"""Filter and strip a section out of properties.

    In other words: select and return a subtree of the properties tree.

    For example
      properties_section(
          {
              "a.b.c": 5,
              "e.g.h.i": -17,
              "a.b.d.j": "meter",
              "a.f.k": 7
          }, "a.b"
      )
    returns
      {
          "c": 5,
          "d.j": "meter",
      }
    i.e. the entries starting with 'a.b.', but with the common prefix removed.

    Expressed as trees:
             .
            / \
           a   e
          / \   \
         b   f   g          →          .
        / \   \   \                   / \
       c   d   k   h                 c   d
            \       \                     \
             j       i                     j

    """
    section = {}
    extended_prefix = prefix + "."
    idx0 = len(extended_prefix)
    for key, val in properties.items():
        if key.startswith(extended_prefix):
            section[key[idx0:]] = val

    if section:
        return section
    else:
        raise TypeError(f"No such section: {prefix}")


def parsejpkh5_header(file_path):
    file_metadata = {}
    h5file = h5py.File(file_path, 'r')

    file_metadata["file_path"] = file_path
    file_metadata["Entry_filename"] = os.path.basename(file_path)
    file_metadata["file_size_bytes"] = os.path.getsize(file_path)
    # TODO pleaswe add this
    file_metadata['height_channel_key'] = 'Height'
    file_metadata['found_vDeflection'] = 'add this'
    file_metadata['Entry_tot_nb_curve'] = 1

    file_metadata["file_type"] = decode_byte_string(
        h5file.attrs["file-format-info"])
    file_metadata['UFF_code'] = UFF_code
    file_metadata['Entry_UFF_version'] = UFF_version
    file_metadata['image_path_dict'] = {}

    shared_data_prefix = 'shared-data.'
    if file_metadata['file_type'] == 'JPK MultiScan Force Map Spectroscopy':
        # this is for smart map
        top_group = "Measurement_000/Map/"
        file_metadata['top_group'] = top_group

        prefix = 'multi-scan-series.map.header'
        pre_header = ".settings"
        file_metadata['force_volume'] = 1

        # grid_position_pattern = GridPositionPattern.from_properties(
        #     get_attributes_matching(
        #         "multi-scan-series.map.header.position-pattern", top.attrs))

        valid_indices = np.asarray(
            h5file[top_group]["meta-data"]["valid-indices"]).flatten()
        file_metadata['valid_indices'] = valid_indices

        file_metadata['Entry_tot_nb_curve'] = len(valid_indices)

        file_metadata['image_path_dict'] = {'VDeflection': 'Measurement_000/AnalyzedImage/Channel_000/VDeflection',
                                            'MeasuredHeight': 'Measurement_000/AnalyzedImage/Channel_001/MeasuredHeight',
                                            'Height': 'Measurement_000/AnalyzedImage/Channel_002/Height',
                                            'Slope': 'Measurement_000/AnalyzedImage/Channel_003/Slope',
                                            'Adhesion': 'Measurement_000/AnalyzedImage/Channel_004/Adhesion',
                                            'CombinedHeightMeasured': 'Measurement_000/AnalyzedImage/Channel_005/CombinedHeightMeasured'}

    elif file_metadata['file_type'] == "JPK MultiScan Force Spectroscopy":
        # this is for smart points
        top_group = "Measurement_000/"
        file_metadata['top_group'] = top_group

        prefix = 'multi-scan-series.header'
        pre_header = ''

        file_metadata['force_volume'] = 1
        file_metadata['Entry_tot_nb_curve'] = 1

    elif file_metadata['file_type'] == "JPK QNM MAP":
        # this is for QNM
        # TODO define this prefix

        prefix = ''
        file_metadata['force_volume'] = 0

        top_group = "Measurement_000/Map/Trace/"
        file_metadata['top_group'] = top_group

        file_metadata['Entry_tot_nb_curve'] = 1

    attrs = read_clean_attrs(h5file[top_group])
    _sharedataprops = {key: val for key,
                       val in attrs.items() if key.startswith("shared-data")}

    header_properties = h5file[top_group].attrs

    file_metadata["Experimental_instrument"] = decode_byte_string(header_properties.get(
        prefix + ".description.instrument"))
    file_metadata["JPK_file_format_version"] = header_properties.get(
        "file-format-version")
    file_metadata["JPK_software_version"] = decode_byte_string(header_properties.get(
        prefix + ".description.source-software"))

    file_metadata["retracted_delay"] = float(header_properties.get(
        prefix + ".settings.force-settings.retracted-pause-time", default_delay))
    file_metadata["extended_delay"] = float(header_properties.get(
        prefix + ".settings.force-settings.extended-pause-time", default_delay))
    file_metadata["Entry_date"] = decode_byte_string(
        header_properties.get(prefix + ".start-time"))

    file_metadata["scan_angle"] = float(header_properties.get(
        prefix + ".position-pattern.grid.theta", default_angle))

    file_metadata["num_x_pixels"] = int(header_properties.get(
        prefix + ".position-pattern.grid.ilength", multiplier_default))
    file_metadata["num_y_pixels"] = int(header_properties.get(
        prefix + ".position-pattern.grid.jlength", multiplier_default))
    # the scan size is now stored in meters
    file_metadata["scan_size_x"] = round(float(header_properties.get(
        prefix + ".position-pattern.grid.ulength", offset_default)), 10)
    file_metadata["scan_size_y"] = round(float(header_properties.get(
        prefix + ".position-pattern.grid.vlength", offset_default)), 10)
    file_metadata['scan_grid_center_x'] = round(float(header_properties.get(
        prefix + ".position-pattern.grid.xcenter", offset_default)), 10)
    file_metadata['scan_grid_center_y'] = round(float(header_properties.get(
        prefix + ".position-pattern.grid.ycenter", offset_default)), 10)
    file_metadata['position_pattern_type'] = header_properties.get(
        prefix + ".position-pattern.type",'attribute')
    file_metadata['scan_numbering'] = header_properties.get(
        prefix + ".position-pattern.grid.numbering", offset_default)

    file_metadata["z_closed_loop"] = header_properties.get(
        prefix + ".settings.force-settings.closed-loop", boolean_default).strip().lower() == "true"

    file_metadata["Recording_Z_close_loop_on"] = "On" if file_metadata["z_closed_loop"] else "Off"

    # TODO this needs to be fixed
    # file_metadata["Entry_tot_nb_curve"] = int(
    #     header_properties.get(prefix + ".indexes.max", offset_default)) + 1

    file_metadata["extend_pause_duration"] = float(header_properties.get(
        prefix + ".settings.force-settings.extended-pause-time", offset_default))

    if file_metadata["file_type"] in ("JPK MultiScan Force Map Spectroscopy"):
        file_metadata["relative_z_start"] = float(header_properties.get(
            "relative-z-start", offset_default)) * scaling_factor
        file_metadata["relative_z_end"] = float(header_properties.get(
            "relative-z-end", offset_default)) * scaling_factor
        file_metadata["relative_ramp_size"] = file_metadata["relative_z_end"] - \
            file_metadata["relative_z_start"]  # This can be 0

    elif file_metadata["file_type"] in ("jpk-qi-data"):
        file_metadata["relative_z_start"] = float(header_properties.get(
            "settings.force-settings.extend.z-start", offset_default)) * scaling_factor
        file_metadata["relative_z_end"] = float(header_properties.get(
            "settings.force-settings.extend.z-end", offset_default)) * scaling_factor
        file_metadata["relative_ramp_size"] = file_metadata["relative_z_end"] - \
            file_metadata["relative_z_start"]  # This can be 0

    file_metadata["force_setpoint"] = float(header_properties.get(
        prefix + pre_header + ".force-settings.relative-setpoint", offset_default))

    file_metadata['settings_type'] = decode_byte_string(header_properties.get(
        "multi-scan-series.header.force-settings.type"))

    sprefix = 'shared-data.'
    # Get number of channels saved
    file_metadata["nbr_channels"] = int(
        _sharedataprops[f"{sprefix}lcd-info.count"])
    # Get number of segments saved
    if file_metadata["file_type"] == "jpk-force":
        file_metadata["Recording_number_segment"] = int(header_properties.get(
            "force-scan-series.force-segments.count", num_segments_default))
    else:
        file_metadata["Recording_number_segment"] = int(_sharedataprops.get(
            "'shared-data.force-segment-header-info.count", num_segments_default))

    # Create empty key for holding segment properties
    file_metadata["curve_properties"] = {}
    # to store the segment properties

    if file_metadata['settings_type'] == "segmented-force-settings":
        # TODO this needs testing
        print("WARNOING NOT TESTED")
        file_metadata['segment_meta'] = get_modern_segment_infos_pyfm(
            header_properties)
    elif file_metadata['settings_type'] == "relative-force-settings":
        file_metadata['segment_meta'] = get_legacy_segment_infos_pyfm(
            header_properties)
    else:
        raise Exception(
            f"Unknown force settings type '{file_metadata['settings_type']}'")

    # TODO whatever down is errorneous or not needed
    # Get channel properties
    channel_properties = {}
    height_channel_names = ['measuredHeight',
                            'combinedHeight', 'height', 'combinedHeightMeasured', 'capacitiveSensorHeight',
                            "cellhesion-height", 'strainGaugeHeight']

    for channel_id in range(file_metadata["nbr_channels"]):

        properties = {}
        properties["channel_id"] = channel_id

        pre = f"{sprefix}lcd-info.{channel_id}"
        pre_conv = pre + ".conversion-set"
        conv_distance = ".conversion.distance"
        conv_force = ".conversion.force"
        conv_absolute = ".conversion.absolute"
        conv_nominal = ".conversion.nominal"

        channel_name = _sharedataprops.get(pre + ".channel.name")
        if channel_name in ("vDeflection", "hDeflection"):
            properties["encoder_type"] = _sharedataprops.get(
                pre + ".encoder.type")
            properties["encoder_offet_key"] = float(_sharedataprops.get(
                pre + ".encoder.scaling.offset", offset_default))
            properties["encoder_multiplier_key"] = float(_sharedataprops.get(
                pre + ".encoder.scaling.multiplier", multiplier_default))

            properties["base"] = _sharedataprops.get(
                pre_conv + ".conversions.base")

            properties["base_defined"] = _sharedataprops.get(
                pre_conv + ".conversion." + properties["base"] + ".defined", boolean_default).strip().lower() == "true"

            if properties["base_defined"]:
                print(
                    f'[!] The conversion base for {properties["base"]} has been already been defined. Check your loaded data.')

            properties["distance_defined"] = _sharedataprops.get(
                pre_conv + conv_distance + ".defined", boolean_default).strip().lower() == "true"

            properties["deflection_distance_offset"] = float(_sharedataprops.get(
                pre_conv + conv_distance + ".scaling.offset", offset_default)) * scaling_factor  # in nm/V
            properties["deflection_distance_multiplier"] = float(_sharedataprops.get(
                pre_conv + conv_distance + ".scaling.multiplier", offset_default)) * scaling_factor  # in nm/V

            properties["force_defined"] = _sharedataprops.get(
                pre_conv + conv_force + ".defined", boolean_default).strip().lower() == "true"

            properties["deflection_force_offset"] = float(_sharedataprops.get(
                pre_conv + conv_force + ".scaling.offset", offset_default))
            properties["deflection_force_multiplier"] = float(_sharedataprops.get(
                pre_conv + conv_force + ".scaling.multiplier", multiplier_default))

            if channel_name == "vDeflection":
                file_metadata["defl_sens_nmbyV"] = float(properties.get(
                    "deflection_distance_multiplier", multiplier_default))
                file_metadata["spring_const_Nbym"] = float(properties.get(
                    "deflection_force_multiplier", multiplier_default))

                if not properties["distance_defined"] and not properties["force_defined"]:
                    print(f"[!] In the file's {file_metadata['file_id']} header the deflection sensitivity and spring constant could not be found,\
                             the default values of dlection sentivity = {multiplier_default} and K = {multiplier_default} have been assigned!")

        elif channel_name in height_channel_names:
            properties["encoder_type"] = _sharedataprops.get(
                pre + ".encoder.type")
            properties["encoder_offet_key"] = float(_sharedataprops.get(
                pre + ".encoder.scaling.offset", offset_default))
            properties["encoder_multiplier_key"] = float(_sharedataprops.get(
                pre + ".encoder.scaling.multiplier", scaling_factor))

            properties["base"] = _sharedataprops.get(
                pre_conv + ".conversions.base")

            properties["base_defined"] = _sharedataprops.get(
                pre_conv + ".conversion." + properties["base"] + ".defined", boolean_default).strip().lower() == "true"
            if properties["base_defined"]:
                print(
                    f'[!] The conversion base for {properties["base"]} has been already been defined. Check your loaded data.')

            properties["absolute_defined"] = _sharedataprops.get(
                pre_conv + conv_absolute + ".defined", boolean_default).strip().lower() == "true"

            properties["capSensHeight_abs_offset"] = float(_sharedataprops.get(
                pre_conv + conv_absolute + ".scaling.offset", offset_default))
            properties["capSensHeight_abs_mult"] = float(_sharedataprops.get(
                pre_conv + conv_absolute + ".scaling.multiplier", scaling_factor))

            properties["nominal_defined"] = _sharedataprops.get(
                pre_conv + conv_nominal + ".defined", boolean_default).strip().lower() == "true"

            properties["capSensHeight_nom_offset"] = float(_sharedataprops.get(
                pre_conv + conv_nominal + ".scaling.offset", offset_default))
            properties["capSensHeight_nom_mult"] = float(_sharedataprops.get(
                pre_conv + conv_nominal + ".scaling.multiplier", scaling_factor))

        channel_properties[channel_name] = properties

    file_metadata["channel_properties"] = channel_properties

    h5file.close()
    return file_metadata

# %% segment header


def create_modern_seg_header(props: dict[str, str],
                             dataset_name: str,
                             index: int,
                             ignore_fancy_name: bool = False):
    identifier = properties_section(props, "identifier")
    identifier_type = identifier["type"]
    if identifier_type == "ExtendedStandard":
        prefix = identifier["prefix"]
        name = canonicalize_segment_name(identifier["base-object-name.name"])
        suffix = decode_byte_string(identifier["suffix"])

        full_name = f"{prefix}{name}{suffix}"
    elif identifier_type == "standard":
        full_name = canonicalize_segment_name(identifier["name"])
    elif identifier_type == "default-object-name":
        full_name = identifier["fancy-name"]
        if not ignore_fancy_name:
            dataset_name = canonicalize_segment_name(full_name)
    else:
        raise Exception(f"Unknown identifier type '{identifier_type}'")

    style = props["style"]
    info = {"name": dataset_name, 'style': name, 'index': index, **props}

    return info


def get_modern_segment_infos_pyfm(
    self, attrs: h5py.AttributeManager
):

    if read_bool_attr(attrs, "duplicate-segment-styles", False):
        return self.get_duplicate_segment_infos(attrs)
    else:
        return self.get_unique_segment_infos(attrs)


def get_unique_segment_infos(
        self, attrs: h5py.AttributeManager):
    """List all of the data segments for advanced spectroscopy.

    Here all segments are unique (at most one of Extend , Retract, Pause, etc.), and
    the segments are named like Extend, Modulation, Pause, Retract.

    """
    header_info = get_attributes_matching(
        "multi-scan-series.header.force-settings", attrs
    )

    segment_count: int = header_info["segments.size"]
    segment_infos = {}
    for i in range(segment_count):
        info = properties_section(header_info, f"segment.{i}")

        name = re.sub(r"-spm$", "", info["identifier.name"]).capitalize()
        segment_infos[i] = create_modern_seg_header(info, name, i)
    return segment_infos


def get_duplicate_segment_infos(
        self, attrs: h5py.AttributeManager):
    """List all of the data segments for advanced spectroscopy.

    Here we have duplicate segments (e.g., two Extend segments), and the segments
    are named Segment0, Segment1, etc.

    """
    force_settings = get_attributes_matching(
        "multi-scan-series.header.force-settings", attrs
    )
    count = int(force_settings["segments.size"])

    segment_infos = []
    for i in range(count):
        info = properties_section(
            force_settings, f"segment.{i}")
        name = f'segment{i}'
        segment_infos[i] = create_modern_seg_header(
            info, name, i, ignore_fancy_name=True)

    return segment_infos


def get_legacy_segment_infos_pyfm(header_properties):
    header_info = get_attributes_matching(
        "shared-data.force-segment-header-info", header_properties
    )

    segment_count: int = header_info["count"]
    segment_infos = {}
    for i in range(segment_count):
        info = properties_section(header_info, f"{i}")
        name = re.sub(r"-spm$", "", info["name.name"]).capitalize()
        style = info["settings.style"]
        info = {"name": name, "style": style, **info}
        segment_infos[i] = info
    return segment_infos

# %%


def die(*args: str) -> NoReturn:
    """Print a message and exit.

    Use this to abort on an error that does not need a stack trace.

    """
    for line in args:
        print(line.rstrip())
    sys.exit(1)


def assert_property(properties: dict[str, Any], key: str, value: Any) -> None:
    """Verify that property `key` has value `value`."""
    if key not in properties:
        die(f"Properties\n  {properties}\nlack mandatory key '{key}'")
    prop_value = properties[key]
    if isinstance(prop_value, bytes):
        prop_value = decode_byte_string(prop_value)
    if prop_value != value:
        die(
            f"Properties\n  {properties}\n",
            f"For key {key}: expected '{value}', got '{prop_value}'",
        )


def read_unit(properties: dict[str, Any]) -> str:
    """Read a metric-unit string from properties.

    Properties look like this:

      type: metric-unit
      unit: <unit-string>

    """
    assert_property(properties, "type", "metric-unit")
    return cast(str, decode_byte_string(properties["unit"]))
# %%not used


def read_bool_attr(
    attrs: h5py.AttributeManager, key: str, fallback_value: bool
) -> bool:
    if key not in attrs:
        return fallback_value
    str_value = decode_byte_string(attrs[key]).lower()
    if str_value == "true":
        return True
    elif str_value == "false":
        return False
    else:
        raise Exception(
            f"Cannot parse {key}: '{str_value}' to a boolean value")
