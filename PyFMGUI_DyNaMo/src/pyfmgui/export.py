import contextlib
import os
import pandas as pd
import numpy as np
import traceback
import json
import tifffile

# Import for multiprocessing
import concurrent.futures
from functools import partial
from pyfmreader import loadfile
result_types = [
    'hertz_results',
    'ting_results', 
    'piezochar_results',
    'vdrag_results',
    'microrheo_results'
]

def unpack_hertz_result(row_dict, hertz_result):
    #this is to store the z height at the setpoint of from the force curve
    row_dict['z_at_setpoint'] = hertz_result.z_at_setpoint
    row_dict['hertz_ind_geometry'] = hertz_result.ind_geom
    row_dict['hertz_tip_parameter'] = hertz_result.tip_parameter
    row_dict['hertz_apply_BEC'] = hertz_result.apply_correction_flag
    row_dict['hertz_BEC_model'] = hertz_result.correction_model
    row_dict['hertz_fit_hline_on_baseline'] = hertz_result.fit_hline_flag
    row_dict['hertz_delta0'] = hertz_result.delta0
    row_dict['hertz_E'] = hertz_result.E0
    row_dict['hertz_f0'] = hertz_result.f0
    row_dict['hertz_slope'] = hertz_result.slope
    row_dict['hertz_poisson_ratio'] = hertz_result.poisson_ratio
    row_dict['hertz_sample_height'] = hertz_result.sample_height
    row_dict['hertz_MAE'] = hertz_result.MAE
    row_dict['hertz_MSE'] = hertz_result.MSE
    row_dict['hertz_RMSE'] = hertz_result.RMSE
    row_dict['hertz_Rsquared'] = hertz_result.Rsquared
    row_dict['hertz_chisq'] = hertz_result.chisq
    row_dict['hertz_redchi'] = hertz_result.redchi
    #  Intial POC  estimate from ROV or regula falsi method
    row_dict['hertz_z_c'] = hertz_result.z_c
    # this is indentation calculated from the POC estimated by the fit (hertz.delta0)
    row_dict['hertz_max_ind'] = hertz_result.max_ind
    

    return row_dict

def unpack_ting_result(row_dict, ting_result):
    row_dict['ting_ind_geometry'] = ting_result.ind_geom
    row_dict['ting_tip_parameter'] = ting_result.tip_parameter
    row_dict['ting_modelFt'] = ting_result.modelFt
    row_dict['ting_apply_BEC'] = ting_result.apply_bec_flag
    row_dict['ting_BEC_model'] = ting_result.bec_model
    row_dict['ting_fit_hline_on_baseline'] = ting_result.fit_hline_flag
    row_dict['ting_t0'] = ting_result.t0
    row_dict['ting_E0'] = ting_result.E0
    row_dict['ting_tc'] = ting_result.tc
    row_dict['ting_betaE'] = ting_result.betaE
    row_dict['ting_f0'] = ting_result.F0
    row_dict['ting_poisson_ratio'] = ting_result.poisson_ratio
    row_dict['ting_vdrag'] = ting_result.vdrag
    row_dict['ting_smooth_w'] = ting_result.smooth_w
    row_dict['ting_idx_tm'] = ting_result.idx_tm
    row_dict['ting_MAE'] = ting_result.MAE
    row_dict['ting_MSE'] = ting_result.MSE
    row_dict['ting_RMSE'] = ting_result.RMSE
    row_dict['ting_Rsquared'] = ting_result.Rsquared
    row_dict['ting_chisq'] = ting_result.chisq
    row_dict['ting_redchi'] = ting_result.redchi
    row_dict['ting_v0t_app_vel'] = ting_result.v0t
    row_dict['ting_v0r_ret_vel'] = ting_result.v0r

    return row_dict

def unpack_piezochar_result(row_dict, piezochar_result):
    row_dict['frequency'] = piezochar_result[0]
    row_dict['fi_degrees'] = piezochar_result[1]
    row_dict['amp_quotient'] = piezochar_result[2]
    return row_dict

def unpack_vdrag_result(row_dict, vdrag_result):
    row_dict['frequency'] = vdrag_result[0]
    row_dict['Bh'] = vdrag_result[1]
    row_dict['Hd_real'] = vdrag_result[2].real
    row_dict['Hd_imag'] = vdrag_result[2].imag
    row_dict['distances'] = vdrag_result[4]
    row_dict['fi_degrees'] = vdrag_result[5]
    row_dict['amp_quotient'] = vdrag_result[6]
    return row_dict

