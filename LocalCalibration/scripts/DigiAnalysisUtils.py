import ROOT
import os
import itertools
import json
import gzip
import re

def defineDigiDataFrameFromSpecs(specs, attachProgressBar=True):
    """defines the dataframe to be used for the analysis of DIGIs in NANOAOD"""

    #start RDataFrame from specifications
    rdf = ROOT.RDF.Experimental.FromSpec(specs)
    if attachProgressBar:
        ROOT.RDF.Experimental.AddProgressBar(rdf)
    
    #filter out data for the fed/readout sequence corresponding to a single module
    rdf = rdf.DefinePerSample("ix", 'rdfsampleinfo_.GetI("index")') \
             .DefinePerSample("target_module_fed", 'rdfsampleinfo_.GetI("fed")') \
             .DefinePerSample("target_module_seq", 'rdfsampleinfo_.GetI("seq")') \
             .Define('good_digiadc',  'HGCDigi_flags!=0xFFFF && HGCDigi_tctp<3') \
             .Define('good_digitot',  'HGCDigi_flags!=0xFFFF && HGCDigi_tctp==3') \
             .Define('good_digitoa',  'HGCDigi_flags!=0xFFFF && HGCDigi_toa>0') \
             .Define('target_module', 'HGCDigi_fedId==target_module_fed && HGCDigi_fedReadoutSeq==target_module_seq') \
             .Define('maskadc',       'good_digiadc & target_module') \
             .Define('masktot',       'good_digitot & target_module') \
             .Define('masktoa',       'good_digitoa & target_module') \
             .Define('chtypeadc',     'HGCDigi_chType[maskadc]') \
             .Define('adcm1',         'HGCDigi_adcm1[maskadc]') \
             .Define('adc',           'HGCDigi_adc[maskadc]') \
             .Define('modulecm',      'HGCDigi_cm[maskadc]') \
             .Define('cm2',           'commonMode(modulecm,2)') \
             .Define('cm4',           'commonMode(modulecm,4)') \
             .Define('cmall',         'commonMode(modulecm,-1)') \
             .Define('chadc',         'HGCDigi_channel[maskadc]') \
             .Define('nchadc',        'Sum(maskadc)')\
             .Define('nchtot',        'Sum(masktot)')\
             .Define('nchtoa',        'Sum(masktoa)')\
             .Define('tot',           'HGCDigi_tot[masktot]') \
             .Define('chtot',         'HGCDigi_channel[masktot]') \
             .Define('toa',           'HGCDigi_toa[masktoa]') \
             .Define('chtoa',         'HGCDigi_channel[masktoa]')

    #NOTE: We probably should define goodflags for toa and ADC-1 using the HGC_digiflags so that the histograms below are properly filled
    #NOTE: trigger type should be used for NZS
    
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
    rdf=defineDigiDataFrameFromSpecs(task_spec)
    if len(filter_cond)>0:
        rdf = rdf.Filter(filter_cond)

    #read #pts and #eErx from first task
    with open(task_spec) as json_data:
        samples = json.load(json_data)['samples']
    nerx = samples['data1']['metadata']['nerx']
    nch = nerx*37

    #run a mini scan to determine appropriate bounds
    minirdf = defineDigiDataFrameFromSpecs(task_spec)
    minirdf = minirdf.Range(1000)
    if len(filter_cond)>0:
        minirdf = minirdf.Filter(filter_cond)
        
    obslist = ['adc', 'cm2', 'cm4', 'cmall', 'toa', 'tot']
    obsbounds  = [minirdf.Min(x) for x in obslist]
    obsbounds += [minirdf.Max(x) for x in obslist]
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
        except:
            continue
        bindefs[obs]=(nobs,minobs,maxobs)
    print(f'Bins determined from sub-sample: {bindefs}')

    #declare histograms
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
    fillHistogramsAndSave(histolist = histolist, rfile = f'{outdir}/{module}.root')    
    return True


