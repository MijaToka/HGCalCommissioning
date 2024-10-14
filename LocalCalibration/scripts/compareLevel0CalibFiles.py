# author: 
# Pedro Silva, CERN
# Yulun Miao, Northwestern University
# Code to separate different eras automatically
# Run with
# python3 compareLevel0CalibFiles.py

import json
import numpy as np
from scipy import stats
import re
import glob
try:
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from JSONEncoder import *


def PedestalComparison(pedestal1, sigma1, pedestal2, sigma2, useError=False, p_threshold=0.1):
    x = np.divide(np.square(pedestal1 - pedestal2), np.hypot(sigma1,sigma2)) if useError else np.square(pedestal1 - pedestal2)
    x = x[np.isfinite(x)]
    chi_sq = np.sum(x)
    if(len(x)==0):
        return True
    p = 1 - stats.chi2.cdf(chi_sq, len(x)-1)
    return p > p_threshold

def CommonModePedestalComparison(CommonModePedestal1,CommonModePedestal2):
    # place-holder for now
    return True    

def CommonModeSlopeComparison(CommonModeSlope1,CommonModeSlope2):
    # place-holder for now
    return True    

def loadJson(url : str) -> dict:
    with open(url) as json_data:
        d = json.load(json_data)
    return d
    
def runEraDefinition(calibdir : str, calibfilename : str, pedestal_p_threshold : float = 0.1, outjson : str = 'era_defs.json'):

    # bulid run dictionary {relaynumber : calibration file}
    run_dict={}
    for url in glob.glob(f'{calibdir}/*/{calibfilename}'):
        try:
            relay = int(re.findall(f'Relay(\d+)/{calibfilename}', url)[0])
            run_dict[relay]=url
        except Exception:
            continue
    run_dict=dict(sorted(run_dict.items()))

    #compare
    ref_idx=[list(run_dict.keys())[0]]
    reason=['First Relay']
    for i in range(1,len(run_dict)):
        ref_file=list(run_dict.values())[i-1]
        new_file=list(run_dict.values())[i]

        #print(f'processing file {new_file}')
        #print(f'referencing {ref_file}')

        ref = loadJson(ref_file)
        new = loadJson(new_file)

        if len(new)==0:
            print(f'Invalid reference candidate {new_file}')
            continue
        
        #files have different sizes => update references
        if len(new)!=len(ref) :            
            ref_idx.append(list(run_dict.keys())[i])
            reason.append('Different sizes')
            continue
        
        #files have different modules => update reference
        ref_keys = set(ref.keys())
        new_keys = set(new.keys())
        if new_keys != ref_keys:
            ref_idx.append(list(run_dict.keys())[i])
            reason.append('Different modules')
            continue

        #Pedestal comparison
        passPedestalComparison=[]
        for typecode in ref.keys():
            x = np.array(ref[typecode]['ADC_ped'])
            sx = np.array(ref[typecode]['Noise'])
            y = np.array(new[typecode]['ADC_ped'])
            sy = np.array(new[typecode]['Noise'])
            for pedestal1,sigma1,pedestal2,sigma2 in zip(x,sx,y,sy):
                passPedestalComparison.append(PedestalComparison(pedestal1,sigma1,pedestal2,sigma2,True))
        #print(f'Pedestal comparison result:{passPedestalComparison}')
        if not all(passPedestalComparison):
            ref_idx.append(list(run_dict.keys())[i])
            reason.append('Incompatible pedestal')
            continue
        #Common mode pedestal comparison
        passCommonModePedestalComparison=[]
        for typecode in ref.keys():
            x = np.array(ref[typecode]['CM_ped'])
            y = np.array(new[typecode]['CM_ped'])
            for CM1,CM2 in zip(x,y):
                passCommonModePedestalComparison.append(CommonModePedestalComparison(CM1,CM2))
        #print(f'Common mode pedestal comparison result:{passCommonModePedestalComparison}')
        if not all(passCommonModePedestalComparison):
            ref_idx.append(list(run_dict.keys())[i])
            reason.append('Incompatible common mode pedestal')
            continue
        #Common mode slope comparison
        passCommonModeSlopeComparison=[]
        for typecode in ref.keys():
            x = np.array(ref[typecode]['CM_slope'])
            y = np.array(new[typecode]['CM_slope'])
            for CM1,CM2 in zip(x,y):
                passCommonModeSlopeComparison.append(CommonModeSlopeComparison(CM1,CM2))
        #print(f'Common mode slope comparison result:{passCommonModeSlopeComparison}')
        if not all(passCommonModeSlopeComparison):
            ref_idx.append(list(run_dict.keys())[i])
            reason.append('Incompatible common mode slope')
            continue
        
    
    eras={}
    print('| Era | Relay | Reason |')
    print('| --- | --- | --- |')
    for i,idx in enumerate(ref_idx):
        eras[i+1] = { 'modcalib':run_dict[idx], 'refrelay':idx, 'reason':reason[i] }
        print(f'| {i+1:5d} | {idx:10d} | {reason[i]} |')
    saveAsJson(outjson,eras)
    print(f'More details in {outjson}')

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input",
                        help='input directory=%(default)s',
                        default='/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/SepTB2024/calibrations/', type=str)
    parser.add_argument("-o", "--output",
                        help='output json file=%(default)s',
                        default='era_defs.json', type=str)
    parser.add_argument("-c", "--calibfilename",
                        help='calibration file name=%(default)s',
                        default='level0_calib_params.json', type=str)
    parser.add_argument("-p", "--minPval",
                        help='min p-val allowed to consider files equivalent=%(default)s',
                        default=0.1, type=float)
    args = parser.parse_args()

    runEraDefinition(calibdir=args.input, calibfilename=args.calibfilename, pedestal_p_threshold=args.minPval, outjson=args.output)
