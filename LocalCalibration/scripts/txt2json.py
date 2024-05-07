#! /usr/bin/env python3
# Author: Izaak Neutelings (March 2024)
# Description:
#   Convert txt files with HGCal calibration parameters with to JSON format.
# Sources:
#   https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_0_pre0/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitCalibrationESProducer.cc
#   https://github.com/CMS-HGCAL/cmssw/blob/hgcal-condformat-HGCalNANO-13_2_0_pre2_gain/CalibCalorimetry/HGCalPlugins/test/hgcal_yamlconfig_writer.py
import os, re
import json
from datetime import datetime
from HGCalCommissioning.LocalCalibration.JSONEncoder import CompactJSONEncoder

# DEFAULTS
modnames = [ # module typecodes
  # https://github.com/pfs/Geometry-HGCalMapping/blob/main/ModuleMaps/modulelocator_test.txt
  # https://docs.google.com/spreadsheets/d/1Kvej2OUE_1LFkd1kY0L-r7VuaUmhdMC2Z7Yi58bIeGM/edit#gid=0
  # https://edms.cern.ch/ui/#!master/navigator/document?D:101059405:101148061:subDocs
  'ML-F3PT-TX-0003', # DQM v0
  'ML-F3PC-MX-0003', # DQM v1
  'ML-F3PC-MX-0004', # DQM v2
  'ML-F2WX-IH-0011', # DQM v3
  'ML-F3PT-TX-0001', # DQM v4
  'ML-F3PT-TX-0002', # DQM v5
]
rename_dict = { # rename keys
  'Pedestal':    'ADC_ped',
  'CM_slope':    'CM_ped', # slope/offset columns were switched
  'CM_offset':   'CM_slope', # slope/offset columns were switched
  'BXm1_offset': 'BXm1_ped', # slope/offset columns were switched
}
gainkeys = [ # gain-dependent keys
  'ADC_ped', 'ADCtofC', 'Noise', 'CM_slope', 'CM_ped', 'BXm1_slope', 'BXm1_ped'
]
default_dict = {
  # https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_0_pre0/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitCalibrationESProducer.cc
  # https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_0_pre0/RecoLocalCalo/HGCalRecAlgos/interface/HGCalCalibrationParameterSoA.h
  #'Gain':        2,
  'ADC_ped':     91.,  # Pedestal
  'Noise':       2.0,
  'CM_slope':    0.25, # (rho ?)
  'CM_ped':      91.,  # CM_offset (cm ?)
  'BXm1_slope':  0.,
  'BXm1_ped':    91.,  # redundant, unused !
  'ADCtofC':     0.19,
  'TOTtofC':     2.47,
  'TOT_ped':     9.,
  'TOT_lin':     200.,
  'TOT_P0':      145.0972,
  'TOT_P1':      1.0125,
  'TOT_P2':      0.0037,
  'TOAtops':     24.41,
  'MIPS_scale':  1.,
  'Valid':       1, # "integer boolean": 0 or 1
}


def green(string,**kwargs):
  return "\033[32m%s\033[0m"%string
  

def readfeather(infname,data_dict=None,maxrows=-1,verb=0):
  """Read & parse feather file into a dictionary."""
  keys_dict = { } # column index -> column key
  if data_dict==None:
    data_dict = { }
  raise NotImplementedError("Feather not implemented...")
  print(f">>> readtxt:  Found {len(data_dict)} modules: {', '.join(data_dict.keys())}...")
  return data_dict, keys_dict


