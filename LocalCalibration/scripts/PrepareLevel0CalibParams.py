import os, re
import json
from argparse import ArgumentParser, RawTextHelpFormatter

try:
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from JSONEncoder import *

def getCalibTemplate(nch) :
  """ builds the default template for the level-0 calibration json file"""
  
  z=np.zeros(nch).tolist()
  o=np.ones(nch).tolist()
  
  calib_templ_dict = {
    'Channel': [i for i in range(nch)],
    'ADC_ped': z,
    'Noise': z,
    'CM_ped': z,
    'CM_slope': z,
    'BXm1_slope': z,
    'BXm1_ped': z,
    'TOTtoADC': o,
    'TOT_ped': z,
    'TOT_lin': z,
    'TOT_P0': z,
    'TOT_P1': z,
    'TOT_P2': z,
    'TOA_CTDC': np.zeros((nch, 32)).tolist(),
    'TOA_FTDC': np.zeros((nch, 8)).tolist(),
    'TOA_TW': np.zeros((nch, 3)).tolist(),
    'MIPS_scale': o,
    'Valid': o
  }
  
  return calib_templ_dict


def buildLevel0CalibParams(input_json : dict) -> dict:
  
  #load data to merge
  data : dict = {}
  for k,f in input_json.items():
    if type(f)==str:
      with open(f) as jsonf:
        data[k] = json.load(jsonf)
    else:
      data[k] = f
      
  #build the calibration dict
  level0_calib : dict = {}

  if 'ped' in data:
    for m,mdata in data['ped'].items():    
      nch = len(mdata['Channel'])
      typecode=m.replace('_','-')
      if "MH" in typecode:
          cm = "4"
      elif "ML" in typecode:
          cm = "2"
      level0_calib[typecode] = getCalibTemplate(nch)
      level0_calib[typecode]['Channel'] = mdata['Channel'].copy()
      level0_calib[typecode]['Valid'] = mdata['Valid'].copy()
      level0_calib[typecode]['ADC_ped'] = mdata['ADC_ped'].copy()
      level0_calib[typecode]['Noise'] = mdata['ADC_rms'].copy()
      level0_calib[typecode]['CM_ped'] = mdata[f'cm{cm}_ped'].copy()
      level0_calib[typecode]['CM_slope'] = mdata[f'cm{cm}_slope'].copy()
  #add the calpulse results also
  if 'calpulse' in data:
    
    for m,mdata in data['calpulse'].items():
      nch = len(mdata['adc0'])
      typecode = m.replace('_','-')      

      #if by chance this typecode does not existing already the max we can do
      #is to assign the pedestal from the one fit in the CalPulse run
      if not typecode in level0_calib :
        level0_calib[typecode] = getCalibTemplate(nch)
        level0_calib[typecode]['ADC_ped'] = mdata['adc0'].copy()

      #
      mdata_np = dict( [(k,np.array(v)) for k,v in mdata.items()] )
      k = mdata_np['adc2fC']
      p = mdata_np['adc0']
      ktot = mdata_np['tot2fC']
      ptot = mdata_np['tot0']
      x0 = mdata_np['totlin']
      a = mdata_np['a']      
      level0_calib[typecode]['TOTtoADC'] = (ktot/k).tolist()
      level0_calib[typecode]['TOT_ped'] = (ptot - p*k/ktot).tolist()
      level0_calib[typecode]['TOT_lin'] = x0.tolist()
      level0_calib[typecode]['TOT_P2'] = (a / k).tolist()
      level0_calib[typecode]['TOT_P1'] = ((ktot -2*a*x0) / k).tolist()
      level0_calib[typecode]['TOT_P0'] = ((a*x0*x0-ktot*ptot) / k + p).tolist()
  return level0_calib
  
  
def main():

  parser = ArgumentParser(
    description="""
    [Prepare the level 0 calibration json]
    The json can be prepared using the parameters described below. 
    To check carefully the distributions you can use the calibrations viewer app
    Some back of the envelope values to keep in mind

    | Quantity  | order of magnitude             | example                                  |
    | ========= | ============================== | ======================================== |
    | ADC_ped   | 100-200                        | 150                                      |
    | --------- | ------------------------------ | ---------------------------------------- |
    | ADC2fC    | fsc / (1024-pedestal)          | 0.19 for fsc = 160 fC and ADC_ped=150    |
    | --------- | ------------------------------ | ---------------------------------------- |
    | TOTtoADC  | (10pC / 2^12) / ( fsc / 2^10 ) | 15                                       |
    | --------- | ------------------------------ | ---------------------------------------- |  
    | MIP_scale | q_MIP / ADC2fC                 | for {120,200,300} microns                |
    |           |                                | q_MIP = {1.2, 1.9 3.5} fC                |
    |           |                                | for ADC2fC=0.19 300 microns MIP_scale=18 |
    """,
    epilog="Good luck!", formatter_class=RawTextHelpFormatter)
  parser.add_argument("-o", "--output",   default="level0_calib_params.json", help="output JSON file, default=%(default)r")
  parser.add_argument("-p", "--ped",      default=None, help="Pedestal file default=%(default)r")
  parser.add_argument("-c", "--calpulse", default=None, help="Calpulse file default=%(default)r")
  parser.add_argument("-m", "--mip", default=None, help="MIP file default=%(default)r")
  args = parser.parse_args()

  #parse arguments
  input_json = {}
  if not args.ped is None: input_json['ped'] = args.ped
  if not args.calpulse is None: input_json['calpulse'] = args.calpulse
  if not args.mip is None: input_json['mip'] = args.mip
  exp_keys=['ped','mip','calpulse']
  available_keys=[k in input_json for k in exp_keys]
  if sum(available_keys)==0:
    raise ValueError(f'Expect at least one of {exp_keys}')

  #build calib dict and save
  level0_calib, cm = buildLevel0CalibParams(input_json)
  saveAsJson(args.output, level0_calib)
  
if __name__=='__main__':
  main()
    
