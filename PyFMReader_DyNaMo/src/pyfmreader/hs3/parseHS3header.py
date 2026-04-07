
import os
from scipy.signal import decimate


#from ..constants import *

from nptdms import TdmsFile

def parseHS3header(filepath):
    """
    Function used to load the metadata of an HS3 file.

    Parameters:
        filepath (str): Path to the .tdms file.
    Returns:
        file_metadata (dict): Dictionary containing all the file metadata.
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
    
    # prepare holders
        file_metadata = {
            "file_path": filepath,
            "file_id": os.path.basename(filepath),
            'Entry_filename': os.path.basename(filepath)[:-4],  # remove .tdms
            "params_file": os.path.basename(params_file),
            "params_folder": directory,
            "file_size_bytes": os.path.getsize(filepath),
            'Entry_tot_nb_curve': 1,
            'num_segments': 3,
            'curve_id': 0,  
        }

    # defaults
    for line in lines:
        if line.startswith("Sensitivity"):
            file_metadata["sensitivity_nm_per_V"] = float(line.split()[-1])

        elif line.startswith("invOLS"):
            file_metadata["invOLS_nm_per_V"] = float(line.split()[-1])
            file_metadata["defl_sens_nmbyV"] = float(line.split()[-1])

        elif line.startswith("K"):
            file_metadata["spring_constant_N_per_m"] = float(line.split()[-1])
            file_metadata["spring_const_Nbym"] = float(line.split()[-1])

        elif line.startswith("f1"):
            file_metadata["chirp_start_Hz"] = float(line.split()[-1])
        
        elif line.startswith("f2"):
            file_metadata["chirp_end_Hz"] = float(line.split()[-1])
        
        elif line.startswith("Piezo Gain"):
            file_metadata["piezo_gain"] = float(line.split()[-1])
        
        elif line.startswith("Dec Factor (approach)"):
            file_metadata["dec_factor_approach"] = float(line.split()[-1])
        
        elif line.startswith("Dec Factor (Contact)"):
            file_metadata["dec_factor_contact"] = float(line.split()[-1])
        
        elif line.startswith("Dec Factor (Retract)"):
            file_metadata["dec_factor_retract"] = float(line.split()[-1])
        
        elif line.startswith("S1\t") or line.startswith("S1 "):
            file_metadata["S1_ms"]=float(line.split()[-1])

        
        elif line.startswith("S2\t") or line.startswith("S2 "):
            file_metadata["S2_ms"]=float(line.split()[-1])
        
        elif line.startswith("S3\t") or line.startswith("S3 "):
            file_metadata["S3_ms"]=float(line.split()[-1])

        
        elif line.startswith("S4\t") or line.startswith("S4 "):
            file_metadata["S4_ms"]=float(line.split()[-1])
        
        elif line.startswith("S5\t") or line.startswith("S5 "):
            file_metadata["S5_ms"]=float(line.split()[-1])
        
        elif "WFM Type" in line:
            file_metadata["force_curve_type"] = int(line.split()[-1])
        
        elif line.startswith("Approach_S2"):
            file_metadata["approach_points"] = int(line.split()[-1])
        
        elif line.startswith("Approach_S1S2"):
            file_metadata["approach_points"] = int(line.split()[-1])
        
        elif line.startswith("Contact_S3"):
            file_metadata["dwell_points"] = int(line.split()[-1])
        
        elif line.startswith("Retract_S4"):
            file_metadata["retract_points"] = int(line.split()[-1])
        
        elif line.startswith("Retract_S4S5"):
            file_metadata["retract_points"] = int(line.split()[-1])
        
        elif line.startswith("Reading Sample Rate"):
            file_metadata["reading_sample_rate_Hz"] = float(line.split()[-1])

        
        elif line.startswith("V1\t") or line.startswith("V1 "):
            file_metadata["V1"]=float(line.split()[-1])
        
        elif line.startswith("V3\t") or line.startswith("V3 "):
            file_metadata["V3"]=float(line.split()[-1])
        
        elif line.startswith("V5\t") or line.startswith("V5 "):
            file_metadata["V5"]=float(line.split()[-1])
        


    
    return file_metadata