def readtxt(infname,data_dict=None,maxrows=-1,igain=-1,verb=0):
  """Read & parse txt file into a dictionary."""
  keys_dict = { } # column index -> column key
  if data_dict==None:
    data_dict = { }
  
  # READ TXT FILE and convert to DICT
  imod = -1 # current module
  module = None # current module
  with open(infname,'r') as infile:
    for irow, line in enumerate(infile):
      if maxrows>=1 and irow>maxrows:
        print(f">>> readtxt:    Stop reading: irow={irow}, maxrows={maxrows}")
        continue
      cols = line.split()
      if irow==0: # read header
        for icol, key in enumerate(cols):
          if key in rename_dict:
            oldkey = key
            key = rename_dict[key]
            print(f">>> readtxt:    Renamed column {oldkey!r} ->  {key!r}")
          keys_dict[icol] = key
          #data_dict[key]  = [ ]
        keys_dict[icol]
      else: # read data
        for icol, val in enumerate(cols):
          key = keys_dict[icol]
          if key=='Channel': # convert hexidecimal to decimal integer
            oldval = val
            val = 0x3FF & int(val,16) # only keep first 10 bits
            #val = int(val,16)%1024 # only keep first 10 bits
            if verb>=3:
              print(f">>> readtxt:    channel = {oldval} & 0x3FF = {val}")
            if val==0: # start new module !
              oldimod = imod
              oldmod  = module
              imod    = min(len(modnames)-1,imod+1)
              module  = modnames[imod]
              if verb>=1:
                print(f">>> readtxt:    Start new module: channel={oldval!r}->{val!r}, imod={oldimod} -> {imod},"
                      f" typecode={oldmod!r} -> {module!r}")
              if module in data_dict:
                print(f">>> readtxt:  WARNING! Overwriting data for module {module!r} !!!")
              data_dict[module] = { k: ([[],[],[]] if k in gainkeys else [ ] ) for k in keys_dict.values() }
            if verb>=2:
              print(f">>> readtxt:  Converting {oldval!r} -> {val!r}")
          elif key in ['Gain','Valid']: # convert to integer
            val = int(val)
          elif key not in ['Module']: # convert to float
            val = float(val)
          #print(data_dict)
          if key in gainkeys: # gain-dependent parameter: list of lists with values
            if igain>=0: # add value only to list at index igain
              data_dict[module][key][igain].append(val) # add to list at index igain
            else: # add placeholders to all lists
              data_dict[module][key][0].append(val) # add to gain=1 ( 80fC)
              data_dict[module][key][1].append(val) # add to gain=2 (160fC)
              data_dict[module][key][2].append(val) # add to gain=4 (320fC)
          else: # gain-independent parameter: list of values
            data_dict[module][key].append(val)
        #data_dict['Module'].append(modnames[max(imod,0)])
  print(f">>> readtxt:  Found {len(data_dict)} modules: {', '.join(data_dict.keys())}...")
  return data_dict, keys_dict
  

