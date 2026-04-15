
# import os
# # from scipy.signal import decimate


# #from ..constants import *

# # from nptdms import TdmsFile

# def parseHS3header(filepath):
#     """
#     Function used to load the metadata of an HS3 file.

#     Parameters:
#         filepath (str): Path to the .tdms file.
#     Returns:
#         file_metadata (dict): Dictionary containing all the file metadata.
#     """
#     # 1) Find the .dat file in the same directory
#     directory = os.path.dirname(filepath)
#     params_file = None
#     for root, dirs, files in os.walk(directory):
#         for fn in files:
#             if fn.lower().endswith(".dat"):
#                 params_file = os.path.join(root, fn)
#                 break
#         if params_file:
#             break

#     if params_file is None:
#         raise FileNotFoundError(f"No .dat file found in {directory}")
    
#     # 2) Read and parse the .dat file
#     with open(params_file, "r") as f:
#         lines = [l.strip() for l in f if l.strip()]
    
#     # prepare holders
#     S1S2 = []; S3 = []; S4S5 = []
#     file_metadata = {
#         "file_path": filepath,
#         "params_file":    os.path.basename(params_file),
#         "params_folder":  directory,
#         "file_size_bytes": os.path.getsize(filepath),
#         "Entry_filename": os.path.split(filepath)[-1]
#     }
#     file_metadata["height_channel_key"] = "Piezo"
#     file_metadata["deflection_channel_key"] = "Deflection"   

#     # defaults
#     for line in lines:
#         if line.startswith("Sensitivity"):
#             file_metadata["defl_sens_nmbyV"] = float(line.split()[-1])

#         elif line.startswith("invOLS"):
#             file_metadata["invOLS_nm_per_V"] = float(line.split()[-1])
        
#         elif line.startswith("K"):
#             file_metadata["spring_const_Nbym"] = float(line.split()[-1])
        
#         elif line.startswith("f1"):
#             file_metadata["chirp_start_Hz"] = float(line.split()[-1])
        
#         elif line.startswith("f2"):
#             file_metadata["chirp_end_Hz"] = float(line.split()[-1])
        
#         elif line.startswith("Piezo Gain"):
#             file_metadata["piezo_gain"] = float(line.split()[-1])
        
#         elif line.startswith("Dec Factor (approach)"):
#             file_metadata["dec_factor_approach"] = float(line.split()[-1])
        
#         elif line.startswith("Dec Factor (Contact)"):
#             file_metadata["dec_factor_contact"] = float(line.split()[-1])
        
#         elif line.startswith("Dec Factor (Retract)"):
#             file_metadata["dec_factor_retract"] = float(line.split()[-1])
        
#         elif line.startswith("S1\t") or line.startswith("S1 "):
#             S1S2.append(float(line.split()[-1]))
        
#         elif line.startswith("S2\t") or line.startswith("S2 "):
#             S1S2.append(float(line.split()[-1]))
        
#         elif line.startswith("S3\t") or line.startswith("S3 "):
#             S3.append(float(line.split()[-1]))
        
#         elif line.startswith("S4\t") or line.startswith("S4 "):
#             S4S5.append(float(line.split()[-1]))
        
#         elif line.startswith("S5\t") or line.startswith("S5 "):
#             S4S5.append(float(line.split()[-1]))
        
#         elif "WFM Type" in line:
#             file_metadata["force_curve_type"] = int(line.split()[-1])
        
#         elif line.startswith("Approach_S2"):
#             file_metadata["approach_points"] = int(line.split()[-1])
        
#         elif line.startswith("Approach_S1S2"):
#             file_metadata["approach_points"] = int(line.split()[-1])
        
#         elif line.startswith("Contact_S3"):
#             file_metadata["dwell_points"] = int(line.split()[-1])
        
#         elif line.startswith("Retract_S4"):
#             file_metadata["retract_points"] = int(line.split()[-1])
        
#         elif line.startswith("Retract_S4S5"):
#             file_metadata["retract_points"] = int(line.split()[-1])
        
#         elif line.startswith("Reading Sample Rate"):
#             file_metadata["reading_sample_rate_Hz"] = float(line.split()[-1])

#     # assemble S1,S2,S3,S4,S5 if present
#     if len(S1S2) == 2:
#         file_metadata["S1_ms"], file_metadata["S2_ms"] = S1S2
#     if len(S3) == 1:
#         file_metadata["S3_ms"] = S3[0]
#     if len(S4S5) == 2:
#         file_metadata["S4_ms"], file_metadata["S5_ms"] = S4S5

    
#     return file_metadata



import os
import logging

logger = logging.getLogger(__name__)

