#! /usr/bin/env python3
# Author: Izaak Neutelings (September 2024)
# Description:
#   Plot & compare JSONs
# Instructions:
#   ./plotjson.py /eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/Test/calibrations/*/level0_calib_params.json
# Sources:
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/LocalCalibration/data/level0_calib_params.json
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-sysval-offline/-/merge_requests/13
import os, re
import json
from HGCalCommissioning.LocalCalibration.plot.wafer_plotly import *
import plotly.graph_objects as go
colorscale, colorscale_tuple = getcolorscale('RdBu',invert=True)


def bold(string,prefix=""):
  return f"{prefix}\033[1m{string}\033[0m"
  

def ensuredir(dname,verb=0):
  """Make directory if it does not exist."""
  if not dname:
    return dname
  if not os.path.exists(dname):
    if verb>=1:
      print(f">>> Making directory {dname}...")
    os.makedirs(dname)
  return dname
  

def loadjson(fname,verb=0):
  if verb>=1:
    print(f">>> loadjson: Reading {fname!r}...")
  with open(fname,'r') as file:
    data = json.load(file)
  return data
  

def commonkeys(datasets):
  """Return common keys from list of dictionaries."""
  keys = set()
  for dataset in datasets:
    if len(keys)>=1:
      keys = keys & dataset.keys() # intersection
    else: # set for first time
      keys = dataset.keys()
  return keys
  

def plotlist_wafer(fname,zvals,title,outdir='plots',template='plotly',
                   modtype='ML_F',ztitle='',exts=['.png'],verb=0):
  """Plot list for one or more ECON-D modules. X axis should be (dense) channel index."""
  if verb>=1:
    print(f">>> plotlist_wafer: Plotting fname={fname}, title={title!r}, ztitle={ztitle!r}, modtype={modtype!r}")
  modtype = modtype[:4].replace('-','_')
  
  # CREATE FIGURE from CACHED TEMPLATE
  fig = create_wafer_template(len(zvals),modtype=modtype,template=template,verb=verb)
  zmin, zmax = getzlimits(zvals)
  for i, z in enumerate(zvals):
    color = getcolor(z,zmin,zmax,colorscale=colorscale_tuple)
    fig.data[i].text=f"i={i}<br>z={z:.5g}"
    fig.data[i].fillcolor=color
  
  #### CREATE FIGURE FROM SCRATCH
  ###xvals, yvals = get_wafer_from_ROOT(zvals,modtype=modtype,verb=verb)
  ###if verb>=2:
  ###  print(f">>> plotlist_wafer: Creating traces...")
  ###fig = go.Figure()
  ###zmin, zmax = getzlimits(zvals)
  ###for i, (x, y, z) in enumerate(zip(xvals,yvals,zvals)):
  ###  color = getcolor(z,zmin,zmax,colorscale=colorscale_tuple)
  ###  fig.add_trace(go.Scatter( # add channel (hexagon)
  ###    x=x,y=y,
  ###    text=f"i={i}<br>z={z:.5g}",
  ###    mode='lines',#line_color='black',
  ###    line=dict(
  ###      color='black',
  ###      width=1,
  ###    ),
  ###    fill='toself',fillcolor=color, #'white',
  ###    opacity=0.8,
  ###  ))
  ###
  #### LAYOUT
  ###xmin, xmax = waferlimits[modtype]['x'] #getlimits(xvals,margin=0.04)
  ###ymin, ymax = waferlimits[modtype]['y'] #getlimits(yvals,margin=0.04)
  ###pad = 2
  ###fig.update_layout(
  ###  title=title,
  ###  xaxis_title='x',
  ###  yaxis_title='y',
  ###  template=template,
  ###  xaxis=dict(
  ###    ###tickfont=dict(size=20),
  ###    ###rangemode='tozero',
  ###    range=[xmin,xmax],
  ###  ),
  ###  yaxis=dict(
  ###    ###tickfont=dict(size=20),
  ###    range=[ymin,ymax],
  ###  ),
  ###  showlegend=False,
  ###  font=dict(
  ###    family='Arial, sans-serif',
  ###    size=22
  ###  ),
  ###  width=800, height=650,
  ###  margin=dict(r=90,t=50,l=10,b=22,pad=pad),
  ###)
  
  # DUMMY TRACE to obtain COLOR BAR
  fsize = 22 if len(ztitle)<=8 else 20 if len(ztitle)<=12 else 18
  fig.add_trace(go.Scatter(
    x=[None], y=[None],
    mode='markers',
    marker=dict(
      colorscale=colorscale, 
      showscale=True,
      cmin=zmin, cmax=zmax,
      colorbar=dict(
        title=dict(
          text=ztitle,
          font=dict(size=fsize),
        ),
        ticks='outside', #tickvals=[-5, 5]
        thickness=25, outlinewidth=0.5
      )
    ),
    hoverinfo='none'
  ))
  
  #### ADD COLOR SCALE BAR in right margin
  ###fig.add_shape(
  ###  type="rect",
  ###  xref="paper", yref="paper", # coordinate system (relative to the entire figure)
  ###  x0=1.05, y0=0.0, # bottom left corner in right margin
  ###  x1=1.10, y1=1.0, # top right corner in right margin
  ###  line=dict(color="RoyalBlue"),
  ###  fillcolor="LightSkyBlue",
  ###)
  
  # SAVE
  fname = os.path.join(outdir,fname)
  for ext in exts:
    fname_ = fname+ext
    if verb>=1:
      print(f">>> plotlist_wafer: Writing {fname_}...")
    fig.write_image(fname_)
  

