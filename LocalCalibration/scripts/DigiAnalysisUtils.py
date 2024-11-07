import ROOT
import os
import itertools
import json
import gzip
import re
import pandas as pd

def defineDigiDataFrameFromSpecs(specs, attachProgressBar=True, ix_filter_cond='ix>=0'):
    """defines the dataframe to be used for the analysis of DIGIs in NANOAOD
    specs is a json file used to instatiate the RDataFrame. if the name is of the form json:ix
    it is split and the ix passed is used to split the full instantiation
    """
    
    #start RDataFrame from specifications
    ROOT.gInterpreter.Declare('#include "interface/helpers.h"')
    rdf = ROOT.RDF.Experimental.FromSpec(specs)
    if attachProgressBar:
        ROOT.RDF.Experimental.AddProgressBar(rdf)
        
    # filter out data for the fed/readout sequence corresponding to a single module
    rdf = rdf.DefinePerSample('ix', 'rdfsampleinfo_.GetI("index")') \
             .Filter(ix_filter_cond) \
             .DefinePerSample('target_module_fed', 'rdfsampleinfo_.GetI("fed")') \
             .DefinePerSample('target_module_seq', 'rdfsampleinfo_.GetI("seq")') \
             .Define('good_digiadc',  'HGCDigi_flags!=0xFFFF && HGCDigi_tctp<3') \
             .Define('good_digitot',  'HGCDigi_flags!=0xFFFF && HGCDigi_tctp==3') \
             .Define('good_digitoa',  'HGCDigi_flags!=0xFFFF && HGCDigi_toa>0') \
             .Define('target_module', 'HGCDigi_fedId==target_module_fed && HGCDigi_fedReadoutSeq==target_module_seq') \
             .Define('maskadc',       'good_digiadc & target_module') \
             .Define('masktot',       'good_digitot & target_module') \
             .Define('masktoa',       'good_digitoa & target_module') \
             .Define('chadc',         'HGCDigi_channel[maskadc]') \
             .Define('chtot',         'HGCDigi_channel[masktot]') \
             .Define('chtoa',         'HGCDigi_channel[masktoa]') \
             .Define('chtypeadc',     'HGCDigi_chType[maskadc]') \
             .Define('adcm1',         'HGCDigi_adcm1[maskadc]') \
             .Define('adc',           'HGCDigi_adc[maskadc]') \
             .Define('adc_tctp3',     'HGCDigi_adc[masktot]') \
             .Define('tot',           'HGCDigi_tot[masktot]') \
             .Define('toa',           'HGCDigi_toa[masktoa]') \
             .Define('modulecm',      'HGCDigi_cm[maskadc]') \
             .Define('cm2',           'commonMode(modulecm,2)') \
             .Define('cm4',           'commonMode(modulecm,4)') \
             .Define('cmall',         'commonMode(modulecm,-1)') \
             .Define('nchadc',        'Sum(maskadc)') \
             .Define('nchtot',        'Sum(masktot)') \
             .Define('nchtoa',        'Sum(masktoa)')
    
    # NOTE: We probably should define goodflags for toa and ADC-1 using the HGC_digiflags so that the histograms below are properly filled
    # NOTE: trigger type should be used for NZS
    
    return rdf


