"""
Created on Thu Feb 11 13:56:01 2021

@author: Ismahene
"""

from nptdms import TdmsFile 
import numpy as np
import matplotlib.pyplot as plt
import os
import scipy.signal
from scipy.optimize import curve_fit  # For curve fitting
import pandas as pd
import statistics
from math import pi


def grab_tdms(directory):
    """
    This function gets all the tdms files of the directory
    and sorts them by time then returns the first file of
    the directory (the oldest file)
    Parameters
    ----------
    directory : str
        The directory selected by the user within the GUI

    Returns
    -------
    first_file: str
        The oldest file of the directory
    
    all_tdms : list of strings
        The list of all the tdms files of the directory

    """
    all_tdms=[]
    #get all the files of the directory and sort them by time
    files=sorted(os.scandir(directory), key=lambda d: d.stat().st_mtime)
    # loop over the files
    for entry in files: 
        #take only files that have tdms extension
        if  (entry.is_file() and entry.name.endswith('.tdms')):
            #append these files on a list
            all_tdms.append(entry.path)
    # select the first file 
    if not all_tdms:
        raise FileNotFoundError("No .tdms files found in the directory")
    first_file = all_tdms[0]
    # return the first file and all the list to facilitate the navigation
    return first_file, all_tdms


def parse_tdms(myfile, deflectionChannel='Deflection', zDisplacement = 'Z-pos', mainGroup = 'Force Curve'):
    """
    This function opens tdms file and extracts info

    Parameters
    ----------
    myfile : str
        the tdms file path
        
    deflectionChannel : str
        default = 'Deflection'
        Name of group channel string under 
    
    zDisplacement : str
        default = 'Z-pos'
        
    mainGroup : str
        default = 'Force Curve'

    Returns
    -------
    channel_data_deflection_v : numpy array

    channel_data_piezo_v : numpy array
    
    channel_time_ms : numpy array of time in index. ! need to convert !

    """
    with TdmsFile.open(myfile) as tdms_file:
        
        channel_piezo= tdms_file[mainGroup][zDisplacement]
        channel_data_piezo= channel_piezo[:]
        channel_deflection= tdms_file[mainGroup][deflectionChannel]
        channel_data_deflection= channel_deflection[:]
        channel_time = channel_deflection.time_track()
        

    #using 'with open' closes the file automatically at the end of the operation
    return channel_data_deflection, channel_data_piezo, channel_time


def process_tdms_file(myfile):
    """
    This function processes a TDMS file and extracts channel data and time information.

    Parameters
    ----------
    myfile : str
        The path to the TDMS file.

    Returns
    -------
    channel_dict : dict
        A dictionary with channel names as keys and channel data as values.
    time : numpy array
        An array containing the time information.
    """
    with TdmsFile.open(myfile) as tdms_file:  
        all_groups = tdms_file.groups()
        main_group = all_groups[0].name
        channels = tdms_file[main_group].channels()
        # print(f'all_groups: {all_groups[0]}')
        channel_dict = {}
        channel_names_dict = {}
        i = 0 
        for channel in channels:
            # print(f'channel: {channel.name}')   
            channel_dict[channel.name] = tdms_file[main_group][channel.name][:]   
            channel_names_dict[i] = tdms_file[main_group][channel.name].name
            i += 1
        # print(channel_dict)
        # print (channel_names_dict)
        dt = tdms_file[main_group][channel_names_dict[0]].properties["wf_increment"]
        time_us = tdms_file[main_group][channel_names_dict[0]].time_track()
        time = time_us*dt
    return channel_dict, time

