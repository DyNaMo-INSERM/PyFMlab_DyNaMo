import os
import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq
import logging
logger = logging.getLogger()

import pyfmgui.const as cts
from pyfmrheo.utils.signal_processing import *
from pyfmgui.threading import Worker
from pyfmgui.compute import compute
from pyfmgui.widgets.get_params import get_params

from pyfmrheo.utils.force_curves import get_poc_RoV_method, get_poc_regulaFalsi_method,correct_tilt,correct_offset

class MicrorheoWidget(QtWidgets.QWidget):
    def __init__(self, session, parent=None):
        super(MicrorheoWidget, self).__init__(parent)
        self.session = session
        self.methodkey = None
        self.current_file = None
        self.offset_roi = None
        self.file_dict = {}
        self.session.microrheo_widget = self
        self.init_gui()
        if self.session.loaded_files != {}:
            self.updateCombo()
        if self.session.piezo_char_file_path:
            self.piezochar_text.setText(os.path.basename(self.session.piezo_char_file_path))

    def init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)

        params_layout = QtWidgets.QVBoxLayout()

        self.pushButton = QtWidgets.QPushButton("computeButton")
        self.pushButton.setText("Compute")
        self.pushButton.clicked.connect(self.do_MR)

        self.combobox = QtWidgets.QComboBox()
        self.combobox.currentTextChanged.connect(self.file_changed)

        piezochar_select_layout = QtWidgets.QGridLayout()
        self.piezochar_label = QtWidgets.QLabel("Piezo Char File")
        self.piezochar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.piezochar_label.setMaximumWidth(150)
        self.piezochar_text = QtWidgets.QTextEdit()
        self.piezochar_text.setMaximumHeight(40)
        self.piezochar_bttn = QtWidgets.QPushButton()
        self.piezochar_bttn.setText("Browse")
        self.piezochar_bttn.clicked.connect(self.load_piezo_char)
        self.clear_piezochar_bttn = QtWidgets.QPushButton()
        self.clear_piezochar_bttn.setText("Clear")
        self.clear_piezochar_bttn.clicked.connect(self.clear_piezo_char)

        piezochar_select_layout.addWidget(self.piezochar_label, 0, 0, 1, 1)
        piezochar_select_layout.addWidget(self.piezochar_text, 0, 1, 1, 2)
        piezochar_select_layout.addWidget(self.piezochar_bttn, 1, 2, 1, 1)
        piezochar_select_layout.addWidget(self.clear_piezochar_bttn, 1, 1, 1, 1)

        self.params = Parameter.create(name='params', children=cts.microrheo_params)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)

        self.l2 = pg.GraphicsLayoutWidget()

        params_layout.addWidget(self.combobox, 1)
        params_layout.addLayout(piezochar_select_layout, 1)
        params_layout.addWidget(self.paramTree, 3)
        params_layout.addWidget(self.pushButton, 1)
        params_layout.addWidget(self.l2, 2)

        self.l = pg.GraphicsLayoutWidget()
        
        ## Add 3 plots into the first row (automatic position)
        self.plotItem = pg.PlotItem(lockAspect=True)
        vb = self.plotItem.getViewBox()
        vb.setAspectLocked(lock=True, ratio=1)

        self.ROI = pg.ROI([0,0], [1,1], movable=False, rotatable=False, resizable=False, removable=False, aspectLocked=True)
        self.ROI.setPen("r", linewidht=2)
        self.ROI.setZValue(10)

        self.correlogram = pg.ImageItem(lockAspect=True)
        self.plotItem.addItem(self.correlogram)    # display correlogram
        
        self.p1 = pg.PlotItem()
        self.p2 = pg.PlotItem()
        self.p3 = pg.PlotItem()
        self.p4 = pg.PlotItem()
        self.p5 = pg.PlotItem()
        self.p6 = pg.PlotItem()
        self.p7 = pg.PlotItem()
        self.p8 = pg.PlotItem()
        self.p8legend = self.p8.addLegend()

        self.p3legend = self.p3.addLegend()
        self.p4legend = self.p4.addLegend()

        ## Put vertical label on left side
        main_layout.addLayout(params_layout, 1)
        main_layout.addWidget(self.l, 3)
    
    def closeEvent(self, evnt):
        self.session.microrheo_widget = None
    
    def clear(self):
        self.combobox.clear()
        self.l.clear()
        self.l2.clear()

    def do_MR(self):
        if not self.current_file:
            return
        if self.params.child('General Options').child('Compute All Files').value():
            filedict = self.session.loaded_files
        else:
            filedict = {self.session.current_file.filemetadata['Entry_filename']:self.session.current_file}
        if self.params.child('Analysis Params').child('Method').value() == "FFT":
            self.methodkey = "Microrheo"
        else:
            self.methodkey = "MicrorheoSine"
        self.session.microrheo_results = {}
        params = get_params(self.params, self.methodkey)
        params['piezo_char_data'] = self.session.piezo_char_data
        # compute(self.session, params, self.filedict, methodkey)
        logger.info(f'Started {self.methodkey}...')
        logger.info(f'Processing {len(filedict)} files')
        logger.info(f'Analysis parameters used: {params}')
        self.session.pbar_widget.reset_pbar()
        self.session.pbar_widget.set_label_text(f'Computing {self.methodkey}...')
        self.session.pbar_widget.show()
        self.session.pbar_widget.set_pbar_range(0, len(filedict))
        # Create thread to run compute
        self.thread = QtCore.QThread()
        # Create worker to run compute
        self.worker = Worker(compute, self.session, params, filedict, self.methodkey)
        # Move worker to thread
        self.worker.moveToThread(self.thread)
        # When thread starts run worker
        self.thread.started.connect(self.worker.run)
        self.worker.signals.progress.connect(self.reportProgress)
        self.worker.signals.range.connect(self.setPbarRange)
        self.worker.signals.step.connect(self.changestep)
        self.worker.signals.finished.connect(self.oncomplete) # Reset button
        # Start thread
        self.thread.start()
        # Final resets
        self.pushButton.setEnabled(False) # Prevent user from starting another
        # Update the gui
        self.updatePlots()
    
    def changestep(self, step):
        self.session.pbar_widget.set_label_sub_text(step)
    
    def reportProgress(self, n):
        self.session.pbar_widget.set_pbar_value(n)
    
    def setPbarRange(self, n):
        self.session.pbar_widget.set_pbar_range(0, n)
    
    def oncomplete(self):
        self.thread.terminate()
        self.session.pbar_widget.hide()
        self.session.pbar_widget.reset_pbar()
        self.pushButton.setEnabled(True)
        self.updatePlots()
        logger.info(f'{self.methodkey} completed!')
    
    def load_piezo_char(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
        	self, 'Open file', './', "Piezo Char Files (*.csv)"
        )
        if fname != "":
            self.session.piezo_char_file_path = fname
            self.piezochar_text.setText(os.path.basename(self.session.piezo_char_file_path))
            piezo_char_data_raw = pd.read_csv(self.session.piezo_char_file_path)
            piezo_char_data = piezo_char_data_raw[["frequency",  "fi_degrees",  "amp_quotient"]]
            self.session.piezo_char_data = piezo_char_data.groupby('frequency', as_index=False).median()
            if self.session.vdrag_widget:
                self.session.vdrag_widget.piezochar_text.setText(os.path.basename(self.session.piezo_char_file_path))
        else:
            self.piezochar_text.setText("")
    
    def clear_piezo_char(self):
        self.session.piezo_char_file_path = None
        self.session.piezo_char_data = None
        self.piezochar_text.setText("")
        if self.session.vdrag_widget:
                self.session.vdrag_widget.piezochar_text.setText("")

    def update(self):
        self.current_file = self.session.current_file
        self.updateParams()
        self.l2.clear()
        if self.current_file.isFV:
            self.l2.addItem(self.plotItem)
            self.plotItem.addItem(self.ROI)
            self.plotItem.scene().sigMouseClicked.connect(self.mouseMoved)
            # create transform to center the corner element on the origin, for any assigned image:
            if self.session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
                img = self.session.current_file.imagedata.get('Height(measured)', None)
                if img is None:
                    img = self.session.current_file.imagedata.get('Height', None)
                img = np.rot90(np.fliplr(img))
                shape = img.shape
                rows, cols = shape[0], shape[1]
                curve_coords = np.arange(cols*rows).reshape((cols, rows))
                if self.session.current_file.filemetadata['file_type'] == "jpk-force-map":
                    curve_coords = np.asarray([row[::(-1)**i] for i, row in enumerate(curve_coords)])
                    
                curve_coords = np.rot90(np.fliplr(curve_coords))
            elif self.session.current_file.filemetadata['file_type'] in cts.nanoscope_file_extensions+cts.asylum_file_extensions:
                img = self.session.current_file.piezoimg
                img = np.rot90(np.fliplr(img))
                shape = img.shape
                rows, cols = shape[0], shape[1]
                curve_coords = np.arange(cols*rows).reshape((cols, rows))
                curve_coords = np.rot90(np.fliplr(curve_coords))
            elif self.session.current_file.filemetadata['file_type'] in cts.jpk_h5_file:
                #img = self.session.current_file.piezoimg
                img = self.session.current_file.imagedata['CombinedHeightMeasured']
                img = np.rot90(np.fliplr(img))

                self.plotItem.setTitle("test Height (μm)")
                shape = img.shape
                rows, cols = shape[0], shape[1]
                curve_coords = self.session.current_file.imagedata['coordinate']
                curve_coords = np.rot90(np.fliplr(curve_coords))
                curve_coords = curve_coords
            self.correlogram.setImage(img)
            shape = img.shape
            rows, cols = shape[0], shape[1]
            self.plotItem.setXRange(0, cols)
            self.plotItem.setYRange(0, rows)

            self.session.map_coords = curve_coords
        self.session.current_curve_index = 0
        self.ROI.setPos(0, 0)
        self.updatePlots()
    
    def file_changed(self, file_id):
        self.session.current_file = self.session.loaded_files[file_id]
        self.session.current_curve_index = 0
        self.update()
    
    def updateCombo(self):
        self.combobox.clear()
        self.combobox.addItems(self.session.loaded_files.keys())
        index = self.combobox.findText(self.current_file.filemetadata['Entry_filename'], QtCore.Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.combobox.setCurrentIndex(index)
        self.update()
    
    def mouseMoved(self,event):
        vb = self.plotItem.vb
        scene_coords = event.scenePos()
        if self.correlogram.sceneBoundingRect().contains(scene_coords):
            items = vb.mapSceneToView(event.scenePos())
            pixels = vb.mapFromViewToItem(self.correlogram, items)
            x, y = int(pixels.x()), int(pixels.y())
            self.ROI.setPos(x, y)
            self.session.current_curve_index = self.session.map_coords[x,y]
            self.updatePlots()
            if self.session.data_viewer_widget is not None:
                self.session.data_viewer_widget.ROI.setPos(x, y)
                self.session.data_viewer_widget.updateCurve()
    
    def manual_override(self):
        pass

    def open_msg_box(self, message):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Export Status")
        dlg.setText(message)
        dlg.exec()

    def updatePlots(self):

        if not self.current_file:
            return

        self.l.clear()
        self.p1.clear()
        self.p2.clear()
        self.p3.clear()
        self.p3legend.clear()
        self.p4.clear()
        self.p4legend.clear()
        self.p5.clear()
        self.p6.clear()
        self.p7.clear()
        self.p8.clear()
        self.p8legend.clear()

        self.freqs = None
        self.G_storage = None
        self.G_loss = None
        self.Loss_tan = None
        self.ind_results = None
        self.defl_results = None
        self.hertz_result = None
        self.hertz_d0 = 0
        self.hertz_E = None
        self.wc = None

        analysis_params = self.params.child('Analysis Params')
        current_file_id = self.current_file.filemetadata['Entry_filename']
        current_file = self.current_file
        current_curve_indx = self.session.current_curve_index
        height_channel = analysis_params.child('Height Channel').value()
        deflection_sens = (self.current_file.filemetadata['defl_sens_nmbyV'] 
                if self.session.global_involts is None
                else self.session.global_involts)/ 1e9

        spring_k = (self.current_file.filemetadata['spring_const_Nbym']
            if self.session.global_k is None
            else self.session.global_k)
    
        method = analysis_params.child('Method').value()
        correct_tilt_flag = analysis_params.child('Correct Tilt').value()

        hertz_params = self.params.child('Hertz Fit Params')
        poc_method = hertz_params.child('PoC Method').value()
        poc_win = hertz_params.child('PoC Window').value() / 1e9
        poc_sigma = hertz_params.child('Sigma').value()

        force_curve = current_file.getcurve(current_curve_indx)
        force_curve.preprocess_force_curve(deflection_sens, height_channel)
        if self.session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
            force_curve.shift_height()
        modulation_segments = force_curve.modulation_segments

        if modulation_segments == []:
            self.open_msg_box(f'No modulation segments found in file:\n {current_file_id}')
            return

        microrheo_result = self.session.microrheo_results.get(current_file_id, None)

        if microrheo_result:
            for curve_indx, curve_microrheo_result in microrheo_result:
                try:
                    if curve_microrheo_result is None:
                        continue
                    if curve_indx == self.session.current_curve_index:
                        # print(curve_microrheo_result)
                        self.hertz_result = curve_microrheo_result[0]
                        self.hertz_d0 = self.hertz_result.delta0
                        self.hertz_E =self.hertz_result.E0
                        self.freqs = curve_microrheo_result[1]
                        self.G_storage = np.array(curve_microrheo_result[2])
                        self.G_loss = np.array(curve_microrheo_result[3])
                        self.Loss_tan = self.G_loss / self.G_storage
                        self.wc = curve_microrheo_result[-1]
                        if method == 'Sine Fit':
                            self.ind_results = curve_microrheo_result[4]
                            self.defl_results = curve_microrheo_result[5]
                except Exception:
                    continue
        #approach data
        self.seg_data = force_curve.extend_segments[-1][1]
        self.p7.plot(self.seg_data.zheight, self.seg_data.vdeflection)
        
        self.update_tilt_range()

        # Perform tilt correction
        if correct_tilt_flag:
            self.seg_data.vdeflection = correct_tilt(
                self.seg_data.zheight, self.seg_data.vdeflection, self.maxoffset, self.minoffset
            )
        else:
            self.seg_data.vdeflection = correct_offset(
                self.seg_data.zheight, self.seg_data.vdeflection, self.maxoffset, self.minoffset
            )

        comp_PoC = [0, 0]
        if poc_method == 'RoV':
            comp_PoC = get_poc_RoV_method(self.seg_data.zheight, self.seg_data.vdeflection, poc_win)
        else:
            comp_PoC = get_poc_regulaFalsi_method(self.seg_data.zheight, self.seg_data.vdeflection, poc_sigma)
        
        if comp_PoC is not None:
            poc = [comp_PoC[0], 0]
        else:
            poc = [0, 0]
        
        force_curve.get_force_vs_indentation(poc, spring_k)
        indapp = self.seg_data.indentation 
        forceapp = self.seg_data.force

        if self.wc is None:
            self.wc = indapp.max()

        self.wc *= 1e9
        analysis_params.child('Computed Working Ind.').setValue(self.wc)
        self.p8.plot(indapp - self.hertz_d0 , forceapp)
        vertical_line = pg.InfiniteLine(pos=0, angle=90, pen='y', movable=False, label='Init d0', labelOpts={'color':'y', 'position':0.5})
        self.p8.addItem(vertical_line, ignoreBounds=True)
        style = pg.PlotDataItem(pen=None)

        if self.hertz_result is not None:
            x = indapp
            y = self.hertz_result.eval(x)
            self.p8.plot(x - self.hertz_d0, y, pen='g', name='Fit')
            self.p8legend.addItem(style, f'Hertz E: {self.hertz_E:.2f} Pa')

        if analysis_params.child('Overwrite Working Ind.').value():
            set_ind = analysis_params.child('Set Working Ind.').value()
            self.p8legend.addItem(style, f'Set Working Ind.: {self.wc:.2f} nm')
        else:
            self.p8legend.addItem(style, f'Computed Working Ind.: {self.wc:.2f} nm')

        t0 = 0
        t0_2 = 0
        n_segments = len(modulation_segments)
        if method == 'FFT':
            for i, (_, segment) in enumerate(modulation_segments):
                time = segment.time
                freq = segment.segment_metadata['frequency']
                label = f"{freq} Hz"
                deltat = time[1] - time[0]
                nfft = len(segment.vdeflection)
                W = fftfreq(nfft, d=deltat)
                fft_height = fft(segment.zheight, nfft)
                psd_height = fft_height * np.conj(fft_height) / nfft
                fft_deflect = fft(segment.vdeflection, nfft)
                psd_deflect = fft_deflect * np.conj(fft_deflect) / nfft
                L = np.arange(1, np.floor(nfft/2), dtype='int')
                self.p3.plot(W[L], psd_height[L].real, pen=(i,n_segments), name=f"{freq} Hz")
                self.p4.plot(W[L], psd_deflect[L].real, pen=(i,n_segments), name=f"{freq} Hz")
                plot_time = time + t0
                self.p1.plot(plot_time, segment.zheight, pen=(i,n_segments), name=label)
                self.p2.plot(plot_time, segment.vdeflection, pen=(i,n_segments), name=label)
                t0 = plot_time[-1]
        
            self.p3.setLabel('left', 'zHeight PSD')
            self.p3.setLabel('bottom', 'Frequency', 'Hz')
            self.p3.setTitle("FFT")
            self.p3.setLogMode(True, False)
            self.p3.addLegend()

            self.p4.setLabel('left', 'Deflection PSD')
            self.p4.setLabel('bottom', 'Frequency', 'Hz')
            self.p4.setTitle("FFT")
            self.p4.setLogMode(True, False)
            self.p4.addLegend()

        elif method == 'Sine Fit':
            for i, (_, segment) in enumerate(modulation_segments):
                time = segment.time
                freq = segment.segment_metadata['frequency']
                label = f"{freq} Hz"
                zheight, vdeflection, time_2 =\
                    detrend_rolling_average(freq, segment.zheight, segment.vdeflection, time, 'zheight', 'deflection', [])
                indentation = zheight -  vdeflection
                plot_time_2 = time_2 - time_2[0] + t0_2
                self.p3.plot(plot_time_2 , indentation, pen='w')
                self.p4.plot(plot_time_2, vdeflection, pen='w')
                if self.ind_results is not None and self.defl_results is not None:
                    idx = int((np.abs(np.array(self.freqs) - freq)).argmin())
                    indentation_res = self.ind_results[idx].eval(time=time_2)
                    deflection_res = self.defl_results[idx].eval(time=time_2)
                    self.p3.plot(plot_time_2, -1 * indentation_res, pen='g')
                    self.p4.plot(plot_time_2, deflection_res, pen='g')
                plot_time_1 = time + t0
                self.p1.plot(plot_time_1, segment.zheight, pen=(i,n_segments), name=label)
                self.p2.plot(plot_time_1, segment.vdeflection, pen=(i,n_segments), name=label)
                t0 = plot_time_1[-1]
                t0_2 = plot_time_2[-1]

            self.p3.setLabel('left', 'Detrended Indentation', 'm')
            self.p3.setLabel('bottom', 'Time', 's')
            self.p3.setTitle("Detrended Indentation-Time")
            self.p3.setLogMode(False, False)
            self.p3.addLegend()

            self.p4.setLabel('left', 'Detrended Deflection', 'm')
            self.p4.setLabel('bottom', 'Time', 's')
            self.p4.setTitle("Detrended Deflection-Time")
            self.p4.setLogMode(False, False)

            if self.ind_results is not None and self.defl_results is not None:
                style = pg.PlotDataItem(pen='g')
                self.p3legend.addItem(style, "Sine Fit")
                self.p4legend.addItem(style, "Sine Fit")
         
        if self.G_storage is not None and self.G_loss is not None:
            self.p5.plot(self.freqs, self.G_storage, pen='r', symbol='o', symbolBrush='r', name="G Storage")
            self.p5.plot(self.freqs, self.G_loss, pen='b', symbol='o', symbolBrush='b', name="G Loss")
        
        if self.Loss_tan is not None:
            self.p6.plot(self.freqs, self.Loss_tan, pen='g', symbol='o', symbolBrush='g')
        
        self.p1.setLabel('left', 'zHeight', 'm')
        self.p1.setLabel('bottom', 'Time', 's')
        self.p1.setTitle("Modulation zHeight-Time")
        self.p1.addLegend()

        self.p2.setLabel('left', 'Deflection', 'm')
        self.p2.setLabel('bottom', 'Time', 's')
        self.p2.setTitle("Modulation Deflection-Time")
        self.p2.addLegend()
        
        self.p5.setLabel('left', 'Complex Modulus', 'Pa')
        self.p5.setLabel('bottom', 'Frequency', 'Hz')
        self.p5.setTitle("Complex Modulus-Frequency")
        self.p5.setLogMode(True, True)
        self.p5.addLegend()

        self.p6.setLabel('left', 'Loss Tangent')
        self.p6.setLabel('bottom', 'Frequency', 'Hz')
        self.p6.setTitle("Loss Tangent-Frequency")
        self.p6.setLogMode(True, False)

        self.p7.setLabel('left', 'Deflection', 'm')
        self.p7.setLabel('bottom', 'zHeight', 'm')
        self.p7.setTitle("Approach zHeight-Deflection")
        self.p7.addLegend()

        self.p8.setLabel('left', 'Force', 'N')
        self.p8.setLabel('bottom', 'Indentation', 'm')
        self.p8.setTitle("Approach Force-Indentation")
        self.p8.addLegend()

        self.l.addItem(self.p7)
        self.l.addItem(self.p8)
        self.l.nextRow()
        self.l.addItem(self.p1)
        self.l.addItem(self.p2)
        self.l.nextRow()
        self.l.addItem(self.p3)
        self.l.addItem(self.p4)
        self.l.nextRow()
        self.l.addItem(self.p5)
        self.l.addItem(self.p6)

    def update_tilt_range(self):
        dataItems = self.p7.listDataItems()
        analysis_params = self.params.child('Analysis Params')
        offset_type = analysis_params.child('Offset Type').value()
        if offset_type == 'percentage':
            deltaz = self.seg_data.zheight.max() - self.seg_data.zheight.min()
            maxperc = analysis_params.child('Perc. Max Offset').value() / 1e2
            minperc = analysis_params.child('Perc. Min Offset').value() / 1e2
            self.maxoffset = self.seg_data.zheight.min() + deltaz * maxperc
            self.minoffset = self.seg_data.zheight.min() + deltaz * minperc
        else:
            self.maxoffset = analysis_params.child(
                'Abs. Max Offset').value() / 1e9
            self.minoffset = analysis_params.child(
                'Abs. Min Offset').value() / 1e9
        if self.offset_roi is not None:
            self.p7.removeItem(self.offset_roi)
        self.offset_roi = pg.LinearRegionItem(
            brush=(50, 50, 200, 0), pen='w', movable=False)
        self.offset_roi.setZValue(10)
        self.offset_roi.setClipItem(dataItems[0])
        self.p7.removeItem(self.offset_roi)
        self.p7.addItem(self.offset_roi, ignoreBounds=True)
        self.offset_roi.setRegion([self.minoffset, self.maxoffset])
        
    def update_global_k_ols(self):
        analysis_params = self.params.child('Analysis Params')

        if analysis_params.child('Overwrite Deflection Sensitivity').value():
            self.session.global_involts = analysis_params.child('Global Deflection Sensitivity').value()
        else:
            self.session.global_involts = None
            analysis_params.child('Deflection Sensitivity').setValue(
                self.current_file.filemetadata['defl_sens_nmbyV'])
        if analysis_params.child('Overwrite Spring Constant').value():
            self.session.global_k = analysis_params.child('Global Spring Constant').value()
        else:
            self.session.global_k = None
            analysis_params.child('Spring Constant').setValue(
                self.current_file.filemetadata['spring_const_Nbym'])

    def updateParams(self):
        # Updates params related to the current file
        analysis_params = self.params.child('Analysis Params')
        analysis_params.child('Height Channel').setValue(
            self.current_file.filemetadata['height_channel_key'])
        
        if self.session.global_k is None:
            analysis_params.child('Spring Constant').setValue(
                self.current_file.filemetadata['spring_const_Nbym'])
        if self.session.global_involts is None:
            analysis_params.child('Deflection Sensitivity').setValue(
                self.current_file.filemetadata['defl_sens_nmbyV'])
        
        analysis_params.child(
        'Overwrite Deflection Sensitivity').sigValueChanged.connect(self.update_global_k_ols)
     
        analysis_params.child(
        'Overwrite Spring Constant').sigValueChanged.connect(self.update_global_k_ols)
        analysis_params.child(
        'Global Deflection Sensitivity').sigValueChanged.connect(self.update_global_k_ols)
        analysis_params.child(
        'Global Spring Constant').sigValueChanged.connect(self.update_global_k_ols)

        analysis_params.child(
            'Correct Tilt').sigValueChanged.connect(self.updatePlots)
        analysis_params.child(
            'Offset Type').sigValueChanged.connect(self.updatePlots)
        analysis_params.child(
            'Perc. Min Offset').sigValueChanged.connect(self.updatePlots)
        analysis_params.child(
            'Perc. Max Offset').sigValueChanged.connect(self.updatePlots)
        analysis_params.child(
            'Abs. Min Offset').sigValueChanged.connect(self.updatePlots)
        analysis_params.child(
            'Abs. Max Offset').sigValueChanged.connect(self.updatePlots)

