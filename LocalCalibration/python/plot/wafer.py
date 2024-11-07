#! /usr/bin/env python3
# Author: Izaak Neutelings (September 2024)
# Description: Help functions for plotting wafers
# Sources:
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-sysval-offline/-/merge_requests/13
#   https://github.com/ywkao/hexagonal_histograms/tree/main/waferMaps
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/tree/master/DQM/data
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-sysval-offline/-/tree/master/data/geometry
# Instructions to run as script and create plotly templates for the wafers:
#  cd $CMSSW_BASE/src/HGCalCommissioning/LocalCalibration
#  python3 python/plot/wafer.py
import os, re
import json
try:
  import plotly.graph_objects as go
  import plotly.colors as pc
  import plotly.io as pio
except ModuleNotFoundError as error:
  error.msg += "! Please install with 'python3 -m pip install --user plotly'"
  #raise error #do not raise ... jobs ran within CMSSW do not need this

rgb_exp = re.compile(r"\d+")
#datadir = "../DQM/data" #"$CMSSW_BASE/src/HGCalCommissioning/DQM/data"
datadir = os.path.relpath(os.path.join(os.environ.get("CMSSW_BASE"),"src/HGCalCommissioning/DQM/data"),os.getcwd())
wafertraces = { } # cache (x,y) traces of (hexagonal) wafers
waferlimits = { } # cache of (xmin,xmax) & (ymin,ymax) of wafers traces
waferfigs   = { } # cache template of plotly figure traces of (hexagonal) wafers

  
def getcolorscale(colorscale='Hot',invert=False):
  """Get plotly color scale, and convert RGB string to tuple of integers!"""
  # https://plotly.com/python/builtin-colorscales/#builtin-sequential-color-scales
  if isinstance(colorscale,str):
    colorscale = pc.get_colorscale(colorscale)
  if invert:
    ncols = len(colorscale)
    colorscale = [ (colorscale[i][0],colorscale[ncols-i-1][1]) for i in range(ncols)]
  colorscale_tuple = colorscale[:] # copy to prevent overwriting
  for idx, (fraction, color) in enumerate(colorscale):
    if isinstance(color,str):
      if color.startswith('rgb'):
        matches = rgb_exp.findall(color)
        assert len(matches)==3, f"Got color={color!r}, expected format 'rgb(\\d+,\\d+,\\d+)'"
        colorscale_tuple[idx] = (fraction,tuple(map(int,matches[:3]))) # overwrite color
      else:
        raise ValueError(f"getcolorscale: Unknown color format: {low[1]!r}, {high[1]!r}, ")
  return colorscale, colorscale_tuple
  