def txt2json(infname,outfname=None,outdir=None,maxrows=-1,compress=False,verb=0):
  """Convert txt file with calibration parameters to JSON. Basic structure:
  {
    typecode: {
      parameter: [ values ] # gain-independent (Channel, TOT_*, TOAtops, MIPS_scale)
      parameter: [   # gain-dependent (ADC_ped, ADCtofC, Noise, CM_slope, CM_ped, BXm1_slope, BXm1_ped)
        [ values ],  # index=0, gain=1, charge= 80 fC
        [ values ],  # index=1, gain=2, charge=160 fC
        [ values ],  # index=2, gain=4, charge=320 fC
      ]
    }
  }
  Note:
  - Typecode follows 'MM-TTTT-LL-NNNN' pattern, e.g. 'ML-F3PT-TX-0003'
    https://edms.cern.ch/ui/#!master/navigator/document?D:101059405:101148061:subDocs
  - Parameter keys are renamed using rename_dict so they can be parsed in CMSSW.
    https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_0_pre0/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitCalibrationESProducer.cc
  """
  
  # FILENAME OUT defaults
  if outfname==None:
    outfname = re.sub(r"\.(txt|feather)$",'',os.path.basename(infname))+".json"
    #outfname = os.path.basename(infname).replace('.txt','.json')
  if outdir!=None:
    outfname = os.path.join(outdir,os.path.basename(outfname))
  if compress and outfname[-3:]!='.gz':
    outfname += '.gz'
  
  # DATA DICT to be written to JSON
  #data_dict = { 'Module': [ ] } # column key -> array values
  data_dict = { } # module type code -> column key -> array values
  ###data_dict['Metadata'] = { # meta data for self-documentation
  ###  'date': datetime.now().strftime("Created %d/%m/%Y, %H:%M:%S"),
  ###  'source': [infname],
  ###}
  
  # READ & PARSE INPUT FILE
  print(f">>> txt2json: Reading {green(infname)}...")
  if '.feather' in infname[-8:]: # not implemented
    data_dict, keys_dict = readfeather(infname,data_dict,verb=verb)
  else: # assume txt file
    data_dict, keys_dict = readtxt(infname,data_dict,verb=verb)
  
  # LOOP over MODULES
  key0 = 'Channel' #keys_dict[0]
  for module in data_dict:
    print(f">>> txt2json: Checking module {module!r}...")
    if '-' not in module: continue # skip metadata
    nrows = len(data_dict[module][key0])
    
    # SANITY CHECK
    for key in data_dict[module]:
      nrowsset = [ ]
      if key in gainkeys: # gain-dependent parameter: list of lists with values
        assert len(data_dict[module][key])==3, f"len(data_dict[{module!r}][{key!r}])={len(data_dict[module][key])} must be 3!"
        for i in [0,1,2]:
          nrows_ = len(data_dict[module][key][i])
          if nrows!=nrows_:
            print(f">>> txt2json: WARNING! Columns appear to have different number of rows!!! {key0!r} has {nrows}, {key!r} has {nrows_} for igain={i}")
      else: # gain-independent parameter: list of values
        nrows_ = len(data_dict[module][key])
        if nrows!=nrows_:
          print(f">>> txt2json: WARNING! Columns appear to have different number of rows!!! {key0!r} has {nrows}, {key!r} has {nrows_}")
    
    # FILL MISSING COLUMNS with default values
    print(f">>> txt2json:   Found {len(data_dict[module])} columns with {nrows} rows: {', '.join(data_dict[module].keys())}")
    for key in default_dict:
      if key not in data_dict[module]: # add array of default values
        default_val = default_dict[key]
        if verb>=1:
          print(f">>> txt2json:   Adding array of length {nrows} for {key} with default value {default_val}")
        if key in gainkeys:
          data_dict[module][key] = [
            [default_val]*nrows, # index=0, gain=1, charge= 80 fC
            [default_val]*nrows, # index=1, gain=2, charge=160 fC
            [default_val]*nrows  # index=2, gain=4, charge=320 fC
          ]
        else:
          data_dict[module][key] = [default_val]*nrows
           # same length as others
  
  # WRITE JSON file
  print(f">>> txt2json: Writing {outfname}...")
  if compress:
    import gzip
    with gzip.open(outfname,'w') as outfile:
      outfile.write(json.dumps(data_dict,cls=CompactJSONEncoder,sort_keys=False,indent=2).encode('utf-8'))
  else:
    with open(outfname,'w') as outfile:
      json.dump(data_dict,outfile,cls=CompactJSONEncoder,sort_keys=False,indent=2)
  
  return data_dict
  

if __name__=='__main__':
  #import sys; print(sys.argv)
  from argparse import ArgumentParser
  parser = ArgumentParser(description="Convert txt file with calibration parameters. to JSON format",epilog="Good luck!")
  moddir = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) # HGCalCommissioning/LocalCalibration/data/
  outdir = os.path.join(moddir,"data")
  eosdir = "/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/CMSSW/ReReco_Oct10/"
  #print(__file__,moddir)
  parser.add_argument("infiles",         nargs='*',
                      metavar="TXT",     help="input file" )
  parser.add_argument('-o', "--outdir",  default=outdir,
                                         help="output directory for JSON file, default=%(default)r" )
  parser.add_argument('-z', "--gzip",    dest='compress', action='store_true',
                                         help="compress output with gzip, default=%(default)r" )
  parser.add_argument('-v', "--verbose", dest='verbosity', type=int, nargs='?', const=1, default=0,
                                         help="set level of verbosity, default=%(default)s" )
  args = parser.parse_args()
  fnames = args.infiles or [
    f"{eosdir}/Run1695563673/26428d8a-6d27-11ee-8957-fa163e8039dc/calibs/level0_calib_params.txt",
    "/eos/cms/store/group/dpg_hgcal/comm_hgcal/ykao/calibration_parameters_v2.txt", # default in CMSSW
  ]
  for fname in fnames:
    #txt2json(fname,maxrows=50,outdir=args.outdir,compress=args.compress,verb=args.verbosity)
    txt2json(fname,maxrows=-1,outdir=args.outdir,compress=args.compress,verb=args.verbosity)
  
