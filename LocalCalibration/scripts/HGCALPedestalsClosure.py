import sys
sys.path.append("./")
from HGCALCalibration import HGCALCalibration
import DigiAnalysisUtils as DAU
import HexPlotUtils as HPU
import numpy as np
import ROOT
try:
    from HGCalCommissioning.LocalCalibration.JSONEncoder import getCalibTemplate
except ImportError:
    sys.path.append('./python/')
    from JSONEncoder import getCalibTemplate

class HGCALPedestalsClosure(HGCALCalibration):

    def __init__(self):
        self.histofiller = self.histoFillerForClosure
        ROOT.gInterpreter.Declare('#include "interface/helpers.h"')
        super().__init__()

    @staticmethod
    def histoFillerForClosure(args):
        """defines the filling of the histograms for closure tests of the pedestal"""
        
        outdir, module, task_spec = args
    
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
                .Define('rocidx',        f'sumOverRoc(ch,en,0)') \
                .Define('nchperroc',     f'sumOverRoc(ch,en,1)') \
                .Define('dsen',          f'sumOverRoc(ch,en,2)') \
                .Define('asen',          f'sumOverRoc(ch,en,3)') \
                .Define('cm',            'HGCDigi_cm[maskhit]')
        #NOTE: Calibration channels should be re-enabled for closure in ROCv3b!!!

        profiles=[]
        nch=222 #NOTE: fix me, should be in the task_spec depending on the module
        nrocs=int(nch/74)
        chbinning=(nch,-0.5,nch-0.5)
        encmbinning=(100,-10,10,200,149.5,349.5)
        rocchbinning=(nrocs,-0.5,nrocs-0.5,75,-0.5,74.5)
        rocensumbinning=(nrocs,-0.5,nrocs-0.5,500,-250.5,249.5)
        profiles += [
            rdf.Histo3D(("envscm",    ';Channel;RecHit energy;CM', *chbinning, *encmbinning), "ch", "en", "cm"),
            rdf.Histo2D(("nchperroc", ';ROC;#channels used',       *rocchbinning),            "rocidx", "nchperroc"),
            rdf.Histo2D(("dsen",      ';ROC;DS energy',            *rocensumbinning),         "rocidx", "dsen"),
            rdf.Histo2D(("asen",      ';ROC;AS energy',            *rocensumbinning),         "rocidx", "asen")
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
        parser.set_defaults(output='calibrations_closure')

    def buildScanParametersDict(self,file_list,module_list):
        """return lists of empty dicts"""
        nfiles = len(file_list)
        scanparams={}
        for m in module_list:
            scanparams[m] = [
                {} for i in range(nfiles)
            ]
        return scanparams

    @staticmethod
    def analyze(args):
        """profiles the Channel vs ADC vs CM histogram to find pedestals to use"""

        typecode, url, cmdargs = args

        #summary of pedestals and noise
        results = DAU.profile3DHisto(url,'envscm')
        cor_values = {
            'Typecode' : typecode.replace('_','-'),
            'En_ped' : results['Y_mean'],            
            'Noise' : results['Y_rms'],
            'R' : results['YZ_rho'],
        }

        #fraction of coherent noise per roc
        nch = np.array(DAU.profile2DHisto(url,'nchperroc')['Y_mean'])
        dsum_rms = np.array(DAU.profile2DHisto(url,'dsen')['Y_rms'])
        asum_rms = np.array(DAU.profile2DHisto(url,'asen')['Y_rms'])

        inc_noise = asum_rms / np.sqrt(nch)
        coh_noise = np.sqrt(dsum_rms**2 - asum_rms**2) / nch
        cnf = coh_noise/inc_noise
        cor_values['CNF'] = np.ravel( [ np.ones(74)*x for x in cnf ] ).tolist()
        
        return cor_values


    def createCorrectionsFile(self, results):
        
        """ final tweaks of the analysis results to export as a json file for CMSSW """

        jsonurl = f'{self.output}/pedestalsclosure.json'
        correctors={}
        for r in results:
            typecode = r.pop('Typecode')
            correctors[typecode]=r
        DAU.saveAsJson(jsonurl, correctors, compress=False)

        rooturl = f'{self.output}/pedestalsclosure_hexplots.root'
        HPU.createCalibHexPlotSummary(jsonurl,rooturl)
            
        return jsonurl


if __name__ == '__main__':

    pedestalclosure = HGCALPedestalsClosure()
