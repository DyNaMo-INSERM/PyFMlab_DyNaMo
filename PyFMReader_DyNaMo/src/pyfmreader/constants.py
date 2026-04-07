# File containing constants used in the package.

# File extensions of files supported by this library
jpkfiles = ('jpk-force', 'jpk-force-map', 'jpk-qi-data','jpk-qi-series')        # As in 18-07-2022
jpk_h5_file = ('h5-jpk','JPK MultiScan Force Map Spectroscopy')                                        # As in 18-08-2025
nanoscfiles = ('spm', 'pfc')                                    # As in 18-07-2022
ufffiles = ('uff')                                              # As in 18-07-2022
jpkthermalfiles = ('tnd')                                       # As in 18-07-2022
psnexfiles = ('PSNEX.tdms')                      # As in 31.05.2024
hs3files = ( 'HS3.tdms')                      # As in 31.05.2024

ibwfiles = ('.ibw')                                             # As in 31.06.2025
ARDFfiles = ('.ARDF')                                           # As in 31.06.2025


# Default values for UFF (Universal File Format) files.
UFF_code = '_1_2_3_4_5'                                         # Default UFF code for V.0.1.1
UFF_version = '0'                                               # Default UFF version for V.0.1.1

# Defaults values for JPK file headers.
default_angle = 0                                               # in degrees
default_delay = 0                                               # in seconds
multiplier_default = 1                                          # no units
offset_default = 0                                              # no units
boolean_default = 'false'                                       # no units
num_segments_default = 2                                        # no units, asume approach-retract
scaling_factor = 1e9                                            # nanometer --> meter

# Hard coded values for JPK and Nanoscope files.
JPK_SETPOINT_MODE = 'Relative'                                  # JPK setpoint mode is always relative.                                           