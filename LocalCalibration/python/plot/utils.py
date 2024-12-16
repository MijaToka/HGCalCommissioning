# Author: Izaak Neutelings (November 2024)
import os
import math
import ROOT
lcolors = [
  ROOT.kBlue+1, ROOT.kRed+1, ROOT.kGreen+2, ROOT.kOrange+1,
  ROOT.kPink+1, ROOT.kAzure+1, ROOT.kGreen-9, ROOT.kOrange+7, ROOT.kMagenta
]


def columnize(oldlist,ncols=2):
    """Reorder list, such that the order follows from top to bottom, left to right.""" 
    nrows = math.ceil(len(oldlist)/float(ncols))
    return [x for i in range(nrows) for x in oldlist[i::nrows]]
    

def setstyle(hist):
    """Help function to set default draw style for ROOT file."""
    hist.SetLineColor(ROOT.kBlue)
    hist.SetLineWidth(2)
    hist.SetMarkerColor(ROOT.kBlue+1)
    hist.SetMarkerStyle(ROOT.kFullDotLarge) # scalable
    hist.SetMarkerSize(0.6)
    

def makehist(*args,ymin=None,ymax=None):
    """Help function to create 1D histogram for given name & title."""
    hist = ROOT.TH1F(*args)
    setstyle(hist)
    if ymin!=None: # for plotting
        hist.SetMinimum(ymin)
    if ymax!=None: # for plotting
        hist.SetMaximum(ymax)
    return hist
    

def makegraph(name,title=None,np=-1,ymin=None,ymax=None,errors=False):
    """Help function to create graph for given name & title."""
    TGraph = ROOT.TGraphAsymmErrors if errors else ROOT.TGraph
    graph  = TGraph(np) if np>0 else TGraph()
    graph.SetName(name)
    graph.SetTitle(name if title is None else title)
    setstyle(graph)
    if ymin!=None: # for plotting
        graph.SetMinimum(ymin)
    if ymax!=None: # for plotting
        graph.SetMaximum(ymax)
    return graph
    

def gethist_from_file(hname,file=None,verb=0):
    """Get histogram from file."""
    if verb>=1:
        print(f">>> gethist_from_file: Retrieving {hname!r}...")
    if ':' in hname:
        fname, hname = hname.split(':')
        file = ROOT.TFile.Open(fname,'READ')
    elif not file:
        raise OSError(f"No valid input: hname={hname!r}, file={file!r}")
    assert (file and not file.IsZombie()), f"Could not open file {fname}..."
    hist = file.Get(hname)
    assert hist, f"Could not extract file {fname}:{hname}..."
    if hasattr(hist,'SetDirectory'):
        hist.SetDirectory(0) # to keep in memory before closing file
    file.Close()
    return hist
     