def analyzeSimplePedestal(outdir, module, task_spec, filter_cond : str = ''):
    """
    a base method to fill histograms which are common in most of the runs dedicated to extract baseline constants for the offline and online
    the method signature is such that it can be dispatched using a pool
    args is a tuple containing output directory, the module to select and the specification of the tasks for RDataFrame
    NOTE: as the histograms are heavy a single thread is used otherwise mem explodes with copies...
    an alternative would be to use boost histograms and Josh Bendavid's narf
    """

    ROOT.gInterpreter.Declare('#include "interface/helpers.h"')

    #read #pts and #eErx from first task
    with open(task_spec) as json_data:
        samples = json.load(json_data)['samples']
    nerx = samples['data1']['metadata']['nerx']
    nch = nerx*37
    npts = max(d['metadata']['index'] for s, d in samples.items()) #len(samples)

    #run a mini scan to determine appropriate bounds
    minirdf = defineDigiDataFrameFromSpecs(task_spec)
    minirdf = minirdf.Range(1000)
    if len(filter_cond)>0:
        minirdf = minirdf.Filter(filter_cond)
        
    obslist = ['adc', 'cm2', 'cm4', 'cmall', 'toa', 'tot']
    obsbounds  = [minirdf.Min(x) for x in obslist]
    obsbounds += [minirdf.Max(x) for x in obslist]
    obsbounds += [minirdf.Mean(x) for x in obslist]
    ROOT.RDF.RunGraphs(obsbounds)
    bindefs={}
    for i,obs in enumerate(obslist):
        minobs = int(obsbounds[i].GetValue()) - 0.5            
        maxobs = int(obsbounds[i+len(obslist)].GetValue()) + 0.5
        #if no values to determine min/max the difference will be inf
        #conversion to int is impossible
        #limit also cases where the number of bins is 0 or larger than 12b
        try:
            nobs = int(maxobs - minobs)
            if nobs<1 or nobs>4095 :
                raise ValueError

            #if there is a large spread in ADC-like channels it's suspicious
            #to avoid booking a large histogram prefer to focus on a window around the mean
            if not obs in ['toa','tot'] and nobs>512:
                avgobs = int(obsbounds[i+2*len(obslist)].GetValue())
                minobs = max(avgobs-256-0.5,-0.5)
                maxobs = min(avgobs+256+0.5,1024.5)
                nobs = int(maxobs - minobs)
                print('[Warning] Limited binning for {obs} due to large number of bins')            
        except:
            continue
        bindefs[obs]=(nobs,minobs,maxobs)
    print(f'Bins determined from sub-sample: {bindefs}')

    #fill a histo with the scan info
    ptbinning=(npts,0.5,npts+0.5)
    infobinning = (2,0,2)
    scanInfoHist = ROOT.TH2F('scaninfo', 'Scan point;Parameters', *ptbinning, *infobinning)
    scanInfoHist.GetYaxis().SetBinLabel(1,'Run')
    scanInfoHist.GetYaxis().SetBinLabel(2,'LS')
    for ls,lsinfo in samples.items():
        idx = lsinfo["metadata"]["index"]
        run, postfix = re.findall('.*/NANO_(\d+)_(.*).root',lsinfo['files'][0])[0]        
        scanInfoHist.SetBinContent(idx,1,int(run))
        scanInfoHist.SetBinContent(idx,2,int(postfix) if postfix.isdigit() else idx+1)
        
    #declare histograms with full statistics
    rdf=defineDigiDataFrameFromSpecs(task_spec)
    if len(filter_cond)>0:
        rdf = rdf.Filter(filter_cond)
    graphlist=[]
    chbinning=(nch,-0.5,nch-0.5)    
    if 'adc' in bindefs:
        graphlist += [
            rdf.Histo2D(("adcm1",      ';ADC(BX-1);Channel', *chbinning, *bindefs['adc']), "chadc", "adcm1"),
            rdf.Histo2D(("adc",        ';ADC;Channel',       *chbinning, *bindefs['adc']), "chadc", "adc"),
            rdf.Histo3D(("adcvsadcm1", ';Channel;ADC-1;ADC', *chbinning, *bindefs['adc'], *bindefs['adc']), "chadc", "adcm1", "adc")
        ]
    if 'cmall' in bindefs:
        graphlist += [
            rdf.Histo3D(("adcvscm2",   ';Channel;CM2;ADC',   *chbinning, *bindefs['cm2'],   *bindefs['adc']), "chadc", "cm2",   "adc"),
            rdf.Histo3D(("adcvscm4",   ';Channel;CM4;ADC',   *chbinning, *bindefs['cm4'],   *bindefs['adc']), "chadc", "cm4",   "adc"),
            rdf.Histo3D(("adcvscmall", ';Channel;CMall;ADC', *chbinning, *bindefs['cmall'], *bindefs['adc']), "chadc", "cmall", "adc"),
        ]
    if 'tot' in bindefs:
        graphlist += [
            rdf.Histo2D(("tot", ';TOT;Channel', *chbinning, *bindefs['tot']), "chtot", "tot")
        ]
    if 'toa' in bindefs:
        graphlist += [
            rdf.Histo2D(("toa", ';TOA;Channel', *chbinning, *bindefs['toa']), "chtoa", "toa"),
        ]

    #run and save
    ROOT.RDF.RunGraphs(graphlist)
    histolist = [obj.GetValue() for obj in graphlist]
    rfile =  f'{outdir}/{module}.root'
    fillHistogramsAndSave(histolist = histolist, rfile = rfile)    
    return rfile

    
