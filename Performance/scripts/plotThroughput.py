#! /usr/bin/env python3
# Author: Izaak Neutelings (January 2025)
# Instructions
#   plotThroughput.py ThroughputService*.log
import re
import numpy as np
np.finfo(np.dtype('float32')) # stop warnings
np.finfo(np.dtype('float64'))
import matplotlib.pyplot as plt
from datetime import datetime
from HGCalCommissioning.Performance.plot import *

# GLOBAL SETTINGS
header_dict = {
  'DIGI':        "BIN $\\rightarrow$ RAW $\\rightarrow$ DIGI",
  'RAW2DIGI':    "BIN $\\rightarrow$ RAW $\\rightarrow$ DIGI",
  'FEDRAW2DIGI': "FEDRAW $\\rightarrow$ DIGI",
  'RECO':        "DIGI $\\rightarrow$ RECO",
  '_onlyin':     "Input only (GenericConsumer)",
  '_fullchain':  "Input+kernels+output",
  '_noout':      "Input+kernels (no output)",
}
rexp_fname = re.compile(r"ThroughputService_(?P<proc>.*)_scale(?P<scale>.*)_nthreads?(?P<nthread>\d+)(?P<label>.*).log$")
rexp_trytag = re.compile(r"_try\d+$")


def parsecommon(matches,common,i=0,invert=False):
  """Put common labels in header and outtag."""
  outtag = ""
  header = ""
  if common['proc']!=invert:
    proc = matches['proc'][i]
    header = header_dict.get(proc,proc)+": "
    outtag = '_'+proc
  if common['label']!=invert:
    label = matches['label'][i]
    label0 = rexp_trytag.sub('',label)
    #print(label,label0)
    if label0 in header_dict:
      header += header_dict.get(label0,'')+", "
  if common['scale']!=invert:
    scale = matches['scale'][i]
    #if int(scale)>=1:
    #  header += f"scale {scale}, "
    header += (f"9 mods, " if int(scale)<=1 else f"9x{scale} mods, ")
    outtag += f"_scale{scale}"
  if common['nthread']!=invert:
    nthread = int(matches['nthread'][i])
    header += f"{nthread} thread{'s' if nthread>=2 else ''}, "
    outtag += f"_nthread{nthread}"
  if common['label']!=invert:
    outtag += matches['label'][i]
  return header.strip(',: '), outtag
  

def parsefnames(fnames,verb=0):
  """Check if all filenames have common pattern."""
  titles, header, outtag = [ ], "", ""
  matches = { k: [ ] for k in ['proc','scale','nthread','label'] } # pattern matches
  for i, fname in enumerate(fnames):
    if '=' in fname: # name given by user
      parts = fname.split('=')
      title = '='.join(parts[:-1])
      fnames[i] = parts[-1] # overwrite
    else: # parse ourselves
      match = rexp_fname.match(fname)
      if match: # my known pattern
        scale   = int(match.group('scale'))
        nthread = int(match.group('nthread'))
        title = f"9 mods, " if int(scale)<=1 else f"9x{scale} mods, "
        title += f"nthread{'s' if nthread>=2 else ''} {nthread}"
        for key in matches:
          matches[key].append(match.group(key))
      else: # no known pattern
        title = fname.replace("ThroughputService",'').strip('_').replace('_',' ').replace(".log",'')
    titles.append(title)
  nfiles = len(fnames)
  if verb>=2:
    print(f">>> parsefnames: titles={titles}, matches={matches}")
  if len(matches['proc'])==nfiles: # all files match pattern
    common = { k: v.count(v[0])==nfiles for k, v in matches.items() }
    if verb>=2:
      print(f">>> parsefnames: common={common}")
    header, outtag = parsecommon(matches,common)
    if verb>=1:
      print(f">>> parsefnames: header={header!r}, outtag={outtag!r}")
    for i, fname in enumerate(fnames):
      titles[i], _ = parsecommon(matches,common,i=i,invert=True)
      if verb>=1:
        print(f">>> parsefnames:   fname={fname!r} => title={titles[i]!r}")
  return titles, header, outtag
  

def main(args):
  verbosity = args.verbosity
  fnames    = args.fnames
  titles, header, outtag = parsefnames(fnames,verb=verbosity)
  outfname  = args.outfname
  header    = args.header if args.header!=None else header
  outtag    = args.outtag if args.outtag!=None else outtag
  
  # COLLECT DATA
  data = { }
  for title, fname in zip(titles,fnames):
    print(f">>> Processing {fname}...")
    points = parsefile(fname)
    data[title] = points
  
  # COLLECT DATA
  outfname = outfname.replace('$TAG',outtag) #f"ThroughputService{outtag}.png"
  plotboth(data,header=header,fname=outfname)
  

if __name__ == '__main__':
  from argparse import ArgumentParser
  description = '''This script plots Throughput.'''
  parser = ArgumentParser(description=description,epilog="Good luck!")
  parser.add_argument('fnames', nargs='+', help="Input file with comma-separated event table from ThroughputService")
  parser.add_argument('-H', '--header',   help="header of plot, default=%(default)r")
  parser.add_argument('-o', '--outfname', default="ThroughputService$TAG.png",
                                          help="output filename, default=%(default)r")
  parser.add_argument('-t', '--tag',      dest='outtag',
                                          help="tag for output filename, default=%(default)r")
  parser.add_argument('-v', '--verbose',  dest='verbosity', type=int, nargs='?', const=1, default=0,
                                          help="set verbosity level, default=%(default)r" )
  args = parser.parse_args()
  main(args)
  print(">>> Done.")
  