def get_channel_names(myfile):
    """
    This function retrieves the channel names from a TDMS file.

    Parameters
    ----------
    myfile : str
        The path to the TDMS file.

    Returns
    -------
    channel_names_dict : dict
        A dictionary with channel indices as keys and channel names as values.
    main_group : str
        The name of the main group in the TDMS file.
    dt : float
        The waveform increment property of the first channel.
    """
    with TdmsFile.open(myfile) as tdms_file:  
        all_groups = tdms_file.groups()
        main_group = all_groups[0].name
        channels = tdms_file[main_group].channels()
        channel_names_dict = {}
        i = 0 
        for channel in channels:
            channel_names_dict[i] = tdms_file[main_group][channel.name].name
            i += 1
        dt = tdms_file[main_group][channel_names_dict[0]].properties["wf_increment"]
    return channel_names_dict, main_group, dt

def DeflectionInNanometer(channel_data_deflection, invOLS):
    """
    This function takes the deflection in Volts and 
    retunns the deflection in nanometer

    Parameters
    ----------
    channel_data_deflection : np array\
        The deflection in volts.
    invOLS : int
        

    Returns
    -------
    deflection: np array
        deflection in nanometer

    """
    deflection= channel_data_deflection *invOLS
    return deflection 


def GetForceDistAndParms(directory, channel_data_deflection, channel_data_piezo, time):

    """
    This function converts deflection & piezo mouvement
    and extract the information from the parameter file

    Parameters
    ----------
    directory : str
        the current directory containing the parameter file
    channel_data_deflection : np array
        a matrix containing the deflection data in volts.
    channel_data_piezo : np array
        a matrix containing the pizeo mouvement in volts.
    time : np array
        time array in whatever units the in input

    Returns
    -------
    distance : list
        the distance in nanometer (indentation/separation ).
    force : list
        the force in pN.
    K : float
        K represents the spring constant.
    invOLS : float
        (nm/V)
    Sensitivity: float
        in (nm/V).

    """

    for root, dirs, files in os.walk(os.path.abspath(directory)):
        #print("root", root)
        #print("directory", dirs)
        #print("files", files)
        for file in files:
            if file.endswith(".dat"):
                parms_file= os.path.join(os.path.abspath(root), file)
        break

    file = open(parms_file, "r")

    force= []
    distance= []
    approach=[]
    contact=[]
    retract=[]
    S1S2=[]
    S4S5=[]

    #print(file.readline())

    lines= file.readlines()
    #print(lines)
    for line in lines:
      #  print(line)
        if "Sensitivity" in line:
            sensitivity= float(line.split()[-1])
        elif "invOLS" in line:
            invOLS= float(line.split()[-1]) #unit: nm/V
        elif "K" in line:
            K= float(line.split()[-1]) #unit N/m
          #  print(K)
        elif "Piezo Gain" in line:
            piezo_gain= float(line.split()[-1])
        elif "Dec Factor (approach)" in line:
            real_sample_rate_approach= float(line.split()[-1])
        
        elif "Dec Factor (Retract)" in line:
            real_sample_rate_retract= float(line.split()[-1])

        elif "Dec Factor (Contact)" in line:
            dec_factor_contact= float(line.split()[-1])
                     
        elif line.startswith("S1"):
            S1S2.append(float(line.split()[-1]))

        elif line.startswith("S2"):
            S1S2.append(float(line.split()[-1]))
                
        elif line.startswith("S3"):
            S3_ms = (float(line.split()[-1]))
            
        elif line.startswith("S4"):
            S4S5.append(float(line.split()[-1]))

        elif line.startswith("S5"):
            S4S5.append(float(line.split()[-1])) 

        elif line.startswith("f1"):
            f0 = (float(line.split()[-1])) 

        elif line.startswith("f2"):
            f1 = (float(line.split()[-1]))    

        elif "WFM Type (Basic 0, Chirp 1)" in line:
            WFM_Type= (int(line.split()[-1]))
            print(WFM_Type)
 
        elif "Approach_S1S2" in line:
            approach_S1S2= float(line.split()[-1])

        elif "Approach_S2" in line:
            approach_S1S2= float(line.split()[-1])

        elif "Retract_S4S5" in line:
            retract_S4S5= float(line.split()[-1])

        elif "Retract_S4" in line:
            retract_S4S5= float(line.split()[-1])     

        elif line.startswith("Contact_S3"):
            contact_pts= float(line.split()[-1])

    file.close()

    for i in S1S2:
        approach.append(i*real_sample_rate_retract)
    coef= approach_S1S2/ sum(approach)   #ramener le resultat retract à Approach_S1S2 en multipliant par coeff
    approach[:] = [x * coef for x in approach]

  #  print("retract", retract)
    # time_retract =[]

    for i in S4S5:
        retract.append(i*real_sample_rate_approach)

    coef_contact= contact_pts / dec_factor_contact
    print(coef_contact, dec_factor_contact)

    coef= retract_S4S5/ sum(retract)
    retract[:] = [x * coef for x in retract]
    approach= sorted(approach)
    index_start_approach= int(approach[0])
   # index_end_approach= int(approach[1])
    index_end_approach=  int(approach_S1S2)
   # index_end_approach= int(retract[0])
   # print("approach S1S2", approach_S1S2)
    
    
    retract= sorted(retract)
   # index_start_retract= int(approach[1])
    index_start_retract= int(approach_S1S2)
   # index_start_retract= int(retract[0])
   # index_end_retract= int(retract[1])
    index_end_retract= len(channel_data_deflection)
    
    # print('S1S2', S1S2)
    # print('S4S5', S4S5)
    # print('retract S4S5', retract_S4S5)
    # print('approach S1S2', approach_S1S2)
    # print('start approach', index_start_approach)
    # print('end approach', index_end_approach)
    # print('start retract', index_start_retract)
    # print('end retract', index_end_retract)
    
    for i in channel_data_deflection:
        force.append( i * K *invOLS*1e+12*10**-9) #force in pN

    for i in channel_data_piezo:
        distance.append(i* sensitivity*piezo_gain ) #distance is in nm

    
    time[index_start_approach : index_end_approach]= np.flip(time[index_start_approach : index_end_approach]*real_sample_rate_approach )
    time[index_start_approach : index_end_approach]= time[index_start_approach : index_end_approach]- max(time[index_start_approach : index_end_approach])
   # print(abs(time[index_start_retract : index_end_retract][-1]))
        
    time[index_start_retract : index_end_retract]= time[index_start_retract : index_end_retract]*real_sample_rate_retract 




    return distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract, int(contact_pts),time