def plotlist(fname,dataset,labels,key,outdir='plots',template='plotly',exts=['.png'],verb=0):
  """Plot list for one or more ECON-D modules. X axis should be (dense) channel index."""
  if verb>=1:
    print(f">>> plotlist: Plotting fname={fname}, key={key}, labels={labels}")
  ndsets = len(dataset)
  if len(labels)!=ndsets:
    print(f">>> plotlist: WARNING! len(labels)={len(labels)}!={ndsets}=len(dataset)")
  
  # XVALUES
  xvalset = [ ]
  nmin   = min(len(ds) for ds in dataset)
  nmax   = max(len(ds) for ds in dataset)
  if nmin!=nmax: # add gaps
    assert nmin%37==0 and nmax%37==0, f"plotlist:   nmin={nmin}, nmax={nmax}"
    xvals_gap = [i*39+j for i in range(nmax//39) for j in range(0,37)]
    for yvals in dataset:
      if nmin==len(yvals): # add gaps
        xvalset.append(xvals_gap)
      else:
        xvalset.append(list(range(nmax)))
  else:
    for yvals in dataset:
      xvalset.append(list(range(nmax)))
  
  # ADD DATA
  fig = go.Figure()
  allxvals = set() # unique xvals
  nrows = 1 if ndsets<=4 else 2
  for i, (label, xvals, yvals) in enumerate(zip(labels,xvalset,dataset)):
    #print(f">>> plotlist:   Adding label={label}")
    if len(xvals)!=len(yvals):
      print(f">>> plotlist: WARNING! len(xvals)={len(xvals)}!={len(yvals)}=len(yvals)")
    assert isinstance(yvals,list), f"Expected list, but got: yvals={yvals!r} for fname={fname!r}..."
    xvals = [str(x) for x in xvals] # convert to category labels
    allxvals.update(xvals)
    size = 8.-2.*i/(ndsets-1)
    row  = 1 if (nrows==1 or i<ndsets/2) else 2
    fig.add_trace(go.Scatter(
      x=xvals,y=yvals,name=label,
      mode='lines+markers',marker=dict(size=size),
      legend=f"legend{row}"
    ))
  
  # SET Y AXIS RANGE
  ymin, ymax = min(min(ds) for ds in dataset), max(max(ds) for ds in dataset)
  if ymin==0 and ymax==0:
    ymax = 1
  elif ymin==ymax:
    span = abs(ymin)
    ymin -= 0.08*span # add bottom margin
    ymax += (0.15+0.03*ndsets)*span # add top margin
  else:
    span = (ymax-ymin)
    ymin -= 0.08*span # add bottom margin
    ymax += (0.15+0.03*ndsets)*span # add top margin
  
  # ADD VERTICAL LINES to separate eRx
  nchan = 39 if (nmin!=nmax or nmax%39==0) else 37 # add gaps
  xgap  = nchan-0.5
  while xgap<nmax-5:
    if verb>=2:
      print(f">>> plotlist:   Adding line at x={xgap}, ymin={ymin}, ymax={ymax}...")
    fig.add_shape(
      x0=xgap, x1=xgap, y0=ymin, y1=ymax,
      type='line',
      line=dict(color='Red',width=1.4,dash='dash')
    )
    xgap += nchan
  
  # LAYOUT
  pad    = 2
  width  = 1500
  height = 600
  rmarg  = 6 # px
  fig.update_layout(
    title=f"Comparison of {key}",
    xaxis_title='Channel index',
    yaxis_title=key,
    template=template,
    xaxis=dict(
      #type='category',
      #categoryorder='array',
      #categoryarray=sorted(allxvals,key=int),
      tickfont=dict(size=10),
      tickangle=45,
      rangemode='tozero',
      range=[-1*pad,nmax+pad-1]
    ),
    yaxis=dict(
      range=[ymin,ymax],
      #automargin=True,
    ),
    font=dict(
      family='Arial, sans-serif',
      size=22
    ), #color="RebeccaPurple"
    width=width, height=height,
    margin=dict(r=rmarg,t=50,l=5,b=25,pad=pad),
  )
  ###fig.update_xaxes(
  ###  categoryorder='array',
  ###  categoryarray=sorted(list(allxvals))
  ###)
  
  # LEGEND(S)
  extrakwargs = { }
  for row in range(1,nrows+1):
    extrakwargs[f"legend{row}"] = dict(
      x=0.02,y=0.99-(row-1)*0.092,
      orientation='h' if nrows>=2 else 'v',
      xanchor='left',yanchor='top',
      font=dict(
        family='Arial, sans-serif',
        size=24
      ), #color="RebeccaPurple")
      bgcolor='rgba(255,255,255,0.8)',
      #entrywidth=, # change it to 0.3
      #entrywidthmode='pixels',
    )
  fig.update_layout(**extrakwargs)
  
  # SAVE
  #fig.show()
  fname = os.path.join(outdir,fname)
  for ext in exts:
    fname_ = fname+ext
    if verb>=1:
      print(f">>> plotlist: Writing {fname_}...")
    fig.write_image(fname_)
  

def process(datasets,labels,name='compare',outdir='plots',filter=None,veto=None,gains=None,verb=0):
  """Process data for plotting."""
  if verb>=1:
    print(f">>> process: Data with label={labels} for name={name!r}")
  
  # GET X VALUES
  keys = commonkeys(datasets)
  ###if 'Channel' not in keys:
  ###  print(f">>> process:   Did not find channels indices in (all) JSONs ?")
  ###xvalset = [ds['Channel'] for ds in datasets] # use as default
  
  # GET Y VALUES
  for key in keys:
    if (veto and key in veto) or (filter and key not in filter):
      if verb>=2:
        print(f">>> process:   Ignoring key={key!r}...")
      continue # ignore keys
    if verb>=1:
      print(f">>> process:   Processing key={key!r}...")
    
    # CHECK FOR LISTS
    dset = [ds[key] for ds in datasets] # get yval data for this key
    if any(not isinstance(ds,list) for ds in dset):
      types = [type(ds) for ds in datasets]
      print(f">>> process:   WARNING! Not all data are lists for key={key!r}."
            f" Found types={types}. Ignore...")
      continue
    
    # CHECK LIST LENGTHS
    vlen = len(dset[0])
    if any(len(ds)!=vlen for ds in dset[1:]):
      vlens = [len(ds) for ds in dset]
      print(f">>> process:   WARNING! Not all data have lists of the same length for key={key!r}."
            f" Found lengths={vlens}.")
      #continue
    if vlen<1:
      print(f">>> process:   Empty list for {key!r}. Ignoring...")
    
    # CHECK DATA TYPES IN LIST
    vtype = type(dset[0][0]) # get datatype of first list's first element
    if any(type(ds[0])!=vtype for ds in dset[1:]):
      vtypes = [type(ds) for ds in dset]
      print(f">>> process:   WARNING! Not all data are lists of the same datatype for key={key!r}."
            f" Found vtypes={vtypes}. Ignore...")
      continue
    
    # PLOT
    fname = f"{name}_{key}"
    title = key
    if vtype==list: # list of list
      nlists = min(len(ds) for ds in dset)
      indices = gains or list(range(nlists))
      for i in indices:
        dset_  = [ds[i] for ds in dset]
        title_ = f"{title} (gain = {80*2**i} fC)"
        fname_ = f"{fname}_gain{i}"
        plotlist(fname_,dset_,labels,title_,outdir=outdir,verb=verb)
    elif vtype in [int,float]: # assume list of number
      plotlist(fname,dset,labels,title,outdir=outdir,verb=verb)
    else:
      print(f">>> process:   Data for key={key!r} is list of type vtype={vtype}. Ignore...")
  

def main(args):
  verbosity  = args.verbosity
  fnames     = args.files
  modules    = args.modules
  gains      = args.gains # filter gain by index
  filterkeys = args.filterkeys # keys to filter
  vetokeys   = set(['Channel','Valid']+args.vetokeys) # keys to ignore
  plotwafer  = args.plotwafer
  template   = 'plotly' if args.dark else 'plotly_dark' # plotly template
  outdir     = ensuredir(args.outdir)
  datasets   = [ ]
  labels     = [ ] #*len(fnames)
  import time; start0 = time.time()
  
  #### WRITE TEMPLATES
  ###for nc, mt in [(111,'ML_L'),(444,'MH_F'),(222,'ML_F'),(111,'ML_R')]:
  ###  #get_wafer_from_ROOT(nc,modtype=mt,outdir=datadir,verb=0)
  ###  create_wafer_template(nc,modtype=mt,template='plotly',outdir=datadir,write=True,verb=0)
  
  # LOAD DATA FROM JSON FILES
  print(">>> "+bold("Reading data..."))
  for fname in fnames:
    if '=' in fname: # user passed label via command line
      label, fname = fname.split('=')[-2:]
    else: # get unique label from file name
      label = re.sub(r".json$","",os.path.basename(fname),re.IGNORECASE)
      if label=='level0_calib_params': # guess subdirectory has unique name
        label = os.path.basename(os.path.dirname(fname))
    datasets.append(loadjson(fname,verb=verbosity))
    labels.append(label.replace('level0_calib_params_',''))
  
  # FIND COMMON ECON-D MODULE TYPECODES
  allmodules = commonkeys(datasets) # common set of modules
  if not allmodules:
    print(">>> Did not find any common modules...")
  if not modules:
    modules = allmodules
  
  # PROCESS DATA FOR PLOTTING
  print(">>> "+bold("Plot data per module & compare runs..."))
  for module in modules:
    if 'IH0014' not in module: continue
    dset = [ds[module] for ds in datasets] # datasets for this module
    name = f"compare_{module}"
    process(dset,labels,name=name,filter=filterkeys,veto=vetokeys,gains=gains,outdir=outdir,verb=verbosity)
  
  # COMPARE MODULES per JSON
  print(">>> "+bold("Plot data per run & compare modules..."))
  for label, dataset in zip(labels,datasets):
    allmodules = list(dataset.keys())
    dset = [dataset[m] for m in allmodules] # datasets for this module
    name = f"compare_{label.replace(' ','_')}"
    process(dset,allmodules,name=name,filter=filterkeys,veto=vetokeys,gains=gains,outdir=outdir,verb=verbosity)
  
  # HEXAPLOT per MODULE & JSON
  if plotwafer:
    print(">>> "+bold("Plot data hexagon plots..."))
    for label, dataset in zip(labels,datasets):
      for module in dataset:
        for key, zvals in dataset[module].items():
          if (vetokeys and key in vetokeys) or (filterkeys and key not in filterkeys):
            continue # ignore keys
          title = f"{module}: {key}"
          name = f"hexplot_{module}_{label.replace(' ','_')}_{key}"
          if isinstance(zvals[0],list):
            indices = gains or list(range(len(zvals)))
            for i in indices:
              name_ = f"{name}_gain{i}"
              title_ = f"{title} (gain = {80*2**i} fC)"
              plotlist_wafer(name_,zvals[i],title_,ztitle=key,modtype=module,outdir=outdir,verb=verbosity)
          else:
            plotlist_wafer(name,zvals,title,ztitle=key,modtype=module,outdir=outdir,verb=verbosity)
  
  print(">>> Done after %.1f seconds"%(time.time()-start0))
  

if __name__=='__main__':
  from argparse import ArgumentParser
  parser = ArgumentParser(description="Plot & compare JSONs",epilog="Good luck!")
  parser.add_argument("files",            nargs='+',
                      metavar="JSON",     help="input JSON files with calibration constants, use label=json format to label JSON files in the plot" )
  parser.add_argument('-m', "--mods",     dest='modules', nargs='+', default=None,
                      metavar="TYPECODE", help="filter ECON-D modules to plot/compare by typecodes, default: plot all modules" )
  parser.add_argument('-k', "--filter",   dest='filterkeys', nargs='+', default=None,
                      metavar="NAME",     help="filter parameter keys to plot, default: plot all keys" )
  parser.add_argument('-x', "--veto",     dest='vetokeys', nargs='+', default=[ ],
                      metavar="NAME",     help="veto parameter keys to plot, default: plot all keys" )
  parser.add_argument('-g', "--gain",     dest='gains', type=int, nargs='+', default=None,
                                          help="filter gains by index" )
  parser.add_argument('-d', "--dark",     dest='dark', action='store_true',
                                          help="dark theme ('plotly_dark')" ) 
  parser.add_argument('-o', "--outdir",   default='plots',
                                          help="output directory for JSON file, default=%(default)r" )
  parser.add_argument('-w', "--wafer",    dest='plotwafer',action='store_true',
                                          help="create hexagonal wafer plots" ) 
  parser.add_argument('-v', "--verbose",  dest='verbosity', type=int, nargs='?', const=1, default=0,
                                          help="set level of verbosity, default=%(default)s" )
  args = parser.parse_args()
  main(args)
  