def getcolor(x,xmin,xmax,colorscale='Hot'):
  """Get color from color scale for given value."""
  xnorm = max(0,min(1,(x-xmin)/(xmax-xmin))) # normalized within [0,1]
  if isinstance(colorscale,str):
    _, colorscale = getcolorscale(colorscale)
  color = colorscale[-1][1]
  for i in range(len(colorscale) - 1):
    low = colorscale[i]
    high = colorscale[i+1]
    if low[0]<=xnorm<=high[0]:
      xmid = (xnorm-low[0])/(high[0]-low[0])
      color = (
        int(low[1][0]+xmid*(high[1][0]-low[1][0])), # red
        int(low[1][1]+xmid*(high[1][1]-low[1][1])), # blue
        int(low[1][2]+xmid*(high[1][2]-low[1][2])), # green
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
      print(ch_values,moduletype)
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
  name_rexp = re.compile(r"hex(:?_nc)?_(\d+)$")
  for key in file.GetListOfKeys():
    obj = key.ReadObj()
    if not obj.InheritsFrom("TGraph"): continue
    isCM = (iobj%39==37) or (iobj%39==38)
    if isCM: # ignore CM
      iobj += 1
      continue
    xvals.append(list(obj.GetX()))
    yvals.append(list(obj.GetY()))
    name = obj.GetName()
    match = name_rexp.match(name)
    if match:
      if iobj!=int(match.group(2)):
        print(f">>> get_wafer_from_ROOT: WARNING! iobj={iobj}, name={name!r}, match={match.groups()}")
    else:
      print(f">>> get_wafer_from_ROOT: WARNING! iobj={iobj}, name={name!r}, match={match.groups()}")
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
  
  #### WRITE TO JSON (ROOT is so slow to import...)
  ###outfname = os.path.join(outdir,f"geometry_{modtype}_wafer.json")
  ###print(f">>> get_wafer_from_ROOT: Writing xy values to {outfname}...")
  ###with open(outfname,'w') as outfile:
  ###  json.dump(wafertraces[modtype],outfile)
  
  return xvals, yvals
    

def get_wafer_from_JSON(modtype='ML_L',outdir=datadir,verb=0):
  """Retrieve plotly template from JSON."""
  modtype = modtype[:4].replace('-','_')
  if modtype in waferfigs:
    if verb>=2:
      print(f">>> get_wafer_from_JSON: Reusing cached template for wafer traces of modtype={modtype!r}...")
    fig = waferfigs[modtype]
  else:
    fname = os.path.join(datadir,f"geometry_{modtype}_wafer.json")
    if verb>=2:
      print(f">>> get_wafer_from_JSON: Loading template for wafer for modtype={modtype!r} from {fname}...")
    with open(fname,'r') as file:
      fig = pio.read_json(file)
    waferfigs[modtype] = fig
  return go.Figure(fig)
  

def get_boundaries_JSON(modtype,verb=0):
  """Create boundaries between eRxs in wafers, loaded from JSON"""
  # https://github.com/ywkao/hexagonal_histograms/blob/main/include/
  # https://gitlab.cern.ch/hgcal-dpg/hgcal-sysval-offline/-/tree/master/data/geometry
  modtype = modtype[:4].replace('-','_')
  if verb>=1:
    print(f">>> get_boundaries_JSON for modtype={modtype!r}")
  fname = os.path.join(datadir,"geometry_wafer_boundaries.json")
  with open(fname,'r') as file:
    data = json.load(file)
  return data[modtype]
  

def create_wafer_template(nchans,modtype='ML_F',outdir=datadir,title="",tag="",
                          lines=True,root=False,verb=0,**kwargs):
  """Create wafer plot template to hopefully speed up creation of plots."""
  tmarg         = kwargs.pop('tmarg',    50       )
  rmarg         = kwargs.pop('rmarg',    90       )
  write_numbers = kwargs.pop('numbers',  False    ) # write numbers on plot
  write         = kwargs.pop('write',    False    ) # write to JSON
  write_plot    = kwargs.pop('plot',     write    ) # write to PNG
  docolor       = kwargs.pop('color',    False    )
  opacity       = kwargs.pop('opacity',  0.6 if docolor else 0.8 )
  template      = kwargs.pop('template', 'plotly' )
  modtype       = modtype[:4].replace('-','_')
  colorscale, colorscale_tuple = getcolorscale('RdBu',invert=True)
  
  # FROM CACHE / JSON
  if (modtype in waferfigs) and (not write_plot):
    if verb>=2:
      print(f">>> create_wafer_template: Reusing cached template for wafer traces of modtype={modtype!r}...")
    return go.Figure(waferfigs[modtype]) # copy
  elif not root:
    return get_wafer_from_JSON(modtype,verb=verb)
  
  # FROM ROOT
  if verb>=1:
    print(f">>> create_wafer_template: Creating new template for wafer traces of modtype={modtype!r} from ROOT...")
  xvals, yvals = get_wafer_from_ROOT(nchans,modtype=modtype,verb=verb)
  xmin, xmax = waferlimits[modtype]['x'] #getlimits(xvals,margin=0.04)
  ymin, ymax = waferlimits[modtype]['y'] #getlimits(yvals,margin=0.04)
  
  # CREATE FIGURE
  fig = go.Figure()
  for i, (x, y) in enumerate(zip(xvals,yvals)): # loop over cells
    xwmin, xwmax = min(x), max(x)
    ywmin, ywmax = min(y), max(y)
    xw = (xwmin+xwmax)/2.
    yw = (ywmin+ywmax)/2.
    color = getcolor(i,0,nchans-1,colorscale=colorscale_tuple) if docolor else 'white'
    fig.add_trace(go.Scatter( # add channel (hexagon)
      x=x,y=y,
      text=f"i={i}<br>x={xw:.3g}<br>y={yw:.3g}",
      mode='lines',#line_color='black',
      line=dict(color='black',width=1),
      fill='toself',fillcolor=color,
      opacity=opacity,
    ))
    
    # WRITE CHANNEL NUMBERS
    if write_numbers:
      tsize = 11
      ww = xwmax-xwmin # cell width
      hw = ywmax-ywmin # cell height
      if len(x)>16:
        #xy = [f"({x_:.2g},{y_:.2g})" for x_, y_ in zip(x,y)]
        #print(f">>> i={i:2d}, npoints={len(x):2d}, (x,y)=({xw:.2g},{yw:.2g}), xy={xy}")
        #xw -= 0.17
        yw += 0.32*hw
        tsize = 9.5
      elif i>9 and hw<0.9: # calibration cells
        tsize = 9 if i>99 else 10
      elif modtype=='ML_R' and i in [16,105]:
        xw += -0.14*ww
        yw += (0.14 if i<100 else -0.14)*hw
      fig.add_annotation(
        x=xw,y=yw,yshift=0,
        text=str(i),showarrow=False,
        font=dict(size=tsize,color='blue',shadow='white 0px 0px 4px'),
      )
  
  # ADD BOUNDARY LINES
  if lines:
    if verb>=2:
      print(f">>> create_wafer_template: Adding boundary lines...")
    lines = get_boundaries_JSON(modtype,verb=verb)
    for line in lines:
      fig.add_trace(go.Scatter( # add channel (hexagon)
        x=line['x'],y=line['y'],
        mode='lines',#line_color='black',
        line=dict(color='red',width=1.8),
        opacity=1,
        hoverinfo='skip', # no info box when hovered over
      ))
  
  # UPDATE LAYOUT
  width  = (710 if abs(xmax-xmin)>15 else 410) + rmarg
  height = 600 + tmarg
  fig.update_layout(
    title=title,
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
    width=width, height=height,
    margin=dict(r=rmarg,t=tmarg,l=10,b=22,pad=2),
  )
  waferfigs[modtype] = fig # cache to speed up creation of figures
  
  # WRITE TO JSON (ROOT is slow...)
  if write:
    outfname = os.path.join(outdir,f"geometry_{modtype}_wafer{tag}.json")
    print(f">>> create_wafer_template: Writing figure template to {outfname}...")
    fig.write_json(outfname,pretty=True) #.replace(".json","_fig.json")
  
  # WRITE TO PNG
  if write_plot:
    plotname = os.path.join(outdir,f"geometry_{modtype}_wafer{tag}.png")
    print(f">>> create_wafer_template: Writing figure template to {plotname}...")
    fig.write_image(plotname,scale=2.6)
  
  if verb>=2:
    print(f">>> create_wafer_template: Done with template {plotname}...")
  
  return go.Figure(fig) # copy
  

if __name__ == '__main__': # run as script
  
  # CONVERT wafer templates from ROOT -> JSON
  verb = 4
  mods = [
    (444,'MH_F'),(222,'ML_F'),
    (111,'ML_L'),(111,'ML_R') # partials
  ]
  tags = [
    '',
    #'_color'
  ]
  for tag in tags:
    kwargs = dict(
      root  = True,
      write = True,
      plot  = True,
      docol = False,
      tag   = tag
    )
    if tag in ['_color','_dark']:
      kwargs.update(dict(
        write = False,
        numbers = True,
        docol = True,
        tmarg=10,
        rmarg=10,
      ))
      write = False
      docol = True
    if tag in ['_dark']:
      kwargs.update(dict(
        template='plotly_dark'
      ))
    for nchans, modtype in mods:
      #get_wafer_from_ROOT(nc,modtype=mt,outdir=datadir,verb=0)
      create_wafer_template(nchans,modtype=modtype,outdir=datadir,verb=verb,**kwargs)
    
