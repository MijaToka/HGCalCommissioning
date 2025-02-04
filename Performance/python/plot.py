#! /usr/bin/env python3
# Author: Izaak Neutelings (January 2025)
# Instructions
#   ./plotThroughput.py ThroughputService.log
# Sources:
#  https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots_adjust.html
import re
import numpy as np
np.finfo(np.dtype('float32')) # stop warnings
np.finfo(np.dtype('float64'))
import matplotlib.pyplot as plt
from datetime import datetime

# GLOBAL SETTINGS
lsize  = 20
tsize  = 23
plt.rcParams.update({
  'text.usetex':        False,
  'figure.titlesize':   tsize,
  'figure.titleweight': 'bold',
  'axes.titlesize':     tsize,
  'axes.labelsize':     tsize,
  'xtick.labelsize':    lsize,
  'ytick.labelsize':    lsize,
  'legend.fontsize':    lsize-1,
})
tlabel = "Wallclock runtime [s]"
nlabel = "Number of processed events"
rlabel = "Throughput [evts/s]"


def parsefile(fname):
  """Parse comma-separated columns from ThroughputService."""
  nevts = [ ]
  timestamps = [ ]
  dts = [ ]
  location = 'header'
  with open(fname,'r') as file:
    for line in file:
      if 'ThroughputService' in line:
        location = 'middle'
        continue
      elif not location=='middle':
        continue
      columns = line.strip().split(', ')
      if len(columns)!=2:
        location = 'tail'
        break
      nevts_str, timestamp = columns
      nevts.append(int(nevts_str))
      timestamps.append(datetime.strptime(timestamp,'%d-%b-%Y %H:%M:%S.%f %Z'))
  
  if len(nevts)==0:
    print(f">>> WARNING! No data found in {fname}! (location={location}!r)")
  else:
    # convert timestamps to time differences (dt) relative to the first timestamp
    ts0 = timestamps[0]
    dts = [(ts-ts0).total_seconds() for ts in timestamps]
  
  #print(nevts)
  #print(dt)
  return (dts,nevts)
  

def getrate(x,y):
  """Compute rate."""
  n2 = len(x)-1
  x2 = [(x[i+1]+x[i])/2 for i in range(n2)]
  y2 = [(y[i+1]-y[i])/(x[i+1]-x[i]) for i in range(n2)]
  return (x2,y2)
  

def getaverage(xvals,yvals,xmin=None,xmax=None):
  """Compute average."""
  imin, imax = 0, len(xvals)-1
  if xmin==None:
    xmin = xvals[imin]
  else:
    xmins = [x for x in xvals if x>=xmin]
    if xmins:
      xmin = min(xmins)
      imin = xvals.index(xmin)
    else:
      print(f">>> getaverage: xmin={xmin} leaves 0 x values! Taking full range...")
      xmin = xvals[0]
      imin = 0
  if xmax==None:
    xmax = xvals[imax]
  else:
    xmax = max(x for x in xvals[imin:] if x<=xmin)
    imax = xvals.index(xmax)
  mean = sum(yvals[imin:imax+1])/(imax+1-imin)
  #print(len(xvals),imin,imax,xmin,xmax,yvals[imin],yvals[imax]) 
  return ([xmin,xmax],[mean,mean])
  

def one_over(x,scale=1.):
  """Vectorized 1/x, treating x==0 manually for secondary axis."""
  # https://matplotlib.org/stable/gallery/subplots_axes_and_figures/secondary_axis.html
  x = np.array(x, float)
  near_zero = np.isclose(x, 0)
  x[near_zero] = np.inf
  x[~near_zero] = scale / x[~near_zero]
  return x
tp2ms = lambda tp: one_over(tp,scale=1e3)
ms2tp = lambda tp: one_over(tp,scale=1e-3)


def plotsingle(data,header=None,fname="ThroughputService.png"):
  """Plot data."""
  plt.figure(figsize=(8,6))
  fig.subplots_adjust(
    top=0.95, bottom=0.07,
    left=0.12, right=0.99,
    hspace=0.04, wspace=0.04 # space between subplots
  )
  plt.xlabel(tlabel)
  plt.ylabel(nlabel)
  if header is not None:
    plt.title(header)
  plt.grid(True)
  for label, (x, y) in data.items():
    plt.plot(x, y, marker='o', linestyle='-', label=label) #, color='b'
  plt.legend()
  #plt.show()
  plt.savefig(fname)
  print(f">>> Created {fname}")
  

def plotboth(data,header=None,fname="ThroughputService.png"):
  """Plot data."""
  print(">>> Plotting...")
  fig, axes = plt.subplots(2, 1, figsize=(12,12), sharex=True)
  #fig.tight_layout() # too tight...
  fig.subplots_adjust(
    top=0.96, bottom=0.062,
    left=0.12, right=0.99,
    hspace=0.04, wspace=0.04 # space between subplots
  )
  if header is not None:
    fig.suptitle(header,x=0.54,y=0.99)
  
  # COMPUTE XMIN for "unbiased" average
  xmax = max([max(xy[0]) for xy in data.values() ])
  xmin = 2.5 if xmax>=10 else 0.15*xmax
  #print(xmin,xmax)
  
  # PLOT nevts vs. dt
  sargs = dict(marker='o', linestyle='-', linewidth=2.5, markersize=5)
  for label, (x, y) in data.items():
    x2, r = getrate(x,y)
    x3, a = getaverage(x2,r,xmin=xmin,xmax=None)
    label = f"{label}: {a[0]:.0f} evts/s, {1000/a[0]:.2f} ms/evt"
    label = label.replace('thread:','thread: ')
    lines = axes[0].plot(x, y, label=label, **sargs)
    color = lines[-1].get_color()
    axes[1].plot(x2, r, color=color, **sargs)
    axes[1].plot(x3, a, marker='', linestyle='-', color=color)
  
  # SETTINGS
  axes[0].legend()
  axes[1].set_xlabel(tlabel)
  axes[0].set_ylabel(nlabel)
  axes[1].set_ylabel(rlabel)
  axes[0].grid(True)
  axes[1].grid(True)
  #axes[1].legend()
  #yaxis3 = axes[1].secondary_yaxis('right',functions=(tp2ms,ms2tp))
  #yaxis3.set_ylabel('Time [ms/evt]')
  
  # SAVE
  plt.savefig(fname)
  print(f">>> Created {fname}")
  