def parseHS3header(filepath):
    """
    Function used to load the metadata of an HS3 file.

    Parameters:
        filepath (str): Path to the .tdms file.
    Returns:
        file_metadata (dict): Dictionary containing all the file metadata.
    Raises:
        FileNotFoundError: If no .dat file found in the same directory
        ValueError: If required metadata fields are missing
    """
    # 1) Find the .dat file in the same directory
    directory = os.path.dirname(filepath)
    params_file = None
    for root, dirs, files in os.walk(directory):
        for fn in files:
            if fn.lower().endswith(".dat"):
                params_file = os.path.join(root, fn)
                break
        if params_file:
            break

    if params_file is None:
        raise FileNotFoundError(f"No .dat file found in {directory}")
    
    # 2) Read and parse the .dat file
    with open(params_file, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    
    logger.debug(f"Parsing HS3 metadata from: {params_file}")
    
    # prepare holders
    S1S2 = []; S3 = []; S4S5 = []
    file_metadata = {
        "file_path": filepath,
        "params_file":    os.path.basename(params_file),
        "params_folder":  directory,
        "file_size_bytes": os.path.getsize(filepath),
        "Entry_filename": os.path.split(filepath)[-1]
    }
    file_metadata["height_channel_key"] = "Piezo"
    file_metadata["deflection_channel_key"] = "Deflection"   

    # Parse all lines - be flexible with whitespace
    for line in lines:
        # Skip comments
        if line.startswith("#"):
            continue
            
        try:
            if "Sensitivity" in line and "Sensitivity" == line.split()[0]:
                file_metadata["defl_sens_nmbyV"] = float(line.split()[-1])

            elif "invOLS" in line and "invOLS" == line.split()[0]:
                file_metadata["invOLS_nm_per_V"] = float(line.split()[-1])
            
            elif line.startswith("K\t") or (line.startswith("K ") and len(line.split()) >= 2):
                file_metadata["spring_const_Nbym"] = float(line.split()[-1])
            
            elif "f1" in line and "f1" == line.split()[0]:
                file_metadata["chirp_start_Hz"] = float(line.split()[-1])
            
            elif "f2" in line and "f2" == line.split()[0]:
                file_metadata["chirp_end_Hz"] = float(line.split()[-1])
            
            elif "Piezo Gain" in line:
                file_metadata["piezo_gain"] = float(line.split()[-1])
            
            elif "Dec Factor" in line and "approach" in line.lower():
                file_metadata["dec_factor_approach"] = float(line.split()[-1])
            
            elif "Dec Factor" in line and "contact" in line.lower():
                file_metadata["dec_factor_contact"] = float(line.split()[-1])
            
            elif "Dec Factor" in line and "retract" in line.lower():
                file_metadata["dec_factor_retract"] = float(line.split()[-1])
            
            elif line[0] == "S" and len(line.split()) >= 2:
                s_num = line.split()[0]  # Get "S1", "S2", etc.
                value = float(line.split()[-1])
                
                if s_num == "S1":
                    S1S2.append(value)
                elif s_num == "S2":
                    S1S2.append(value)
                elif s_num == "S3":
                    S3.append(value)
                elif s_num == "S4":
                    S4S5.append(value)
                elif s_num == "S5":
                    S4S5.append(value)
            
            elif "WFM Type" in line:
                file_metadata["force_curve_type"] = int(line.split()[-1])
            
            elif "Approach" in line and "points" in line.lower():
                file_metadata["approach_points"] = int(line.split()[-1])
            
            elif "Contact" in line and "points" in line.lower():
                file_metadata["dwell_points"] = int(line.split()[-1])
            
            elif "Retract" in line and "points" in line.lower():
                file_metadata["retract_points"] = int(line.split()[-1])
            
            elif "Reading Sample Rate" in line or "Sample Rate" in line.lower():
                file_metadata["reading_sample_rate_Hz"] = float(line.split()[-1])
        
        except (ValueError, IndexError) as e:
            logger.warning(f"Could not parse line: {line}. Error: {e}")
            continue

    # assemble S1,S2,S3,S4,S5 if present
    if len(S1S2) == 2:
        file_metadata["S1_ms"], file_metadata["S2_ms"] = S1S2
    if len(S3) == 1:
        file_metadata["S3_ms"] = S3[0]
    if len(S4S5) == 2:
        file_metadata["S4_ms"], file_metadata["S5_ms"] = S4S5

    # Validate required fields
    required_fields = [
        "defl_sens_nmbyV",
        "invOLS_nm_per_V", 
        "spring_const_Nbym",
        "dec_factor_approach",
        "dec_factor_contact",
        "dec_factor_retract",
        "S1_ms",
        "S2_ms",
        "S3_ms",
        "S4_ms",
        "S5_ms",
        "reading_sample_rate_Hz"
    ]
    
    missing_fields = [f for f in required_fields if f not in file_metadata]
    if missing_fields:
        logger.error(f"Missing required metadata fields: {missing_fields}")
        logger.error(f"Parsed metadata keys: {list(file_metadata.keys())}")
        raise ValueError(
            f"Failed to parse HS3 metadata. Missing fields: {missing_fields}. "
            f"Check that the .dat file contains all required parameters.\n"
            f"Parsed from: {params_file}"
        )
    
    logger.debug(f"Successfully parsed HS3 metadata with {len(file_metadata)} fields")
    return file_metadata