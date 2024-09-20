#! /usr/bin/env python3
# Author: Izaak Neutelings (September 2024)
# Description: Help functions for plotting wafers
# Sources:
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-sysval-offline/-/merge_requests/13
import os, re
import json
try:
  import plotly.graph_objects as go
  import plotly.colors as pc
  import plotly.io as pio
except ModuleNotFoundError as error:
  error.msg += "! Please install with 'python3 -m pip install --user plotly'"
  raise error
#datadir = "../DQM/data" #"$CMSSW_BASE/src/HGCalCommissioning/DQM/data"
datadir = os.path.join(os.environ.get("CMSSW_BASE"),"src/HGCalCommissioning/DQM/data")
wafertraces = { } # cache (x,y) traces of (hexagonal) wafers
waferlimits = { } # cache of (xmin,xmax) & (ymin,ymax) of wafers traces
waferfigs   = { } # cache template of plotly figure traces of (hexagonal) wafers


def getcolorscale(colorscale='Hot'):
  """Get plotly color scale, and convert RGB string to tuple of integers!"""
  # https://plotly.com/python/builtin-colorscales/#builtin-sequential-color-scales
  if isinstance(colorscale,str):
    colorscale = pc.get_colorscale(colorscale)
  colorscale = colorscale[:] # copy to prevent overwriting
  for idx, (fraction, color) in enumerate(colorscale[:]):
    if isinstance(color,str):
      if color.startswith('rgb'):
        matches = re.findall(r'\d+',color)
        assert len(matches)==3, f"Got color={color!r}, expected format 'rgb(\d+,\d+,\d+)'"
        colorscale[idx] = (fraction,tuple(map(int,matches[:3]))) # overwrite color
      else:
        raise ValueError(f"getcolorscale: Unknown color format: {low[1]!r}, {high[1]!r}, ")
  return colorscale
  

def getcolor(x,xmin,xmax,colorscale='Viridis'):
  """Get color from color scale for given value."""
  xnorm = max(0,min(1,(x-xmin)/(xmax-xmin))) # normalized within [0,1]
  if isinstance(colorscale,str):
    colorscale = getcolorscale(colorscale)
  color = colorscale[-1][1]
  for i in range(len(colorscale) - 1):
    low = colorscale[i]
    high = colorscale[i+1]
    if low[0]<=xnorm<=high[0]:
      xmid = (xnorm-low[0])/(high[0]-low[0])
      color = (
        int(low[1][0]+xmid*(low[1][0]+high[1][0])), # red
        int(low[1][1]+xmid*(low[1][1]+high[1][1])), # blue
        int(low[1][2]+xmid*(low[1][2]+high[1][2])), # green
      )
      #rgb = pc.find_intermediate_color(low[1],high[1],interp_factor) #,colortype=='rgb')
  return f"rgb{color}"
  

def getlimits(xvals,xmin=1e10,xmax=-1e10,margin=0):
  """Help function to set x & y axis limits from list of lists."""
  for x in xvals:
    xmin_ = min(x)
    xmax_ = max(x)
    if xmin_<xmin: xmin = xmin_
    elif xmax_>xmax: xmax = xmax_
  if margin!=0:
    span = xmax-xmin
    xmin -= margin*span
    xmax += margin*span
  return xmin, xmax
  

def getzlimits(zvals,margin=0):
  """Help function to set z axis limits from list."""
  zmin, zmax = min(zvals), max(zvals)
  if zmin==0 and zmax==0:
    zmax = 1
  elif zmin==zmax:
    span  = abs(zmax)
    zmin -= 0.1*span
    zmax += 0.1*span
  elif margin!=0:
    span = zmax-zmin
    zmin -= margin*span
    zmax += margin*span
  return zmin, zmax
  

def fill_wafer_hist(ch_values,moduletype='ML_L'):
    """
    This method takes care of instatiating a hexplot for a given module type and fill it with the values for the required channels
    ch_values is a dict of (channel number, value)
    module_type is a string with the module type to be used in the hexplot
    """
    import ROOT
    hex_plot = ROOT.TH2Poly()
    hex_plot.SetDirectory(0)
    file = ROOT.TFile.Open(f'../DQM/data/geometry_{moduletype}_wafer.root','R')
    iobj = 0
    for key in file.GetListOfKeys():
      obj = key.ReadObj()
      if not obj.InheritsFrom("TGraph") : continue
      
      # ignore CM
      isCM = (iobj % 39 == 37) or (iobj % 39 == 38)
      if isCM :
        iobj += 1
        continue
      
      hex_plot.AddBin(obj)
      eRx = int(iobj/39)
      idx = iobj - eRx*2 #take out 2 CM per eRx to get the proper idx
      if idx < len(ch_values):
        hex_plot.SetBinContent(idx+1,ch_values[idx])
      else:
        raise ValueError(f'Length of values {len(ch_values)} does not accomodate for #obj={iobj} eRx={eRx} idx={idx}')
      iobj += 1
      
    file.Close()
    return hex_plot