def GetForceDistAndParms_lv(directory, channel_data_deflection, channel_data_piezo, time):

    """
    This function converts deflection & piezo movement
    and extracts the information from the parameter file

    Parameters
    ----------
    directory : str
        the current directory containing the parameter file
    channel_data_deflection : np array
        a matrix containing the deflection data in volts.
    channel_data_piezo : np array
        a matrix containing the piezo movement in volts.
    time : np array
        time array in whatever units the input

    Returns
    -------
    distance : list
        the distance in nanometers (indentation/separation).
    force : list
        the force in pN.
    K : float
        K represents the spring constant.
    invOLS : float
        (nm/V)
    Sensitivity: float
        in (nm/V).
    parameters : dict
        A dictionary containing all extracted parameters.
    """

    import os
    import numpy as np

    for root, dirs, files in os.walk(os.path.abspath(directory)):
        for file in files:
            if file.endswith(".dat"):
                parms_file = os.path.join(os.path.abspath(root), file)
        break

    file = open(parms_file, "r")

    force = []
    distance = []
    approach = []
    contact = []
    retract = []
    S1S2 = []
    S4S5 = []
    
    parameters = {}  # Dictionary to store parameters

    lines = file.readlines()
    for line in lines:
        if line.strip():
            key_value = line.split("\t") if "\t" in line else line.split()
            if len(key_value) == 2:
                key, value = key_value
                try:
                    value = float(value) if '.' in value or 'e' in value.lower() else int(value)
                except ValueError:
                    pass
                parameters[key.strip()] = value

    file.close()

    # Extract essential parameters
    K = parameters.get("K (N/m)", 0.1)
    invOLS = parameters.get("invOLS (nm/V)", 50)
    sensitivity = parameters.get("Sensitivity (nm/V)", 10.4)
    piezo_gain = parameters.get("Piezo Gain", 2.085)
    real_sample_rate_approach = parameters.get("Dec Factor (approach)", 1000)
    real_sample_rate_retract = parameters.get("Dec Factor (Retract)", 1)
    dec_factor_contact = parameters.get("Dec Factor (Contact)", 1)
    contact_pts = parameters.get("Contact_S3", 200000)
    approach_S1S2 = parameters.get("Approach_S2", 220)
    retract_S4S5 = parameters.get("Retract_S4", 220000)

    for i in [parameters.get("S1", 0), parameters.get("S2", 0)]:
        S1S2.append(i)
        approach.append(i * real_sample_rate_retract)

    coef = approach_S1S2 / sum(approach)
    approach[:] = [x * coef for x in approach]

    for i in [parameters.get("S4", 0), parameters.get("S5", 0)]:
        S4S5.append(i)
        retract.append(i * real_sample_rate_approach)

    coef_contact = contact_pts / dec_factor_contact
    coef = retract_S4S5 / sum(retract)
    retract[:] = [x * coef for x in retract]

    approach = sorted(approach)
    index_start_approach = int(approach[0])
    index_end_approach = int(approach_S1S2)

    retract = sorted(retract)
    index_start_retract = int(approach_S1S2)
    index_end_retract = len(channel_data_deflection)

    for i in channel_data_deflection:
        force.append(i * K * invOLS * 1e+12 * 10 ** -9)  # force in pN

    for i in channel_data_piezo:
        distance.append(i * sensitivity * piezo_gain)  # distance in nm

    time[index_start_approach:index_end_approach] = np.flip(
        time[index_start_approach:index_end_approach] * real_sample_rate_approach)
    time[index_start_approach:index_end_approach] = time[index_start_approach:index_end_approach] - max(
        time[index_start_approach:index_end_approach])

    time[index_start_retract:index_end_retract] = time[index_start_retract:index_end_retract] * real_sample_rate_retract

    return distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract, int(contact_pts), time, parameters