def unpack_microrheo_result(row_dict, microrheo_result):
    row_dict['frequency'] = microrheo_result[0]
    row_dict['G_storage'] = microrheo_result[1]
    row_dict['G_loss'] = microrheo_result[2]
    row_dict['losstan'] = np.array(row_dict['G_storage']) / np.array(row_dict['G_loss'])
    row_dict['fi_degrees'] = microrheo_result[-4]
    row_dict['amp_quotient'] = microrheo_result[-3]
    row_dict['B(0)'] = microrheo_result[-2]
    row_dict['w_ind'] = microrheo_result[-1]
    return row_dict

def get_file_results(result_type, file_metadata_and_results):
    file_id, filemetadata, file_result = file_metadata_and_results
    file_path = filemetadata['file_path']
    k = filemetadata['spring_const_Nbym']
    defl_sens = filemetadata['defl_sens_nmbyV']
    num_x_px,num_y_px = 0,0
    scan_x_size,scan_y_size=0,0
    if bool(filemetadata['force_volume']):

        num_x_px = int(filemetadata.get("num_x_pixels") )
        num_y_px = int(filemetadata.get("num_y_pixels"))
        #px size in m (for both jpk and nanscope files) 
        scan_x_size = float(filemetadata.get("scan_size_x") )
        scan_y_size = float(filemetadata.get("scan_size_y") )

    scan_size_m = json.dumps([scan_x_size,scan_y_size])
    map_size = json.dumps([num_x_px,num_y_px])

    file_results = []
    for curve_result in file_result:
        curve_indx = curve_result[0]
        row_dict = {
            'file_path': file_path, 'file_id': file_id, 
            'curve_idx': curve_indx ,'kcanti': k, 'defl_sens': defl_sens,
            'scan_size_x_y_m': scan_size_m,'map_size_x_y_pixels': map_size,
        }
        try:
            if result_type == 'hertz_results' and curve_result[1] is not None:
                hertz_result = curve_result[1]
                if hertz_result is not None:
                    row_dict = unpack_hertz_result(row_dict, hertz_result)
            elif result_type == 'ting_results' and curve_result[1] is not None:
                curve_indx = curve_result[0]
                ting_result = curve_result[1][0]
                hertz_result = curve_result[1][1]
                if ting_result is not None and hertz_result is not None:
                    row_dict = unpack_hertz_result(row_dict, hertz_result)
                    row_dict = unpack_ting_result(row_dict, ting_result)
            elif result_type == 'piezochar_results':
                curve_indx = curve_result[0]
                piezochar_result = curve_result[1]
                if piezochar_result is not None:
                    row_dict = unpack_piezochar_result(row_dict, piezochar_result)
            elif result_type == 'vdrag_results':
                curve_indx = curve_result[0]
                vdrag_result = curve_result[1]
                if vdrag_result is not None:
                    row_dict = unpack_vdrag_result(row_dict, vdrag_result)
            elif result_type == 'microrheo_results':
                curve_indx = curve_result[0]
                microrheo_result = curve_result[1]
                if microrheo_result is not None:
                    row_dict = unpack_microrheo_result(row_dict, microrheo_result)
        except Exception as e:
            file_results.append(row_dict)
            print(e)
            continue
        file_results.append(row_dict)
    return file_results

def prepare_export_results(session, progress_callback, range_callback, step_callback):
    # Map to relate result type to variable
    # where they are saved in the session.
    results = {
        'hertz_results': session.hertz_fit_results,
        'ting_results': session.ting_fit_results,
        'piezochar_results': session.piezo_char_results,
        'vdrag_results': session.vdrag_results,
        'microrheo_results': session.microrheo_results
    }
    # Dictionary to output results
    output = {
        'hertz_results': None,
        'ting_results': None, 
        'piezochar_results': None,
        'vdrag_results': None,
        'microrheo_results': None
    }
    # Loop through the results stored in the 
    # session and check if they are empty.
    for result_type, result in results.items():
        if result != {}:
            # Get files in session
            files_metadata_and_results = [(file_id, session.loaded_files[file_id].filemetadata, file_result) for (file_id, file_result) in result.items()]
            # Start multiprocessing
            count = 0
            range_callback.emit(len(files_metadata_and_results))
            file_results = []
            with concurrent.futures.ProcessPoolExecutor() as executor:
                # file_results = executor.map(partial(get_file_results, result_type), files_metadata_and_results)
                futures = [executor.submit(get_file_results, result_type, fileinfo) for fileinfo in files_metadata_and_results]
                for future in concurrent.futures.as_completed(futures):
                    file_results.append(future.result())
                    count+=1
                    progress_callback.emit(count)
            # Flatten result list
            flat_file_results = [item for sublist in file_results for item in sublist]
            # Create dataframe from list of dicts
            outputdf = pd.DataFrame(flat_file_results) # This consumes too much memory?
            # There are some parameters in the dicts that contain lists.
            # The explode method creates a new row from each item in the list.
            if result_type == 'piezochar_results':
                outputdf = outputdf.explode(['frequency', 'fi_degrees', 'amp_quotient'])
            elif result_type == 'vdrag_results':
                outputdf = outputdf.explode(['frequency', 'Bh', 'Hd_real', 'Hd_imag', 'distances', 'fi_degrees', 'amp_quotient'])
            elif result_type == 'microrheo_results':
                outputdf = outputdf.explode(['frequency', 'G_storage', 'G_loss', 'losstan', 'fi_degrees', 'amp_quotient'])
            # Sort values by file path and curve index
            outputdf.sort_values(by=['file_path', 'curve_idx'])
            # Assign results to proper result type
            output[result_type] = outputdf
    # Output loaded results
    session.prepared_results = output

