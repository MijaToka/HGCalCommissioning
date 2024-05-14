#! /usr/bin/env python3
# Author: Izaak Neutelings (May 2024)
# Description:
#   Merge HGCal calibration JSONs.
import os, re
#import json
#from datetime import datetime
#from HGCalCommissioning.LocalCalibration.JSONEncoder import CompactJSONEncoder


def green(string,**kwargs):
  return "\033[32m%s\033[0m"%string
  

def merge(infnames,outfname="merge.json",verb=0):
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
  print(infnames)
  print(outfname)
  for infname in infnames:
    print(infname.split('='))
  

if __name__=='__main__':
  from argparse import ArgumentParser
  parser = ArgumentParser(description="Merge JSON files",epilog="Good luck!")
  parser.add_argument('-v', "--verbose", dest='verbosity', type=int, nargs='?', const=1, default=0,
                                         help="set level of verbosity, default=%(default)s" )
  subparsers = parser.add_subparsers(title="sub-commands",dest='subcommand',help="sub-command help")
  
  # COMMON PARSER
  parser_cmn = ArgumentParser(add_help=False)
  parser_cmn.add_argument('-v', '--verbose', dest='verbosity', type=int, nargs='?', const=1, default=0,
                                             help="set verbosity")
  
  # SUBCOMMAND: MERGE
  help_add = "Merge JSONS"
  parser_add = subparsers.add_parser('merge', parents=[parser_cmn], help=help_add, description=help_add)
  parser_add.add_argument("infiles",         nargs='*',
                          metavar="JSON",    help="input file" )
  parser_add.add_argument('-o', "--output",  default="merged.json",
                                             help="output JSON file, default=%(default)r" )
  parser_add.add_argument('-z', "--gzip",    dest='compress', action='store_true',
                                             help="compress output with gzip, default=%(default)r" )
  
  # PARSE ARGUMENTS
  args = parser.parse_args()
  verb = args.verbosity
  if args.subcommand=='merge':
    merge(args.infiles,args.output,verb=verb)
    
