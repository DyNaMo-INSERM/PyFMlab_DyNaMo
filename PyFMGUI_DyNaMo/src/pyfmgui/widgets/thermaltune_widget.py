import os
import numpy as np
import pandas as pd
import requests
import xml.etree.ElementTree as etree
import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.exporters import ImageExporter

from pyfmreader import loadfile
from pyfmrheo.models.calibration import Stark_Chi_force_constant
from pyfmrheo.models.sho import SHOModel

import pyfmgui.const as cts

class ThermalTuneWidget(QtWidgets.QWidget):
    def __init__(self, session, parent=None):
        super(ThermalTuneWidget, self).__init__(parent)
        self.session = session
        self.session.thermal_tune_widget = self
        
        # Lists to store multiple files - restore from session if available
        self.air_files_data = self.session.thermal_tune_air_files_data.copy() if self.session.thermal_tune_air_files_data else []
        self.liquid_files_data = self.session.thermal_tune_liquid_files_data.copy() if self.session.thermal_tune_liquid_files_data else []
        
        # Dictionaries to store fitted results per file - restore from session if available
        self.air_fit_results = self.session.thermal_tune_air_fit_results.copy() if self.session.thermal_tune_air_fit_results else {}
        self.liquid_fit_results = self.session.thermal_tune_liquid_fit_results.copy() if self.session.thermal_tune_liquid_fit_results else {}
        
        # Current selected data (for backward compatibility)
        self.inliquid_thermal_ampl = None
        self.inliquid_thermal_freq = None
        self.inliquid_fit_data = None
        self.inliquid_params = None
        self.inair_thermal_ampl = None
        self.inair_thermal_freq = None
        self.inair_fit_data = None
        self.inair_params = None
        self.thermal_fit_air = None
        self.thermal_fit_lq = None
        self.freq_fit_air = None
        self.freq_fit_lq = None
        self.fR_air = None  # Center frequency for air fit
        self.fR_lq = None   # Center frequency for liquid fit
        self.k0 = None
        self.GCI_cant_springConst = None
        self.involsValue = None
        self.invOLS_H = None
        self.sader_canti_list = {}
        self.filename = None
        self.init_gui()
        
        # Restore UI elements from saved data
        self._restore_ui_from_session_data()
        
        # Try to login, but don't block if it fails
        # try:
        #     self.sader_login()
        # except Exception as e:
        #     print(f"Warning: Could not auto-login to SADER: {e}")
        #     print("You can manually login using the Login button")

    def init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)

        params_layout = QtWidgets.QVBoxLayout()

        file_select_layout = QtWidgets.QGridLayout()

        air_thermal_label = QtWidgets.QLabel("Air Thermal File")
        air_thermal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        air_thermal_label.setMaximumWidth(150)
        self.air_thermal_text = QtWidgets.QLineEdit()
        self.air_thermal_text.setMaximumHeight(40)
        self.air_thermal_text.setAcceptDrops(True)
        self.air_thermal_text.dragEnterEvent = self.air_dragEnterEvent
        self.air_thermal_text.dropEvent = self.air_dropEvent
        
        # Air file selector dropdown
        self.air_file_selector = QtWidgets.QComboBox()
        self.air_file_selector.setMaximumHeight(40)
        self.air_file_selector.currentIndexChanged.connect(self.on_air_file_selected)
        self.air_file_selector.wheelEvent = self.air_wheel_event
        
        air_thermal_browse_bttn = QtWidgets.QPushButton()
        air_thermal_browse_bttn.setText("Browse")
        air_thermal_browse_bttn.clicked.connect(self.load_air_data)
        air_thermal_clear_bttn = QtWidgets.QPushButton()
        air_thermal_clear_bttn.setText("Clear Air Data")
        air_thermal_clear_bttn.clicked.connect(self.clear_air_data)

        lq_thermal_label = QtWidgets.QLabel("Liquid Thermal File")
        lq_thermal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        lq_thermal_label.setMaximumWidth(150)
        self.lq_thermal_text = QtWidgets.QLineEdit()
        self.lq_thermal_text.setMaximumHeight(40)
        self.lq_thermal_text.setAcceptDrops(True)
        self.lq_thermal_text.dragEnterEvent = self.lq_dragEnterEvent
        self.lq_thermal_text.dropEvent = self.lq_dropEvent
        
        # Liquid file selector dropdown
        self.lq_file_selector = QtWidgets.QComboBox()
        self.lq_file_selector.setMaximumHeight(40)
        self.lq_file_selector.currentIndexChanged.connect(self.on_liquid_file_selected)
        self.lq_file_selector.wheelEvent = self.lq_wheel_event
        
        lq_thermal_browse_bttn = QtWidgets.QPushButton()
        lq_thermal_browse_bttn.setText("Browse")
        lq_thermal_browse_bttn.clicked.connect(self.load_liquid_data)
        lq_thermal_clear_bttn = QtWidgets.QPushButton()
        lq_thermal_clear_bttn.setText("Clear Liq. Data")
        lq_thermal_clear_bttn.clicked.connect(self.clear_lq_data)

        file_select_layout.addWidget(air_thermal_label, 0, 0, 1, 1)
        file_select_layout.addWidget(self.air_thermal_text, 0, 1, 1, 2)
        file_select_layout.addWidget(self.air_file_selector, 1, 1, 1, 2)
        file_select_layout.addWidget(air_thermal_browse_bttn, 2, 2, 1, 1)
        file_select_layout.addWidget(air_thermal_clear_bttn, 2, 1, 1, 1)
        file_select_layout.addWidget(lq_thermal_label, 3, 0, 1, 1)
        file_select_layout.addWidget(self.lq_thermal_text, 3, 1, 1, 2)
        file_select_layout.addWidget(self.lq_file_selector, 4, 1, 1, 2)
        file_select_layout.addWidget(lq_thermal_browse_bttn, 5, 2, 1, 1)
        file_select_layout.addWidget(lq_thermal_clear_bttn, 5, 1, 1, 1)

        login_layout = QtWidgets.QGridLayout()
        user_name_label = QtWidgets.QLabel("SADER Username")
        user_name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        user_name_label.setMaximumWidth(150)
        self.user_name_text = QtWidgets.QLineEdit()
        self.user_name_text.setMaximumHeight(40)
        self.user_name_text.setText(cts.DEFAULT_SADER_USERNAME)
        user_pwd_label = QtWidgets.QLabel("SADER Password")
        user_pwd_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        user_pwd_label.setMaximumWidth(150)
        self.user_pwd_text = QtWidgets.QLineEdit()
        self.user_pwd_text.setMaximumHeight(40)
        self.user_pwd_text.setText(cts.DEFAULT_SADER_PASSWORD)
        self.user_pwd_text.setEchoMode(QtWidgets.QLineEdit.Password)
        login_bttn = QtWidgets.QPushButton()
        login_bttn.setText("Login")
        login_bttn.clicked.connect(self.sader_login)

        login_layout.addWidget(user_name_label, 0, 0, 1, 1)
        login_layout.addWidget(self.user_name_text, 0, 1, 1, 2)
        login_layout.addWidget(user_pwd_label, 1, 0, 1, 1)
        login_layout.addWidget(self.user_pwd_text, 1, 1, 1, 2)
        login_layout.addWidget(login_bttn, 2, 2, 1, 1)

        self.params = Parameter.create(name='params', children=cts.thermaltune_params)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)

        self.pushButton = QtWidgets.QPushButton("computeButton")
        self.pushButton.setText("Compute")
        self.pushButton.clicked.connect(self.do_thermalfit)

        self.saveButton = QtWidgets.QPushButton("saveButton")
        self.saveButton.setText("save as png")
        self.saveButton.clicked.connect(self.save_results_to_png)

        # Apply and Reset buttons layout
        apply_reset_layout = QtWidgets.QHBoxLayout()
        
        self.applyButton = QtWidgets.QPushButton("applyButton")
        self.applyButton.setText("Apply Calibration")
        self.applyButton.clicked.connect(self.apply_calibration)
        self.applyButton.setEnabled(False)
        
        self.resetButton = QtWidgets.QPushButton("resetButton")
        self.resetButton.setText("Reset Calibration")
        self.resetButton.clicked.connect(self.reset_calibration)
        
        apply_reset_layout.addWidget(self.applyButton)
        apply_reset_layout.addWidget(self.resetButton)

        params_layout.addLayout(file_select_layout, 2)
        params_layout.addLayout(login_layout, 2)
        params_layout.addWidget(self.paramTree, 2)
        params_layout.addWidget(self.pushButton, 1)
        params_layout.addWidget(self.saveButton, 1)
        params_layout.addLayout(apply_reset_layout, 1)

        ## Add 3 plots into the first row (automatic position)
        self.l = pg.GraphicsLayoutWidget()
        self.p1 = pg.PlotItem()
        self.p1legend = self.p1.addLegend()
        
        # Add the plot to the layout
        self.l.addItem(self.p1)
        
        # Initialize ROI objects
        self.air_roi = pg.LinearRegionItem(brush=(50,50,200,0), pen='w')
        self.air_roi.setZValue(10)
        self.lq_roi = pg.LinearRegionItem(brush=(50,50,200,0), pen='y')
        self.lq_roi.setZValue(10)

        ## Put vertical label on left side
        main_layout.addLayout(params_layout, 1)
        main_layout.addWidget(self.l, 3)

    def _restore_ui_from_session_data(self):
        """Restore UI elements (dropdowns) from previously saved session data"""
        # Restore air file dropdown
        if self.air_files_data:
            for fname, ampl, freq, fit_data, params in self.air_files_data:
                if fname not in [self.air_file_selector.itemText(i) for i in range(self.air_file_selector.count())]:
                    self.air_file_selector.addItem(fname)
            # Select the last file
            if self.air_files_data:
                last_file = self.air_files_data[-1][0]
                self.air_file_selector.setCurrentText(last_file)
                self.on_air_file_selected(0)  # Trigger update
        
        # Restore liquid file dropdown
        if self.liquid_files_data:
            for fname, ampl, freq, fit_data, params in self.liquid_files_data:
                if fname not in [self.lq_file_selector.itemText(i) for i in range(self.lq_file_selector.count())]:
                    self.lq_file_selector.addItem(fname)
            # Select the last file
            if self.liquid_files_data:
                last_file = self.liquid_files_data[-1][0]
                self.lq_file_selector.setCurrentText(last_file)
                self.on_liquid_file_selected(0)  # Trigger update

    def read_afm_data(self, file_path):
        """Read thermal data from .dat file (custom format)"""
        file_ext = os.path.splitext(file_path)[1]
        if file_ext != ".dat":
            raise ValueError("Unsupported file format. Please provide a .dat file.")

        headers = {}
        data = []

        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('#'):
                    key, value = line[1:].strip().split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    try:
                        headers[key] = float(value)
                    except ValueError:
                        headers[key] = value
                else:
                    if line.strip():
                        data.append([float(x) for x in line.split()])

        df = pd.DataFrame(data, columns=['Frequency', 'VerticalDeflectionPSD'])
        amplitude = df['VerticalDeflectionPSD'].values
        frequencies = df['Frequency'].values
        fit_data = np.zeros_like(amplitude)
        parameters = headers
        
        print(f"Loaded thermal data: {len(frequencies)} points, freq range: {frequencies.min():.1f} to {frequencies.max():.1f} Hz")

        return amplitude, frequencies, fit_data, parameters

    def closeEvent(self, evnt):
        # Save working data to session before closing
        self.session.thermal_tune_air_files_data = self.air_files_data.copy() if self.air_files_data else []
        self.session.thermal_tune_liquid_files_data = self.liquid_files_data.copy() if self.liquid_files_data else []
        self.session.thermal_tune_air_fit_results = self.air_fit_results.copy() if self.air_fit_results else {}
        self.session.thermal_tune_liquid_fit_results = self.liquid_fit_results.copy() if self.liquid_fit_results else {}
        self.session.thermal_tune_widget = None
    
    def air_dragEnterEvent(self, event):
        """Handle drag enter events for air thermal file field"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            # Check if all files are .dat or .tnd files
            valid_files = all(url.toLocalFile().endswith(('.dat', '.tnd')) for url in urls)
            if valid_files:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def air_dropEvent(self, event):
        """Handle drop events for air thermal file field"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            successfully_loaded = []
            errors = []
            
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.endswith(('.dat', '.tnd')):
                    try:
                        if file_path.endswith('.dat'):
                            ampl, freq, fit_data, params = self.read_afm_data(file_path)
                            data = (ampl, None, freq, None, params)  # Match .tnd format
                        else:  # .tnd file
                            data = loadfile(file_path)
                        
                        fname = os.path.basename(file_path)
                        ampl, _, freq, _, params = data
                        fit_data = np.zeros_like(ampl)
                        self.air_files_data.append((fname, ampl, freq, fit_data, params))
                        successfully_loaded.append(fname)
                    except Exception as e:
                        errors.append(f"{os.path.basename(file_path)}: {str(e)}")
                        
            if successfully_loaded:
                # Select the last successfully loaded file
                last_file = successfully_loaded[-1]
                if last_file not in [self.air_file_selector.itemText(i) for i in range(self.air_file_selector.count())]:
                    self.air_file_selector.addItem(last_file)
                self.air_file_selector.setCurrentText(last_file)
                
                # Set filename for analysis functions
                self.filename = last_file
                
                # Update the current data to the last loaded file
                for fname, ampl, freq, fit_data, params in self.air_files_data:
                    if fname == last_file:
                        self.inair_thermal_ampl = ampl
                        self.inair_thermal_freq = freq
                        self.inair_fit_data = fit_data
                        self.inair_params = params
                        break
                
                self.air_thermal_text.setText(f"{len(self.air_files_data)} files loaded (current: {last_file})")
                
                self.update_plot()
                event.acceptProposedAction()
                
                # Print summary
                print(f"Successfully loaded {len(successfully_loaded)} air thermal files: {', '.join(successfully_loaded)}")
                if errors:
                    print(f"Errors: {'; '.join(errors)}")
            else:
                print(f"No files could be loaded. Errors: {'; '.join(errors)}")
                event.ignore()
        else:
            event.ignore()
    
    def lq_dragEnterEvent(self, event):
        """Handle drag enter events for liquid thermal file field"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            # Check if all files are .dat or .tnd files
            valid_files = all(url.toLocalFile().endswith(('.dat', '.tnd')) for url in urls)
            if valid_files:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def lq_dropEvent(self, event):
        """Handle drop events for liquid thermal file field"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            successfully_loaded = []
            errors = []
            
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.endswith(('.dat', '.tnd')):
                    try:
                        if file_path.endswith('.dat'):
                            ampl, freq, fit_data, params = self.read_afm_data(file_path)
                            data = (ampl, None, freq, None, params)  # Match .tnd format
                        else:  # .tnd file
                            data = loadfile(file_path)
                        
                        fname = os.path.basename(file_path)
                        ampl, _, freq, _, params = data
                        fit_data = np.zeros_like(ampl)
                        self.liquid_files_data.append((fname, ampl, freq, fit_data, params))
                        successfully_loaded.append(fname)
                    except Exception as e:
                        errors.append(f"{os.path.basename(file_path)}: {str(e)}")
                        
            if successfully_loaded:
                # Select the last successfully loaded file
                last_file = successfully_loaded[-1]
                if last_file not in [self.lq_file_selector.itemText(i) for i in range(self.lq_file_selector.count())]:
                    self.lq_file_selector.addItem(last_file)
                self.lq_file_selector.setCurrentText(last_file)
                
                # Set filename for analysis functions
                self.filename = last_file
                
                # Update the current data to the last loaded file
                for fname, ampl, freq, fit_data, params in self.liquid_files_data:
                    if fname == last_file:
                        self.inliquid_thermal_ampl = ampl
                        self.inliquid_thermal_freq = freq
                        self.inliquid_fit_data = fit_data
                        self.inliquid_params = params
                        break
                
                self.lq_thermal_text.setText(f"{len(self.liquid_files_data)} files loaded (current: {last_file})")
                
                self.update_plot()
                event.acceptProposedAction()
                
                # Print summary
                print(f"Successfully loaded {len(successfully_loaded)} liquid thermal files: {', '.join(successfully_loaded)}")
                if errors:
                    print(f"Errors: {'; '.join(errors)}")
            else:
                print(f"No files could be loaded. Errors: {'; '.join(errors)}")
                event.ignore()
        else:
            event.ignore()
    
    def load_data(self):
        """Load multiple data files from either .dat or .tnd files"""
        fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, 'Open files', self.session.last_browsed_paths['thermal_files'], "Thermal files (*.dat *.tnd)"
        )
        
        if not fnames:
            return []
        
        # Update the last browsed directory
        self.session.last_browsed_paths['thermal_files'] = os.path.dirname(os.path.abspath(fnames[0]))
        
        results = []
        for fname in fnames:
            self.filename = fname
            
            try:
                if fname.endswith('.dat'):
                    # .dat file returns (ampl, freq, fit_data, params)
                    ampl, freq, fit_data, params = self.read_afm_data(fname)
                    data = (ampl, None, freq, None, params)  # Match .tnd format (5-tuple)
                else:  # .tnd file
                    # .tnd file returns (ampl, ?, freq, ?, params) - 5 values
                    data = loadfile(fname)
                
                results.append((data, os.path.basename(fname)))
            except Exception as e:
                print(f"Error loading file {fname}: {e}")
        
        return results

    def load_air_data(self):
        """Load multiple air thermal data files"""
        data_list = self.load_data()
        if not data_list:
            return
        
        for data, fname in data_list:
            # Unpack the 5-tuple (ampl, ?, freq, ?, params)
            ampl, _, freq, _, params = data
            fit_data = np.zeros_like(ampl)
            
            # Add the new file to the list
            self.air_files_data.append((fname, ampl, freq, fit_data, params))
            
            # Update the dropdown
            if fname not in [self.air_file_selector.itemText(i) for i in range(self.air_file_selector.count())]:
                self.air_file_selector.addItem(fname)
        
        # Select the last loaded file
        if data_list:
            last_fname = data_list[-1][1]
            self.air_file_selector.setCurrentText(last_fname)
            
            # Set filename for analysis functions
            self.filename = last_fname
            
            # Update the current data (for analysis)
            ampl, _, freq, _, params = data_list[-1][0]
            fit_data = np.zeros_like(ampl)
            self.inair_thermal_ampl = ampl
            self.inair_thermal_freq = freq
            self.inair_fit_data = fit_data
            self.inair_params = params
            self.air_thermal_text.setText(f"{len(self.air_files_data)} files loaded (current: {last_fname})")
            
            # Set ROI region
            try:
                resonancef = params.get('parameter.f', 43000)
                if isinstance(resonancef, str):
                    resonancef = float(resonancef)
                self.air_roi.setRegion([np.log10(resonancef/2), np.log10(resonancef*2)])
            except (ValueError, TypeError, KeyError) as e:
                print(f"Error setting air ROI: {e}, using default frequency")
                self.air_roi.setRegion([np.log10(43000/2), np.log10(43000*2)])
            
            self.update_plot()

    def load_liquid_data(self):
        """Load multiple liquid thermal data files"""
        data_list = self.load_data()
        if not data_list:
            return
        
        for data, fname in data_list:
            # Unpack the 5-tuple (ampl, ?, freq, ?, params)
            ampl, _, freq, _, params = data
            fit_data = np.zeros_like(ampl)
            
            # Add the new file to the list
            self.liquid_files_data.append((fname, ampl, freq, fit_data, params))
            
            # Update the dropdown
            if fname not in [self.lq_file_selector.itemText(i) for i in range(self.lq_file_selector.count())]:
                self.lq_file_selector.addItem(fname)
        
        # Select the last loaded file
        if data_list:
            last_fname = data_list[-1][1]
            self.lq_file_selector.setCurrentText(last_fname)
            
            # Set filename for analysis functions
            self.filename = last_fname
            
            # Update the current data (for analysis)
            ampl, _, freq, _, params = data_list[-1][0]
            fit_data = np.zeros_like(ampl)
            self.inliquid_thermal_ampl = ampl
            self.inliquid_thermal_freq = freq
            self.inliquid_fit_data = fit_data
            self.inliquid_params = params
            self.lq_thermal_text.setText(f"{len(self.liquid_files_data)} files loaded (current: {last_fname})")
            
            # Set ROI region
            try:
                resonancef = params.get('parameter.f', 43000)
                if isinstance(resonancef, str):
                    resonancef = float(resonancef)
                self.lq_roi.setRegion([np.log10(resonancef/2), np.log10(resonancef*2)])
            except Exception as e:
                print(f"Error setting liquid ROI: {e}")
            
            self.update_plot()
    
    def clear_air_data(self):
        """Clear all air data"""
        self.air_files_data.clear()
        self.air_fit_results.clear()
        self.air_file_selector.clear()
        self.inair_thermal_ampl = None
        self.inair_thermal_freq = None
        self.inair_fit_data = None
        self.freq_fit_air = None
        self.thermal_fit_air = None
        self.fR_air = None
        self.inair_params = None
        self.air_thermal_text.setText("")
        self.update_plot()
    
    def clear_lq_data(self):
        """Clear all liquid data"""
        self.liquid_files_data.clear()
        self.liquid_fit_results.clear()
        self.lq_file_selector.clear()
        self.inliquid_thermal_ampl = None
        self.inliquid_thermal_freq = None
        self.inliquid_fit_data = None
        self.freq_fit_lq = None
        self.thermal_fit_lq = None
        self.fR_lq = None
        self.inliquid_params = None
        self.lq_thermal_text.setText("")
        self.update_plot()
    
    def on_air_file_selected(self, index):
        """Handle air file selection from dropdown"""
        if index < 0 or index >= len(self.air_files_data):
            return
        
        fname, ampl, freq, fit_data, params = self.air_files_data[index]
        self.filename = fname
        self.inair_thermal_ampl = ampl
        self.inair_thermal_freq = freq
        self.inair_fit_data = fit_data
        self.inair_params = params
        
        # Check if this file has been fitted before and restore fit results
        if fname in self.air_fit_results:
            fit_res = self.air_fit_results[fname]
            self.freq_fit_air = fit_res['freq_fit']
            self.thermal_fit_air = fit_res['thermal_fit']
            self.k0_air = fit_res['k0']
            self.GCI_cant_springConst_air = fit_res['GCI_cant_springConst']
            self.involsValue_air = fit_res['involsValue']
            self.invOLS_H_air = fit_res['invOLS_H']
            
            # Restore ROI region
            if 'roi_region' in fit_res:
                self.air_roi.setRegion(fit_res['roi_region'])
            
            print(f"Restored fit results for: {fname}")
        else:
            # Clear fit data if this file hasn't been fitted
            self.thermal_fit_air = None
            self.freq_fit_air = None
            
            # Set default ROI region
            try:
                resonancef = params.get('parameter.f', 43000)
                if isinstance(resonancef, str):
                    resonancef = float(resonancef)
                self.air_roi.setRegion([np.log10(resonancef/2), np.log10(resonancef*2)])
            except (ValueError, TypeError, KeyError):
                self.air_roi.setRegion([np.log10(43000/2), np.log10(43000*2)])
        
        self.update_plot()
    
    def on_liquid_file_selected(self, index):
        """Handle liquid file selection from dropdown"""
        if index < 0 or index >= len(self.liquid_files_data):
            return
        
        fname, ampl, freq, fit_data, params = self.liquid_files_data[index]
        self.filename = fname
        self.inliquid_thermal_ampl = ampl
        self.inliquid_thermal_freq = freq
        self.inliquid_fit_data = fit_data
        self.inliquid_params = params
        
        # Check if this file has been fitted before and restore fit results
        if fname in self.liquid_fit_results:
            fit_res = self.liquid_fit_results[fname]
            self.freq_fit_lq = fit_res['freq_fit']
            self.thermal_fit_lq = fit_res['thermal_fit']
            self.k0_lq = fit_res['k0']
            self.GCI_cant_springConst_lq = fit_res['GCI_cant_springConst']
            self.involsValue_lq = fit_res['involsValue']
            self.invOLS_H_lq = fit_res['invOLS_H']
            
            # Restore ROI region
            if 'roi_region' in fit_res:
                self.lq_roi.setRegion(fit_res['roi_region'])
            
            print(f"Restored fit results for: {fname}")
        else:
            # Clear fit data if this file hasn't been fitted
            self.thermal_fit_lq = None
            self.freq_fit_lq = None
            
            # Set default ROI region
            try:
                resonancef = params.get('parameter.f', 43000)
                if isinstance(resonancef, str):
                    resonancef = float(resonancef)
                self.lq_roi.setRegion([np.log10(resonancef/2), np.log10(resonancef*2)])
            except (ValueError, TypeError, KeyError):
                self.lq_roi.setRegion([np.log10(43000/2), np.log10(43000*2)])
        
        self.update_plot()
    
    def air_wheel_event(self, event):
        """Handle mouse wheel events for air file selector"""
        current_index = self.air_file_selector.currentIndex()
        if current_index < 0:
            return
        
        # Scroll up = previous file, scroll down = next file
        if event.angleDelta().y() > 0:  # Scroll up
            new_index = max(0, current_index - 1)
        else:  # Scroll down
            new_index = min(len(self.air_files_data) - 1, current_index + 1)
        
        if new_index != current_index:
            self.air_file_selector.setCurrentIndex(new_index)
    
    def lq_wheel_event(self, event):
        """Handle mouse wheel events for liquid file selector"""
        current_index = self.lq_file_selector.currentIndex()
        if current_index < 0:
            return
        
        # Scroll up = previous file, scroll down = next file
        if event.angleDelta().y() > 0:  # Scroll up
            new_index = max(0, current_index - 1)
        else:  # Scroll down
            new_index = min(len(self.liquid_files_data) - 1, current_index + 1)
        
        if new_index != current_index:
            self.lq_file_selector.setCurrentIndex(new_index)
    
    def update_plot(self):
        """Update the plot with current thermal data and fits"""
        self.l.clear()
        self.p1.clear()
        self.p1legend.clear()

        if self.inair_thermal_freq is not None and self.inair_thermal_ampl is not None:
            air = self.p1.plot(self.inair_thermal_freq, self.inair_thermal_ampl, pen='w', name='Air Data')
            self.p1.addItem(self.air_roi, ignoreBounds=True)
            self.air_roi.setClipItem(air)
        
        if self.inliquid_thermal_freq is not None and self.inliquid_thermal_ampl is not None:
            lq = self.p1.plot(self.inliquid_thermal_freq, self.inliquid_thermal_ampl, pen='y', name='Liquid Data')
            self.p1.addItem(self.lq_roi, ignoreBounds=True)
            self.lq_roi.setClipItem(lq)
        
        if self.thermal_fit_air is not None:
            self.p1.plot(self.freq_fit_air, self.thermal_fit_air, pen={'color':'c', 'width': 3}, name='Air SHO Fit')
            style = pg.PlotDataItem(pen=None)
            try:
                self.p1legend.addItem(style, f'K Air: {self.k0_air:.3f} N/m')
                self.p1legend.addItem(style, f'K Air GCI: {self.GCI_cant_springConst_air:.3f} N/m')
                self.p1legend.addItem(style, f'InVOLS Air: {self.involsValue_air * 1e9:.3f} nm/V')
                self.p1legend.addItem(style, f'InVOLS H Air: {self.invOLS_H_air * 1e9:.3f} nm/V')
            except (AttributeError, TypeError):
                pass
        
        if self.thermal_fit_lq is not None:
            self.p1.plot(self.freq_fit_lq, self.thermal_fit_lq, pen={'color':'g', 'width': 3}, name='Liquid SHO Fit')
            style = pg.PlotDataItem(pen=None)
            try:
                self.p1legend.addItem(style, f'K Liquid: {self.k0_lq:.3f} N/m')
                self.p1legend.addItem(style, f'K Liquid GCI: {self.GCI_cant_springConst_lq:.3f} N/m')
                self.p1legend.addItem(style, f'InVOLS Liquid: {self.involsValue_lq * 1e9:.3f} nm/V')
                self.p1legend.addItem(style, f'InVOLS H Liquid: {self.invOLS_H_lq * 1e9:.3f} nm/V')
            except (AttributeError, TypeError):
                pass

        self.p1.setTitle("Amplitude-Frequency")
        self.p1.setLabel('left', 'Amplitude (pm^2/V)')
        self.p1.setLabel('bottom', 'Frequency', 'Hz')
        self.p1.setLogMode(True, True)

        self.l.addItem(self.p1)
    
    def get_params(self):
        amb_params = self.params.child('Ambient Params')
        self.Tc = amb_params.child('Temperature').value()
        self.RH = amb_params.child('Rel. Humidity').value()
        canti_params = self.params.child('Cantilever Params')
        self.cantType = canti_params.child('Canti Shape').value()
        self.cantiWidth = canti_params.child('Width').value() / 1e6
        self.cantiLen = canti_params.child('Length').value() / 1e6
        self.cantiWidthLegs = canti_params.child('Width Legs').value() / 1e6
        cal_params = self.params.child('Calibration Params')
        self.selectedCantId = cal_params.child('Cantilever Code').value()
        self.selectedCantCode = self.sader_canti_list.get(self.selectedCantId, "")
    
    def SaderGCI_GetLeverList(self):
        payload = '''<?xml version="1.0" encoding="UTF-8" ?>
        <saderrequest>
        <username>'''+self.session.sader_username+'''</username>
        <password>'''+self.session.sader_password+'''</password>
        <operation>LIST</operation>
        </saderrequest>'''
        headers = {'user-agent': cts.SADER_API_version, 'Content-type': cts.SADER_API_type}
        
        try:
            r = requests.post(cts.SADER_API_url, data=payload, headers=headers, timeout=5)
            r.raise_for_status()  # Raise exception for bad status codes
            
            # Check if response is empty
            if not r.content or not r.content.strip():
                print("SADER API returned empty response")
                return {}
            
            doc = etree.fromstring(r.content)
        except requests.exceptions.RequestException as e:
            print(f"SADER API request error: {e}")
            return {}
        except etree.ParseError as e:
            print(f"SADER API XML parse error: {e}")
            return {}
        except Exception as e:
            print(f"SADER API unexpected error: {e}")
            return {}
        
        cantilever_ids = doc.findall('./cantilevers/cantilever/id')
        cantilever_labels = doc.findall('./cantilevers/cantilever/label')

        canti_ids = {}

        for a in range(len(cantilever_ids)):
            canti_lbl = cantilever_labels[a].text
            canti_id  = cantilever_ids[a].text.replace('data_','')
            canti_ids[canti_lbl] = canti_id
        
        return canti_ids
    
    def open_msg_box(self, message):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Login Status")
        dlg.setText(message)
        dlg.exec()
    
    def sader_login(self):
        self.session.sader_username = self.user_name_text.text()
        self.session.sader_password = self.user_pwd_text.text()
        try:
            self.sader_canti_list = self.SaderGCI_GetLeverList()
            if self.sader_canti_list == {}:
                self.open_msg_box("Could not Login! Please check your credentials and internet connection.")
                return
            cantilever_code = self.params.child('Calibration Params').child('Cantilever Code')
            cantilever_codes = list(self.sader_canti_list.keys())
            cantilever_code.setLimits(cantilever_codes)
            if cantilever_codes:
                cantilever_code.setValue(cantilever_codes[0])
            self.open_msg_box("Login was successful!")
        except Exception as e:
            print(f"Error during SADER login: {e}")
            self.open_msg_box("Could not Login! Please check your credentials and internet connection.")
    
    def do_thermalfit(self):
        # Change to the routines present in PyFMRheo
        # Air
        self.get_params()
        if self.inair_thermal_ampl is not None and self.inair_thermal_freq is not None:
            minfreq, maxfreq = self.air_roi.getRegion()
            minfreq = 10 ** minfreq
            maxfreq = 10 ** maxfreq
            mask = np.logical_and(self.inair_thermal_freq >= minfreq, self.inair_thermal_freq <= maxfreq)
            ampl_fit = self.inair_thermal_ampl[mask]
            freq_fit = self.inair_thermal_freq[mask]
            sho_model_air = SHOModel()
            sho_model_air.fit(freq_fit, ampl_fit)
            self.freq_fit_air = freq_fit
            self.thermal_fit_air = sho_model_air.eval(self.freq_fit_air)
            A1_air = sho_model_air.A
            fR1_air = sho_model_air.fR
            Q1_air = sho_model_air.Q
            self.k0_air, self.GCI_cant_springConst_air, self.involsValue_air, self.invOLS_H_air =\
                Stark_Chi_force_constant(
                    self.cantiWidth, self.cantiLen, self.cantiWidthLegs,
                    A1_air, fR1_air, Q1_air, self.Tc, self.RH, 'air',
                    self.cantType, username = self.session.sader_username,
                    password = self.session.sader_password, selectedCantCode = self.selectedCantCode
                )