def makeHistComparisonCanvas(hists,**kwargs):
    """Plot comparison with histograms. Return canvas."""
    xtitle   = kwargs.pop('xtitle',   None     )
    ytitle   = kwargs.pop('ytitle',   None     )
    rtitle   = kwargs.pop('rtitle',   "Ratio"  )
    xmin     = kwargs.pop('xmin',     None     )
    xmax     = kwargs.pop('xmax',     None     )
    ymin     = kwargs.pop('ymin',     None     )
    ymax     = kwargs.pop('ymax',     None     )
    rmin     = kwargs.pop('rmin',     0.0      )
    rmax     = kwargs.pop('rmax',     2.0      )
    tsize    = kwargs.pop('tsize',    0.052    )
    lmarg    = kwargs.pop('lmarg',    0.12     )
    rmarg    = kwargs.pop('rmarg',    0.02     )
    bmarg    = kwargs.pop('bmarg',    0.12     )
    tmarg    = kwargs.pop('tmarg',    0.06     )
    lwidth   = kwargs.pop('lwidth',   1.0      )
    lheight  = kwargs.pop('lheight',  1.0      )
    text     = kwargs.pop('text',     None     ) # extra text in the corner
    header   = kwargs.pop('header',   ""       ) # legend header
    x1       = kwargs.pop('x1',       0.54     ) # legend top right corner
    y1       = kwargs.pop('y1',       0.95     ) # legend top right corner
    ratio    = kwargs.pop('ratio',    True     )
    norm     = kwargs.pop('norm',     False    )
    lumitext = kwargs.pop('lumi',     ""       )
    
    # INPUT
    if isinstance(hists,dict):
        hists_ = [ ]
        for title, hist in hists.items():
            if isinstance(hist,str):
                hist = gethist_from_file(hist)
            hist.SetTitle(title)
            hists_.append(hist)
        hists = hists_
    
    # NORMALIZE
    if norm is not False:
        norm = float(norm)
        for hist in hists:
            area = hist.Integral()
            if area!=0:
                hist.Scale(norm/area)
    
    # CANVAS
    mainframe  = hists[0].Clone('mainframe')
    canvas     = getcanvas(lmarg=lmarg,rmarg=rmarg,bmarg=bmarg,tmarg=tmarg,ratio=ratio)
    mainpad    = canvas.cd(1)
    mainframe, scale = setaxis(mainframe,xmin,xmax,ymin,ymax,xtitle=xtitle,ytitle=ytitle,
                               pad=mainpad,tsize=tsize,ratio=ratio)
    setHGCalStyle(mainpad,iPosX=0,lumiText=lumitext)
    
    # LEGEND
    colsep   = 0.03
    nlines   = len(hists)
    ncols    = 1 if nlines<=4 else 2 # number of columns
    lsize    = tsize #*scale
    lwidth  *= 0.23
    if ncols>=2:
      hists   = columnize(hists,ncols) # reorder: top to bottom, left to right
      nchars  = len(hists[0].GetTitle()) # rough estimate
      lwidth *= ncols/(1-colsep)*(1.0 if nchars>=10 else 0.8)
      nlines  = (nlines+1)//2 # half then number of lines, rounding up
      margin  = 0.068/lwidth
      x1     -= lwidth/2.4
    else:
      margin = 0.036/lwidth
    lheight *= 1.17*lsize*nlines
    if header:
        lheight += tsize*1.2
    x1 += mainpad.GetLeftMargin()
    y1 -= mainpad.GetTopMargin()
    x2  = x1 + lwidth
    y2  = y1 - lheight
    #print(f">>> (x1,x2,y1,y2)=({x1:3.2f},{x2:3.2f},{y1:3.2f},{y2:3.2f})")
    legend = ROOT.TLegend(x1,y1,x2,y2)
    legend.SetFillStyle(0)
    legend.SetBorderSize(0)
    legend.SetTextSize(lsize)
    legend.SetMargin(margin)
    if ncols>1:
        legend.SetNColumns(ncols)
        legend.SetColumnSeparation(colsep)
    if header:
        legend.SetTextFont(62) # bold
        legend.SetHeader(header)
    legend.SetTextFont(42)
    
    # DRAW
    #dopt = 'PE1 SAME'
    dopt = 'HIST SAME'
    for i, hist in enumerate(hists):
        color  = lcolors[i%len(lcolors)]
        hist.SetLineColor(color)
        hist.SetLineWidth(3)
        hist.SetMarkerSize(0.8)
        hist.SetMarkerColor(color)
        hist.SetMarkerStyle(ROOT.kFullDotLarge) # scalable point
        hist.Draw(dopt)
        legend.AddEntry(hist,hist.GetTitle(),'lp')
    legend.Draw()
    mainpad.RedrawAxis()
    
    # TEXT
    latex = addtext(mainpad,text,tsize=tsize)
    
    # BOTTOM PANEL
    lowframe = None
    rhists = [ ]
    if ratio:
        dopt = 'HIST ][ SAME'
        lowpad = canvas.cd(2)
        hden = hists[0].Clone('lowframe')
        lowframe, rscale = setaxis(hden,xmin,xmax,rmin,rmax,xtitle=xtitle,ytitle=rtitle,
                                   pad=lowpad,tsize=tsize,ratio=ratio)
        for hnum in hists:
            rhist = hnum.Clone("ratio_"+hnum.GetName())
            rhist.Divide(hden)
            rhist.Draw(dopt)
            rhists.append(rhist)
        lowpad.RedrawAxis()
    
    # attach objects to canvas to evade memory garbage collection
    canvas.cache = [mainframe,lowframe,legend,latex]+rhists
    return canvas
    