# Calculate the value :
def calc_sine(x,a,b,c,d):
    #perms of sinus: amplitude, period, phase shif, vertical shift (a,b,c,d)
    #return a * np.sin(b* ( x + np.radians(c))) + d
    return a+b*np.sin(2*pi*x/c+d)

def CorrectVirtualDeflection( deflection, distance,  Npoly, index_start_approach, index_end_approach, index_start_retract, index_end_retract, percentage,  **kwargs):
    """
    Corrects virtual deflection from the approach curve only
    the percentage is taken from the end of the approach curve

    Parameters
    ----------
    deflection_approach : numpy array
        contains the deflection data of the approach curve.
    distance : list
        contains all distance values .
    percentage : 
        DESCRIPTION.

    Returns
    -------
    corrected_deflection_approach : TYPE
        DESCRIPTION.

    """
    
    #https://towardsdatascience.com/polynomial-regression-bbe8b9d97491

    dist_approach= distance[index_start_approach:index_end_approach]

    index_end= int(len(dist_approach)*(percentage/100))

    hysteresis = kwargs.get('hysteresis', 0)

    deflection_approach= deflection[index_start_approach: index_end_approach]


    
    if Npoly ==99:
        stdyp=statistics.stdev(deflection)
        distance[index_start_retract: index_end_retract]= np.array(distance[index_start_retract: index_end_retract]) - hysteresis

        popt, pcov = curve_fit(calc_sine, np.asarray(distance[index_start_approach: index_end_approach][: index_end]),
                      deflection_approach[: index_end],
                      bounds= ([min(deflection), 0, 200, -pi*2],
                               [max(deflection), 10*stdyp, 350, pi*2]))
        corrected_deflection=  deflection - calc_sine(np.asarray(distance),*popt)
        #print(popt)
        
        #Coefficient
    else:
       # p= P.fit(dist_approach[:index_end], deflection_approach[:index_end], Npoly)
        z = np.polyfit(dist_approach[:index_end], deflection_approach[:index_end], Npoly)
        p = np.poly1d(z)    #equation
    #print('equation ', p)
        distance[index_start_retract: index_end_retract]= np.array(distance[index_start_retract: index_end_retract]) - hysteresis
        corrected_deflection= deflection - p(distance)

    
    return  corrected_deflection #corrected_deflection_approach, corrected_deflection_retract



