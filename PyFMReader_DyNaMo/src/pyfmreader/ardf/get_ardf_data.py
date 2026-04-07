#!/usr/bin/env python3

""" The following script and functions are based on the work of Matheww Poss in MATLAB that can
be checked out here https://se.mathworks.com/matlabcentral/fileexchange/80212-ardf-to-matlab 

Created on Tue Apr 15 2025

@author: Carlota Carbajo """

import numpy as np
from .read_ardf import read_ardf_metadata
from .utils_ardf import *

def extract_ardf_data(filename, get_line, get_point, trace, file_struct=None):
    """
    Load force curve data from an Asylum Research Data File (ARDF).

    Parameters:
    ----------
    filename : str
        Path to the ARDF file (e.g., 'Foo.ardf').
    get_point : int
        Point number starting at 0. Use -1 to return the entire line.
    get_line : int
        Line number, starting at 0 (e.g., 0, 1, ..., 255).
    trace : int
        1 for trace, 0 for retrace.
    file_struct : dict
        Pre-parsed file structure from `read_ardf()` to improve read times.

    Returns:
    -------
    G : dict
        Dictionary containing the loaded force curve data.
    """

    has_file_struct = file_struct is not None

    
    if has_file_struct:
        # print("Using provided file structure for faster access.")
        F = file_struct['FileStructure']
    else:
        # print("No file structure provided, parsing from scratch.")
        F = read_ardf_metadata(filename)['FileStructure']
    
    # Intialize data structure
    G = {}

    
    with open(filename, 'rb') as fid:
        
        # =======================================
        # Get Desired Data
        # =======================================
        # Trace/retrace selection
        # If we have two volumes, choose the desired one
        if F['numbVolm'] > 1:
            if trace == F['volm1']['trace']:
                getVolm = 'volm1'
            else:
                getVolm = 'volm2'
        else:
            getVolm = 'volm1'

        # Get number of points
        numbPoints = F[getVolm]['vdef']['points']

        # If ScanDown, create an adjusted line index variable
        numbLines = F[getVolm]['vdef']['lines']
        if F[getVolm]['scanDown'] == 1:
            adjLine = numbLines - get_line - 1
        else:
            adjLine = get_line

        # Determine the number of data channels
        numbChannels = len(F['volm1']['vchn'])

        # Get location of first VSET in line
        # Code adapted from MATLAB
        # For python we dont need + 1
        # locLine = F[getVolm]['idx']['linPointer'][adjLine + 1]
        locLine = F[getVolm]['idx']['linPointer'][adjLine]

        # If data exists
        if locLine != 0:

            fid.seek(locLine, 0)

            # Initialize data arrays
            G = {
                'numbForce': [],
                'numbLine': [],
                'numbPoint': [],
                'locPrev': [],
                'locNext': [],
                'name': [],
                'y': [],
                'pnt0': [],
                'pnt1': [],
                'pnt2': []
            }

            for n in range(numbPoints):

                vset = local_read_vset(fid, -1)

                G['numbForce'].append(vset['force'])
                G['numbLine'].append(vset['line'])
                G['numbPoint'].append(vset['point'])
                G['locPrev'].append(vset['prev'])
                G['locNext'].append(vset['next'])

                vnam = local_read_vnam(fid, -1)
                G['name'].append(vnam['name'])
                

                theData = []

                for r in range(numbChannels):
                    vdat = local_read_vdat(fid, -1)
                    theData.append(vdat['data'])

                theData = np.column_stack(theData)

                local_read_xdat(fid, -1)

                theData = np.asarray(theData)
                if n != 0 and len(G['y']) != 0:
                    gy = np.array(G['y'])
                    if gy.ndim == 3:
                        rowsGy = gy.shape[0]
                    else:
                        rowsGy = gy.shape[0]
                    rowsDat = theData.shape[0]
                    if rowsGy != rowsDat:
                        maxRows = max(rowsGy, rowsDat)

                        if rowsGy < maxRows:
                            sizeGy = list(gy.shape)
                            sizeGy[0] = maxRows
                            newGy = np.zeros(sizeGy)
                            if len(sizeGy) > 2:
                                newGy[:rowsGy, :, :] = gy
                            else:
                                newGy[:rowsGy, :] = gy
                            G['y'] = newGy
                        else:
                            sizeDat = list(theData.shape)
                            sizeDat[0] = maxRows
                            newDat = np.zeros(sizeDat)
                            newDat[:rowsDat, :] = theData
                            theData = newDat

                G['y'] = np.dstack((G['y'], theData)) if len(G['y']) != 0 else theData[:, :, np.newaxis]

                G['pnt0'].append(vdat['pnt0'])
                G['pnt1'].append(vdat['pnt1'])
                G['pnt2'].append(vdat['pnt2'])

            # Flip each array if retrace data
            if G['numbPoint'][0] != 0:
                G['numbForce'] = G['numbForce'][::-1]
                G['numbLine'] = G['numbLine'][::-1]
                G['numbPoint'] = G['numbPoint'][::-1]
                G['locPrev'] = G['locPrev'][::-1]
                G['locNext'] = G['locNext'][::-1]
                G['name'] = G['name'][::-1]
                G['y'] = np.flip(G['y'], axis=2)
                G['pnt0'] = G['pnt0'][::-1]
                G['pnt1'] = G['pnt1'][::-1]
                G['pnt2'] = G['pnt2'][::-1]

            # If only a point desired, return only the point
            if get_point != -1:
                # again it is not needed in python bc we start counting at 0
                # get_point += 1
                G['numbForce'] = G['numbForce'][get_point]
                G['numbLine'] = G['numbLine'][get_point]
                G['numbPoint'] = G['numbPoint'][get_point]
                G['locPrev'] = G['locPrev'][get_point]
                G['locNext'] = G['locNext'][get_point]
                G['name'] = G['name'][get_point]
                G['y'] = G['y'][:, :, get_point]
                G['pnt0'] = G['pnt0'][get_point]
                G['pnt1'] = G['pnt1'][get_point]
                G['pnt2'] = G['pnt2'][get_point]
        else:
            G = {}

    fid.close()


    return G





"""
if __name__ == "__main__":
    filename = "/home/clotis/MyUnixWorkplace/exchange_work/format_UFF/test/ForceMap20.ARDF"
    my_D = read_ardf_metadata(filename)
    data = extract_ardf_data(filename, 1, 9, 1, my_D)

    
    # Tests
    import matplotlib
    matplotlib.use('Agg')  # I dont want GUI

    import matplotlib.pyplot as plt

    plt.figure(figsize=(6, 4))
    plt.plot(data['y'][:,2], data['y'][:,1], label='Defl vs Distance', marker='o')
    plt.plot(data['y'][:,2], deflection, label='Defl vs Distance', marker='o')
    plt.xlabel('Distance')
    plt.ylabel('Defl')
    plt.title('Force Curve')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    
    plt.savefig('force_curve_plot.png', dpi=300)
    """
