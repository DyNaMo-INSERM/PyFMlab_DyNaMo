#!/usr/bin/env python3

""" The following script and functions are based on the work of Matheww Poss in MATLAB that can
be checked out here https://se.mathworks.com/matlabcentral/fileexchange/80212-ardf-to-matlab 

Created on Mon Apr 14 2025

@author: Carlota Carbajo """

import os
import numpy as np
from .utils_ardf import *

def read_ardf_metadata(filename):
    """
    Reads basic metadata and header from an Asylum Research ARDF file into a dictionary.
    Does NOT load force curves. Use get_ardf_data() for detailed data extraction.
    
    Parameters:
        filename (str): Path to the ARDF file.
    
    Returns:
        dict: Dictionary D containing ARDF metadata.
    """
    D = {}
    D["FileName"] = os.path.splitext(os.path.basename(filename))[0]
    D["FileType"] = "ARDF"

    # =======================================
    # ARDF: Asylum Research Data File
    # Read file header
    # =======================================

    # Open file in binary read mode
    with open(filename, 'rb') as fid:
        # Read file header (pointer at offset 0)
        dum_crc, dum_size, last_type, dum_misc = local_read_ardf_pointer(fid, 0)
        local_check_type(last_type, "ARDF", fid)

    
        # =======================================
        # FTOC: File Table of Contents
        # =======================================

        # Read FTOC table
        F = {}
        F['ftoc'] = local_read_toc(fid, -1, 'FTOC')

        # =======================================
        # TTOC: Text Table of Contents
        # =======================================

        # Read TTOC Table
        loc_TTOC = F['ftoc']['sizeTable'] + 16
        F['ttoc'] = local_read_toc(fid, loc_TTOC, 'TTOC')


        # =======================================
        # Read Main Notes
        # =======================================

        # Determine number of main notes to read
        F['ttoc']['numbNotes'] = len(F['ttoc']['pntText'])

        # Assuming a single main note
        # Read note
        note_main = local_read_text(fid, F['ttoc']['pntText'][0])

        # Parse Note
        # D['Notes'] = parse_notes(note_main)


        # =======================================
        # IMAG: Images
        # =======================================

        # Determine number of images to import
        F['numbImag'] = len(F['ftoc']['pntImag'])

        # Initialize data arrays
        D['imageList'] = []
        D['y'] = []

        # Import all images
        for n in range(F['numbImag']):
            imag_key = f"imag{n + 1}"

            # * * * * * * * * * * * * *
            # IMAG header
            F[imag_key] = local_read_toc(fid, F['ftoc']['pntImag'][n], 'IMAG')

            # * * * * * * * * * * * * *
            # IMAG-TTOC header
            loc_imag_ttoc = F['ftoc']['pntImag'][n] + F[imag_key]['sizeTable']
            F[imag_key]['ttoc'] = local_read_toc(fid, loc_imag_ttoc, 'TTOC')

            # * * * * * * * * * * * * *
            # IDEF header
            loc_imag_idef = F['ftoc']['pntImag'][n] + F[imag_key]['sizeTable'] + F[imag_key]['ttoc']['sizeTable']
            F[imag_key]['idef'] = local_read_def(fid, loc_imag_idef, 'IDEF')


            # Add to imageList
            D['imageList'].append(F[imag_key]['idef']['imageTitle'])

            # * * * * * * * * * * * * *
            # IBOX & IDAT image data
            idat = local_read_toc(fid, -1, 'IBOX')

            image_data = np.array(idat['data'])

            # If it's 1D, reshape it (example: to 5x10)
            if image_data.ndim == 1:
                expected_height = F[imag_key]['idef']['lines']
                expected_width = F[imag_key]['idef']['points']
                image_data = image_data.reshape((expected_height, expected_width))

            # Add 3rd dimension for stacking
            image_data = image_data[..., None]

            # Write IDAT data to image array
            if 'y' not in D or len(D['y']) == 0:
                D['y'] = image_data  # Initialize with first image
            else:
                D['y'] = np.concatenate((D['y'], image_data), axis=2)


            # Read closing IMAG header (GAMI), verify header type
            dum_crc, dum_size, last_type, dum_misc = local_read_ardf_pointer(fid, -1)
            local_check_type(last_type, 'GAMI', fid)

            # * * * * * * * * * * * * *
            # IMAG-TEXT
            numb_imag_text = len(F[imag_key]['ttoc']['pntText'])

            for r in range(numb_imag_text):
                the_note = local_read_text(fid, F[imag_key]['ttoc']['pntText'][r])

                # Mimic MATLAB's `contains` and replacement
                if '[' in the_note:
                    the_note = the_note.replace('[', '').replace(']', '')

                # Assign note logic
                if numb_imag_text > 1 or n == 0:
                    if r == 0:
                        note_thumb = the_note
                    elif r == 1:
                        F[imag_key]['note'] = parse_notes(the_note)
                    elif r == 2:
                        note_quick = the_note
                else:
                    F[imag_key]['note'] = parse_notes(the_note)

        # End of image import loop

        # =======================================
        # NOTES: Parse and save
        # =======================================

        the_note = note_main  # Start with note_main

        # Check if note_quick exists (not None)
        if 'note_quick' in locals() and note_quick is not None:
            the_note = note_main + note_thumb + note_quick
        elif 'note_thumb' in locals() and note_thumb is not None:
            the_note = note_main + note_thumb

        # Parse the note
        D['Notes'] = parse_notes(the_note)


        # =======================================
        # VOLM: Force Curve Data
        # =======================================

        # Determine number of volumes
        F['numbVolm'] = len(F['ftoc']['pntVolm'])

        # Initialize data arrays
        D['channelList'] = []

        # Import header data and pointers for each volume
        for n in range(F['numbVolm']):
            volm_key = f"volm{n + 1}"

            # * * * * * * * * * * *
            # VOLM Header
            F[volm_key] = local_read_toc(fid, F['ftoc']['pntVolm'][n], 'VOLM')

            # * * * * * * * * * * *
            # VOLM-TTOC
            loc_volm_ttoc = F['ftoc']['pntVolm'][n] + F[volm_key]['sizeTable']
            F[volm_key]['ttoc'] = local_read_toc(fid, loc_volm_ttoc, 'TTOC')

            # * * * * * * * * * * *
            # VOLM-VDEF
            loc_vdef_imag = F['ftoc']['pntVolm'][n] + F[volm_key]['sizeTable'] + F[volm_key]['ttoc']['sizeTable']
            F[volm_key]['vdef'] = local_read_def(fid, loc_vdef_imag, 'VDEF')

            # * * * * * * * * * * *
            # VOLM-VCHN & VOLM-XDEF
            F[volm_key]['vchn'] = []
            F[volm_key]['xdef'] = {}

            done = False
            while not done:
                dum_crc, last_size, last_type, dum_misc = local_read_ardf_pointer(fid, -1)

                if last_type == 'VCHN':
                    text_size = 32
                    the_channel = ''.join(map(chr, fid.read(text_size)))
                    F[volm_key]['vchn'].append(the_channel)

                    remaining_size = last_size - 16 - text_size
                    fid.read(remaining_size)

                elif last_type == 'XDEF':
                    fid.read(4)  # uint32
                    F[volm_key]['xdef']['sizeTable'] = int.from_bytes(fid.read(4), 'little')
                    size_table = F[volm_key]['xdef']['sizeTable']
                    F[volm_key]['xdef']['text'] = ''.join(map(chr, fid.read(size_table)))

                    remaining = last_size - 16 - 8 - size_table
                    fid.read(remaining)

                    done = True

                else:
                    raise ValueError(f"ERROR: {last_type} not recognized!")

            # Write channel list data to structure
            D['channelList'].append(F[volm_key]['vchn'])

            # * * * * * * * * * * *
            # VOLM-VTOC & VOLM-VOFF
            F[volm_key]['idx'] = local_read_toc(fid, -1, 'VTOC')

            # * * * * * * * * * * *
            # VOLM-MLOV
            dum_crc, last_size, last_type, dum_misc = local_read_ardf_pointer(fid, -1)
            local_check_type(last_type, 'MLOV', fid)

            # * * * * * * * * * * *
            # VOLM-VSET
            for r in [1, F[volm_key]['vdef']['lines']]:
                vset_key = f"vset{r}"
                loc = F[volm_key]['idx']['linPointer'][r - 1]

                if loc != 0:
                    F[volm_key].setdefault('line', {})[vset_key] = local_read_vset(fid, loc)

                    line = F[volm_key]['line'][vset_key]['line']
                    point = F[volm_key]['line'][vset_key]['point']

                    F[volm_key]['scanDown'] = 1 if line != (r - 1) else 0
                    F[volm_key]['trace'] = 1 if point == 0 else 0

            # =======================================
            # Partial File Handling
            # =======================================
            idx_zero = [i for i, p in enumerate(F[volm_key]['idx']['linPointer']) if p == 0]

            inc_min = 1
            inc_max = 0

            if F[volm_key].get('scanDown', 0) == 1:
                lines = F[volm_key]['vdef']['lines']
                idx_zero = [lines - i for i in idx_zero]
                inc_min = 0
                inc_max = 1

        # After the loop — Partial file handling continued
        if idx_zero:
            idx_zero_min = min(idx_zero) - inc_min
            idx_zero_max = max(idx_zero) + inc_max

            # Delete zero rows from D['y']
            if isinstance(D['y'], np.ndarray):
                D['y'] = np.delete(D['y'], slice(idx_zero_min, idx_zero_max + 1), axis=1)

        # =======================================
        # THMB: Thumbnails
        # =======================================

        # Do nothing with these.

        # =======================================
        # User Notes
        # =======================================

        # Parse user notes from UserData.csv
        # user_file_name = 'UserData.csv'
        # if os.path.isfile(user_file_name):
        #     D['userNotes'] = parse_user_data(D['FileName'], user_file_name)
        # else:
        #     raise FileNotFoundError(f"No {user_file_name} file found!")

        # Add additional notes
        D['endNote'] = {}
        D['endNote']['IsImage'] = '1'

        # =======================================
        # Detailed File Information
        # =======================================

        # Write file structure information to Python dictionary
        D['FileStructure'] = F

        # Close the file
        fid.close()



    return D