def CorrectDeflectionFromRetract(deflection, distance,  Npoly, index_start_approach, index_end_approach, index_start_retract, index_end_retract, percentage_retract, percentage_approach):
    """
    

    Parameters
    ----------
    deflection : array
        the deflection of the laser.
    distance : array
        the distance in nm.
    Npoly : int
        the order of the polynomial fitting.
    index_start_approach : int
        index of where the approach curve starts
    index_end_approach : int
        index of where the retract curve ends
    index_start_retract : int
        index of where the retract curve starts.
    index_end_retract : int
        index of where the retract curve ends
    percentage_retract : int
        percentage of retract curve to fit (from the end)
    percentage_approach : int
        percentage of approach curve to fit (from the end)

    Returns
    -------
    corrected deflection: array
        the corrected deflection after fitting

    """
    
    dist_approach= distance[index_start_approach:index_end_approach]
    deflection_approach= deflection[index_start_approach : index_end_approach]
    deflection_retract= deflection[index_start_retract : index_end_retract]
   
    index_end_a= int(len(dist_approach)*(percentage_approach/100))

    dist_retract= distance[index_start_retract:index_end_retract]

    index_end_r= len(deflection_retract) -  int(len(dist_retract)*(percentage_retract/100))


    if Npoly== 99:
    #optimal parameters
        meanyp= statistics.mean(deflection)
        stdyp=statistics.stdev(deflection)
        popt_approach, pcov_approach = curve_fit(calc_sine, distance[index_start_approach: index_end_approach][: index_end_a], 
                      deflection[index_start_approach: index_end_approach][: index_end_a],
                      bounds= ([min(deflection), 0, 200, -pi*2],
                               [max(deflection), 10*stdyp, 350, pi*2]))
        

        popt_retract, pcov_retract= curve_fit(calc_sine, distance[index_start_retract: index_end_retract][: index_end_r], 
                      deflection[index_start_retract: index_end_retract][: index_end_r],
                      bounds= ([min(deflection), 0, 200, -pi*2],
                               [max(deflection), 10*stdyp, 350, pi*2]))
        
        
        corrected_deflection= np.zeros(len(deflection))
        for i in range(len(deflection[index_start_retract: index_end_retract])):
            corrected_deflection[index_start_retract: index_end_retract][i]=  deflection_retract[i] - calc_sine(np.asarray(distance[index_start_retract: index_end_retract][i]),*popt_retract)
        
        for i in range(len(deflection[index_start_approach: index_end_approach])):
            corrected_deflection[index_start_approach: index_end_approach][i]=  deflection_approach[i] - calc_sine(np.asarray(distance[index_start_approach: index_end_approach][i]),*popt_approach)

        
    else:

        #Coefficient
        za = np.polyfit(dist_approach[:index_end_a], deflection_approach[:index_end_a], Npoly)
   #     print('coeff of polynomial', za) 
        pa = np.poly1d(za)    #equation
   #     print('equation ', pa)
    
       # corrected_deflection_approach= deflection_approach - pa(dist_approach)
        z = np.polyfit(dist_retract[index_end_r:], deflection_retract[index_end_r:], Npoly)
        p = np.poly1d(z)    #equation
        
        corrected_deflection= np.zeros(len(deflection))
        for i in range(len(deflection[index_start_retract: index_end_retract])):
            corrected_deflection[index_start_retract: index_end_retract][i]= deflection_retract[i]- p(distance[index_start_retract: index_end_retract][i])
        
        for i in range(len(deflection[index_start_approach: index_end_approach])):
            corrected_deflection[index_start_approach: index_end_approach][i]= deflection_approach[i] - pa(dist_approach[i])

        #corrected_deflection_retract= deflection_retract- p(distance[index_start_retract: index_end_retract])

   # return corrected_deflection_approach, corrected_deflection_retract
    return corrected_deflection

