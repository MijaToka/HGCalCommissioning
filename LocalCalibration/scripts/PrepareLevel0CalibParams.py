import os, re
import json
from argparse import ArgumentParser

try:
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from JSONEncoder import *

  
def buildLevel0CalibParams(input_json : dict, gainidx : int, cm : str) -> dict:
  
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
  for m,mdata in data['ped'].items():    
    nch = len(mdata['Channel'])
    typecode=m.replace('_','-')
    level0_calib[typecode] = getCalibTemplate(nch)
    level0_calib[typecode]['Channel'] = mdata['Channel'].copy()
    level0_calib[typecode]['Valid'] = mdata['Valid'].copy()
    level0_calib[typecode]['ADC_ped'][gainidx] = mdata['ADC_ped'].copy()
    level0_calib[typecode]['Noise'][gainidx] = mdata['ADC_rms'].copy()
    level0_calib[typecode]['CM_ped'][gainidx] = mdata[f'cm{cm}_ped'].copy()
    level0_calib[typecode]['CM_slope'][gainidx] = mdata[f'cm{cm}_slope'].copy()
      
  return level0_calib
  
  
def main():

  parser = ArgumentParser(description="Prepare the level 0 calibration json",epilog="Good luck!")
  parser.add_argument("-o", "--output",  default="level0_calib_params.json", help="output JSON file, default=%(default)r")
  parser.add_argument("-c", "--calibs",  default=None, help="{'ped':pedestals_file,'chinj',chinj_file,'mip':mip_file,...} default=%(default)r")
  parser.add_argument("--cm", default="2", help="common mode to use default=%(default)r")
  parser.add_argument("-g", "--gainIdx", default=1, type=int, help="Gain index: 0=80 fC, 1=160 fC, 2=320fC default=%(default)r")
  args = parser.parse_args()

  #parse arguments
  input_json = json.loads(args.calibs)
  exp_keys=['ped','mip','chinj']
  available_keys=[k in input_json for k in exp_keys]
  if sum(available_keys)==0:
    raise ValueError(f'Expect at least one of {exp_keys}')
  if not 'ped' in input_json:
    raise ValueError(f'ped key is always required')

  #build calib dict and save
  level0_calib = buildLevel0CalibParams(input_json, args.gainIdx, args.cm)
  saveAsJson(args.output, level0_calib)
  
if __name__=='__main__':
  main()
    
