
"""
Created on Mon Aug 18 17:24:28 2025

@author: yogehs
"""
import numpy as np
import h5py

#TODO please rename this function
def _get_matching_data_set(
    containing_group: h5py.Group, channel_name: str
) -> tuple[h5py.Group, h5py.Group]:
    """Return the data set matching channel_name.

    The structure of the containing group's tree is something like

        Peakforce_Cycle
        ├── Channel_000
        │   └── ShiftedMeasuredHeight
        ├── Channel_001
        │   └── CorrectedHeight
        ⋮
        └── meta-data
            ├── baseline
            ├── duration
            ⋮

    and the channel name we are looking for is e.g. "CorrectedHeight".
    In this example, return the HDF5 groups

      (Channel_001, Corrected_Height)

    """
    for channel_group in containing_group.values():
        for name, data_set in channel_group.items():
            if name == channel_name:
                return channel_group, data_set

    raise KeyError(
        f"Channel {channel_name} not found in file {containing_group}")