def export_results(results, dirname, file_prefix):
    success_flag = False
    for result_type, result_df in results.items():
        if result_df is None:
            continue
        result_df.to_csv(os.path.join(dirname, f'{file_prefix}_{result_type}.csv'), index=False)
        success_flag = True
    return success_flag


def find_piezo_coord(nx,ny,file_path = ''):
    file_ext = file_path.split(os.extsep)[-1]

    piezoimg_corrd = np.arange(nx*ny).reshape((ny, nx))
    if file_ext =='jpk-force-map':
        
        piezoimg_corrd = np.asarray([row[::(-1)**i] for i, row in enumerate(piezoimg_corrd)])
    elif file_ext == 'h5-jpk':
        h5_uff = loadfile(file_path)
        piezoimg_corrd = h5_uff.imagedata['coordinate']
    
    map_corrd_2D = np.rot90(np.fliplr(piezoimg_corrd))
    map_corrd_lin = map_corrd_2D.flatten()
    return map_corrd_2D, map_corrd_lin
    

def tiff_results(df_fileid, dirname, file_prefix, result_type):
    success_check = 0

    # Input validation
    if not isinstance(df_fileid, pd.DataFrame) or df_fileid.empty:
        return

    first_row = df_fileid.iloc[0]
    name = first_row['file_id']
    extension = name.split('.')[-1]
    file_path =first_row['file_path'] 
    nx, ny = json.loads(first_row['map_size_x_y_pixels'])
    scan_size_x, scan_size_y = json.loads(first_row['scan_size_x_y_m'])

    Param1_lin = np.nan * np.ones(nx * ny)
    _, map_corrd_lin = find_piezo_coord(nx, ny, file_path)
    N_curve = len(map_corrd_lin)

    # Assign result field names only once
    result_id_1 = None
    result_id_2 = None
    if result_type == 'hertz_results':
        df_fileid['log10_hertz_E'] = np.log10(
            df_fileid["hertz_E"].replace(0, np.nan)).to_numpy()
        results_id = ['log10_hertz_E','hertz_E', 'hertz_delta0','z_at_setpoint']
    elif result_type == 'ting_results':
        df_fileid['log10_ting_E0'] = np.log10(
            df_fileid["ting_E0"].replace(0, np.nan)).to_numpy()
        results_id = ['log10_ting_E0','ting_E0', 'ting_betaE','z_at_setpoint']
    else:
        #results_id = None
        # Unknown result_type
        return

    for res in results_id:
        for i in range(N_curve):
            temp_cid = map_corrd_lin[i]
            df_found = df_fileid[df_fileid['curve_idx'].isin([temp_cid])]
            if len(df_found) == 1:
                Param1_lin[i] = df_found[res].iloc[0]

        # Reshape and flip maps
        Map_2d_1 = np.reshape(Param1_lin, (nx, ny))
        Map_2d_1 = np.flipud(Map_2d_1)

        # Save TIFFs if arrays are valid
        if Map_2d_1 is not None:

            tifffile.imwrite(
                os.path.join(dirname, f'{file_prefix}_{res}_{name}.tiff'),
                Map_2d_1,
                resolution=(nx * 1e-2 / scan_size_x, ny * 1e-2 / scan_size_y),
                resolutionunit='CENTIMETER'
            )
            success_check += 1
    return success_check

def export_to_tiff(res, dirname, file_prefix, result_type):
    success_flag = False
    if isinstance(res, pd.DataFrame):
        group_file = res.groupby(by='file_id')
    
        for name, df_fileid in group_file:
            success_check = tiff_results(df_fileid, dirname, file_prefix, result_type)
            if success_check > 1:
                success_flag = True
    return success_flag