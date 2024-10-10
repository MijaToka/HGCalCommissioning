import sys
sys.path.append("./")
from HGCALCalibration import HGCALCalibration
import DigiAnalysisUtils as DAU
import HexPlotUtils as HPU
import numpy as np
from scipy import stats
import itertools
from tqdm import tqdm
import ROOT

try:
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from JSONEncoder import *

class HGCALMIPScaleAnalysis(HGCALCalibration):

    """
    MIP scale analysis is a class used to fill histograms which can be useful to extract the 
    signal expected for a minimum ionizing particle. It assumes that the NANO to be analyzed
    contains the calibrated hits with at least the pedestal subtracted and the common mode correction applied
    The histograms are filled as function of the channel and trigger phase
    After selecting the optimal fitting range (best trigger phase) for each channel the events are fit
    with a two component model using
    - gaussian to model noise
    - landau convoluted with gaussian to model the MIP signal
    The fitted Landau MPV is then scaled to the energy of a MIP using the Bethe-Bloch curve
    """

    def __init__(self):
        self.histofiller = self.mipHistoFiller
        ROOT.gROOT.SetBatch(True)
        ROOT.gInterpreter.Declare('#include "interface/fit_models.h"')
        ROOT.shushRooFit()
        super().__init__()

    @staticmethod
    def mipHistoFiller(args):
        """costumize the histo filler for the MIP analysis"""

        outdir, module, task_spec, cmdargs = args
    
        #start RDataFrame from specifications
        rdf = ROOT.RDF.Experimental.FromSpec(task_spec)
        ROOT.RDF.Experimental.AddProgressBar(rdf)
    
        #filter out data for the fed/readout sequence corresponding to a single module
        rdf = rdf.DefinePerSample("target_module_fed", 'rdfsampleinfo_.GetI("fed")') \
                .DefinePerSample("target_module_seq", 'rdfsampleinfo_.GetI("seq")') \
                .Define('good_rechit',   'HGCHit_flags==0 && HGCDigi_chType==1') \
                .Define('target_module', 'HGCDigi_fedId==target_module_fed && HGCDigi_fedReadoutSeq==target_module_seq') \
                .Define('maskhit',       'good_rechit & target_module') \
                .Define('ch',            'HGCDigi_channel[maskhit]') \
                .Define('en',            'HGCHit_energy[maskhit]') \
                .Define('deltaADC',      'HGCDigi_adc[maskhit]-HGCDigi_adcm1[maskhit]') \
                .Filter('HGCMetaData_trigType==1') \
                .Filter('HGCMetaData_trigSubType==2') 
        


        profiles=[]
        nch=222 #NOTE: fix me, should be in the task_spec depending on the module
        enbinning=(nch,-0.5,nch-0.5,200,-0.5,199.5,100,-10.25,39.75) #0.5 binning in RecHit energy
        adcbinning=(nch,-0.5,nch-0.5,200,-0.5,199.5,50,-10.5,39.5)
        profiles += [
            rdf.Histo3D(("en",       ';Channel;Trig phase;RecHit energy', *enbinning),  "ch", "HGCMetaData_trigTime", "en"),
            rdf.Histo3D(("deltaADC", ';Channel;Trig phase;#Delta ADC',    *adcbinning), "ch", "HGCMetaData_trigTime", "deltaADC")
        ]    
        ROOT.RDF.RunGraphs(profiles)
    
        #write histograms to file
        rfile=f'{outdir}/{module}.root'
        fOut=ROOT.TFile.Open(rfile,'RECREATE')
        fOut.cd()
        for p in profiles:
            obj=p.GetValue()
            obj.SetDirectory(fOut)
            obj.Write()
        fOut.Close()
        print(f'Histograms available in {rfile}')
    
        return True

    def addCommandLineOptions(self,parser):
        """add specific command line options for pedestals"""
        parser.add_argument("-e", "--energy",
                            help='beam energy (if <0, use stored in NANO)=%(default)s',
                            default=-1, type=int)
        parser.add_argument("--prescanCOI",
                            action='store_true',
                            help='prescan potential channel of interest from <ADC-ADC_{-1}>')
        parser.add_argument("--trigTimeRan",
                            default='-1,-1', type=str,
                            help='Force analysis in this trigtime range default=%(default)s')
        parser.add_argument("--rebinForFit",
                            default='-1', type=int,
                            help='Rebin for fit=%(default)s')
        parser.add_argument("--doHexPlots",
                            action='store_true',
                            help='save hexplots for the pedestals')

    @staticmethod
    def analyze(args):
        """steers the fitting of the mip peaks and the collection of results"""
        typecode, url, cmdargs = args

        #open the ROOT file and read the histograms of interest
        fIn=ROOT.TFile.Open(url,'READ')
        #deltaADC=fIn.Get('deltaADC')
        en=fIn.Get('en')

        #determine trigger time range of the analysis
        ttimeran = [float(x) for x in cmdargs.trigTimeRan.split(',')]
        moderan, coi_trigtime = HGCALMIPScaleAnalysis.findBestTrigTimePerChannel(en)
        if ttimeran[0]<0 : ttimeran[0]=moderan[0]
        if ttimeran[1]<0 : ttimeran[1]=moderan[1]

        #run mip fits
        mipfitreport = HGCALMIPScaleAnalysis.runMIPFits(en,*ttimeran,cmdargs.rebinForFit)
        mipfitreport['Typecode'] = typecode

        #save histograms to ROOT file
        rooturl = f'{cmdargs.output}/mipfits_{typecode}.root'
        fOut=ROOT.TFile.Open(rooturl,'RECREATE')
        for h in mipfitreport['Histos']:
            h.Write()
        fOut.Close()
        
        #all done
        fIn.Close()

        
        return mipfitreport

    def createCorrectionsFile(self, results):        
        """ final tweaks of the analysis results to export as a json file for CMSSW """
    
        correctors={}
        for r in results:
            typecode = r.pop('Typecode')
            histos = r.pop('Histos')
            correctors[typecode]=r
        jsonurl = f'{self.cmdargs.output}/mipfits.json'
        saveAsJson(jsonurl, correctors)

        if self.cmdargs.doHexPlots:
            rooturl = f'{self.cmdargs.output}/mipfits_hexplots.root'
            HPU.createCalibHexPlotSummary(jsonurl,rooturl)
            
        return jsonurl

    @staticmethod
    def findBestTrigTimePerChannel(h,krms=2, maxDrop=0.95):
        """analyzes a 3D histogram of channel vs trig time vs observable
        for each channel determines the RMS from the inclusive distribution of the observable
        a threshold is then defined loc + krms*RMS
        the algorithm then profiles the observable (for observable > threshold) 
        as function of trigtime and finds it's maximum
        the proposed trig time range (by which it drops at most by maxDrop) is returned per channel
        """
        coi_trigtime={}
        nx,xmin,xmax=h.GetNbinsX(),h.GetXaxis().GetXmin(),h.GetXaxis().GetXmax()
        ny,ymin,ymax=h.GetNbinsY(),h.GetYaxis().GetXmin(),h.GetYaxis().GetXmax()
        nz,zmin,zmax=h.GetNbinsZ(),h.GetZaxis().GetXmin(),h.GetZaxis().GetXmax()
        hyz=ROOT.TH2F('pyz','',ny,ymin,ymax,nz,zmin,zmax)
        for xbin in range(nx):
        
            hyz.Reset('ICE')            
            for ybin,zbin in itertools.product(range(ny),range(nz)):
                hyz.SetBinContent(ybin+1,zbin+1, h.GetBinContent(xbin+1,ybin+1,zbin+1) )

            #determine a noise threshold from the inclusive distribution of the observable
            loc = hyz.GetMean(2)
            rms = hyz.GetRMS(2)
            if rms<1e-6:
                coi_trigtime[xbin]=None
                continue

            #now profile the observable for values above the noise
            meanz=[]
            for ybin in range(ny):

                #project at fixed trig time
                hz = hyz.ProjectionY('pz',ybin+1,ybin+1)
            
                #bin to start integrating from
                zbinmin = hz.FindBin(loc+krms*rms)+1

                #if bin not valid, set mean to 0 and continue
                if zbinmin==0 or zbinmin>nz:
                    meanz.append(0)
                    hz.Delete()
                    continue

                #compute the truncated mean
                sumw, sumzw = 0., 0.
                for zbin in range(zbinmin,nz+1):
                    z = hz.GetXaxis().GetBinCenter(zbin)
                    w = hz.GetBinContent(zbin)
                    sumw += w
                    sumzw += z*w
                meanz.append( sumzw/sumw if sumw>0. else 0. )
                hz.Delete()
        
            #determine the acceptable trigtime window
            meanz = np.array(meanz)        
            max_meanz = meanz.max()
            if max_meanz>0:
                accept =  np.argwhere(meanz/max_meanz > maxDrop).ravel().tolist()
                coi_trigtime[xbin] = (accept[0],accept[-1])
            else: 
                coi_trigtime[xbin] = None

        hyz.Delete()

        #return the mode of the range limits found
        minran = stats.mode( [ran[0] for _,ran in coi_trigtime.items() if not ran is None], nan_policy='raise', keepdims=False)
        maxran = stats.mode( [ran[1] for _,ran in coi_trigtime.items() if not ran is None], nan_policy='raise', keepdims=False)
        moderan = (minran.mode,maxran.mode)
        return moderan, coi_trigtime

    @staticmethod
    def runMIPFits(h,minttime,maxttime,rebinFact : int):
        """analyzes a 3D histogram of channel vs trig time vs energy
        and projects the energy spectrum in the slide of (minttime,maxttime) for each channel
        the energy spectrum is fit with a physics model
        the histogram projected, the model parameters and quality of the fit are returned
        """

        mipfitsreport = {
            'Histos':[],
            'Chi2':[],
            'NDOF':[],
            'Status':[],
        }

        #init the workspace for the fit
        nz,zmin,zmax=h.GetNbinsZ(),h.GetZaxis().GetXmin(),h.GetZaxis().GetXmax()
        w = ROOT.defineMIPFitWorkspace(zmin,zmax);
        x = w.var('x')        
        x.setBins(nz)
        if rebinFact>1: x.setBins(int(nz/rebinFact))
        model = w.pdf('model')

        #loop over each channel and run the fit
        nx,xmin,xmax=h.GetNbinsX(),h.GetXaxis().GetXmin(),h.GetXaxis().GetXmax()
        ybinmin,ybinmax=h.GetYaxis().FindBin(minttime),h.GetYaxis().FindBin(maxttime)
        for xbin in tqdm(range(nx)):

            #prepare data
            hpz=h.ProjectionZ(f"en_{xbin}",xbin+1,xbin+1,ybinmin,ybinmax)
            if rebinFact>1:
                hpz=hpz.Rebin(rebinFact)

            #run fit
            fr = ROOT.runMIPFit(hpz, model, x)

            #append results of the fit
            for i,pname in enumerate(fr.parNames):
                k=str(pname)
                if not k in mipfitsreport:
                    mipfitsreport[k] = ["None"]*nx
                    mipfitsreport[k+'Unc'] = ["None"]*nx
                mipfitsreport[k][xbin] = fr.parVals[i]
                mipfitsreport[k+'Unc'][xbin] = fr.parUncs[i]
            mipfitsreport['Chi2'].append( fr.chi2 )
            mipfitsreport['NDOF'].append( fr.ndof )
            mipfitsreport['Status'].append( fr.status )
            cnv = fr.fitPlot
            cnv.SetName(f'ch{xbin}')
            cnv.SetTitle(f'Channel {xbin} {minttime:3.0f}<t_{{trig}}<{maxttime:3.0f}')
            mipfitsreport['Histos'].append(cnv)

        return mipfitsreport


if __name__ == '__main__':
    
    mipscale = HGCALMIPScaleAnalysis()
    