def comparehists(hists,tag="",text=None,**kwargs):
    """Plot comparison with histograms. Write canvas."""
    outdir = kwargs.pop('outdir', 'plots'         )
    fname  = kwargs.pop('fname',  "compare"+tag   )
    exts   = kwargs.pop('ext',    ['.pdf','.png'] )
    fname  = os.path.join(outdir,fname)
    os.makedirs(outdir,exist_ok=True)
    canvas = makeHistComparisonCanvas(hists,tag=tag,text=text,**kwargs)
    for ext in exts:
        canvas.SaveAs(fname+ext)
    canvas.Close()
    #ROOT.gDirectory.ls()
    

def addtext(pad,text,tsize=0.050):
    """Add text to plot."""
    if not text:
        return None
    lines = [text] if isinstance(text,str) else text
    x = pad.GetLeftMargin()+0.045
    y = 0.95-pad.GetTopMargin()
    latex = ROOT.TLatex()
    latex.SetTextSize(tsize)
    latex.SetTextAlign(13) # right, top
    latex.SetTextFont(42)
    #latex.SetNDC(True)
    for line in lines:
        latex.DrawLatexNDC(x,y,line)
        y -= 1.1*tsize
    return latex
    

def getcanvas(width=1000,lmarg=0.11,rmarg=0.06,bmarg=0.13,tmarg=0.06,ratio=False):
    """Create canvas."""
    npanels = int(ratio)
    ysplit  = 0.33
    height  = 750+npanels*250
    canvas  = ROOT.TCanvas('canvas','canvas',width,height) # XYWH
    canvas.SetFillColor(0)
    #canvas.SetFillStyle(0)
    canvas.SetBorderMode(0)
    canvas.SetFrameBorderMode(0)
    if npanels==0:
        canvas.SetMargin(lmarg,rmarg,bmarg,tmarg) # LRBT
    else:
        tmarg_ = 750*tmarg/(height*(1.-ysplit))
        bmarg_ = 750*bmarg/(height*ysplit)
        #print(tmarg,tmarg_,bmarg,bmarg_)
        canvas.SetMargin(0.0,0.0,0.0,0.0) # LRBT
        canvas.Divide(2)
        mainpad = canvas.cd(1)
        mainpad.SetPad('mainpad','mainpad',0.0,ysplit,1.0,1.0) # xlow,ylow,xup,yup
        mainpad.SetMargin(lmarg,rmarg,0.0282,tmarg_) # LRBT
        mainpad.SetFillColor(0)
        mainpad.SetFillStyle(4000) # transparant (for pdf)
        #mainpad.SetFillStyle(0)
        mainpad.SetTicks(1,1)
        mainpad.SetBorderMode(0)
        mainpad.Draw()
        lowpad = canvas.cd(2)
        lowpad.SetPad('lowpad','lowpad',0.0,0.0,1.0,ysplit) # xlow,ylow,xup,yup
        lowpad.SetMargin(lmarg,rmarg,bmarg_,0.035) # LRBT
        lowpad.SetFillColor(0) #lowpad.SetFillColorAlpha(0,0.0)
        lowpad.SetFillStyle(4000) # transparant (for pdf)
        lowpad.SetBorderMode(0)
        lowpad.SetTicks(1,1)
        lowpad.Draw()
    canvas.cd(1)
    return canvas
    