# here apply the spring constant after calculation
            canti_params = self.params.child('Cantilever Params')
            canti_params.child('nominal k').setValue(float(self.k0_air))
            
            # Save fit results and ROI region for this file
            if self.filename:
                roi_min, roi_max = self.air_roi.getRegion()
                self.air_fit_results[self.filename] = {
                    'freq_fit': self.freq_fit_air,
                    'thermal_fit': self.thermal_fit_air,
                    'k0': self.k0_air,
                    'GCI_cant_springConst': self.GCI_cant_springConst_air,
                    'involsValue': self.involsValue_air,
                    'invOLS_H': self.invOLS_H_air,
                    'roi_region': [roi_min, roi_max]
                }
                print(f"Saved air fit results and ROI for: {self.filename}")
        
        # Liquid
        if self.inliquid_thermal_ampl is not None and self.inliquid_thermal_freq is not None:
            minfreq, maxfreq = self.lq_roi.getRegion()
            minfreq = 10 ** minfreq
            maxfreq = 10 ** maxfreq
            mask = np.logical_and(self.inliquid_thermal_freq >= minfreq, self.inliquid_thermal_freq <= maxfreq)
            ampl_fit = self.inliquid_thermal_ampl[mask]
            freq_fit = self.inliquid_thermal_freq[mask]
            sho_model_lq = SHOModel()
            sho_model_lq.fit(freq_fit, ampl_fit)
            self.freq_fit_lq = freq_fit
            self.thermal_fit_lq = sho_model_lq.eval(self.freq_fit_lq)
            A1_lq = sho_model_lq.A
            fR1_lq = sho_model_lq.fR
            Q1_lq = sho_model_lq.Q
            self.k0_lq, self.GCI_cant_springConst_lq, self.involsValue_lq, self.invOLS_H_lq =\
                Stark_Chi_force_constant(
                    self.cantiWidth, self.cantiLen, self.cantiWidthLegs,
                    A1_lq, fR1_lq, Q1_lq, self.Tc, self.RH, 'water', 
                    self.cantType, username = self.session.sader_username,
                    password = self.session.sader_password, selectedCantCode = self.selectedCantCode
                )
            
            # Save fit results and ROI region for this file
            if self.filename:
                roi_min, roi_max = self.lq_roi.getRegion()
                self.liquid_fit_results[self.filename] = {
                    'freq_fit': self.freq_fit_lq,
                    'thermal_fit': self.thermal_fit_lq,
                    'k0': self.k0_lq,
                    'GCI_cant_springConst': self.GCI_cant_springConst_lq,
                    'involsValue': self.involsValue_lq,
                    'invOLS_H': self.invOLS_H_lq,
                    'roi_region': [roi_min, roi_max]
                }
                print(f"Saved liquid fit results and ROI for: {self.filename}")
        
        # Enable the Apply button if we have computed results
        if (hasattr(self, 'k0_air') and self.k0_air is not None) or \
           (hasattr(self, 'k0_lq') and self.k0_lq is not None):
            self.applyButton.setEnabled(True)
        
        self.update_plot()
    
    def apply_calibration(self):
        """Apply computed thermal tune calibration values to the session"""
        # Create dialog to choose which medium to apply
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Apply Calibration")
        dlg.setMinimumWidth(550)
        dlg.setMinimumHeight(500)
        
        layout = QtWidgets.QVBoxLayout()
        
        label = QtWidgets.QLabel("Choose which calibration values to apply:")
        layout.addWidget(label)
        
        # Radio buttons for medium selection
        air_radio = QtWidgets.QRadioButton("Apply Air Calibration")
        liquid_radio = QtWidgets.QRadioButton("Apply Liquid Calibration")
        both_radio = QtWidgets.QRadioButton("Apply Both (use Air values)")
        
        air_has_data = hasattr(self, 'k0_air') and self.k0_air is not None
        liquid_has_data = hasattr(self, 'k0_lq') and self.k0_lq is not None
        
        air_radio.setEnabled(air_has_data)
        liquid_radio.setEnabled(liquid_has_data)
        both_radio.setEnabled(air_has_data and liquid_has_data)
        
        if air_has_data:
            air_radio.setChecked(True)
        elif liquid_has_data:
            liquid_radio.setChecked(True)
        
        layout.addWidget(air_radio)
        layout.addWidget(liquid_radio)
        layout.addWidget(both_radio)
        
        layout.addSpacing(15)
        
        # Editable values section
        values_label = QtWidgets.QLabel("Edit calibration values:")
        values_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(values_label)
        
        # Create scroll area for editable fields
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout()
        
        # Air values
        if air_has_data:
            air_group = QtWidgets.QGroupBox("Air Calibration Values")
            air_layout = QtWidgets.QGridLayout()
            
            self.air_k0_edit = QtWidgets.QLineEdit()
            self.air_k0_edit.setText(f"{self.k0_air:.6f}")
            self.air_k0_edit.setToolTip("Spring constant in N/m")
            
            self.air_invols_edit = QtWidgets.QLineEdit()
            self.air_invols_edit.setText(f"{self.involsValue_air*1e9:.6f}")
            self.air_invols_edit.setToolTip("Deflection sensitivity in nm/V")
            
            self.air_gci_edit = QtWidgets.QLineEdit()
            gci_air_text = "N/A" if (isinstance(self.GCI_cant_springConst_air, float) and self.GCI_cant_springConst_air != self.GCI_cant_springConst_air) else f"{self.GCI_cant_springConst_air:.6f}"
            self.air_gci_edit.setText(gci_air_text)
            self.air_gci_edit.setToolTip("GCI spring constant in N/m (may be unavailable if SADER request fails)")
            
            self.air_invols_h_edit = QtWidgets.QLineEdit()
            self.air_invols_h_edit.setText(f"{self.invOLS_H_air*1e9:.6f}")
            self.air_invols_h_edit.setToolTip("InVOLS H in nm/V")
            
            air_layout.addWidget(QtWidgets.QLabel("k₀ (N/m):"), 0, 0)
            air_layout.addWidget(self.air_k0_edit, 0, 1)
            air_layout.addWidget(QtWidgets.QLabel("InVOLS (nm/V):"), 1, 0)
            air_layout.addWidget(self.air_invols_edit, 1, 1)
            air_layout.addWidget(QtWidgets.QLabel("GCI k (N/m):"), 2, 0)
            air_layout.addWidget(self.air_gci_edit, 2, 1)
            air_layout.addWidget(QtWidgets.QLabel("InVOLS H (nm/V):"), 3, 0)
            air_layout.addWidget(self.air_invols_h_edit, 3, 1)
            
            air_group.setLayout(air_layout)
            scroll_layout.addWidget(air_group)
        
        # Liquid values
        if liquid_has_data:
            liquid_group = QtWidgets.QGroupBox("Liquid Calibration Values")
            liquid_layout = QtWidgets.QGridLayout()
            
            self.lq_k0_edit = QtWidgets.QLineEdit()
            self.lq_k0_edit.setText(f"{self.k0_lq:.6f}")
            self.lq_k0_edit.setToolTip("Spring constant in N/m")
            
            self.lq_invols_edit = QtWidgets.QLineEdit()
            self.lq_invols_edit.setText(f"{self.involsValue_lq*1e9:.6f}")
            self.lq_invols_edit.setToolTip("Deflection sensitivity in nm/V")
            
            self.lq_gci_edit = QtWidgets.QLineEdit()
            gci_lq_text = "N/A" if (isinstance(self.GCI_cant_springConst_lq, float) and self.GCI_cant_springConst_lq != self.GCI_cant_springConst_lq) else f"{self.GCI_cant_springConst_lq:.6f}"
            self.lq_gci_edit.setText(gci_lq_text)
            self.lq_gci_edit.setToolTip("GCI spring constant in N/m (may be unavailable if SADER request fails)")
            
            self.lq_invols_h_edit = QtWidgets.QLineEdit()
            self.lq_invols_h_edit.setText(f"{self.invOLS_H_lq*1e9:.6f}")
            self.lq_invols_h_edit.setToolTip("InVOLS H in nm/V")
            
            liquid_layout.addWidget(QtWidgets.QLabel("k₀ (N/m):"), 0, 0)
            liquid_layout.addWidget(self.lq_k0_edit, 0, 1)
            liquid_layout.addWidget(QtWidgets.QLabel("InVOLS (nm/V):"), 1, 0)
            liquid_layout.addWidget(self.lq_invols_edit, 1, 1)
            liquid_layout.addWidget(QtWidgets.QLabel("GCI k (N/m):"), 2, 0)
            liquid_layout.addWidget(self.lq_gci_edit, 2, 1)
            liquid_layout.addWidget(QtWidgets.QLabel("InVOLS H (nm/V):"), 3, 0)
            liquid_layout.addWidget(self.lq_invols_h_edit, 3, 1)
            
            liquid_group.setLayout(liquid_layout)
            scroll_layout.addWidget(liquid_group)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        ok_button = QtWidgets.QPushButton("Apply")
        cancel_button = QtWidgets.QPushButton("Cancel")
        ok_button.clicked.connect(dlg.accept)
        cancel_button.clicked.connect(dlg.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dlg.setLayout(layout)
        
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            # Get edited values from UI
            try:
                def convert_value(text):
                    """Convert text to float, handling N/A as NaN"""
                    if text.upper() == "N/A":
                        return float('nan')
                    return float(text)
                
                if air_has_data:
                    self.k0_air = float(self.air_k0_edit.text())
                    self.involsValue_air = float(self.air_invols_edit.text()) / 1e9
                    self.GCI_cant_springConst_air = convert_value(self.air_gci_edit.text())
                    self.invOLS_H_air = float(self.air_invols_h_edit.text()) / 1e9
                
                if liquid_has_data:
                    self.k0_lq = float(self.lq_k0_edit.text())
                    self.involsValue_lq = float(self.lq_invols_edit.text()) / 1e9
                    self.GCI_cant_springConst_lq = convert_value(self.lq_gci_edit.text())
                    self.invOLS_H_lq = float(self.lq_invols_h_edit.text()) / 1e9
                
                # Determine which values to apply
                if air_radio.isChecked():
                    self._apply_air_calibration()
                elif liquid_radio.isChecked():
                    self._apply_liquid_calibration()
                elif both_radio.isChecked():
                    self._apply_both_calibrations()
            except ValueError as e:
                error_dlg = QtWidgets.QMessageBox(self)
                error_dlg.setWindowTitle("Invalid Input")
                error_dlg.setText(f"Error: Please enter valid numbers for all fields.\n{str(e)}")
                error_dlg.setIcon(QtWidgets.QMessageBox.Warning)
                error_dlg.exec()
    
    def _apply_air_calibration(self):
        """Apply air calibration values to session"""
        if hasattr(self, 'k0_air') and hasattr(self, 'involsValue_air') and \
           self.k0_air is not None and self.involsValue_air is not None:
            
            self.session.global_k = self.k0_air
            self.session.global_involts = self.involsValue_air
            
            # Store full results in session
            if not hasattr(self.session, 'thermal_tune_results'):
                self.session.thermal_tune_results = {}
            
            self.session.thermal_tune_results['air'] = {
                'k0': self.k0_air,
                'GCI_cant_springConst': self.GCI_cant_springConst_air,
                'involsValue': self.involsValue_air,
                'invOLS_H': self.invOLS_H_air,
                'filename': self.filename,
                'medium': 'air'
            }
            
            msg = f"Applied Air Calibration:\n\n" \
                  f"Spring Constant (k₀): {self.k0_air:.6f} N/m\n" \
                  f"Deflection Sensitivity (InVOLS): {self.involsValue_air*1e9:.3f} nm/V\n" \
                  f"GCI Spring Const: {self.GCI_cant_springConst_air:.6f} N/m\n" \
                  f"InVOLS H: {self.invOLS_H_air*1e9:.3f} nm/V"
            
            print(msg)
            self.open_msg_box(msg)
            
            # Update button states
            self.applyButton.setEnabled(False)
            
            # Notify other widgets if they're open
            if self.session.data_viewer_widget:
                self.session.data_viewer_widget.updatePlots()
        else:
            self.open_msg_box("Error: Air calibration data not available.\nPlease compute air calibration first.")
    
    def _apply_liquid_calibration(self):
        """Apply liquid calibration values to session"""
        if hasattr(self, 'k0_lq') and hasattr(self, 'involsValue_lq') and \
           self.k0_lq is not None and self.involsValue_lq is not None:
            
            self.session.global_k = self.k0_lq
            self.session.global_involts = self.involsValue_lq
            
            # Store full results in session
            if not hasattr(self.session, 'thermal_tune_results'):
                self.session.thermal_tune_results = {}
            
            self.session.thermal_tune_results['liquid'] = {
                'k0': self.k0_lq,
                'GCI_cant_springConst': self.GCI_cant_springConst_lq,
                'involsValue': self.involsValue_lq,
                'invOLS_H': self.invOLS_H_lq,
                'filename': self.filename,
                'medium': 'liquid'
            }
            
            msg = f"Applied Liquid Calibration:\n\n" \
                  f"Spring Constant (k₀): {self.k0_lq:.6f} N/m\n" \
                  f"Deflection Sensitivity (InVOLS): {self.involsValue_lq*1e9:.3f} nm/V\n" \
                  f"GCI Spring Const: {self.GCI_cant_springConst_lq:.6f} N/m\n" \
                  f"InVOLS H: {self.invOLS_H_lq*1e9:.3f} nm/V"
            
            print(msg)
            self.open_msg_box(msg)
            
            # Update button states
            self.applyButton.setEnabled(False)
            
            # Notify other widgets if they're open
            if self.session.data_viewer_widget:
                self.session.data_viewer_widget.updatePlots()
        else:
            self.open_msg_box("Error: Liquid calibration data not available.\nPlease compute liquid calibration first.")
    
    def _apply_both_calibrations(self):
        """Apply both calibrations, preferring air values"""
        if hasattr(self, 'k0_air') and hasattr(self, 'involsValue_air') and \
           self.k0_air is not None and self.involsValue_air is not None:
            
            self.session.global_k = self.k0_air
            self.session.global_involts = self.involsValue_air
            
            # Store full results in session
            if not hasattr(self.session, 'thermal_tune_results'):
                self.session.thermal_tune_results = {}
            
            self.session.thermal_tune_results['air'] = {
                'k0': self.k0_air,
                'GCI_cant_springConst': self.GCI_cant_springConst_air,
                'involsValue': self.involsValue_air,
                'invOLS_H': self.invOLS_H_air,
                'filename': self.filename,
                'medium': 'air'
            }
            
            if hasattr(self, 'k0_lq') and self.k0_lq is not None:
                self.session.thermal_tune_results['liquid'] = {
                    'k0': self.k0_lq,
                    'GCI_cant_springConst': self.GCI_cant_springConst_lq,
                    'involsValue': self.involsValue_lq,
                    'invOLS_H': self.invOLS_H_lq,
                    'filename': self.filename,
                    'medium': 'liquid'
                }
            
            msg = f"Applied Both Calibrations (using Air as global):\n\n" \
                  f"GLOBAL VALUES (Air):\n" \
                  f"Spring Constant (k₀): {self.k0_air:.6f} N/m\n" \
                  f"Deflection Sensitivity (InVOLS): {self.involsValue_air*1e9:.3f} nm/V\n\n"
            
            if hasattr(self, 'k0_lq') and self.k0_lq is not None:
                msg += f"Liquid Calibration also stored:\n" \
                       f"Spring Constant (k₀): {self.k0_lq:.6f} N/m\n" \
                       f"Deflection Sensitivity (InVOLS): {self.involsValue_lq*1e9:.3f} nm/V"
            
            print(msg)
            self.open_msg_box(msg)
            
            # Update button states
            self.applyButton.setEnabled(False)
            
            # Notify other widgets if they're open
            if self.session.data_viewer_widget:
                self.session.data_viewer_widget.updatePlots()
        else:
            self.open_msg_box("Error: Air calibration data not available.\nPlease compute air calibration first.")
    
    def reset_calibration(self):
        """Reset global calibration values"""
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Reset Calibration")
        dlg.setText("Are you sure you want to reset the global calibration values?\n\n"
                   "This will remove the applied thermal tune calibration from all modules.")
        dlg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        dlg.setDefaultButton(QtWidgets.QMessageBox.No)
        
        if dlg.exec() == QtWidgets.QMessageBox.Yes:
            self.session.global_k = None
            self.session.global_involts = None
            self.session.thermal_tune_results = {}
            
            # Update button states
            self.applyButton.setEnabled(True)
            
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Calibration Reset")
            msg_box.setText("Global calibration values have been reset.\n"
                           "All modules will now use default file metadata values.")
            msg_box.exec()
            
            print("Calibration reset: global_k and global_involts cleared")
            
            # # Notify other widgets if they're open
            # if self.session.data_viewer_widget:
            #     self.session.data_viewer_widget.updateCurve()

            if self.session.data_viewer_widget and self.session.data_viewer_widget is not None:
                try:
                    self.session.data_viewer_widget.updateCurve()
                except Exception as e:
                    print(f"Warning: Could not update data viewer: {e}")
            
    
    def save_results_to_png(self):
        """Save the current plot as PNG file"""
        # Use filename if available, otherwise prompt user
        if self.filename:
            base_name = os.path.splitext(self.filename)[0]
            default_path = f"{base_name}_thermal_analysis.png"
        else:
            default_path = "thermal_analysis.png"
        
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save as PNG", os.path.join(self.session.last_browsed_paths['thermal_files'], default_path), "PNG Images (*.png)"
        )
        
        if file_path:
            self.session.last_browsed_paths['thermal_files'] = os.path.dirname(file_path)
        
        if not file_path:
            return
        
        try:
            # Export the PlotItem directly; GraphicsLayoutWidget is not supported by ImageExporter.
            exporter = ImageExporter(self.p1)
            exporter.params['width'] = 1200
            exporter.params['height'] = 600
            exporter.export(fileName=file_path)
            
            print(f"Plot saved to: {file_path}")
            
            # Show success message
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Export Success")
            dlg.setText(f"Plot successfully saved to:\n{file_path}")
            dlg.exec()
        except Exception as e:
            print(f"Error saving PNG: {e}")
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Export Error")
            dlg.setText(f"Error saving plot:\n{str(e)}")
            dlg.setIcon(QtWidgets.QMessageBox.Warning)
            dlg.exec()