def get_wafer_from_ROOT(ch_values,modtype='ML_L',outdir=datadir,verb=0):
  """
  Retrieve (x,y) coordinates of (hexagonal) wafer traces from ROOT file.
  * ch_values is a dict of (channel number, value) or a list of [value]
  * module_type is a string with the module type to be used in the hexplot
  Adapted from
    https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/LocalCalibration/scripts/HexPlotUtils.py
    https://gitlab.cern.ch/hgcal-integration/hgcal-sioptim/-/blob/master/utils/module_app_plotting.py#L208-220
    https://github.com/ywkao/hexagonal_histograms/blob/main/include/auxiliary_boundary_lines_HD_full_wafer.h
  """
  modtype = modtype[:4].replace('-','_')
  if verb>=1:
    print(f">>> get_wafer_from_ROOT for modtype={modtype!r}")
  if modtype in wafertraces:
    return (wafertraces[modtype]['x'],wafertraces[modtype]['y'])
  import ROOT
  ROOT.gROOT.SetBatch(True) # don't open GUI windows
  nchans = ch_values if isinstance(ch_values,int) else len(ch_values)
  
  # CREATE HEXPLOT from geometry file
  fname = os.path.join(datadir,f"geometry_{modtype}_wafer.root")
  file = ROOT.TFile.Open(fname,'READ')
  assert file, f"get_wafer_from_ROOT: Could not open {fname}..."
  iobj = 0
  xvals = [ ]
  yvals = [ ]
  ###hexhist = ROOT.TH2Poly()
  ###hexhist.SetDirectory(0)
  for key in file.GetListOfKeys():
    obj = key.ReadObj()
    if not obj.InheritsFrom("TGraph"): continue
    isCM = (iobj%39==37) or (iobj%39==38)
    if isCM: # ignore CM
      iobj += 1
      continue
    xvals.append(list(obj.GetX()))
    yvals.append(list(obj.GetY()))
    ###hexhist.AddBin(obj) # TGraph defines bin
    ###eRx = int(iobj/39) # index of HGROC half
    ###idx = iobj-2*eRx # take out 2 CM per eRx to get the proper idx
    ###if verb>=3:
    ###  x, y = obj.GetPointX(0), obj.GetPointY(0)
    ###  print(f"get_wafer_from_ROOT: Add obj={iobj}, eRx={eRx}, idx={idx} at (x,y)=({x:4.1f},{y:4.1f})")
    iobj += 1
  file.Close()
  
  # SANITY CHECK: final number of channels
  eRx = int(iobj/39) # index of HGROC half
  nobj = iobj-2*eRx
  if nobj!=nchans:
    print(f">>> get_wafer_from_ROOT: WARNING! Length of values ({nchans}) does match number of (non-CM) graphs in {fname} ({nobj})!"
          " Did you choose the correct module map or did you correctly index the channel (omitting common modes)?")
  
  #### PLOT TH2Poly with ROOT
  ###tsize = 0.042
  ###lmarg, rmarg = 0.11, 0.11
  ###bmarg, tmarg = 0.08, 0.05
  ###canvas = ROOT.TCanvas('canvas','canvas',100,100,800,800) # XYWH
  ###canvas.SetMargin(lmarg,rmarg,bmarg,tmarg) # LRBT
  ###hexhist.SetTitle("")
  ###hexhist.GetXaxis().SetTitle("x")
  ###hexhist.GetYaxis().SetTitle("y")
  ###hexhist.GetXaxis().SetTitleSize(tsize)
  ###hexhist.GetYaxis().SetTitleSize(tsize)
  ###hexhist.GetXaxis().SetLabelSize(0.9*tsize)
  ###hexhist.GetYaxis().SetLabelSize(0.9*tsize)
  ###hexhist.GetXaxis().SetTitleOffset(1.05)
  ###hexhist.GetYaxis().SetTitleOffset(1.04)
  ###hexhist.GetXaxis().SetRangeUser(-15,15)
  ###hexhist.GetYaxis().SetRangeUser(-15,15)
  ######hexhist.GetXaxis().SetMinimum(ymin)
  ######hexhist.GetXaxis().SetMinimum(ymin)
  ######hexhist.SetMaximum(ymax)
  ###hexhist.Draw("COLZ")
  ###canvas.SaveAs("test.png")
  
  # CACHE for reuse
  wafertraces[modtype] = { 'x': xvals, 'y': yvals }
  waferlimits[modtype] = { 'x': getlimits(xvals,margin=0.03), 'y': getlimits(yvals,margin=0.03) }
  
  # WRITE TO JSON (ROOT is so slow to import...)
  outfname = os.path.join(outdir,f"geometry_{modtype}_wafer.json")
  print(f">>> get_wafer_from_ROOT: Writing xy values to {outfname}...")
  with open(outfname,'w') as outfile:
    json.dump(wafertraces[modtype],outfile)
  
  return xvals, yvals
    