def ComputeExtension(force, distance, K):
    """

    Parameters
    ----------
    force : list
        force in pN.
    distance : list
        in nm.
    K : float
        N/m is converted in the code to pN/nm.

    Returns
    -------
    extension: list
        the extension is nm, mentionned as Tip Separation Surface in the GUI.

    """
    
    inter_dist=[]
    extension=[]
    for i in force:
        inter_dist.append(i/(K*10**3))
        
    extension= np.subtract(distance, inter_dist)
    #extension= extension + max(extension)
    
    return extension #in nm


def FDmodifParms(channel_data_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity):
    """
    When one of the parameters is modified on the GUI, 
    this function  is called to calculate the
    new values of force and distance

    Parameters
    ----------
    channel_data_deflection : TYPE
        DESCRIPTION.
    channel_data_piezo : TYPE
        DESCRIPTION.
    K : TYPE
        DESCRIPTION.
    invOLS : TYPE
        DESCRIPTION.
    piezo_gain : TYPE
        DESCRIPTION.
    sensitivity : TYPE
        DESCRIPTION.

    Returns
    -------
    distance : TYPE
        DESCRIPTION.
    force : TYPE
        DESCRIPTION.

    """
    force= []
    distance= []
    for i in channel_data_deflection:
        force.append( float(i) * float(K) *float(invOLS)*1e+12*10**-9) #force in pN

    for i in channel_data_piezo:
        distance.append(float(i)* float(sensitivity)* float(piezo_gain)) # distance here os in nanometer
       

    return distance, force

def props(cls):
    """
    Get all the properties of a given class

    Parameters
    ----------
    cls : TYPE
        DESCRIPTION.

    Returns
    -------
    list
        DESCRIPTION.

    """
    
    return [i for i in cls.__dict__.keys() if i[:1] != '_']


def ApplySavgol(data, window):
    """
    

    Parameters
    ----------
    data : np array
        the matrix containing data.
    window : int
        the window length, this number has to be greater than 3 (the order) and impair  .

    Returns
    -------
    smoothed : np array
        a matrix containing the smoothed data.

    """
    smoothed= scipy.signal.savgol_filter(data, window, 3) # window size 51, polynomial order 3
    return smoothed


def downsampling(data, pts):
    
    """
    Parameters
    ----------
    filepath : str
        array of data.

    Returns
    -------
    dict
        

    """
    data=np.array(data)
    l=len(data) #length of data
    new_sample=[]
    for i in range(0, l , pts):
        new_sample.append(data[i:i+pts])
    new_sample=pd.DataFrame(new_sample)
    return new_sample[0]


def read_parameter_file(filepath):
    """
    Parameters
    ----------
    filepath : str file path of .dat parameter file

    Returns
    -------
    parameters: dictionary of parameter files and their values in string
        

    """
    
    parameters = {}
    with open(filepath, 'r') as file:
        for line in file:
            # Skip empty lines
            if not line.strip():
                continue
            # Split the line by any whitespace characters (spaces, tabs, etc.)
            key_value = line.strip().split()
            
            # If the line has exactly two parts, treat it as key-value
            if len(key_value) == 2:
                key, value = key_value
                
                # Try to convert values to int or float if possible
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                
                parameters[key] = value
            else:
                # If the line doesn't match the expected pattern, store it as a string.
                parameters[line.strip()] = ""
    
    return parameters