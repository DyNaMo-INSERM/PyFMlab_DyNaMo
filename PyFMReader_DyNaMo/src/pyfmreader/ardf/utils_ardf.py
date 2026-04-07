#!/usr/bin/env python3

""" The following script and functions are based on the work of Matheww Poss in MATLAB that can
be checked out here https://se.mathworks.com/matlabcentral/fileexchange/80212-ardf-to-matlab 

Created on Mon Apr 14 2025

@author: Carlota Carbajo """

import struct
import numpy as np

# =======================================
# readARDFpointer Function
# Reads ARDF pointer. All pointers have similar 16 byte header.
# =======================================

def local_read_ardf_pointer(fid, address):
    """
    Reads a 16-byte ARDF pointer structure from a binary file.

    Parameters:
        fid (file object): Opened binary file (use mode 'rb').
        address (int): Byte offset in the file. If -1, read from current position.

    Returns:
        check_crc32 (int): CRC-32 checksum.
        size_bytes (int): Byte size of section.
        type_pnt (str): 4-character pointer type.
        misc_num (int): Miscellaneous number.
    """
    if address != -1:
        fid.seek(address, 0)  # 0 means absolute positioning ('bof' in MATLAB)

    # Read and unpack data
    check_crc32 = struct.unpack('<I', fid.read(4))[0]       # uint32
    size_bytes = struct.unpack('<I', fid.read(4))[0]         # uint32
    type_pnt = fid.read(4).decode('ascii')                   # 4 chars
    misc_num = struct.unpack('<I', fid.read(4))[0]           # uint32

    return check_crc32, size_bytes, type_pnt, misc_num


# =======================================
# checkType Function
# 
# Verifies that pointer type is the expected type.
# =======================================
      
def local_check_type(found, expected, fid):
    if found != expected:
        location = fid.tell() - 16
        raise ValueError(f"ERROR: No {expected} here! Found: {found} Location: {location}")



# =======================================
# PARSE NOTESS Function
# =======================================

def parse_notes(nts):
    """
    Parses Asylum Research Notes into a structured dictionary.

    Parameters:
        nts (str): The raw note string.

    Returns:
        dict: A structured dictionary of note titles and their corresponding data.
    """
    nts_struct = {}
    size = len(nts)
    idx = 0

    pnt_title_start = 0
    pnt_title_end = 0
    pnt_first_colon = 0
    pnt_data_start = 0
    pnt_data_end = 0

    found = False

    while idx < size:
        # Check for the first colon
        if nts[idx] == ':' and not found:
            pnt_first_colon = idx
            pnt_title_end = idx - 1
            if idx + 1 < size and nts[idx + 1] == ' ':
                pnt_data_start = idx + 2
            else:
                pnt_data_start = idx + 1
            found = True

        # Check for carriage return (end of a note line)
        if ord(nts[idx]) == 13:  # 13 is carriage return '\r'
            pnt_data_end = idx - 1

            # Extract and clean the title
            temp_str = nts[pnt_title_start:pnt_title_end + 1]
            temp_str = ''.join(temp_str.split())  # Remove spaces
            temp_str = temp_str.replace('.', '')  # Remove periods

            # Extract data
            temp_ar = nts[pnt_data_start:pnt_data_end + 1]

            if found:
                # Make sure the title doesn't start with a number
                if not temp_str or temp_str[0].isdigit():
                    temp_str = 'n' + temp_str
                nts_struct[temp_str] = temp_ar

            # Reset for the next entry
            pnt_title_start = idx + 1
            found = False

        idx += 1

    return nts_struct



# =======================================
# readXDAT Function
# =======================================

def local_read_xdat(fid, address):
    if address != -1:
        fid.seek(address, 0)  # BOF

    _, lastSize, lastType, _ = local_read_ardf_pointer(fid, -1)

    if lastType not in ('XDAT', 'VSET'):
        current_pos = fid.tell()
        raise ValueError(f"ERROR: No XDAT or VSET here! Found: {lastType}  Location: {current_pos - 16}")

    if lastType == 'XDAT':
        stepDist = lastSize - 16
        fid.seek(stepDist, 1)  # COF
    elif lastType == 'VSET':
        fid.seek(-16, 1)  # COF


# =======================================
# readVDAT Function
# =======================================

