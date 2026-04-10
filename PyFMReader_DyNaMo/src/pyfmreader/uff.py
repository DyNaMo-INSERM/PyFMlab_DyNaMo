# File containing the UFF class.
# Used to store data and metadata.

from zipfile import ZipFile

from .constants import *
from .jpk.loadjpkcurve import loadJPKcurve
from .jpk.loadjpkimg import computeJPKPiezoImg
from .jpk_h5.jpkh5piezoimg import computeJPKPiezoImg_h5
from .jpk_h5.loadjpkh5curve import loadJPKh5curve

from .nanosc.loadnanosccurve import loadNANOSCcurve
from .nanosc.loadnanoscimg import loadNANOSCimg
from .ps_nex.loadpsnexcurve import loadPSNEXcurve
from .hs3.loadHS3curve import loadHS3curve
from .ardf.loadARDFcurve import loadARDFcurve
from .ardf.loadARDFimg import loadARDFimg
from .ardf.loadibwcurve import loadIBWcurve
from .load_uff import loadUFFcurve
from .save_uff import saveUFFtxt


class UFF:
    """
    Class used to store the data and metadata of an AFM file.

            Properties:
                    filemetadata (dict): Dictionary containing the file metadata.
                    isFV (bool): Flag indicating if the file is a Force Volume or not.
                    piezoimg (np.array): 2D np.array containing the piezo image of the file.
                    imagedata (dict): dictionary containing additional image data.

            Methods:
                    getcurve
                    getpiezoimg
                    to_txt

    """

    def __init__(self):
        self.filemetadata = None
        # JPK Specific Atributes
        self._sharedataprops = None
        self._groupedpaths = None
        # FV Specific Atribtues
        self.isFV = None
        self.piezoimg = None
        # In files like JPK scans you may
        # have additional image data.
        self.imagedata = None
        self.bool_correct_overshoot = False
        self._curve_cache = None  # Cache for loaded curves to avoid reloading 

    def _loadcurve(self, curveidx, afmfile, file_type):
        """
        Hidden function used to load a single curve from a file.
        bool_correct_overshoot is used to correct the overshoot in PS-NEX files.

        Supported formats:
            - JPK --> .jpk-force, .jpk-force-map, .jpk-qi-data
            - NANOSCOPE --> .spm, .pfc
            - UFF --> .uff
            - PS-NEX --> .tdms
            - HS-3 --> .tdms
            - IBW --> .ibw
            - ARDF --> .ARDF

                Parameters:
                        curveidx (int): Index of curve to load.
                        afmfile (ZipFile): Buffer containing the data of the AFM file. Only used for JPK files.
                        file_type (str): File extension.
                        bool_correct_overshoot (bool): Flag indicating whether to correct overshoot.

                Returns:
                        FC (utils.forcecurve.ForceCurve): ForceCurve object containing the force curve data.
        """
        if file_type in jpkfiles:
            curvepaths = self._groupedpaths[curveidx]
            FC = loadJPKcurve(
                curvepaths, afmfile, curveidx, self.filemetadata
            )
        elif file_type in jpk_h5_file:
            FC = loadJPKh5curve(self.filemetadata, curveidx)
        elif file_type[1:].isdigit() or file_type in nanoscfiles:
            FC = loadNANOSCcurve(curveidx, self.filemetadata)
        elif file_type in ufffiles:
            FC = loadUFFcurve(self.filemetadata)
        elif file_type in psnexfiles:
            FC = loadPSNEXcurve(self.filemetadata, curveidx, bool_correct_overshoot=self.bool_correct_overshoot)
        elif file_type in hs3files:
            FC = loadHS3curve(self.filemetadata, curveidx, bool_correct_overshoot=False)
        elif file_type in ibwfiles:
            FC = loadIBWcurve(self.filemetadata, curveidx)
        elif file_type in ARDFfiles:
            FC = loadARDFcurve(self.filemetadata, curveidx)
        return FC

    def getcurve(self, curveidx, bool_correct_overshoot=False):
        """
        Function used to load a single curve from a file.

        Supported formats:
            - JPK --> .jpk-force, .jpk-force-map, .jpk-qi-data
            - NANOSCOPE --> .spm, .pfc
            - UFF --> .uff
            - PS-NEX --> .tdms
            - HS-3 --> .tdms
            - IBW --> .ibw
            - ARDF --> .ARDF

                Parameters:
                        curveidx (int): Index of curve to load.
                        bool_correct_overshoot (bool): Flag indicating whether to correct overshoot.

                Returns:
                        FC (utils.forcecurve.ForceCurve): ForceCurve object containing the force curve data.
        """
        # Check if bool_correct_overshoot changed state
        if self.bool_correct_overshoot != bool_correct_overshoot:
            self._curve_cache = None  # Clear cache if correction state changes
        
        self.bool_correct_overshoot = bool_correct_overshoot
        file_type = self.filemetadata['file_type']
        
        if file_type in jpkfiles:
            with open(self.filemetadata['file_path'], 'rb') as file:
                afmfile = ZipFile(file)
                curvepaths = self._groupedpaths[curveidx]
                FC = loadJPKcurve(
                    curvepaths, afmfile, curveidx, self.filemetadata)
            
        elif file_type in jpk_h5_file:
            FC = loadJPKh5curve(self.filemetadata, curveidx)
        elif file_type[1:].isdigit() or file_type in nanoscfiles:
            FC = loadNANOSCcurve(curveidx, self.filemetadata)
        elif file_type in ufffiles:
            FC = loadUFFcurve(self.filemetadata)
        elif file_type in psnexfiles:
            if self._curve_cache is not None and self.bool_correct_overshoot == bool_correct_overshoot:
                # If curve is already cached with same correction state, return it
                FC = self._curve_cache
            else:
                FC = loadPSNEXcurve(self.filemetadata, curveidx, bool_correct_overshoot=self.bool_correct_overshoot)
                self._curve_cache = FC
        elif file_type in hs3files:
            FC = loadHS3curve(self.filemetadata, curveidx, bool_correct_overshoot=bool_correct_overshoot)
        elif file_type in ibwfiles:
            FC = loadIBWcurve(self.filemetadata, curveidx)
        elif file_type in ARDFfiles:
            FC = loadARDFcurve(self.filemetadata, curveidx)
        
        return FC

    def getpiezoimg(self):
        """
        Function used to compute the piezo image of a file.

        It is required that the file is a Force Volume.

        Supported formats:
            - JPK --> .jpk-force-map, .jpk-qi-data
            - JPK H5 --> .h5-jpk
            - NANOSCOPE --> .spm, .pfc
            - PS-NEX --> .tdms
            - Asylum Research --> .ARDF

                Parameters: None

                Returns:
                        piezoimg (np.array): 2D array containing the piezo image of the file.
        """
        file_type = self.filemetadata['file_type']
        if file_type in jpkfiles:
            self.piezoimg = computeJPKPiezoImg(self)
        elif file_type in jpk_h5_file:
            self.piezoimg = computeJPKPiezoImg_h5(self)
        elif file_type[1:].isdigit() or file_type in nanoscfiles:
            self.piezoimg = loadNANOSCimg(self.filemetadata)
        elif file_type in psnexfiles:
            from .ps_nex.loadpsneximg import loadPSNEXimg
            self.piezoimg, _ = loadPSNEXimg(self)
        elif file_type in ARDFfiles:
            self.piezoimg = loadARDFimg(self.filemetadata)
        return self.piezoimg

    def to_txt(self, savedir):
        """
        Function used to save the loaded data into a txt file following the UFF.

                Parameters:
                        savedir (str): Path to save the txt UFF file.

                Returns: None
        """
        if self.isFV:
            for curveidx in range(self.filemetadata['Entry_tot_nb_curve']):
                saveUFFtxt(self, self, savedir, curveidx)
        else:
            saveUFFtxt(self, self, savedir)