def setaxis(*args,**kwargs):
    """Create frame & set axis."""
    hists  = [x for x in args if isinstance(x,ROOT.TH1)]
    limits = [x for x in args if isinstance(x,(int,float))]
    limits = limits+[None]*max(0,4-len(limits))
    frame  = kwargs.pop('frame',  hists[0] if hists else None )
    xmin   = kwargs.pop('xmin',   limits[0] )
    xmax   = kwargs.pop('xmax',   limits[1] )
    ymin   = kwargs.pop('ymin',   limits[2] )
    ymax   = kwargs.pop('ymax',   limits[3] )
    ymarg  = kwargs.pop('ymarg',  None      ) # margin above hist maximum
    logx   = kwargs.pop('logx',   False     )
    logy   = kwargs.pop('logy',   False     )
    ratio  = kwargs.pop('ratio',  False     )
    pad    = kwargs.pop('pad',    ROOT.gPad )
    xtitle = kwargs.pop('xtitle', None      )
    ytitle = kwargs.pop('ytitle', None      )
    tsize  = kwargs.pop('tsize',  0.50      )
    pad.SetLogy(logy)
    pad.SetLogx(logx)
    #print(f">>> setaxis: pad={pad.GetName()!r}, Wh={pad.GetWh():.5g}, HNDC={pad.GetHNDC():.5g}")
    ismain  = pad.GetName() in ['mainpad','canvas']
    yscale  = 750/min(pad.GetWh()*pad.GetHNDC(),pad.GetWw()*pad.GetWNDC()) # automatic scaling (e.g. for lower panel)
    xscale  = 0 if (ratio and ismain) else yscale
    xtsize  = 0.9*tsize*xscale
    ytsize  = 0.9*tsize*yscale
    xoffset = 1.00
    yoffset = 9.2/yscale*pad.GetLeftMargin() # ytitleoffset
    if frame is None:
        assert all(x is not None for x in [xmin,xmax,ymin,ymax]), f"xmin={xmin}, ymin={ymin}, xmax={xmax}, ymax={ymax}"
        frame = pad.DrawFrame(xmin,ymin,xmax,ymax)
    else:
        if ymarg is not None:
            ymax = ymarg*max(h.GetMaximum() for h in hists)
        if not (xmin is None or xmax is None):
            xmin = frame.GetXaxis().GetXmin() if xmin is None else xmin
            xmax = frame.GetXaxis().GetXmax() if xmax is None else xmax
            frame.GetXaxis().SetRangeUser(xmin,xmax)
        if ymin is not None:
            frame.SetMinimum(ymin)
        if ymax is not None:
            frame.SetMaximum(ymax)
        if xtitle is None:
             xtitle = frame.GetXaxis().GetTitle()
        if ytitle is None:
             ytitle = frame.GetYaxis().GetTitle()
    frame.GetXaxis().SetTitle(xtitle)
    frame.GetYaxis().SetTitle(ytitle)
    frame.GetXaxis().SetTitleSize(tsize*xscale)
    frame.GetYaxis().SetTitleSize(tsize*yscale)
    #frame.GetXaxis().SetLabelOffset(0.004 if logx else 0.005)
    frame.GetXaxis().SetLabelSize(xtsize)
    frame.GetYaxis().SetLabelSize(ytsize)
    frame.GetXaxis().SetTitleOffset(xoffset)
    frame.GetYaxis().SetTitleOffset(yoffset)
    frame.GetYaxis().CenterTitle(not ismain)
    if logx: # tick labels
        # https://root.cern/doc/master/logscales_8C.html
        frame.GetXaxis().SetNoExponent(True)
        frame.GetXaxis().SetMoreLogLabels(True)
    if not ismain:
        frame.GetXaxis().SetTickLength(0.018/pad.GetHNDC())
        frame.GetYaxis().SetNdivisions(508)
    frame.Draw('AXIS')
    pad.RedrawAxis()
    return frame, yscale
  

def copytdir(source,target):
    """
    Copy all objects and subdirectories of the given ROOT directory 'source'
    as a subdirectory of the current directory.
    https://root.cern.ch/doc/master/copyFiles_8C.html
    """
    if isinstance(source,str):
      source = ROOT.TFile.Open(source,'READ')
      if not source or source.IsZombie():
        print(f">>> File {source.GetPath()!r} does not exist or is corrupt! Skipping...")
        return False
    #source.ls()
    target.cd() # change to the new directory before writing
    for key in source.GetListOfKeys():
        cname = key.GetClassName()
        cls = ROOT.gROOT.GetClass(cname)
        if not cls:
          continue
        kname = key.GetName()
        if cls.InheritsFrom('TDirectory'):
            subdir = key.ReadObj()
            newtarget = target.mkdir(kname)
            copytdir(subdir,newtarget) # recursively copy
            target.cd() # change back to current sourge
        elif cls.InheritsFrom('TTree'):
            oldtree = source.Get(kname)
            newtree = oldtree.CloneTree()
            newtree.Write()
        else:
            obj = key.ReadObj()
            obj.Write()
    return True
    

