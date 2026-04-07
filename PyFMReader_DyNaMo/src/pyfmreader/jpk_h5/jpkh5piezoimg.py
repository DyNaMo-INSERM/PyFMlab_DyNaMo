#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 27 18:43:17 2025

@author: yogehs
"""

from .parsejpkh5header import parsejpkh5_header, get_attributes_matching
from .utlis_grid import GridPositionPattern
import matplotlib.pyplot as plt
import h5py
import numpy as np


def loadJPKimg_h5(filemetadata):
    """
    Returns the contents of the data-image file inside the JPK h5 file.
    the H5 file already has the arrays with the proper valuee.

            Parameters:
                    UFF (uff.UFF): UFF object containing the JPK file metadata.

            Returns:
                    imagedata (dict): dictionary containing all the channels data.
    """
    file_type = filemetadata['file_type']
    image_paths = filemetadata['image_path_dict']
    file = filemetadata['file_path']
    top_group = filemetadata['top_group']

    if file_type in 'JPK MultiScan Force Spectroscopy':
        return

    data = {}
    with h5py.File(file, "r") as h5file:
        top_attrs = h5file[top_group].attrs

        for name, path in image_paths.items():
            # print(name)
            image_arr = h5file[path][:]

            image_2D = image_arr.reshape(
                (filemetadata["num_y_pixels"], filemetadata["num_x_pixels"]))
            data[name] = image_2D
        # file_metadata['position_pattern_type']
        if filemetadata["position_pattern_type"] != 'attribute':
            grid_position_pattern = GridPositionPattern.from_properties(
                get_attributes_matching(
                    "multi-scan-series.map.header.position-pattern", top_attrs))
            data['coordinate'] = find_coordinate(
                filemetadata, grid_position_pattern)
            # data['coordinate'] = 'helo'
        elif "coordinates" in h5file[top_group]['Position_Values'].attrs:
            print(
                "return AttributePositionHelper(h5_file, top_group) need to work on this part")
        else:
            print('return AttributePositionHelper with possition might be incorrect')

    return data


def find_coordinate(filemetadata, grid_position_pattern):
    """
    Function to find the coordinate in the JPK h5 files from insipired from the GridPositionHelper class from the jpk script 
    file.
    #TODO need to work on the AttributePositionHelper 
            Parameters:
                    filemetadata (dict): Dictionary containing the file metadata.

            Returns:
                    coords (np.array): 2D array containing the coordinates of the JPK file.
    """
    # Pre-fill the coordinates array
    coords = np.full((filemetadata["num_y_pixels"],
                      filemetadata["num_x_pixels"]), np.nan)

    # Get all valid indices
    valid_indices = filemetadata['valid_indices'][:
                                                  filemetadata["Entry_tot_nb_curve"]]

    # Convert grid positions to arrays of i and j
    i_list = []
    j_list = []

    for idx in valid_indices:
        i, j = grid_position_pattern.get_idx(idx)
        i_list.append(int(i))
        j_list.append(int(j))

    i_arr = np.array(i_list)
    j_arr = np.array(j_list)

    # Assign all values at once
    coords[j_arr, i_arr] = np.arange(len(valid_indices))

    return coords


def computeJPKPiezoImg_h5(UFF, pizeo_channel='MeasuredHeight'):
    """
    Function used to compute the piezo image of a JPK file.

            Parameters:
                    UFF (uff.UFF): UFF object containing the JPK file metadata.

            Returns:
                    piezoimg (np.array): 2D array containing the piezo image of the JPK file.
    """
    file_path = UFF.filemetadata['file_path']

    file_type = UFF.filemetadata['file_type']
    if file_type == 'JPK MultiScan Force Map Spectroscopy':
        pizeo_channel = 'CombinedHeightMeasured'
    else:
        print("what hell is the channel name here ", file_type)
    image_path = UFF.filemetadata['image_path_dict'][pizeo_channel]
    with h5py.File(file_path, "r") as h5file:

        tempiezoimg = h5file[image_path][:]
        # TODO is this needed
        piezoimg = tempiezoimg - np.nanmin(tempiezoimg)
        # Reshape piezo image
        piezoimg = piezoimg.reshape(
            (UFF.filemetadata["num_y_pixels"], UFF.filemetadata["num_x_pixels"]))

    return piezoimg