def scanHistoFiller(outdir, module, task_spec, filter_conds : dict):
    """
    a base method to fill histograms in a scan (each sub-task in task_spec) is treated as a scan point
    filter_conds is a dict used to define different sub-samples for which the histos will be filled
    """

    #read #pts and #eErx from first task
    with open(task_spec) as json_data:
        samples = json.load(json_data)['samples']
    npts = len(samples)
    nerx = samples['data1']['metadata']['nerx']
    nch = nerx*37

    #fill a histo with the scan info
    ptbinning=(npts,0.5,npts+0.5)
    infobinning = (2,0,2)
    scanInfoHist = ROOT.TH2F('scaninfo', 'Scan point;Parameters', *ptbinning, *infobinning)
    scanInfoHist.GetYaxis().SetBinLabel(1,'Run')
    scanInfoHist.GetYaxis().SetBinLabel(2,'LS')
    for ls,lsinfo in samples.items():
        idx = lsinfo["metadata"]["index"]
        run, ls = re.findall('.*/NANO_(\d+)_(\d+).root',lsinfo['files'][0])[0]
        scanInfoHist.SetBinContent(idx,1,int(run))
        scanInfoHist.SetBinContent(idx,2,int(ls))

    #declare histograms (per sample filtered)
    chbinning=(nch,-0.5,nch-0.5)    
    bin10b = (1024,-0.5,1023.5)
    bin12b = (4096,-0.5,4095.5)
    ROOT.gInterpreter.Declare('#include "interface/helpers.h"')
    rdf=defineDigiDataFrameFromSpecs(task_spec)
    graphlist=[]
    for k,filterval in filter_conds.items():
        filtered_rdf = rdf.Filter(filterval)
        graphlist = [            
            filtered_rdf.Histo3D((f"adc_{k}",  'Scan point;ADC;Channel', *ptbinning, *chbinning, *bin10b), "ix", "chadc", "adc"),
            filtered_rdf.Histo3D((f"nadc_{k}", 'Scan point;ADC;Channel', *ptbinning, *chbinning, *bin10b), "ix", "chadc", "nchadc"),
            filtered_rdf.Histo3D((f"tot_{k}",  'Scan point;TOT;Channel', *ptbinning, *chbinning, *bin12b), "ix", "chtot", "tot"),
            filtered_rdf.Histo3D((f"ntot_{k}", 'Scan point;TOT;Channel', *ptbinning, *chbinning, *bin12b), "ix", "chtot", "nchtot"),
            filtered_rdf.Histo3D((f"toa_{k}",  'Scan point;TOA;Channel', *ptbinning, *chbinning, *bin10b), "ix", "chtoa", "toa"),
            filtered_rdf.Histo3D((f"ntoa_{k}", 'Scan point;TOA;Channel', *ptbinning, *chbinning, *bin10b), "ix", "chtoa", "nchtoa"),
        ]

    #run and save
    ROOT.RDF.RunGraphs(graphlist)
    histolist = [obj.GetValue() for obj in graphlist] + [scanInfoHist]
    fillHistogramsAndSave(histolist = histolist, rfile = f'{outdir}/{module}.root')    
    return True

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

    '''this method analyzes a 3D histogram and summarizes its momenta assuming X is the profiling variable'''
    
    if not os.path.isfile(url) or not url.endswith('.root'):
        raise IOError(f'{url} is not a ROOT file')
    
    fIn=ROOT.TFile.Open(url)
    h=fIn.Get(hname)
    cor_values = {'X':[], 'Y_mean':[], 'Z_mean':[], 'YZ_rho':[], 'Y_rms':[], 'Z_rms':[]}
    
    nx,xmin,xmax=h.GetNbinsX(),h.GetXaxis().GetXmin(),h.GetXaxis().GetXmax()
    ny,ymin,ymax=h.GetNbinsY(),h.GetYaxis().GetXmin(),h.GetYaxis().GetXmax()
    nz,zmin,zmax=h.GetNbinsZ(),h.GetZaxis().GetXmin(),h.GetZaxis().GetXmax()
    h2=ROOT.TH2F(hname+'_proj','',ny,ymin,ymax,nz,zmin,zmax)
    for xbin in range(nx):
        cor_values['X'].append( xbin )
        h2.Reset('ICE')            
        for ybin,zbin in itertools.product(range(ny),range(nz)):
            h2.SetBinContent(ybin+1,zbin+1, h.GetBinContent(xbin+1,ybin+1,zbin+1) )
        cor_values['Y_mean'].append( h2.GetMean(1) )            
        cor_values['Y_rms'].append(h2.GetRMS(1))
        cor_values['Z_mean'].append( h2.GetMean(2) )
        cor_values['Z_rms'].append( h2.GetRMS(2) )
        cor_values['YZ_rho'].append( h2.GetCorrelationFactor() )

    #free mem, close files
    h2.Delete()
    fIn.Close()
    
    return cor_values


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