def scanHistoFiller(outdir, module, task_spec, filter_conds: dict, verb: int=0):
    """
    A base method to fill histograms in a scan (each sub-task in task_spec) is treated as a scan point
    filter_conds is a dict used to define different sub-samples for which the histos will be filled
    """

    ix_filt=-1
    if ':' in task_spec:
        task_spec,ix_filt = task_spec.split(':')
    
    # read #pts and #eErx from first task
    scantype = 'test'
    with open(task_spec) as json_data:
        samples = json.load(json_data)['samples']
    npts = max(d['metadata']['index'] for s, d in samples.items()) #len(samples)
    nerx = samples['data1']['metadata']['nerx']
    nch = nerx*37
    scantype = samples['data1']['metadata']['type'] # automatically recognize scan type
    if verb>=2:
        print(f"scanHistoFiller: scantype={scantype}, npts={npts}, nerx={nerx}, nch={nch}")
    
    # fill a histo with the scan info
    ptbins = (npts,0.5,npts+0.5) # scan points
    run_rexp = re.compile(r".*/NANO_(\d+)_(\d+).root")
    if scantype=='test': # scan over run & lumi section for debugging
        infobins = (2,0,2)
        scanInfoHist = ROOT.TH2F('scaninfo', "Scan point;Parameters", *ptbins, *infobins)
        scanInfoHist.GetYaxis().SetBinLabel(1,'Run')
        scanInfoHist.GetYaxis().SetBinLabel(2,'LS')
        for key, sample in samples.items(): # loop over lumi section blocks
            idx = sample['metadata']['index']
            run, ls = run_rexp.findall(sample['files'][0])[0]
            scanInfoHist.SetBinContent(idx,1,int(run))
            scanInfoHist.SetBinContent(idx,2,int(ls))
    elif scantype=='HGCALCalPulse': # scan over charge injection points ('CalPulseVal')
        infobins = (5,0,5)
        scanInfoHist = ROOT.TH2F('scaninfo', "Scan info;Scan point;Parameters", *ptbins, *infobins)
        scanInfoHist.GetYaxis().SetBinLabel(1,'Run')
        scanInfoHist.GetYaxis().SetBinLabel(2,'LS')
        scanInfoHist.GetYaxis().SetBinLabel(3,'dac')
        scanInfoHist.GetYaxis().SetBinLabel(4,'gain')
        scanInfoHist.GetYaxis().SetBinLabel(5,'n') #if run in different jobs this will be used to count how many sub-jobs are contributing 
        for key, sample in samples.items(): # loop over scan points
            idx  = sample['metadata']['index']
            injq = sample['metadata']['dac'] # injected charge
            gain = sample['metadata']['gain'] # gain
            run, ls = run_rexp.findall(sample['files'][0])[0]
            if verb>=2:
                print(f"scanHistoFiller: mod={module} idx={idx}, run={run}, ls={ls}, injq={injq}, files={sample['files']}")
            scanInfoHist.SetBinContent(idx,1,int(run))
            scanInfoHist.SetBinContent(idx,2,int(ls))
            scanInfoHist.SetBinContent(idx,3,int(injq))
            scanInfoHist.SetBinContent(idx,4,int(gain))
            scanInfoHist.SetBinContent(idx,5,1)
    else:
        raise IOError(f"Did not recognize scantype={scantype}...")
    
    # prepare RDF
    ROOT.gInterpreter.Declare('#include "interface/helpers.h"')
    ix_filter_cond='ix>=0' if ix_filt==-1 else f'ix=={ix_filt}'
    rdf = defineDigiDataFrameFromSpecs(specs=task_spec, attachProgressBar=True, ix_filter_cond=ix_filter_cond)
    
    # declare histograms (per sample filtered)
    chbins = (nch,-0.5,nch-0.5)    
    bin10b = (1024,-0.5,1023.5) # 10 bits for ADC
    bin12b = (4096,-0.5,4095.5) # 12 bits for TOT
    graphlist = [ ]
    for tag, filterval in filter_conds.items():
        filtered_rdf = rdf.Filter(filterval)
        if tag and tag[0]!='_':
          tag = '_'+tag
        graphlist = [
          filtered_rdf.Histo3D(("adc"+tag,      "ADC;Scan point;Channel;ADC",   *ptbins, *chbins, *bin10b), 'ix', 'chadc', 'adc'),
          filtered_rdf.Histo3D(("adc_tctp3"+tag,"ADC;Scan point;Channel;ADC",   *ptbins, *chbins, *bin10b), 'ix', 'chtot', 'adc_tctp3'),
          filtered_rdf.Histo3D(("nadc"+tag,     "nADC;Scan point;Channel;nADC", *ptbins, *chbins, *bin10b), 'ix', 'chadc', 'nchadc'),
          filtered_rdf.Histo3D(("tot"+tag,      "TOT;Scan point;Channel;TOT",   *ptbins, *chbins, *bin12b), 'ix', 'chtot', 'tot'),
          filtered_rdf.Histo3D(("ntot"+tag,     "nTOT;Scan point;Channel;nTOT", *ptbins, *chbins, *bin12b), 'ix', 'chtot', 'nchtot'),
          filtered_rdf.Histo3D(("toa"+tag,      "TOA;Scan point;Channel;TOA",   *ptbins, *chbins, *bin10b), 'ix', 'chtoa', 'toa'),
          filtered_rdf.Histo3D(("ntoa"+tag,     "nTOA;Scan point;Channel;nTOA", *ptbins, *chbins, *bin10b), 'ix', 'chtoa', 'nchtoa'),
        ]
    
    # run and save
    ROOT.RDF.RunGraphs(graphlist)
    histolist = [obj.GetValue() for obj in graphlist] + [scanInfoHist]
    postfix='' if ix_filt==-1 else f'_ix{ix_filt}'
    rfile = f'{outdir}/{module}{postfix}.root'
    fillHistogramsAndSave(histolist = histolist, rfile = rfile)    
    return rfile