def local_read_vdat(fid, address):
    if address != -1:
        fid.seek(address, 0)  # Seek from beginning of file (BOF)

    _, lastSize, lastType, _ = local_read_ardf_pointer(fid, -1)
    local_check_type(lastType, 'VDAT', fid)

    def read_uint32():
        return int.from_bytes(fid.read(4), 'little')

    def read_floats(count):
        return np.frombuffer(fid.read(4 * count), dtype='<f4')  # Little-endian single precision

    vdat = {}
    vdat['force'] = read_uint32()
    vdat['line'] = read_uint32()
    vdat['point'] = read_uint32()
    vdat['sizeData'] = read_uint32()

    vdat['forceType'] = read_uint32()
    vdat['pnt0'] = read_uint32()
    vdat['pnt1'] = read_uint32()
    vdat['pnt2'] = read_uint32()
    _ = [read_uint32() for _ in range(2)]  # dummy values

    vdat['data'] = read_floats(vdat['sizeData'])

    return vdat

# =======================================
# readVNAM Function
# =======================================

def local_read_vnam(fid, address):
    if address != -1:
        # Navigate to address
        fid.seek(address, 0)  # 'bof' equivalent

    # Read header and verify type
    dumCRC, lastSize, lastType, dumMisc = local_read_ardf_pointer(fid, -1)
    local_check_type(lastType, 'VNAM', fid)

    # Read data
    vnam = {}
    vnam['force'] = int.from_bytes(fid.read(4), 'little')
    vnam['line'] = int.from_bytes(fid.read(4), 'little')
    vnam['point'] = int.from_bytes(fid.read(4), 'little')
    vnam['sizeText'] = int.from_bytes(fid.read(4), 'little')
    vnam['name'] = fid.read(vnam['sizeText']).decode('utf-8')

    # Determine remaining size
    remainingSize = lastSize - 16 - vnam['sizeText'] - 16

    # Read remaining bytes into dummy variable
    dum = fid.read(remainingSize)

    return vnam



# =======================================
# readVSET Function
# =======================================

def local_read_vset(fid, address):
    vset = {}

    if address != -1:
        fid.seek(address)

    # Read header and verify type
    dum_crc, last_size, last_type, dum_misc = local_read_ardf_pointer(fid, -1)
    local_check_type(last_type, 'VSET', fid)

    # Read VSET data
    vset['force'] = int.from_bytes(fid.read(4), 'little')
    vset['line'] = int.from_bytes(fid.read(4), 'little')
    vset['point'] = int.from_bytes(fid.read(4), 'little')
    fid.read(4)  # Skip dum
    vset['prev'] = int.from_bytes(fid.read(8), 'little')
    vset['next'] = int.from_bytes(fid.read(8), 'little')

    return vset


# =======================================
# readDEF Function
# =======================================

def local_read_def(fid, address, expected_type):
    """
    Reads a DEF structure (IDEF or VDEF) from a binary file.

    Parameters:
        fid (file object): Opened binary file (in 'rb' mode).
        address (int): File position to seek to (-1 means current position).
        expected_type (str): Expected type ('IDEF' or 'VDEF').

    Returns:
        def_struct (dict): Dictionary with parsed DEF data.
    """
    if address != -1:
        fid.seek(address, 0)  # 'bof' equivalent in Python

    # Read DEF header, verify correct type
    dum_crc, size_def, type_def, dum_misc = local_read_ardf_pointer(fid, -1)
    local_check_type(type_def, expected_type, fid)

    # Read points and lines
    points = struct.unpack('<I', fid.read(4))[0]
    lines = struct.unpack('<I', fid.read(4))[0]

    # Set bytes to skip based on type
    if type_def == 'IDEF':
        skip = 96
    elif type_def == 'VDEF':
        skip = 144
    else:
        raise ValueError(f"Unknown DEF type: {type_def}")

    # Skip dummy bytes
    fid.read(skip)

    # Read 32 bytes as image title text
    size_text = 32
    image_title = fid.read(size_text).decode('ascii').rstrip('\x00')

    # Skip remaining dummy bytes
    size_head = 16
    remaining_size = size_def - 8 - skip - size_head - size_text
    fid.read(remaining_size)

    # Pack into dictionary
    def_struct = {
        'points': points,
        'lines': lines,
        'imageTitle': image_title
    }

    return def_struct