def get_wafer_from_JSON(modtype='ML_L',outdir=datadir,verb=0):
  """Retrieve plotly template from JSON."""
  #print(">>> get_wafer_from_JSON")
  modtype = modtype[:4].replace('-','_')
  if modtype not in waferfigs:
    fname = os.path.join(datadir,f"geometry_{modtype}_wafer.json")
    with open(fname,'r') as file:
      waferfigs[modtype] = pio.read_json(file)
  return waferfigs[modtype]
  

def get_boundaries_JSON(modtype,verb=0):
  """Create boundaries between eRxs in wafers, loaded from JSON"""
  # https://github.com/ywkao/hexagonal_histograms/blob/main/include/
  modtype = modtype[:4].replace('-','_')
  if verb>=1:
    print(f">>> get_boundaries_JSON for modtype={modtype!r}")
  fname = os.path.join(datadir,"geometry_wafer_boundaries.json")
  with open(fname,'r') as file:
    data = json.load(file)
  return data[modtype]
  

def create_wafer_template(nchans,modtype='ML_F',template='plotly',
                          outdir=datadir,lines=True,root=False,write=False,verb=0):
  """Create wafer plot template to hopefully speed up creation of plots."""
  modtype = modtype[:4].replace('-','_')
  if modtype in waferfigs:
    if verb>=2:
      print(f">>> create_wafer_template: Reusing cached template for wafer traces of modtype={modtype!r}...")
    fig = waferfigs[modtype]
    return go.Figure(fig) # copy
  elif not root:
    return get_wafer_from_JSON(modtype,verb=verb)
  xvals, yvals = get_wafer_from_ROOT(nchans,modtype=modtype,verb=verb)
  if verb>=1:
    print(f">>> create_wafer_template: Creating new template for wafer traces of modtype={modtype!r}...")
  xmin, xmax = waferlimits[modtype]['x'] #getlimits(xvals,margin=0.04)
  ymin, ymax = waferlimits[modtype]['y'] #getlimits(yvals,margin=0.04)
  
  # CREATE FIGURE
  fig = go.Figure()
  for i, (x, y) in enumerate(zip(xvals,yvals)):
    xw = (min(x)+max(x))/2.
    yw = (min(y)+max(y))/2.
    fig.add_trace(go.Scatter( # add channel (hexagon)
      x=x,y=y,
      text=f"i={i}<br>x={xw:.3g}<br>y={yw:.3g}",
      mode='lines',#line_color='black',
      line=dict(color='black',width=1),
      fill='toself',fillcolor='white',
      opacity=0.8,
    ))
  
  # ADD BOUNDARY LINES
  if lines:
    lines = get_boundaries_JSON(modtype,verb=verb)
    for line in lines:
      fig.add_trace(go.Scatter( # add channel (hexagon)
        x=line['x'],y=line['y'],
        mode='lines',#line_color='black',
        line=dict(color='red',width=1.8),
        opacity=1,
      ))
  
  # UPDATE LAYOUT
  width = 800 if abs(xmax-xmin)>15 else 500
  fig.update_layout(
    xaxis_title="x [cm]",
    yaxis_title="y [cm]",
    template=template,
    xaxis=dict(
      title_standoff=11,
      ###tickfont=dict(size=20),
      tickmode='linear', dtick=2,
      showgrid=True,gridwidth=1, #gridcolor='rgb(0.15,0.15,0.25)'
      range=[xmin,xmax],
    ),
    yaxis=dict(
      title_standoff=11,
      ###tickfont=dict(size=20),
      tickmode='linear', dtick=2,
      showgrid=True,gridwidth=1, #gridcolor='rgb(0.15,0.15,0.25)'
      range=[ymin,ymax],
    ),
    showlegend=False,
    font=dict(
      family='Arial, sans-serif',
      size=22 #,weight='normal'
    ),
    width=width, height=650,
    margin=dict(r=90,t=50,l=10,b=22,pad=2),
  )
  waferfigs[modtype] = fig # cache to speed up creation of figures
  
  # WRITE TO JSON (ROOT is slow...)
  outfname = os.path.join(outdir,f"geometry_{modtype}_wafer.json")
  if write:
    print(f">>> create_wafer_template: Writing figure template to {outfname}...")
    fig.write_json(outfname,pretty=True) #.replace(".json","_fig.json")
    fig.write_image(f"template_{modtype}.png")
  return go.Figure(fig) # copy
  