def fillHistogramsAndSave(histolist : list, rfile : str):
    """saves list of histograms in ROOT file"""

    #write histograms to file    
    fOut=ROOT.TFile.Open(rfile,'RECREATE')
    fOut.cd()
    for obj in histolist:
        obj.SetDirectory(fOut)
        obj.Write()
    fOut.Close()
    print(f'Histograms available in {rfile}')
    

def profile3DHisto(url, hname):
    """
    This method analyzes a 3D histogram and summarizes its momenta assuming X is the profiling variable
    """
    
    if not os.path.isfile(url) or not url.endswith('.root'):
        raise IOError(f'{url} is not a ROOT file')
    
    fIn = ROOT.TFile.Open(url)
    h = fIn.Get(hname)
    cor_values = {'X':[], 'Y_mean':[], 'Z_mean':[], 'YZ_rho':[], 'Y_rms':[], 'Z_rms':[]}
    
    nx, xmin, xmax = h.GetNbinsX(), h.GetXaxis().GetXmin(), h.GetXaxis().GetXmax()
    ny, ymin, ymax = h.GetNbinsY(), h.GetYaxis().GetXmin(), h.GetYaxis().GetXmax()
    nz, zmin, zmax = h.GetNbinsZ(), h.GetZaxis().GetXmin(), h.GetZaxis().GetXmax()
    h2 = ROOT.TH2F(hname+'_proj','',ny,ymin,ymax,nz,zmin,zmax)
    for xbin in range(nx):
        cor_values['X'].append(xbin)
        h2.Reset('ICE')
        for ybin, zbin in itertools.product(range(ny),range(nz)):
            h2.SetBinContent(ybin+1,zbin+1, h.GetBinContent(xbin+1,ybin+1,zbin+1) )
        cor_values['Y_mean'].append(h2.GetMean(1))            
        cor_values['Y_rms'].append(h2.GetRMS(1))
        cor_values['Z_mean'].append(h2.GetMean(2))
        cor_values['Z_rms'].append(h2.GetRMS(2))
        cor_values['YZ_rho'].append(h2.GetCorrelationFactor())

    #free mem, close files
    h2.Delete()
    fIn.Close()
    
    return cor_values
    