def setHGCalStyle(pad, iPosX=0, **kwargs):
    """Set CMS style for a given TPad."""
    cmsTextFont    = 61 # 60: Arial bold (helvetica-bold-r-normal)
    extraTextFont  = 52 # 50: Arial italics (helvetica-medium-o-normal)
    lumiTextOffset = 0.20
    cmsText       = kwargs.pop('cmsText',      "CMS HGCal" ) # large, bold text
    extraText     = kwargs.pop('extraText',    "Internal"  ) # 'Preliminary', 'Simulation', ...
    lumiText      = kwargs.pop('lumiText',     ""          ) # luminosity text, e.g. '138 fb^{#minus1} (13 TeV)'
    relPosX       = kwargs.pop('relPosX',      0.044 if cmsText=='CMS' else 0.106 ) # relative position between 'CMS' and extra text
    relPosY       = kwargs.pop('relPosY',      0.035       )
    relExtraDY    = kwargs.pop('relExtraDY',   1.2         )
    cmsTextSize   = kwargs.pop('cmsTextSize',  1.00        )
    lumiTextSize  = kwargs.pop('lumiTextSize', 0.90        )
    extraTextSize = kwargs.pop('extraTextSize',0.78        )*cmsTextSize
    outOfFrame    = kwargs.pop('outOfFrame',   iPosX/10==0 ) # print CMS text outside frame
    verbosity     = kwargs.pop('verb',         0           ) # verbosity level
    if outOfFrame:
        lumiTextSize *= 0.90
    if verbosity>=2:
        print(">>> setCMSLumiStyle: cmsText=%r, extraText=%r, lumiText=%r"%(cmsText,extraText,lumiText))
    
    # https://root.cern.ch/doc/master/classTAttText.html#ATTTEXT1
    alignY_ = 3 # align top
    alignX_ = 2 # align center
    if   iPosX==0:     alignY_ = 1 # align bottom
    if   iPosX//10==0: alignX_ = 1 # align left
    elif iPosX//10==1: alignX_ = 1 # align left
    elif iPosX//10==2: alignX_ = 2 # align center
    elif iPosX//10==3: alignX_ = 3 # align right
    align = 10*alignX_ + alignY_
    
    H = pad.GetWh()*pad.GetHNDC()
    W = pad.GetWw()*pad.GetWNDC()
    l = pad.GetLeftMargin()
    t = pad.GetTopMargin()
    r = pad.GetRightMargin()
    b = pad.GetBottomMargin()
    e = 0.025
    scale = float(H)/W if W>H else 1 # float(W)/H
    pad.cd()
    
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextAngle(0)
    latex.SetTextColor(ROOT.kBlack)
    latex.SetTextFont(42)
    latex.SetTextAlign(31)
    latex.SetTextSize(lumiTextSize*t)
    
    if lumiText:
        latex.DrawLatex(1-r,1-t+lumiTextOffset*t,lumiText)
    
    if iPosX==0:
        relPosX = relPosX*(42*t*scale)*(cmsTextSize/0.84) # scale
        posX = l + relPosX #*(1-l-r)
        posY = 1 - t + lumiTextOffset*t
    else:
        posX = 0
        posY = 1 - t - relPosY*(1-t-b)
        if iPosX%10<=1:
            posX = l + relPosX*(1-l-r)     # left aligned
        elif iPosX%10==2:
            posX = l + 0.5*(1-l-r)          # centered
        elif iPosX%10==3:
            posX = 1 - r - relPosX*(1-l-r) # right aligned
    
    if outOfFrame:
        ROOT.TGaxis.SetExponentOffset(-0.12*float(H)/W,0.015,'y')
        latex.SetTextFont(cmsTextFont)
        latex.SetTextAlign(11)
        latex.SetTextSize(cmsTextSize*t)
        latex.DrawLatex(l,1-t+lumiTextOffset*t,cmsText)
        if extraText:
            latex.SetTextFont(extraTextFont)
            latex.SetTextSize(extraTextSize*t)
            latex.SetTextAlign(align)
            latex.DrawLatex(posX,posY,extraText)
    else: # inside frame
        latex.SetTextFont(cmsTextFont)
        latex.SetTextSize(cmsTextSize*t)
        latex.SetTextAlign(align)
        latex.DrawLatex(posX,posY,cmsText)
        if extraText:
            lines = extraText.split('\n') if '\n' in extraText else [extraText]
            latex.SetTextFont(extraTextFont)
            latex.SetTextAlign(align)
            latex.SetTextSize(extraTextSize*t)
            for i, line in enumerate(lines):
                latex.DrawLatex(posX,posY-(relExtraDY+i)*cmsTextSize*t,line)
    
    pad.SetTicks(1,1) # ticks on all four sides
    pad.Update()
    return latex