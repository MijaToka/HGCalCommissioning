import sys
sys.path.append("./")
from HGCALCalibration import HGCALCalibration
import DigiAnalysisUtils as DAU
import HexPlotUtils as HPU
import numpy as np
import json
import ROOT

class HGCALPedestalsClosure(HGCALCalibration):

    def __init__(self):
        self.histofiller = self.histoFillerForClosure
        ROOT.gInterpreter.Declare('#include "interface/helpers.h"')
        super().__init__()

    @staticmethod
    def definePedestalsClosureRDF(task_spec):
        """defines the RDataFrame with the selections / variables needed for the closure of pedestals"""

        rdf = ROOT.RDF.Experimental.FromSpec(task_spec)
        ROOT.RDF.Experimental.AddProgressBar(rdf)
    
        #filter out data for the fed/readout sequence corresponding to a single module
        rdf = rdf.DefinePerSample("target_module_fed", 'rdfsampleinfo_.GetI("fed")') \
                .DefinePerSample("target_module_seq", 'rdfsampleinfo_.GetI("seq")') \
                .Define('good_rechit',   'HGCHit_flags==0 && HGCDigi_chType>=0') \
                .Define('target_module', 'HGCDigi_fedId==target_module_fed && HGCDigi_fedReadoutSeq==target_module_seq') \
                .Define('maskhit',       'good_rechit & target_module') \
                .Define('ch',            'HGCDigi_channel[maskhit]') \
                .Define('en',            'HGCHit_energy[maskhit]') \
                .Define('rocidx',        f'sumOverRoc(ch,en,0)') \
                .Define('nchperroc',     f'sumOverRoc(ch,en,1)') \
                .Define('dsen',          f'sumOverRoc(ch,en,2)') \
                .Define('asen',          f'sumOverRoc(ch,en,3)') \
                .Define('modulecm',      'HGCDigi_cm[maskhit]') \
                .Define('cm2',           'commonMode(modulecm,2)') \
                .Filter('HGCMetaData_trigType==4')

        return rdf
    
        
    @staticmethod
    def histoFillerForClosure(args):
        """defines the filling of the histograms for closure tests of the pedestal"""
        
        outdir, module, task_spec = args
        
        #read #rocs and #eErx from first task
        with open(task_spec) as json_data:
            samples = json.load(json_data)['samples']
            nerx = samples['data1']['metadata']['nerx']
            nch = nerx*37
            nrocs = int(nerx/2)
            
        #adjust binning from the extremes
        minirdf = HGCALPedestalsClosure.definePedestalsClosureRDF(task_spec)
        minirdf = minirdf.Range(1000)
        obslist = ['en', 'cm2', 'dsen', 'asen']
        obsbounds  = [minirdf.Min(x) for x in obslist]
        obsbounds += [minirdf.Max(x) for x in obslist]
        ROOT.RDF.RunGraphs(obsbounds)
        bindefs={
            'ch' : (nch,-0.5,nch-0.5),
            'rocs' : (nrocs,-0.5,nrocs-0.5),
            'rocch' : (75,-0.5,74.5)
        }
        for i,obs in enumerate(obslist):
            minobs = int(obsbounds[i].GetValue()) - 0.5
            maxobs = int(obsbounds[i+len(obslist)].GetValue()) + 0.5
            nobs = int(maxobs - minobs)            
            bindefs[obs]=(nobs,minobs,maxobs)
        print(f'Bins determined from sub-sample: {bindefs}')
        
        #fill the histograms with full statistics
        rdf = HGCALPedestalsClosure.definePedestalsClosureRDF(task_spec)        
        profiles = [
            rdf.Histo3D(("envscm",    ';Channel;RecHit energy;CM2',*bindefs['ch'],   *bindefs['cm2'],   *bindefs['en']), "ch", "cm2", "en"),
            rdf.Histo2D(("nchperroc", ';ROC;#channels used',       *bindefs['rocs'], *bindefs['rocch']), "rocidx", "nchperroc"),
            rdf.Histo2D(("dsen",      ';ROC;DS energy',            *bindefs['rocs'], *bindefs['dsen']),  "rocidx", "dsen"),
            rdf.Histo2D(("asen",      ';ROC;AS energy',            *bindefs['rocs'], *bindefs['asen']),  "rocidx", "asen")
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

    @staticmethod
    def analyze(args):
        """profiles the Channel vs ADC vs CM histogram to find pedestals to use"""

        typecode, url, cmdargs = args

        #summary of pedestals and noise
        results = DAU.profile3DHisto(url,'envscm')

        cm_rms = np.array(results['Y_rms'])
        en_loc = np.array(results['Z_mean'])
        en_rms = np.array(results['Z_rms'])
        rho = np.array(results['YZ_rho'])
        noslope = np.zeros_like(rho)

        cor_values = {
            'Typecode' : typecode.replace('_','-'),
            'En_ped'   : en_loc.tolist(),
            'En_rms'   : en_rms.tolist(),
            'CM_slope' : np.where(cm_rms>1e-3, rho*en_rms/cm_rms, noslope).tolist()
        }

        #fraction of coherent noise per roc
        nch = np.array(DAU.profile2DHisto(url,'nchperroc')['Y_mean'])
        dsum_rms = np.array(DAU.profile2DHisto(url,'dsen')['Y_rms'])
        asum_rms = np.array(DAU.profile2DHisto(url,'asen')['Y_rms'])
        inc_noise = asum_rms / np.sqrt(nch)
        coh_noise = np.sqrt(dsum_rms**2 - asum_rms**2) / nch
        cnf = coh_noise/inc_noise
        cor_values['Inc_noise'] = np.ravel( [ np.ones(74)*x for x in inc_noise] ).tolist() 
        cor_values['Coh_noise'] = np.ravel( [ np.ones(74)*x for x in coh_noise] ).tolist() 
        cor_values['CNF'] = np.ravel( [ np.ones(74)*x for x in cnf ] ).tolist()
        
        return cor_values


    def createCorrectionsFile(self, results):
        
        """ final tweaks of the analysis results to export as a json file for CMSSW """

        jsonurl = f'{self.output}/pedestalsclosure.json'
        correctors={}
        for r in results:
            typecode = r.pop('Typecode')
            correctors[typecode]=r
        with open(jsonurl,'w') as outfile:
            json.dump(correctors,outfile,sort_keys=False,indent=2)

        rooturl = f'{self.output}/pedestalsclosure_hexplots.root'
        HPU.createCalibHexPlotSummary(jsonurl,rooturl)
            
        return jsonurl


if __name__ == '__main__':

    pedestalclosure = HGCALPedestalsClosure()