# =======================================
# readTEXT Entries
# =======================================


def local_read_text(fid, loc):
    # Navigate to the note section
    fid.seek(loc, 0)  # 0 = 'bof' in Python

    # Read the notes header, verify type
    dum_crc, dum_size, last_type, dum_misc = local_read_ardf_pointer(fid, -1)
    local_check_type(last_type, 'TEXT', fid)

    # Read the remainder of the header
    dum_misc = struct.unpack('<I', fid.read(4))[0]  # uint32
    size_note = struct.unpack('<I', fid.read(4))[0]  # uint32

    # Read the notes as characters and convert to string
    txt = fid.read(size_note).decode('latin-1')  # assuming UTF-8 encoded text

    return txt



# =======================================
# readTOC Function
# =======================================

def local_read_toc(fid, address, expected_type):
    null_case = '\x00\x00\x00\x00'

    if address != -1:
        fid.seek(address, 0)  # 'bof' equivalent is 0

    dum_crc, last_size, last_type, dum_misc = local_read_ardf_pointer(fid, -1)
    local_check_type(last_type, expected_type, fid)

    toc = {}

    # Read remaining TOC header (32-byte header assumed)
    toc['sizeTable'] = struct.unpack('<Q', fid.read(8))[0]  # uint64
    toc['numbEntry'] = struct.unpack('<I', fid.read(4))[0]  # uint32
    toc['sizeEntry'] = struct.unpack('<I', fid.read(4))[0]  # uint32

    size_entry = toc['sizeEntry']

    if size_entry == 24:
        toc.update({'pntImag': [], 'pntVolm': [], 'pntNext': [], 'pntNset': [], 'pntThmb': []})
    elif size_entry == 32:
        toc.update({'idxText': [], 'pntText': []})
    elif size_entry == 40:
        toc.update({'pntCounter': [], 'linCounter': [], 'linPointer': []})
    else:
        toc['data'] = []
        size_read = (size_entry - 16) // 4

    done = False
    numb_read = 1

    while not done and numb_read <= toc['numbEntry']:
        dum_crc, dum_size, type_entry, dum_misc = local_read_ardf_pointer(fid, -1)

        if size_entry == 24:
            last_pointer = struct.unpack('<Q', fid.read(8))[0]
        elif size_entry == 32:
            last_index = struct.unpack('<Q', fid.read(8))[0]
            last_pointer = struct.unpack('<Q', fid.read(8))[0]
        elif size_entry == 40:
            last_pnt_count = struct.unpack('<I', fid.read(4))[0]
            last_lin_count = struct.unpack('<I', fid.read(4))[0]
            dum = struct.unpack('<Q', fid.read(8))[0]
            last_lin_point = struct.unpack('<Q', fid.read(8))[0]
        else:
            last_data = list(struct.unpack('<' + 'f' * size_read, fid.read(4 * size_read)))

        if type_entry == 'IMAG':
            toc['pntImag'].append(last_pointer)
        elif type_entry == 'VOLM':
            toc['pntVolm'].append(last_pointer)
        elif type_entry == 'NEXT':
            toc['pntNext'].append(last_pointer)
        elif type_entry == 'NSET':
            toc['pntNset'].append(last_pointer)
        elif type_entry == 'THMB':
            toc['pntThmb'].append(last_pointer)
        elif type_entry == 'TOFF':
            toc['idxText'].append(last_index)
            toc['pntText'].append(last_pointer)
        elif type_entry == 'IDAT':
            toc['data'].extend(last_data)
        elif type_entry == 'VOFF':
            toc['pntCounter'].append(last_pnt_count)
            toc['linCounter'].append(last_lin_count)
            toc['linPointer'].append(last_lin_point)
        elif type_entry == null_case:
            if last_type == 'IBOX':
                toc['data'].extend(last_data)
            elif last_type == 'VTOC':
                toc['pntCounter'].append(last_pnt_count)
                toc['linCounter'].append(last_lin_count)
                toc['linPointer'].append(last_lin_point)
            else:
                done = True
        else:
            raise ValueError(f"ERROR: {type_entry} not recognized!")
        

        numb_read += 1

    return toc
