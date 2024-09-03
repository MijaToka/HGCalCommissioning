import ROOT
import os
import itertools
import json
import gzip
try:
    from HGCalCommissioning.LocalCalibration.JSONEncoder import CompactJSONEncoder
except ImportError:
    sys.path.append('./python/')
    from JSONEncoder import CompactJSONEncoder

_baseHistoBinDefs = {
    'adcvscm':(200,49.5,249.5,200,149.5,349.5),
    'adc':(1024,-0.5,1023.5),
    'adcm1':(1024,-0.5,1023.5),
    'toa':(1024,-0.5,1023.5),
    'tot':(4096,-0.5,4095.5),
    'adcm1scan':(1024,-0.5,1023.5),
    'adcscan':(1024,-0.5,1023.5),
    'toascan':(1024,-0.5,1023.5),
    'totscan':(4096,-0.5,4095.5),
}
    
def baseHistoFiller(args, binDefs : dict =_baseHistoBinDefs):
    """
    a base method to fill histograms which are common in most of the runs dedicated to extract baseline constants for the offline and online
    the method signature is such that it can be dispatched using a pool
    args is a tuple containing output directory, the module to select and the specification of the tasks for RDataFrame
    binDefs is a dict containing the bin definitions
    NOTE: as the histograms are heavy a single thread is used otherwise mem explodes with copies...
    an alternative would be to use boost histograms and Josh Bendavid's narf
    """

    outdir, module, task_spec = args
    
    #start RDataFrame from specifications
    rdf = ROOT.RDF.Experimental.FromSpec(task_spec)
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
             .Redefine('adc',         '(chtypeadc!=0)*adc+(chtypeadc==0)*adcm1') \
             .Define('cm',            'HGCDigi_cm[maskadc]') \
             .Define('chadc',         'HGCDigi_channel[maskadc]') \
             .Define('tot',           'HGCDigi_tot[masktot]') \
             .Define('chtot',         'HGCDigi_channel[masktot]') \
             .Define('toa',           'HGCDigi_toa[masktoa]') \
             .Define('chtoa',         'HGCDigi_channel[masktoa]')
    #NOTE: Calibration channels should not need the ADC assigment from ADC-1 in ROCv3b!!!
    #NOTE: We probably should define goodflags for toa and ADC-1 using the HGC_digiflags so that the histograms
    #below are properly filled
    
    profiles=[]
    nch=222 #NOTE: fix me, should be in the task_spec depending on the module
    chbinning=(nch,-0.5,nch-0.5)
    npts=1  #NOTE: fix me, should be read from the task_spec depending on the scan type
    scanbinning=(npts,-0.5, npts-0.50)
    if npts>1:
        profiles += [
            rdf.Histo3D(("adcm1scan", 'Scan point;ADC(BX-1);Channel', *ptbinning, *chbinning, *binDefs['adcm1scan']), "ix", "chadc", "adcm1"),
            rdf.Histo3D(("adcscan",   'Scan point;ADC;Channel',       *ptbinning, *chbinning, *binDefs['adcscan']),   "ix", "chadc", "adc"),
            rdf.Histo3D(("totscan",   'Scan point;TOT;Channel',       *ptbinning, *chbinning, *binDefs['totscan']),   "ix", "chtot", "tot"),
            rdf.Histo3D(("toascan",   'Scan point;TOA;Channel',       *ptbinning, *chbinning, *binDefs['toascan']),   "ix", "chtoa", "toa"),
        ]
    else:
        profiles += [
            rdf.Histo3D(("adcvscm", ';Channel;ADC;CM',    *chbinning, *binDefs['adcvscm']), "chadc", "adc", "cm"),
            rdf.Histo2D(("adcm1",   ';ADC(BX-1);Channel', *chbinning, *binDefs['adcm1']),   "chadc", "adcm1"),
            rdf.Histo2D(("adc",     ';ADC;Channel',       *chbinning, *binDefs['adc']),     "chadc", "adc"),
            rdf.Histo2D(("tot",     ';TOT;Channel',       *chbinning, *binDefs['tot']),     "chtot", "tot"),
            rdf.Histo2D(("toa",     ';TOA;Channel',       *chbinning, *binDefs['toa']),     "chtoa", "toa"),
        ]    
    ROOT.RDF.RunGraphs(profiles)
    
    #write histograms to file
    rfile=f'{outdir}/{module}.root'
    fOut=ROOT.TFile.Open(rfile,'RECREATE')
    fOut.cd()
    #NOTE: fixme this is disabled for the moment as we need to adapt with some sort of scan
    #parHisto.SetDirectory(fOut)
    #parHisto.Write()
    #channelHisto.SetDirectory(fOut)
    #channelHisto.Write()
    for p in profiles:
        obj=p.GetValue()
        obj.SetDirectory(fOut)
        obj.Write()
    fOut.Close()
    print(f'Histograms available in {rfile}')
    
    return True


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


def saveAsJson(url : str, results : dict, compress=False):
    """takes care of saving to a json file"""
    
    if compress:
        json_str = json.dumps(results,cls=CompactJSONEncoder) + "\n"
        json_bytes = json_str.encode('utf-8')
        with gzip.open(url, 'w') as outfile:
            outfile.write(json_bytes)
    else:
        with open(url,'w') as outfile:
            json.dump(results,outfile,cls=CompactJSONEncoder,sort_keys=False,indent=2)
