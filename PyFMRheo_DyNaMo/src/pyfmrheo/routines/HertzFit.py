import numpy as np

from ..utils.force_curves import get_poc_RoV_method, get_poc_regulaFalsi_method, correct_tilt, correct_offset
from ..models.hertz import HertzModel

def doHertzFit(fdc, param_dict):
    # Get segment data
    if param_dict['curve_seg'] == 'extend':
        segment_data = fdc.extend_segments[-1][1]
    else:
        segment_data = fdc.retract_segments[-1][1]
        segment_data.zheight = segment_data.zheight[::-1]
        segment_data.vdeflection = segment_data.vdeflection[::-1]
    # Perform tilt correction
    if param_dict['offset_type'] == 'percentage':
        deltaz = segment_data.zheight.max() - segment_data.zheight.min()
        maxoffset = segment_data.zheight.min() + deltaz * param_dict['max_offset']
        minoffset = segment_data.zheight.min() + deltaz * param_dict['min_offset']
    else:
        maxoffset = param_dict['max_offset']
        minoffset = param_dict['min_offset']

    if param_dict['correct_tilt']:
        segment_data.vdeflection =\
            correct_tilt(
                segment_data.zheight, segment_data.vdeflection, maxoffset, minoffset
            )
    else:
        segment_data.vdeflection =\
            correct_offset(
                segment_data.zheight, segment_data.vdeflection, maxoffset, minoffset
            )
    # Get initial estimate of PoC
    if param_dict['poc_method'] == 'RoV':
        comp_PoC = get_poc_RoV_method(
            segment_data.zheight, segment_data.vdeflection, param_dict['poc_win'])
    else:
        comp_PoC = get_poc_regulaFalsi_method(
            segment_data.zheight, segment_data.vdeflection, param_dict['sigma'])
    poc = [comp_PoC[0], 0]
    
    # Downsample signal
    if param_dict['downsample_flag']:
        downfactor= len(segment_data.zheight) // param_dict['pts_downsample']
        idxDown = list(range(0, len(segment_data.zheight), downfactor))
        segment_data.zheight = segment_data.zheight[idxDown]
        segment_data.vdeflection = segment_data.vdeflection[idxDown]
    # Prepare data for the fit

    segment_data.get_force_vs_indentation(poc, param_dict['k'])
    indentation = segment_data.indentation
    force = segment_data.force

    contact_mask = indentation >= 0
    #to reduce the number of points in the non-contact region, we use a contact offset
    non_contact_mask = (indentation < 0)& (indentation>-1*param_dict['contact_offset'])

    ncont_ind = indentation[non_contact_mask]
    cont_ind = indentation[contact_mask]
    ncont_force = force[non_contact_mask]
    cont_force = force[contact_mask]
    if param_dict['fit_range_type'] == 'indentation':
        mask = (cont_ind >= param_dict['min_ind']) & (cont_ind <= param_dict['max_ind'])
        cont_ind, cont_force = cont_ind[mask], cont_force[mask]
    elif param_dict['fit_range_type'] == 'force':
        mask = (cont_force >= param_dict['min_force']) & (cont_force <= param_dict['max_force'])
        cont_ind, cont_force = cont_ind[mask], cont_force[mask]
    indentation = np.r_[ncont_ind, cont_ind]
    force = np.r_[ncont_force, cont_force]
    # Perform fit
    hertz_model = HertzModel(param_dict['contact_model'], param_dict['tip_param'])
    #storing the Z at setpoint in the model better for export 
    hertz_model.z_at_setpoint = fdc.z_at_setpoint
    hertz_model.fit_hline_flag = param_dict['fit_line']
    hertz_model.d0_init = param_dict['d0']
    if not param_dict['auto_init_E0']:
        hertz_model.E0_init = param_dict['E0']
    hertz_model.f0_init = param_dict['f0']
    if param_dict['fit_line']:
        hertz_model.slope_init = param_dict['slope']
    if param_dict.get('fit_method', None) is not None:
        hertz_model.fit_method = param_dict['fit_method']
    #constraining the bounds of delta0 form +- inf 
    hertz_model.delta0_max = np.max(segment_data.zheight)
    hertz_model.delta0_min = -hertz_model.delta0_max

    hertz_model.fit(indentation, force)

    hertz_model.z_c = -1*poc[0]
    true_indentation = indentation - hertz_model.delta0
    
    hertz_model.max_ind = np.max(true_indentation[true_indentation>0])
    # Return fitted model object
    return hertz_model