def profile3DScanHisto(infname, hnames, storehists=True, adc_cut=180, verb=0):
    """
    This method analyzes a 3D histogram created by scanHistoFiller.
    """
    if verb>=1:
      print(f"profile3DScanHisto: fname={infname}, hnames={hnames}")
    
    # retrieve 3D histograms
    if not os.path.isfile(infname) or not infname.endswith('.root'):
        raise IOError(f'{infname} is not a ROOT file')
    infile   = ROOT.TFile.Open(infname,'READ')
    hists3D  = { } # input histograms
    for hname in hnames:
      hist3D = infile.Get(hname)
      if not hist3D:
        print(f"profile3DScanHisto: WARNING! No histogram {hname!r} found in {infname}...")
      hists3D[hname] = hist3D
    hinfo = infile.Get('scaninfo')
    
    # prepare output file
    outdname = os.path.dirname(os.path.dirname(infname))
    outfname = os.path.join(outdname,os.path.basename(infname))
    if verb>=2:
      print(f"profile3DScanHisto: Creating outfile {outfname}...")
    outfile = ROOT.TFile.Open(outfname,'RECREATE')
    
    # prepare directories for extra histograms & graphs
    gdir, hdir = None, None
    sdir = outfile.mkdir('summary','summary')
    if storehists:
      gdir = outfile.mkdir('graphs','graphs')
      hdir = outfile.mkdir('profiles','profiles')
    outfile.cd()
    hinfo.Write(hinfo.GetName())
    
    # prepare graph
    graphs = { h: { } for h in hnames }
    def fillgraph(hname,ch,x,y,yerr):
      """Help function to create & fill graphs."""
      if ch in graphs[hname]: # retrieve from cache
        graph = graphs[hname][ch]
      else: # create from scratch
        color = ROOT.kBlue if 'adc' in hname else ROOT.kRed
        graph = ROOT.TGraphErrors()
        graph.SetName(f"gr_{hname}_chan{ch}")
        graph.SetMarkerStyle(ROOT.kFullDotLarge) # scaleable circle
        graph.SetMarkerSize(1.1)
        graph.SetMarkerColor(color)
        graph.SetLineWidth(2)
        graph.SetLineColor(color)
        graph.SetTitle(f"Scan of {hname} in channel {ch};Injected charge;{hname}")
        graphs[hname][ch] = graph
      np = graph.GetN()
      graph.SetPoint(np,x,y)
      graph.SetPointError(np,0,yerr)
      return graph
    
    # get common binning from 3D histogram:
    #   x: scan point index
    #   y: channel index
    #   z: ADC or TOT
    hist3D0 = hists3D[hnames[0]]
    nx, xmin, xmax = hist3D0.GetNbinsX(), hist3D0.GetXaxis().GetXmin(), hist3D0.GetXaxis().GetXmax()
    ny, ymin, ymax = hist3D0.GetNbinsY(), hist3D0.GetYaxis().GetXmin(), hist3D0.GetYaxis().GetXmax()
    
    # prepare 2D summary histograms
    hists2D = { } # output histograms for summary
    for hname in hnames:
      xtit = hists3D[hname].GetXaxis().GetTitle() # scan point
      ytit = hists3D[hname].GetYaxis().GetTitle() # channel
      ztit = "Events"
      hists2D[hname] = {
        'ave':  ROOT.TH2F(f"ave_{hname}",f"Average {hname};{xtit};{ytit};{ztit}",nx,xmin,xmax,ny,ymin,ymax),
        'rms':  ROOT.TH2F(f"rms_{hname}",f"RMS {hname};{xtit};{ytit};{ztit}",nx,xmin,xmax,ny,ymin,ymax),
        'nevt': ROOT.TH2F(f"nevt_{hname}",f"Number of events in {hname};{xtit};{ytit};{ztit}",nx,xmin,xmax,ny,ymin,ymax),
        'nbin': ROOT.TH2F(f"nbin_{hname}",f"Number of nonzero bins in {hname};{xtit};{ytit};{ztit}",nx,xmin,xmax,ny,ymin,ymax)
      }
      for hist in hists2D[hname].values():
        hist.SetDirectory(sdir)
        hist.SetMarkerSize(1.2) # text size
        hist.SetMarkerColor(ROOT.kRed) # text color
        hist.SetOption('COLZ TEXT') # preset default draw option
    
    # find injected channels first from TOT, so we can also fill ADC
    hists3D_tot = [h for n, h in hists3D.items() if n[:3]=='tot']
    if hists3D_tot:
      hist3D_tot = hists3D_tot[0]
      nz = hist3D_tot.GetNbinsZ()
      iy_scan = set() # bin of channels that were scanned/injected
      if verb>=2:
        print(f"profile3DScanHisto: Look for channels that were scanned in {hist3D_tot.GetName()!r}...")
      for ix in range(1,nx+1): # loop over scan points
        if hinfo.GetBinContent(ix,3)<=2500: # injected charge
          continue # no TOT below 2000 inject charge...
        for iy in range(1,ny+1): # loop over channels
          if any(hist3D_tot.GetBinContent(ix,iy,iz)>10 for iz in range(1,nz+1)):
            iy_scan.add(iy)
      iy_scan = list(sorted(iy_scan)) # python sets cannot be sorted
      if not iy_scan:
        print(f"profile3DScanHisto: WARNING! Did not find any channels with TOT...")
      elif verb>=2:
        print(f"profile3DScanHisto: Found scanned channels in bins {iy_scan}")
    else: # scan all channels
      if verb>=2:
        print(f"profile3DScanHisto: Scan all {ny} channels...")
      iy_scan = range(1,ny+1)
    
    #fill a scan summary
    scan_summary = []
    for ix in range(1,nx+1): # loop over scan points

      nentries = int(hinfo.GetBinContent(ix,5)) # gain
      run = int(hinfo.GetBinContent(ix,1)/nentries) # run number
      ls = int(hinfo.GetBinContent(ix,2)/nentries) # lumi section
      gain = int(hinfo.GetBinContent(ix,4)/nentries) # gain
      dac = int(hinfo.GetBinContent(ix,3)/nentries) # injected charge
      lsb_dict = {0:0.122, 1:1.953, 2:2.075}
      inj_q = lsb_dict[gain]*dac

      #if verb>=2:
      print(f"profile3DScanHisto: Filling tree for scanpoint {nentries} iscan={ix}, run={run}, gain={gain} dac={dac}")

      for iy in iy_scan: # loop over injected channels
        
        ichan = int(hist3D0.GetYaxis().GetBinCenter(iy))

        if verb>=3:
          print(f"profile3DScanHisto: iscan={ix}, channel={ichan}")

        for hname, hist3D in hists3D.items():

          isadc = (hname[:3]=='adc')
                
          #create projection
          ztit = hist3D.GetZaxis().GetTitle()
          nz, zmin, zmax = hist3D.GetNbinsZ(), hist3D.GetZaxis().GetXmin(), hist3D.GetZaxis().GetXmax()
          zname  = f"{hname}_scan{ix}_chan{ichan}"
          ztitle = f"Scan {ix}, q_{{#lower[-0.25]{{inj}}}}={inj_q:3.1f}, channel={ichan};{ztit};Events"
          zhist  = ROOT.TH1F(zname,ztitle,nz,zmin,zmax)
          for iz in range(1,nz+1): # loop over ADC/TOT counts
            nevts = hist3D.GetBinContent(ix,iy,iz)
            if nevts>0:
              zhist.SetBinContent(iz,nevts)

          #get numbers from projection
          nevts = int(zhist.Integral()) # total number of events
          avgcounts = zhist.GetMean()
          rmscounts = zhist.GetRMS()
          spreadcounts = int(zhist.GetEntries()) # nonzero bins
          
          #fill summary and hists if there were events
          if nevts>0:
            
            scan_summary.append(
               [run, ls, ix, ichan, dac, gain, inj_q, isadc, avgcounts, rmscounts, spreadcounts]
            )

            hists2D[hname]['ave'].SetBinContent(ix,iy,avgcounts)
            hists2D[hname]['rms'].SetBinContent(ix,iy,rmscounts)
            hists2D[hname]['nevt'].SetBinContent(ix,iy,nevts)
            hists2D[hname]['nbin'].SetBinContent(ix,iy,spreadcounts)

          #save projection if needed
          if storehists:
            hdir.cd()
            zhist.SetDirectory(hdir)
            zhist.Write(zname)
            fillgraph(hname,ichan,inj_q,avgcounts,rmscounts)
          else: # clean memory to avoid�segfault from bad alloc ?
            #zhist.Delete()
            ROOT.gDirectory.Delete(zhist.GetName())

    #save as a pandas dataframe
    scan_summary = pd.DataFrame(
       scan_summary,
       columns=['run','ls','scanpoint','channel','dac','gain','inj_q','isadc','counts','counts_rms','counts_spread']
    )
    scan_summary.to_feather(outfname.replace('.root','.feather'))

    # write scan graphs
    if storehists:
      gdir.cd()
      for hname in graphs:
        for graph in graphs[hname].values():
          graph.Sort() # sort points by x values
          graph.Write(graph.GetName()) #,graph.kOverwrite)
    
    # write summary histograms
    sdir.cd()
    for hname in hists2D:
      for hist in hists2D[hname].values():
        hist.Write(hist.GetName(),hist.kOverwrite)
        
    # free mem, close files
    outfile.Close()
    infile.Close()
    
    return outfname
    

def profile2DHisto(url, hname):

    '''this method analyzes a 2D histogram and returns its momenta'''
    
    if not os.path.isfile(url) or not url.endswith('.root'):
        raise IOError(f'{url} is not a ROOT file')
    
    fIn=ROOT.TFile.Open(url)
    h=fIn.Get(hname)
    cor_values = {'X':[], 'Y_mean':[], 'Y_rms':[]}
    
    nx,xmin,xmax=h.GetNbinsX(),h.GetXaxis().GetXmin(),h.GetXaxis().GetXmax()
    ny,ymin,ymax=h.GetNbinsY(),h.GetYaxis().GetXmin(),h.GetYaxis().GetXmax()
    for xbin in range(nx):
        cor_values['X'].append( xbin )
        proj = h.ProjectionY('py',xbin+1,xbin+1)
        cor_values['Y_mean'].append( proj.GetMean() )
        cor_values['Y_rms'].append( proj.GetRMS() )
        proj.Delete()
        
    #close files
    fIn.Close()
    
    return cor_values
